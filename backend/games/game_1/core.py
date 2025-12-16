import cv2
import mediapipe as mp
import numpy as np
from .config import *
from .utils import calculate_aspect_ratio, estimate_head_pose
from .hud_renderer import CyberRenderer

class CyberPunkGame:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.renderer = CyberRenderer()

    def process(self, image):
        # 1. 降低亮度，营造赛博朋克暗黑感
        image = cv2.convertScaleAbs(image, alpha=0.8, beta=-20)
        
        img_h, img_w, _ = image.shape
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(img_rgb)

        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                landmarks = face_landmarks.landmark

                # --- A. 头部姿态 ---
                pose_angles, r_vec, t_vec = estimate_head_pose(landmarks, img_w, img_h)
                self.renderer.draw_pose_info(image, pose_angles)

                # --- B. 计算 EAR (眨眼检测) ---
                left_ear = calculate_aspect_ratio(landmarks, LEFT_EYE_IDXS, img_w, img_h)
                right_ear = calculate_aspect_ratio(landmarks, RIGHT_EYE_IDXS, img_w, img_h)
                avg_ear = (left_ear + right_ear) / 2.0
                is_blinking = avg_ear < 0.25  # 阈值可调

                # --- C. 计算 MAR (嘴巴张开程度) ---
                mar = calculate_aspect_ratio(landmarks, MOUTH_IDXS, img_w, img_h)
                
                # --- D. 绘制眼部 UI ---
                # 获取左眼中心 (近似取 362 和 263 关键点)
                l_pt = landmarks[362]
                r_pt = landmarks[33]
                l_center = (l_pt.x * img_w, l_pt.y * img_h)
                r_center = (r_pt.x * img_w, r_pt.y * img_h)
                
                self.renderer.draw_eye_hud(image, l_center, is_blinking)
                self.renderer.draw_eye_hud(image, r_center, is_blinking)

                # --- E. 绘制脸颊数据流 ---
                # 位置定位在脸颊侧面 (例如关键点 454)
                cheek_pt = landmarks[454]
                cheek_pos = (int(cheek_pt.x * img_w), int(cheek_pt.y * img_h))
                self.renderer.draw_cheek_data(image, cheek_pos, speed_factor=mar)

        return image