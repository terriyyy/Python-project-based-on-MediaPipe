# games/parkour_game/src/parkour_renderer.py
import pygame
import cv2
import numpy as np
import time
import math
import random

class ParkourRenderer:
    def __init__(self, w, h):
        pygame.init()
        self.w, self.h = w, h
        self.surface = pygame.Surface((w, h))
        
        # 视觉状态
        self.visual_lane = 0.0
        self.grid_offset_y = 0.0
        
        # 配色
        self.sky_color_top = (10, 0, 30)      
        self.sky_color_bot = (60, 20, 80)     
        self.grid_color = (255, 0, 128)       
        self.sun_color = (255, 200, 0)        
        
        # 预生成远景
        self.city_skyline = []
        for i in range(0, w, 40):
            h_building = random.randint(20, 100)
            self.city_skyline.append((i, h_building))

        # 字体
        try:
            self.font_xl = pygame.font.Font(None, 100)
            self.font_m = pygame.font.Font(None, 40)
            self.font_s = pygame.font.Font(None, 30)
        except:
            self.font_xl = pygame.font.SysFont("arial", 80)
            self.font_m = pygame.font.SysFont("arial", 30)
            self.font_s = pygame.font.SysFont("arial", 20)

    def draw(self, core):
        # 1. 背景
        self._draw_vaporwave_bg(core)
        
        # 2. 场景物体 (核心修复：正确的遮挡关系)
        self._draw_world_3d(core)
        
        # 3. UI
        if core.state == "SELECT_TIME":
            self._draw_menu()
        elif core.state in ["GAME_OVER", "VICTORY"]:
            self._draw_game_over(core)
        else:
            self._draw_hud(core)
            
    def get_image(self):
        view = pygame.surfarray.array3d(self.surface)
        return cv2.cvtColor(view.transpose([1, 0, 2]), cv2.COLOR_RGB2BGR)

    def _draw_vaporwave_bg(self, core):
        # 天空
        horizon_y = int(self.h * 0.5)
        steps = 20
        for i in range(steps):
            ratio = i / steps
            c = (
                self.sky_color_top[0] * (1-ratio) + self.sky_color_bot[0] * ratio,
                self.sky_color_top[1] * (1-ratio) + self.sky_color_bot[1] * ratio,
                self.sky_color_top[2] * (1-ratio) + self.sky_color_bot[2] * ratio
            )
            h_step = horizon_y // steps
            pygame.draw.rect(self.surface, c, (0, i*h_step, self.w, h_step + 1))
            
        # 太阳
        t = time.time()
        pulse = (math.sin(t * 2) + 1) * 0.5 
        sun_radius = int(80 + pulse * 5)
        sun_y = horizon_y - 50 + int(math.sin(t) * 10)
        sun_center = (self.w // 2, sun_y)
        
        glow = pygame.Surface((sun_radius*4, sun_radius*4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 100, 0, 50), (sun_radius*2, sun_radius*2), sun_radius + 20)
        self.surface.blit(glow, (sun_center[0]-sun_radius*2, sun_center[1]-sun_radius*2), special_flags=pygame.BLEND_ADD)
        pygame.draw.circle(self.surface, self.sun_color, sun_center, sun_radius)
        
        for i in range(6):
            y = sun_center[1] + 20 + i * 12
            h_strip = 4 + i
            pygame.draw.rect(self.surface, self.sky_color_bot, (sun_center[0]-100, y, 200, h_strip))

        # 城市
        for bx, bh in self.city_skyline:
            pygame.draw.rect(self.surface, (0, 0, 20), (bx, horizon_y - bh, 42, bh))

        # 地面
        pygame.draw.rect(self.surface, (15, 0, 30), (0, horizon_y, self.w, self.h - horizon_y))
        
        # 车道线
        cx = self.w // 2
        lane_w_bottom = self.w // 3  
        for lane_border in [-0.5, 0.5]: 
            p1 = (cx, horizon_y) 
            x_bottom = cx + lane_border * lane_w_bottom * 4 
            p2 = (x_bottom, self.h)
            pygame.draw.line(self.surface, (0, 255, 255), p1, p2, 3)

        # 网格
        move_speed = 0.5 * core.current_speed_factor * 100
        self.grid_offset_y = (self.grid_offset_y + move_speed) % 100
        for i in range(20):
            z = (i * 100 + self.grid_offset_y) / 2000.0 
            if z > 1: continue
            line_y = horizon_y + (self.h - horizon_y) * (z ** 2)
            fade_color = (int(self.grid_color[0]*0.5), int(self.grid_color[1]*0.5), int(self.grid_color[2]*0.5))
            pygame.draw.line(self.surface, fade_color, (0, int(line_y)), (self.w, int(line_y)), 1)


    def _draw_world_3d(self, core):
        cx = self.w // 2
        horizon_y = int(self.h * 0.5)
        
        self.visual_lane += (core.lane - self.visual_lane) * 0.2
        
        def get_screen_pos(lane_idx, z):
            scale = max(0.01, z)
            lane_w_near = self.w // 3
            screen_x = cx + (lane_idx * lane_w_near) * scale
            screen_y = horizon_y + (self.h - horizon_y) * scale
            return int(screen_x), int(screen_y), scale

        # 【核心修复】分层渲染：将障碍物分为“身后”和“身前”两组
        PLAYER_Z = 0.9 # 玩家固定的 Z 深度
        
        all_obs = sorted([o for o in core.obstacles if o.z > 0.05], key=lambda x: x.z)
        
        # 1. 绘制身后的障碍物 (远处的，或者还没追上玩家的)
        # 注意：在我们的坐标系里，Z 越大越近 (0=远, 1=近)。
        # 所以 "Behind Player" 其实是 Z < PLAYER_Z 的物体 (还没到玩家)
        # "In Front of Player" (遮挡玩家) 其实是 Z > PLAYER_Z 的物体 (已经跑到玩家脸上了)
        
        bg_obstacles = [o for o in all_obs if o.z <= PLAYER_Z]
        fg_obstacles = [o for o in all_obs if o.z > PLAYER_Z]

        # 第一层：背景障碍物
        for obs in bg_obstacles:
            self._draw_single_obstacle(obs, get_screen_pos)

        # 第二层：玩家 (被夹在中间)
        self._draw_player_enhanced(core, get_screen_pos)

        # 第三层：前景障碍物 (会挡住玩家)
        for obs in fg_obstacles:
            if obs.z > 1.3: continue # 太近就剔除，不然会穿模
            self._draw_single_obstacle(obs, get_screen_pos)

    def _draw_single_obstacle(self, obs, get_screen_pos):
        sx, sy, scale = get_screen_pos(obs.lane, obs.z)
        w_base = 200 * scale
        
        if obs.type == "JUMP": 
            h_base = 80 * scale
            rect = pygame.Rect(sx - w_base//2, sy - h_base, w_base, h_base)
            pygame.draw.rect(self.surface, (0, 200, 0), rect) 
            pygame.draw.rect(self.surface, (0, 255, 0), rect, 3) 
            pygame.draw.line(self.surface, (100, 255, 100), rect.topleft, rect.topright, 5)
            self._draw_text_on_obs("JUMP", sx, sy - h_base, scale, (0, 255, 0))

        elif obs.type == "HURDLE": 
            h_base = 120 * scale
            leg_w = 20 * scale
            bar_h = 30 * scale
            rect_top = pygame.Rect(sx - w_base//2, sy - h_base, w_base, bar_h)
            rect_l = pygame.Rect(sx - w_base//2, sy - h_base, leg_w, h_base)
            rect_r = pygame.Rect(sx + w_base//2 - leg_w, sy - h_base, leg_w, h_base)
            color = (255, 200, 0)
            pygame.draw.rect(self.surface, color, rect_top)
            pygame.draw.rect(self.surface, color, rect_l)
            pygame.draw.rect(self.surface, color, rect_r)
            pygame.draw.rect(self.surface, (255, 255, 200), rect_top, 2)
            self._draw_text_on_obs("ANY", sx, sy - h_base, scale, color)

        elif obs.type == "TUNNEL": 
            color = (0, 150, 255) 
            h_base = 250 * scale
            pillar_w = 40 * scale
            top_h = 140 * scale 
            rect_top = pygame.Rect(sx - w_base//2, sy - h_base, w_base, top_h)
            rect_l = pygame.Rect(sx - w_base//2, sy - h_base, pillar_w, h_base)
            rect_r = pygame.Rect(sx + w_base//2 - pillar_w, sy - h_base, pillar_w, h_base)
            pygame.draw.rect(self.surface, color, rect_top)
            pygame.draw.rect(self.surface, color, rect_l)
            pygame.draw.rect(self.surface, color, rect_r)
            pygame.draw.line(self.surface, (0, 255, 255), (sx-w_base//2, sy-h_base+top_h-10), (sx+w_base//2, sy-h_base+top_h-10), 4)
            self._draw_text_on_obs("DUCK", sx, sy - h_base, scale, (0, 255, 255))

        elif obs.type == "FULL": 
            h_base = 250 * scale
            rect = pygame.Rect(sx - w_base//2, sy - h_base, w_base, h_base)
            s = pygame.Surface((int(w_base), int(h_base)))
            s.set_alpha(180)
            s.fill((200, 0, 0))
            self.surface.blit(s, rect)
            pygame.draw.rect(self.surface, (255, 0, 0), rect, 4)
            pygame.draw.line(self.surface, (255, 0, 0), rect.topleft, rect.bottomright, 5)
            pygame.draw.line(self.surface, (255, 0, 0), rect.topright, rect.bottomleft, 5)
            self._draw_text_on_obs("WALL", sx, sy - h_base, scale, (255, 0, 0))

    def _draw_player_enhanced(self, core, get_screen_pos):
        px, py, p_scale = get_screen_pos(self.visual_lane, 0.9)
        
        # 身体基础尺寸
        p_w = 60
        p_h = 100
        head_r = 20
        
        offset_y = 0
        bob = 0
        t = time.time()
        
        # --- 腿部动画参数 ---
        leg_offset = 0 
        
        # 1. 状态计算
        if core.action_state == "RUN":
            # 跑步动画：身体轻微上下，腿部前后摆动
            bob = math.sin(t * 18) * 4
            leg_phase = math.sin(t * 18) # -1 ~ 1
            leg_offset = leg_phase * 15
            
        elif core.action_state == "JUMP":
            dt = time.time() - core.action_timer
            progress = dt / core.jump_duration
            if 0 <= progress <= 1:
                # 抛物线高度
                offset_y = -180 * math.sin(progress * math.pi)
                # 跳跃时身体略微前倾
                bob = -5 

        elif core.action_state == "SLIDE":
            p_w = 110 # 变宽
            p_h = 45  # 变矮
            offset_y = 0 # 贴地
            bob = 0
        
        # 身体矩形计算
        body_y_top = py - p_h + offset_y + bob
        body_rect = pygame.Rect(px - p_w//2, body_y_top, p_w, p_h)
        
        # 2. 绘制腿部 (仅在跑步时明显)
        if core.action_state == "RUN":
            # 左腿
            l_leg_h = 40
            pygame.draw.rect(self.surface, (0, 80, 200), (px - 20, body_rect.bottom - 10 + leg_offset, 15, l_leg_h))
            # 右腿
            pygame.draw.rect(self.surface, (0, 80, 200), (px + 5, body_rect.bottom - 10 - leg_offset, 15, l_leg_h))
            
        # 3. 绘制身体
        pygame.draw.rect(self.surface, (0, 100, 255), body_rect, border_radius=8)
        pygame.draw.rect(self.surface, (0, 255, 255), body_rect, 3, border_radius=8)
        
        # 4. 绘制头部
        head_x = px
        head_y = int(body_rect.top - head_r + 5)
        
        if core.action_state == "SLIDE":
            head_x = px  # 身体中间
            head_y = int(body_rect.top - 5) # 稍微低一点
            
        pygame.draw.circle(self.surface, (255, 255, 255), (head_x, head_y), head_r)
        
        # 5. 绘制喷射背包 & 火焰 (核心修复)
        # 背包位置：背部上方
        jet_w, jet_h = 24, 35
        jet_x = px - jet_w // 2
        jet_y = body_rect.top + 10 # 挂在肩膀位置
        
        if core.action_state == "SLIDE":
             # 滑铲时背包不可见(压在身下)或在侧面，这里简化不画，或者画一点点
             pass
        else:
             jet_rect = pygame.Rect(jet_x, jet_y, jet_w, jet_h)
             pygame.draw.rect(self.surface, (255, 140, 0), jet_rect, border_radius=4)
             pygame.draw.rect(self.surface, (255, 200, 0), jet_rect, 2, border_radius=4)

             # --- 【关键修复】火焰从背包底部喷出 ---
             if core.action_state == "JUMP":
                 # 粒子系统
                 for _ in range(5):
                     # 火焰源点：背包底部中心
                     origin_x = jet_rect.centerx
                     origin_y = jet_rect.bottom
                     
                     # 随机扩散
                     fx = origin_x + random.randint(-6, 6)
                     # 向下喷射
                     fy = origin_y + random.randint(0, 30)
                     
                     size = random.randint(4, 8)
                     color = (255, random.randint(50, 200), 0) # 黄红渐变
                     pygame.draw.circle(self.surface, color, (fx, fy), size)

        # 6. 滑铲火花
        if core.action_state == "SLIDE":
            for _ in range(4):
                # 火花源点：身体底部
                fx = px + random.randint(-p_w//2, p_w//2)
                fy = body_rect.bottom
                pygame.draw.circle(self.surface, (0, 255, 255), (fx, fy), random.randint(2, 5))

        # 状态文字
        if core.action_state != "RUN":
            txt = self.font_m.render(core.action_state + "!", True, (0, 255, 0))
            self.surface.blit(txt, (px - txt.get_width()//2, body_rect.top - 50))

    def _draw_text_on_obs(self, text, x, y, scale, color):
        size = int(40 * scale)
        if size < 10: return
        font = self.font_m if scale > 0.5 else self.font_s
        surf = font.render(text, True, (255, 255, 255))
        surf_outline = font.render(text, True, color)
        dest = (x - surf.get_width()//2, y - size - 10)
        self.surface.blit(surf_outline, (dest[0]+2, dest[1]+2))
        self.surface.blit(surf, dest)

    def _draw_hud(self, core):
        bar_w = 600
        cx = self.w // 2
        progress = min(1.0, core.elapsed_time / core.target_time)
        pygame.draw.rect(self.surface, (50, 50, 50), (cx - bar_w//2, 40, bar_w, 20))
        pygame.draw.rect(self.surface, (0, 255, 128), (cx - bar_w//2, 40, int(bar_w * progress), 20))
        pygame.draw.rect(self.surface, (255, 255, 255), (cx - bar_w//2, 40, bar_w, 20), 2)
        t_str = f"{int(core.elapsed_time)}s / {core.target_time}s"
        txt = self.font_m.render(t_str, True, (255, 255, 255))
        self.surface.blit(txt, (cx - txt.get_width()//2, 10))

    def _draw_menu(self):
        s = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.surface.blit(s, (0,0))
        title = self.font_xl.render("NEON PARKOUR", True, (255, 0, 128))
        title_s = self.font_xl.render("NEON PARKOUR", True, (0, 255, 255))
        cx, cy = self.w // 2, self.h // 2
        self.surface.blit(title_s, (cx - title.get_width()//2 + 4, 150 + 4))
        self.surface.blit(title, (cx - title.get_width()//2, 150))
        opts = [("LEFT HEAD", "60s"), ("NOD DOWN", "90s"), ("RIGHT HEAD", "120s")]
        colors = [(0, 255, 0), (255, 255, 0), (255, 0, 0)]
        for i, (act, time_str) in enumerate(opts):
            x = cx + (i - 1) * 350
            y = 400
            pygame.draw.rect(self.surface, (50, 50, 50), (x - 100, y - 60, 200, 120), border_radius=10)
            pygame.draw.rect(self.surface, colors[i], (x - 100, y - 60, 200, 120), 3, border_radius=10)
            t1 = self.font_m.render(act, True, (200, 200, 200))
            t2 = self.font_xl.render(time_str, True, colors[i])
            self.surface.blit(t1, (x - t1.get_width()//2, y - 40))
            self.surface.blit(t2, (x - t2.get_width()//2, y + 10))

    def _draw_game_over(self, core):
        s = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 200))
        self.surface.blit(s, (0,0))
        txt = "VICTORY!" if core.state == "VICTORY" else "CRASHED!"
        col = (0, 255, 0) if core.state == "VICTORY" else (255, 0, 0)
        t = self.font_xl.render(txt, True, col)
        self.surface.blit(t, (self.w//2 - t.get_width()//2, self.h//2 - 50))
        if core.state == "GAME_OVER":
            rem = 5 - int(time.time() - core.death_time)
            if rem > 0:
                sub = self.font_m.render(f"Restart in {rem}...", True, (255, 255, 255))
                self.surface.blit(sub, (self.w//2 - sub.get_width()//2, self.h//2 + 50))