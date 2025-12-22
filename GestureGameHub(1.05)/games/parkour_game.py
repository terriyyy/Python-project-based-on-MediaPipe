# games/parkour_game.py
import cv2
import numpy as np
import time
import random
import math
import mediapipe as mp
from .base_game import BaseGame

class Obstacle:
    def __init__(self, lane, obs_type, z_pos=0.0):
        self.lane = lane      # -1: 左, 0: 中, 1: 右
        # type: 'JUMP'(矮墙), 'HURDLE'(跨栏-双通), 'TUNNEL'(拱门-蹲), 'FULL'(红墙-死)
        self.type = obs_type  
        self.z = z_pos        # 0.0 (远方) -> 1.0 (面前)
        self.passed = False   # 是否已被玩家通过

class ParkourGame(BaseGame):
    def __init__(self):
        super().__init__()
        # --- 基础配置 ---
        self.canvas_w, self.canvas_h = 1280, 720
        
        # --- MediaPipe 配置 ---
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        # --- 游戏状态 ---
        self.state = "SELECT_TIME" 
        self.target_time = 60       
        self.start_time = 0
        self.elapsed_time = 0
        self.death_time = 0 
        
        # --- 玩家属性 ---
        self.lane = 0        
        self.visual_lane = 0.0 
        self.action_state = "RUN" 
        self.action_timer = 0     
        self.jump_duration = 0.6  
        self.slide_duration = 0.8 
        
        # 冷却系统
        self.last_action_time = 0   
        self.move_cooldown = 0.45   
        
        # --- 头部控制 ---
        self.head_pose = "CENTER" 
        self.last_head_pose = "CENTER" 
        
        # --- 场景与障碍物 ---
        self.obstacles = []
        # [修改点1] 基础速度大幅降低 (0.01 -> 0.006)
        self.base_speed = 0.006   
        self.spawn_timer = 0 
        self.road_horizon_y = int(self.canvas_h * 0.45) 

    def start_game(self, duration):
        """开始/重置游戏"""
        self.target_time = duration
        self.state = "PLAYING"
        self.start_time = time.time()
        self.obstacles = []
        self.lane = 0
        self.visual_lane = 0.0
        # 重置时也要用新的慢速
        self.base_speed = 0.006
        self.last_action_time = time.time()
        self.action_state = "RUN"
        self.spawn_timer = 0

    def detect_head_pose(self, landmarks):
        """解析头部姿态"""
        nose = landmarks[1]
        left_eye = landmarks[33]
        right_eye = landmarks[263]
        chin = landmarks[152]
        forehead = landmarks[10]

        # 计算 Yaw (左右)
        eye_center_x = (left_eye.x + right_eye.x) / 2
        yaw_diff = nose.x - eye_center_x
        
        # 计算 Pitch (上下)
        face_center_y = (forehead.y + chin.y) / 2
        pitch_diff = nose.y - face_center_y

        # --- 灵敏度 ---
        YAW_THRESH = 0.05    
        PITCH_THRESH_UP = 0.025 
        PITCH_THRESH_DOWN = 0.08  

        # 优先检测上下
        if pitch_diff > PITCH_THRESH_DOWN: return "DOWN"
        if pitch_diff < -PITCH_THRESH_UP: return "UP"

        if yaw_diff < -YAW_THRESH: return "LEFT"   
        if yaw_diff > YAW_THRESH: return "RIGHT" 
        
        return "CENTER"

    def generate_obstacle_wave(self):
        """生成障碍物波次"""
        t = self.elapsed_time
        
        # 概率分布 [单体, 成对, 三排]
        probs = [1.0, 0.0, 0.0] 
        if t < 20: probs = [1.0, 0.0, 0.0] 
        elif t < 40: probs = [0.8, 0.2, 0.0] # 降低成对概率
        elif t < 80: probs = [0.5, 0.5, 0.0] 
        elif t < 100: probs = [0.3, 0.5, 0.2] 
        else: probs = [0.1, 0.5, 0.4] 
            
        mode = random.choices([1, 2, 3], weights=probs, k=1)[0]
        lanes = [-1, 0, 1]
        
        if mode == 1: selected_lanes = [random.choice(lanes)]
        elif mode == 2: selected_lanes = random.sample(lanes, 2)
        else: selected_lanes = [-1, 0, 1]

        obs_types = ["JUMP", "HURDLE", "TUNNEL", "FULL"]
        
        wave_obstacles = []
        generated_types = []
        
        for l in selected_lanes:
            o_type = random.choice(obs_types)
            generated_types.append(o_type)
            wave_obstacles.append(Obstacle(l, o_type, 0.0))
            
        # 防死局
        if mode == 3 and generated_types.count("FULL") == 3:
            change_idx = random.randint(0, 2)
            safe_type = random.choice(["JUMP", "HURDLE", "TUNNEL"]) 
            wave_obstacles[change_idx].type = safe_type
            
        return wave_obstacles

    def update_logic(self):
        if self.state != "PLAYING": return

        current_t = time.time()
        self.elapsed_time = current_t - self.start_time

        if self.elapsed_time >= self.target_time:
            self.state = "VICTORY"
            self.death_time = current_t
            return

        # 速度曲线更加平缓
        # 时间除数45，系数0.3
        # 最大速度倍率限制为1.5
        speed_boost = math.log(1 + self.elapsed_time / 45.0) * 0.3
        current_speed = self.base_speed * (1 + min(1.5, speed_boost))

        # 动作恢复
        if self.action_state == "JUMP":
            if current_t - self.action_timer > self.jump_duration: self.action_state = "RUN"
        elif self.action_state == "SLIDE":
            if current_t - self.action_timer > self.slide_duration: self.action_state = "RUN"

        # 视觉移动
        self.visual_lane += (self.lane - self.visual_lane) * 0.2
        if abs(self.visual_lane - self.lane) < 0.01: self.visual_lane = float(self.lane)

        # 障碍物生成
        self.spawn_timer += 1
        
        
        # 基础时间间隔80，随时间减少的幅度也变小
        spawn_interval = max(35, int(80 - self.elapsed_time * 0.4))
        
        if self.spawn_timer > spawn_interval:
            new_wave = self.generate_obstacle_wave()
            self.obstacles.extend(new_wave)
            self.spawn_timer = 0

        # 障碍物移动与碰撞
        for i in range(len(self.obstacles) - 1, -1, -1):
            obs = self.obstacles[i]
            
            # 减弱透视加速 (3.5 -> 2.5)
            perspective_boost = 1.0 + (obs.z * 2.5) 
            obs.z += current_speed * perspective_boost

            if obs.z > 1.3: 
                self.obstacles.pop(i)
                continue

            # 碰撞判定
            if 0.85 < obs.z < 1.0 and not obs.passed:
                if obs.lane == self.lane:
                    collision = False
                    
                    if obs.type == "FULL": 
                        collision = True 
                        
                    elif obs.type == "JUMP":
                        if self.action_state != "JUMP": collision = True
                        
                    elif obs.type == "TUNNEL":
                        if self.action_state != "SLIDE": collision = True
                        
                    elif obs.type == "HURDLE":
                        if self.action_state == "RUN": collision = True
                    
                    if collision:
                        self.state = "GAME_OVER"
                        self.death_time = time.time()
                    else:
                        obs.passed = True 

    def draw_scene(self, frame):
        """渲染场景"""
        canvas = frame.copy() 
        h, w = self.canvas_h, self.canvas_w
        cx, cy = w // 2, self.road_horizon_y

        # 背景
        cv2.rectangle(canvas, (0, 0), (w, cy), (40, 30, 60), -1) 
        cv2.rectangle(canvas, (0, cy), (w, h), (20, 20, 20), -1)

        def get_lane_x(lane_idx, z):
            bottom_width_scale = 1.5 
            x_offset = (lane_idx * (w // 4)) * (z / 1.0) * bottom_width_scale
            return int(cx + x_offset)

        def get_y(z):
            return int(cy + (h - cy) * z)

        def draw_obstacle(obs):
            if obs.z < 0.1: return
            scale = obs.z
            obs_w = int(150 * scale)
            
            # 高度定义
            if obs.type == "JUMP":
                obs_h = int(100 * scale) 
            elif obs.type == "HURDLE":
                obs_h = int(120 * scale) 
            else: 
                obs_h = int(250 * scale) 
            
            center_x = get_lane_x(obs.lane, scale)
            bottom_y = get_y(scale)
            top_left = (center_x - obs_w // 2, bottom_y - obs_h)
            bottom_right = (center_x + obs_w // 2, bottom_y)
            
            # --- 绘制具体样式 ---
            if obs.type == "HURDLE":
                leg_width = int(20 * scale)
                bar_height = int(40 * scale)
                color = (0, 200, 255) 

                cv2.rectangle(canvas, (top_left[0], top_left[1]), 
                              (top_left[0] + leg_width, bottom_right[1]), color, -1)
                cv2.rectangle(canvas, (bottom_right[0] - leg_width, top_left[1]), 
                              (bottom_right[0], bottom_right[1]), color, -1)
                cv2.rectangle(canvas, (top_left[0], top_left[1]), 
                              (bottom_right[0], top_left[1] + bar_height), color, -1)
                
                cv2.rectangle(canvas, top_left, bottom_right, (255, 255, 255), 2)
                cv2.putText(canvas, "ANY!", (top_left[0], top_left[1]-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5 * scale + 0.5, color, 2)

            elif obs.type == "TUNNEL":
                color = (255, 150, 0) # 橙色
                pillar_w = int(30 * scale)
                # 洞的高度做低，让玩家感觉必须蹲
                hole_h = int(90 * scale) 
                header_h = obs_h - hole_h 

                # 顶梁
                cv2.rectangle(canvas, top_left, (bottom_right[0], top_left[1] + header_h), color, -1)
                # 左柱
                cv2.rectangle(canvas, top_left, (top_left[0] + pillar_w, bottom_right[1]), color, -1)
                # 右柱
                cv2.rectangle(canvas, (bottom_right[0] - pillar_w, top_left[1]), bottom_right, color, -1)
                
                # 边框
                cv2.rectangle(canvas, top_left, (bottom_right[0], top_left[1] + header_h), (255,255,255), 2)
                cv2.rectangle(canvas, top_left, (top_left[0] + pillar_w, bottom_right[1]), (255,255,255), 2)
                cv2.rectangle(canvas, (bottom_right[0] - pillar_w, top_left[1]), bottom_right, (255,255,255), 2)
                
                # 内侧边框 (洞口轮廓)
                hole_top_y = top_left[1] + header_h
                cv2.line(canvas, (top_left[0] + pillar_w, hole_top_y), (bottom_right[0] - pillar_w, hole_top_y), (255,255,255), 2)
                cv2.line(canvas, (top_left[0] + pillar_w, hole_top_y), (top_left[0] + pillar_w, bottom_right[1]), (255,255,255), 2)
                cv2.line(canvas, (bottom_right[0] - pillar_w, hole_top_y), (bottom_right[0] - pillar_w, bottom_right[1]), (255,255,255), 2)

                cv2.putText(canvas, "DUCK!", (top_left[0], top_left[1]-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5 * scale + 0.5, color, 2)

            elif obs.type == "FULL":
                color = (50, 50, 255) 
                cv2.rectangle(canvas, top_left, bottom_right, color, -1)
                cv2.line(canvas, top_left, bottom_right, (40, 40, 200), 5)
                cv2.line(canvas, (top_left[0], bottom_right[1]), (bottom_right[0], top_left[1]), (40, 40, 200), 5)
                cv2.rectangle(canvas, top_left, bottom_right, (255, 255, 255), 2)
                cv2.putText(canvas, "WALL!", (top_left[0], top_left[1]-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5 * scale + 0.5, color, 2)

            elif obs.type == "JUMP":
                color = (0, 200, 0)
                cv2.rectangle(canvas, top_left, bottom_right, color, -1)
                cv2.rectangle(canvas, top_left, bottom_right, (255, 255, 255), 2)
                cv2.putText(canvas, "JUMP!", (top_left[0], top_left[1]-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5 * scale + 0.5, color, 2)

        # 网格线
        grid_z_offset = (time.time() * 2) % 0.5 
        for i in range(10):
            z_line = 0.1 + i * 0.1 + grid_z_offset
            if z_line > 1.0: continue
            y = get_y(z_line)
            cv2.line(canvas, (0, y), (w, y), (50, 50, 50), 1)
        for i, l_idx in enumerate([-1.5, -0.5, 0.5, 1.5]):
            p1 = (cx, cy)
            p2 = (int(cx + (l_idx * (w // 3))), h)
            cv2.line(canvas, p1, p2, (80, 80, 80), 2)

        # --- 分层渲染 ---
        PLAYER_Z = 0.9
        sorted_obstacles = sorted(self.obstacles, key=lambda o: o.z)
        
        # A. 身后
        background_obstacles = [o for o in sorted_obstacles if o.z <= PLAYER_Z]
        for obs in background_obstacles:
            draw_obstacle(obs)

        # B. 玩家
        player_screen_x = get_lane_x(self.visual_lane, PLAYER_Z) 
        player_base_y = h - 50
        
        p_w, p_h_standing = 60, 100
        p_h = p_h_standing
        p_color = (255, 255, 0) 
        
        if self.action_state == "JUMP":
            progress = (time.time() - self.action_timer) / self.jump_duration
            if 0 <= progress <= 1:
                jump_height = 150 * math.sin(progress * math.pi)
                player_base_y -= int(jump_height)
                cv2.putText(canvas, "JUMP!", (player_screen_x-40, player_base_y-120), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        elif self.action_state == "SLIDE":
            progress = (time.time() - self.action_timer) / self.slide_duration
            if 0 <= progress <= 1:
                crouch_factor = 1.0
                if progress < 0.2: crouch_factor = 1.0 - (progress / 0.2) * 0.5 
                elif progress > 0.8: crouch_factor = 0.5 + ((progress - 0.8) / 0.2) * 0.5 
                else: crouch_factor = 0.5 
                p_h = int(p_h_standing * crouch_factor)
                player_base_y += int((p_h_standing - p_h)) 
                cv2.putText(canvas, "SLIDE!", (player_screen_x-40, player_base_y-80), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        p_tl = (player_screen_x - p_w//2, player_base_y - p_h)
        p_br = (player_screen_x + p_w//2, player_base_y)
        cv2.rectangle(canvas, p_tl, p_br, p_color, -1)
        cv2.circle(canvas, (player_screen_x, player_base_y - p_h - 15), 20, p_color, -1)

        # C. 身前
        foreground_obstacles = [o for o in sorted_obstacles if o.z > PLAYER_Z]
        for obs in foreground_obstacles:
            draw_obstacle(obs)

        # HUD
        progress = min(1.0, self.elapsed_time / self.target_time)
        bar_w = int(w * 0.8)
        cv2.rectangle(canvas, (w//2 - bar_w//2, 50), (w//2 + bar_w//2, 70), (100,100,100), -1)
        cv2.rectangle(canvas, (w//2 - bar_w//2, 50), (w//2 - bar_w//2 + int(bar_w*progress), 70), (0,255,0), -1)
        timer_text = f"{int(self.elapsed_time)}s / {self.target_time}s"
        cv2.putText(canvas, timer_text, (w//2 - 50, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)

        return canvas

    def draw_menu(self, canvas, head_cmd):
        overlay = canvas.copy()
        cv2.rectangle(overlay, (0, 0), (self.canvas_w, self.canvas_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.8, canvas, 0.2, 0, canvas)

        title = "PARKOUR MASTER"
        cv2.putText(canvas, title, (self.canvas_w//2 - 250, 150), cv2.FONT_HERSHEY_TRIPLEX, 2, (0, 255, 255), 3)

        cx = self.canvas_w // 2
        y = 400
        spacing = 350

        # 左
        cv2.rectangle(canvas, (cx - spacing - 150, y - 50), (cx - spacing + 150, y + 50), (100,100,100), 2)
        cv2.putText(canvas, "LEFT HEAD", (cx - spacing - 100, y - 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 1)
        cv2.putText(canvas, "60s", (cx - spacing - 60, y + 15), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)

        # 中
        cv2.rectangle(canvas, (cx - 150, y - 50), (cx + 150, y + 50), (100,100,100), 2)
        cv2.putText(canvas, "NOD DOWN", (cx - 80, y - 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 1)
        cv2.putText(canvas, "90s", (cx - 60, y + 15), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 0), 3)

        # 右
        cv2.rectangle(canvas, (cx + spacing - 150, y - 50), (cx + spacing + 150, y + 50), (100,100,100), 2)
        cv2.putText(canvas, "RIGHT HEAD", (cx + spacing - 100, y - 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 1)
        cv2.putText(canvas, "120s", (cx + spacing - 80, y + 15), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 0, 0), 3)

        inst_text = "Tilt Left/Right or Nod Down to Start Directly"
        cv2.putText(canvas, inst_text, (self.canvas_w//2 - 300, 600), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 1)

    def draw_pip_camera(self, game_canvas, cam_frame, results, command):
        """画中画"""
        vis_frame = cam_frame.copy()
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                self.mp_draw.draw_landmarks(
                    image=vis_frame,
                    landmark_list=face_landmarks,
                    connections=self.mp_face_mesh.FACEMESH_TESSELATION,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=self.mp_drawing_styles.get_default_face_mesh_tesselation_style()
                )

        pip_h = 180
        pip_w = int(pip_h * (16/9))
        if pip_w > self.canvas_w: pip_w = self.canvas_w // 4
        
        small_cam = cv2.resize(vis_frame, (pip_w, pip_h))
        
        margin = 20
        x_start = self.canvas_w - pip_w - margin
        y_start = margin
        
        border_color = (0, 255, 0) if command != "CENTER" else (100, 100, 100)
        cv2.rectangle(game_canvas, (x_start-2, y_start-2), 
                      (x_start+pip_w+2, y_start+pip_h+2), border_color, 2)
        
        game_canvas[y_start:y_start+pip_h, x_start:x_start+pip_w] = small_cam
        
        status_text = f"CMD: {command}"
        text_color = (0, 255, 0) if command != "CENTER" else (200, 200, 200)
        cv2.putText(game_canvas, status_text, (x_start, y_start + pip_h + 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
        
        if time.time() - self.last_action_time < self.move_cooldown:
            cv2.putText(game_canvas, "WAIT...", (x_start + 150, y_start + pip_h + 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        elif self.last_head_pose != "CENTER" and command != "CENTER":
             cv2.putText(game_canvas, "RESET!", (x_start + 150, y_start + pip_h + 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    def process(self, frame):
        frame = cv2.resize(frame, (self.canvas_w, self.canvas_h))
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        head_cmd = "CENTER"
        
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                head_cmd = self.detect_head_pose(face_landmarks.landmark)
                self.head_pose = head_cmd 

        current_time = time.time()
        trigger_action = None
        
        # 冷却
        if current_time - self.last_action_time > self.move_cooldown:
            if self.last_head_pose == "CENTER" and head_cmd != "CENTER":
                trigger_action = head_cmd
                self.last_action_time = current_time 

        if head_cmd == "CENTER":
            self.last_head_pose = "CENTER"

        if self.state == "SELECT_TIME":
            if trigger_action == "LEFT":
                self.start_game(60)
            elif trigger_action == "RIGHT":
                self.start_game(120)
            elif trigger_action == "DOWN":
                self.start_game(90)
            
            self.draw_menu(frame, head_cmd)
            self.draw_pip_camera(frame, frame.copy(), results, head_cmd)
            return frame

        elif self.state == "PLAYING":
            if trigger_action == "LEFT" and self.lane > -1:
                self.lane -= 1
            elif trigger_action == "RIGHT" and self.lane < 1:
                self.lane += 1
            elif trigger_action == "UP" and self.action_state == "RUN":
                self.action_state = "JUMP"
                self.action_timer = time.time()
            elif trigger_action == "DOWN" and self.action_state == "RUN":
                self.action_state = "SLIDE"
                self.action_timer = time.time()

            self.update_logic()
            
            game_view = self.draw_scene(frame)
            self.draw_pip_camera(game_view, frame, results, head_cmd)
            
            return game_view

        elif self.state in ["GAME_OVER", "VICTORY"]:
            game_view = self.draw_scene(frame)
            overlay = game_view.copy()
            cv2.rectangle(overlay, (0, 0), (self.canvas_w, self.canvas_h), (0,0,0), -1)
            cv2.addWeighted(overlay, 0.7, game_view, 0.3, 0, game_view)
            
            msg = "MISSION FAILED" if self.state == "GAME_OVER" else "VICTORY!"
            color = (0, 0, 255) if self.state == "GAME_OVER" else (0, 255, 0)
            cv2.putText(game_view, msg, (self.canvas_w//2 - 200, self.canvas_h//2 - 50), 
                        cv2.FONT_HERSHEY_TRIPLEX, 2, color, 4)
            
            elapsed_death = current_time - self.death_time
            remaining = 5 - int(elapsed_death)
            
            if remaining > 0:
                cv2.putText(game_view, f"Restart in {remaining}...", (self.canvas_w//2 - 150, self.canvas_h//2 + 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
            else:
                self.state = "SELECT_TIME"
            
            self.draw_pip_camera(game_view, frame, results, head_cmd)

            return game_view

        return frame