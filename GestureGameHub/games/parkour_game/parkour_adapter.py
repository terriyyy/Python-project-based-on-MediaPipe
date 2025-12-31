# games/parkour_game/parkour_adapter.py
import cv2
import numpy as np
import time
import os
import sys
import mediapipe as mp

# 导入同级 src
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, 'src'))

from parkour_core import ParkourCore
from parkour_renderer import ParkourRenderer

class ParkourGame:
    def __init__(self):
        self.canvas_w, self.canvas_h = 1280, 720
        self.sidebar_w = 380
        self.game_w = self.canvas_w - self.sidebar_w
        
        # 实例化核心与渲染器
        self.core = ParkourCore()
        self.renderer = ParkourRenderer(self.game_w, self.canvas_h)
        
        # MediaPipe 面部控制
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        self.last_head_pose = "CENTER"
        self.head_pose = "CENTER"
        self.last_action_time = 0
        self.move_cooldown = 0.35 # 稍微缩短冷却

    def detect_head_pose(self, landmarks):
        """头部姿态检测 (复用原逻辑)"""
        nose = landmarks[1]
        left_eye = landmarks[33]
        right_eye = landmarks[263]
        chin = landmarks[152]
        forehead = landmarks[10]

        yaw_diff = nose.x - (left_eye.x + right_eye.x) / 2
        pitch_diff = nose.y - (forehead.y + chin.y) / 2

        YAW_THRESH = 0.05    
        PITCH_THRESH_UP = 0.025 
        PITCH_THRESH_DOWN = 0.08  

        if pitch_diff > PITCH_THRESH_DOWN: return "DOWN"
        if pitch_diff < -PITCH_THRESH_UP: return "UP"
        if yaw_diff < -YAW_THRESH: return "LEFT"   
        if yaw_diff > YAW_THRESH: return "RIGHT" 
        return "CENTER"

    def process(self, frame):
        # 1. 摄像头识别
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        head_cmd = "CENTER"
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                head_cmd = self.detect_head_pose(face_landmarks.landmark)
                self.head_pose = head_cmd 

        # 2. 触发逻辑
        current_time = time.time()
        trigger_action = None
        
        if current_time - self.last_action_time > self.move_cooldown:
            if self.last_head_pose == "CENTER" and head_cmd != "CENTER":
                trigger_action = head_cmd
                self.last_action_time = current_time 

        if head_cmd == "CENTER":
            self.last_head_pose = "CENTER"

        # 3. 状态分发
        if self.core.state == "SELECT_TIME":
            if trigger_action == "LEFT": self.core.start_game(60)
            elif trigger_action == "RIGHT": self.core.start_game(120)
            elif trigger_action == "DOWN": self.core.start_game(90)
        
        elif self.core.state == "PLAYING":
            self.core.update(trigger_action)
        
        elif self.core.state == "GAME_OVER":
            if time.time() - self.core.death_time > 5:
                self.core.state = "SELECT_TIME"

        # 4. 渲染游戏画面 (Pygame)
        self.renderer.draw(self.core)
        game_img = self.renderer.get_image()

        # 5. 拼接侧边栏 (Opencv)
        combined = np.zeros((self.canvas_h, self.canvas_w, 3), dtype=np.uint8)
        combined[:, :self.game_w] = game_img
        
        # 侧边栏背景
        cv2.rectangle(combined, (self.game_w, 0), (self.canvas_w, self.canvas_h), (20, 10, 30), -1)
        
        # 小摄像头 (画中画)
        cw = self.sidebar_w - 20
        ch = int(cw * 0.75)
        
        vis_frame = frame.copy()
        if results.multi_face_landmarks:
             for face_landmarks in results.multi_face_landmarks:
                self.mp_draw.draw_landmarks(vis_frame, face_landmarks, 
                    connections=self.mp_face_mesh.FACEMESH_TESSELATION,
                    connection_drawing_spec=self.mp_drawing_styles.get_default_face_mesh_tesselation_style())
                    
        cam_small = cv2.resize(vis_frame, (cw, ch))
        y_start = 20
        combined[y_start:y_start+ch, self.game_w+10:self.game_w+10+cw] = cam_small
        
        # 状态显示
        info_y = y_start + ch + 50
        cv2.putText(combined, "HEAD CONTROL", (self.game_w+20, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)
        
        cmd_color = (0, 255, 0) if head_cmd != "CENTER" else (100, 100, 100)
        cv2.putText(combined, f"CMD: {head_cmd}", (self.game_w+20, info_y + 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, cmd_color, 2)
        
        # 玩法提示
        help_y = info_y + 120
        instructions = [
            ("LEFT/RIGHT", "Change Lane"),
            ("NOD UP", "Jump"),
            ("NOD DOWN", "Slide")
        ]
        for i, (act, desc) in enumerate(instructions):
            cv2.putText(combined, act, (self.game_w+20, help_y + i*60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
            cv2.putText(combined, desc, (self.game_w+20, help_y + i*60 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        return combined