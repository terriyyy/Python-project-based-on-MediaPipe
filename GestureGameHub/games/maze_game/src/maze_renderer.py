# games/maze_game/src/maze_renderer.py
import pygame
import numpy as np
import cv2
import time
import math
import traceback

class MazeRenderer:
    def __init__(self, width, height):
        pygame.init()
        self.w = width
        self.h = height
        # 我们的画布叫 self.surface，千万不要写成 screen
        self.surface = pygame.Surface((width, height))
        
        # 缓存层 (性能优化关键)
        self.cache_surface = pygame.Surface((width, height))
        self.cache_level_id = -1
        
        self.visual_pos = [0.0, 0.0]
        self.trail = []
        
        try:
            self.font_big = pygame.font.Font(None, 80)
            self.font_small = pygame.font.Font(None, 40)
        except:
            self.font_big = pygame.font.SysFont("arial", 60)
            self.font_small = pygame.font.SysFont("arial", 30)

        # 8种主题
        self.THEMES = [
            {"style": "BOX",      "bg": (20, 20, 30), "wall": (50, 50, 65),   "hero": (0, 255, 255),   "glow": (0, 255, 255)},
            {"style": "ROUND",    "bg": (30, 10, 10), "wall": (180, 60, 60),  "hero": (255, 200, 0),   "glow": (255, 50, 0)},
            {"style": "GRID",     "bg": (0, 20, 0),   "wall": (0, 150, 0),    "hero": (200, 255, 200), "glow": (0, 255, 0)},
            {"style": "DIAMOND",  "bg": (20, 0, 35),  "wall": (100, 40, 120), "hero": (0, 255, 255),   "glow": (200, 0, 255)},
            {"style": "STAR",     "bg": (30, 25, 10), "wall": (160, 120, 40), "hero": (255, 255, 200), "glow": (255, 215, 0)},
            {"style": "CROSS",    "bg": (20, 10, 20), "wall": (150, 20, 100), "hero": (255, 100, 255), "glow": (255, 0, 255)},
            {"style": "HEX",      "bg": (0, 10, 30),  "wall": (30, 80, 150),  "hero": (0, 191, 255),   "glow": (0, 100, 255)},
            {"style": "TRIANGLE", "bg": (20, 10, 0),  "wall": (160, 80, 20),  "hero": (255, 165, 0),   "glow": (255, 100, 0)},
        ]

    def get_current_theme(self, level):
        idx = (level - 1) % len(self.THEMES)
        return self.THEMES[idx]

    def update_visuals(self, target_pos):
        tx, ty = target_pos
        self.visual_pos[0] += (tx - self.visual_pos[0]) * 0.2
        self.visual_pos[1] += (ty - self.visual_pos[1]) * 0.2
        self.trail.append(tuple(self.visual_pos))
        if len(self.trail) > 8: self.trail.pop(0)

    def draw(self, core):
        try:
            theme = self.get_current_theme(core.level)
            
            # 1. 过渡动画
            if core.game_state == "TRANSITION":
                self.surface.fill(theme["bg"])
                self._draw_generating_anim(core, theme)
                return

            # 2. 检查缓存
            if self.cache_level_id != core.level:
                self.cache_level_id = core.level
                try:
                    self._render_static_layer(core, theme)
                except Exception as e:
                    print(f"Static Render Error: {e}")
                    traceback.print_exc()
                    self.cache_surface.fill(theme["bg"])

            # 3. 贴图 (这里用 self.surface，而不是 screen)
            self.surface.blit(self.cache_surface, (0, 0))

            # 4. 动态元素
            self._draw_dynamic_layer(core, theme)

            # 5. UI
            if core.game_state == "INTRO":
                self._draw_overlay("READY?", "Gesture to Start")
            elif core.game_state == "ALL_CLEARED":
                self._draw_overlay("VICTORY!", f"Time: {core.total_time:.1f}s")
                
        except Exception as e:
            print(f"Draw Loop Error: {e}")
            self.surface.fill((0, 0, 0))

    def _render_static_layer(self, core, theme):
        # 这里的画板是 self.cache_surface
        self.cache_surface.fill(theme["bg"])
        
        cols, rows = core.cols, core.rows
        maze = core.maze
        
        padding = 40
        cell_size = min((self.w - 2*padding)//cols, (self.h - 2*padding)//rows)
        ox = padding + (self.w - 2*padding - cols*cell_size) // 2
        oy = padding + (self.h - 2*padding - rows*cell_size) // 2
        
        self.layout_info = (ox, oy, cell_size)

        # 边框
        border_rect = pygame.Rect(ox - 5, oy - 5, cols * cell_size + 10, rows * cell_size + 10)
        pygame.draw.rect(self.cache_surface, theme["wall"], border_rect, 4) 
        pygame.draw.rect(self.cache_surface, theme["glow"], border_rect, 1)

        style = theme["style"]
        wall_color = theme["wall"]

        for r in range(rows):
            for c in range(cols):
                if maze[r, c] == 0: # Wall
                    cx = int(ox + c * cell_size + cell_size // 2)
                    cy = int(oy + r * cell_size + cell_size // 2)
                    x1 = int(ox + c*cell_size)
                    y1 = int(oy + r*cell_size)
                    sz = int(cell_size)
                    
                    if style == "BOX":
                        rect = (x1, y1, sz, sz)
                        pygame.draw.rect(self.cache_surface, wall_color, rect)
                        highlight = (min(255, wall_color[0]+40), min(255, wall_color[1]+40), min(255, wall_color[2]+40))
                        pygame.draw.rect(self.cache_surface, highlight, (x1, y1, sz, 4))
                    elif style == "ROUND":
                        pygame.draw.circle(self.cache_surface, wall_color, (cx, cy), int(sz/2))
                    elif style == "GRID":
                        rect = (x1 + 4, y1 + 4, sz - 8, sz - 8)
                        pygame.draw.rect(self.cache_surface, wall_color, rect, 2)
                        pygame.draw.line(self.cache_surface, wall_color, (x1, y1), (x1+sz, y1+sz), 1)
                    elif style == "DIAMOND":
                        pts = [(cx, int(cy - sz/2)), (int(cx + sz/2), cy), (cx, int(cy + sz/2)), (int(cx - sz/2), cy)]
                        pygame.draw.polygon(self.cache_surface, wall_color, pts)
                    elif style == "TRIANGLE":
                        p1 = (cx, int(cy - sz/2))
                        p2 = (int(cx + sz/2), int(cy + sz/2))
                        p3 = (int(cx - sz/2), int(cy + sz/2))
                        pygame.draw.polygon(self.cache_surface, wall_color, [p1, p2, p3])
                    elif style == "CROSS":
                        w = int(sz / 3)
                        pygame.draw.rect(self.cache_surface, wall_color, (int(cx - w/2), int(cy - sz/2 + 2), w, sz - 4))
                        pygame.draw.rect(self.cache_surface, wall_color, (int(cx - sz/2 + 2), int(cy - w/2), sz - 4, w))
                    elif style == "HEX":
                        radius = sz / 2 - 2
                        pts = []
                        for i in range(6):
                            angle = math.radians(60 * i)
                            px = int(cx + radius * math.cos(angle))
                            py = int(cy + radius * math.sin(angle))
                            pts.append((px, py))
                        pygame.draw.polygon(self.cache_surface, wall_color, pts)
                    elif style == "STAR":
                        pygame.draw.circle(self.cache_surface, wall_color, (cx, cy), int(sz/3))
                        pygame.draw.line(self.cache_surface, wall_color, (cx, int(cy-sz/2)), (cx, int(cy+sz/2)), 2)
                        pygame.draw.line(self.cache_surface, wall_color, (int(cx-sz/2), cy), (int(cx+sz/2), cy), 2)

    def _draw_dynamic_layer(self, core, theme):
        if not hasattr(self, 'layout_info'): return
        ox, oy, cell_size = self.layout_info
        
        # 1. 终点
        ex, ey = core.end_pos
        end_center = (int(ox + ex*cell_size + cell_size/2), int(oy + ey*cell_size + cell_size/2))
        pulse = (math.sin(time.time() * 8) + 1) / 2
        
        pygame.draw.circle(self.surface, (*theme["glow"], 50), end_center, int(cell_size/1.5 + pulse*5), 2)
        pygame.draw.circle(self.surface, (255, 50, 50), end_center, int(cell_size/3))

        # 2. 拖尾
        for i, (tx, ty) in enumerate(self.trail):
            tcx = int(ox + tx*cell_size + cell_size/2)
            tcy = int(oy + ty*cell_size + cell_size/2)
            radius = int(cell_size/2 * ((i+1)/len(self.trail)))
            if radius > 0:
                pygame.draw.circle(self.surface, theme["glow"], (tcx, tcy), radius)
            
        # 3. 玩家
        vpx, vpy = self.visual_pos
        pcx = int(ox + vpx*cell_size + cell_size/2)
        pcy = int(oy + vpy*cell_size + cell_size/2)
        pygame.draw.circle(self.surface, theme["hero"], (pcx, pcy), int(cell_size/2.5))
        pygame.draw.circle(self.surface, (255, 255, 255), (pcx, pcy), int(cell_size/5))

    def _draw_generating_anim(self, core, theme):
        elapsed = time.time() - core.transition_start_time
        duration = 1.5
        progress = min(elapsed / duration, 1.0)
        
        scan_color = theme["glow"]
        txt = f"LEVEL {core.level}"
        title = self.font_big.render(txt, True, scan_color)
        self.surface.blit(title, title.get_rect(center=(self.w//2, self.h//2)))
        
        scan_y = int(self.h * progress)
        pygame.draw.line(self.surface, scan_color, (0, scan_y), (self.w, scan_y), 5)
        
    def _draw_overlay(self, title, subtitle):
        s = pygame.Surface((self.w, self.h))
        s.set_alpha(180)
        s.fill((0,0,0))
        self.surface.blit(s, (0,0))
        
        t1 = self.font_big.render(title, True, (255, 255, 255))
        self.surface.blit(t1, t1.get_rect(center=(self.w//2, self.h//2 - 30)))
        t2 = self.font_small.render(subtitle, True, (200, 200, 200))
        self.surface.blit(t2, t2.get_rect(center=(self.w//2, self.h//2 + 30)))

    # [核心修复] 确保这个方法存在且缩进正确
    def get_image(self):
        view = pygame.surfarray.array3d(self.surface)
        return cv2.cvtColor(view.transpose([1, 0, 2]), cv2.COLOR_RGB2BGR)