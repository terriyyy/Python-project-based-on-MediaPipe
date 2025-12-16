import cv2
import numpy as np
import random
from .config import *

class CyberRenderer:
    def __init__(self):
        self.angle_counter = 0
        self.data_stream = [hex(random.randint(0, 255)) for _ in range(10)]

    def draw_eye_hud(self, img, eye_center, is_blinking):
        """绘制钢铁侠风格的眼部 UI"""
        color = COLOR_RED if is_blinking else COLOR_CYAN
        radius = 25 if not is_blinking else 15 # 眨眼时收缩
        
        # 增加旋转动态感
        self.angle_counter += 2
        
        cx, cy = int(eye_center[0]), int(eye_center[1])
        
        # 画圆圈
        cv2.circle(img, (cx, cy), radius, color, 2)
        cv2.circle(img, (cx, cy), radius + 10, color, 1)
        
        # 画旋转的刻度线
        x1 = int(cx + (radius + 15) * np.cos(np.radians(self.angle_counter)))
        y1 = int(cy + (radius + 15) * np.sin(np.radians(self.angle_counter)))
        cv2.line(img, (cx, cy), (x1, y1), color, 1)

    def draw_cheek_data(self, img, start_pos, speed_factor):
        """在脸颊旁绘制流动数据"""
        # 嘴巴张越大，速度越快
        scroll_speed = int(1 + speed_factor * 20) 
        
        # 随机更新数据流
        if self.angle_counter % max(1, (10 - scroll_speed)) == 0:
            self.data_stream.pop(0)
            self.data_stream.append(hex(random.randint(0, 255)))

        x, y = start_pos
        for i, text in enumerate(self.data_stream):
            cv2.putText(img, text, (x, y + i * 20), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_NEON_GREEN, 1)

    def draw_pose_info(self, img, pose_angles):
        """左上角显示头部角度"""
        pitch, yaw, roll = pose_angles
        texts = [
            f"PITCH: {pitch:.1f}",
            f"YAW:   {yaw:.1f}",
            f"ROLL:  {roll:.1f}"
        ]
        for i, t in enumerate(texts):
            cv2.putText(img, t, (20, 40 + i * 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_TEXT, 2)