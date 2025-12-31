# games/maze_game/maze_adapter.py
import cv2
import time
import numpy as np
import os
import sys
import mediapipe as mp
import traceback

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, 'src'))

from maze_core import MazeCore
from maze_renderer import MazeRenderer

class MazeGame:
    def __init__(self):
        self.canvas_w, self.canvas_h = 1280, 720
        self.sidebar_w = 380
        self.maze_w = self.canvas_w - self.sidebar_w
        
        self.core = MazeCore()
        self.renderer = MazeRenderer(self.maze_w, self.canvas_h)
        # 初始化时，强制把视觉位置对齐到逻辑位置 (防止小球从 (0,0) 飞过来)
        px, py = self.core.player_pos
        self.renderer.visual_pos = [float(px), float(py)]
        
        self.last_move_time = 0
        self.move_interval = 0.28 
        
        self.win_delay_start = 0 
        self.is_waiting_next_level = False
        
        # 【新增】FPS 控制
        self.target_fps = 20
        self.frame_duration = 1.0 / self.target_fps
        
        # MediaPipe 初始化
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.hands_detector = self.mp_hands.Hands(
            max_num_hands=1,
            model_complexity=0, 
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def start_game(self):
        self.core.start_game()
        self.renderer.cache_level_id = -1 
        # 重置视觉
        px, py = self.core.player_pos
        self.renderer.visual_pos = [float(px), float(py)]
        self.renderer.trail = []

    def detect_gesture(self, landmarks):
        wrist = landmarks.landmark[0]
        tip = landmarks.landmark[8]
        dx, dy = tip.x - wrist.x, tip.y - wrist.y
        threshold = 0.15
        if abs(dx) > abs(dy):
            return "RIGHT" if dx > threshold else "LEFT" if dx < -threshold else "NONE"
        else:
            return "DOWN" if dy > threshold else "UP" if dy < -threshold else "NONE"

    def process(self, frame):
        # 【新增】简单的 FPS 限制
        # 这一行会让程序稍微“休息”一下，释放 CPU 资源
        time.sleep(0.02) 

        try:
            # 1. AI 识别
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands_detector.process(rgb_frame)
            
            command = "NONE"
            if results.multi_hand_landmarks:
                for hl in results.multi_hand_landmarks:
                    self.mp_draw.draw_landmarks(frame, hl, self.mp_hands.HAND_CONNECTIONS)
                    command = self.detect_gesture(hl)

            cur_time = time.time()
            
            # 2. 状态机逻辑
            if self.core.game_state == "TRANSITION":
                if cur_time - self.core.transition_start_time > 2.0:
                    self.core.init_level()
                    self.core.game_state = "PLAYING"
                    
                    # 【关键】关卡刷新后，立刻重置视觉位置到新起点
                    px, py = self.core.player_pos
                    self.renderer.visual_pos = [float(px), float(py)]
                    self.renderer.trail = []
                    
                    self.renderer.cache_level_id = -1 
                    self.is_waiting_next_level = False
            
            elif self.core.game_state == "PLAYING":
                if self.is_waiting_next_level:
                    if cur_time - self.win_delay_start > 0.5: 
                        self.core.next_level()
                        self.is_waiting_next_level = False
                else:
                    if cur_time - self.last_move_time > self.move_interval and command != "NONE":
                        move_res = self.core.move_player(command)
                        if move_res == "WIN":
                            self.last_move_time = cur_time
                            self.win_delay_start = cur_time
                            self.is_waiting_next_level = True
                        elif move_res:
                            self.last_move_time = cur_time

            elif self.core.game_state == "INTRO":
                if command != "NONE": self.start_game()

            # 3. 渲染
            self.renderer.update_visuals(self.core.player_pos)
            self.renderer.draw(self.core)
            game_img = self.renderer.get_image()

            # 4. 拼接
            combined = np.zeros((self.canvas_h, self.canvas_w, 3), dtype=np.uint8)
            combined[:, :self.maze_w] = game_img
            
            theme = self.renderer.get_current_theme(self.core.level)
            cv2.rectangle(combined, (self.maze_w, 0), (self.canvas_w, self.canvas_h), theme["bg"], -1)
            
            cw = self.sidebar_w - 20
            ch = int(cw * 0.75)
            cam_small = cv2.resize(frame, (cw, ch))
            combined[20:20+ch, self.maze_w+10:self.maze_w+10+cw] = cam_small
            
            info_y = 20 + ch + 50
            cv2.putText(combined, f"CMD: {command}", (self.maze_w+20, info_y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
            
            display_level = min(self.core.level, self.core.max_levels)
            cv2.putText(combined, f"LEVEL: {display_level}/{self.core.max_levels}", (self.maze_w+20, info_y+50), cv2.FONT_HERSHEY_SIMPLEX, 0.9, theme["hero"], 2)
            
            # 冷却条
            bar_w = 200
            progress = min(1.0, (cur_time - self.last_move_time) / self.move_interval)
            bar_color = (0, 255, 0) if progress >= 1.0 else (0, 0, 255)
            cv2.rectangle(combined, (self.maze_w+20, info_y+80), (self.maze_w+20+int(bar_w*progress), info_y+90), bar_color, -1)
            cv2.rectangle(combined, (self.maze_w+20, info_y+80), (self.maze_w+20+bar_w, info_y+90), (100,100,100), 1)

            return combined
            
        except Exception as e:
            print("CRITICAL ERROR in process:", e)
            traceback.print_exc()
            return frame