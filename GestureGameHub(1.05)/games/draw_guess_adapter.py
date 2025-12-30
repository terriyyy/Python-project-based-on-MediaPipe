import cv2
import numpy as np
import mediapipe as mp
import torch
import os
import math
import traceback
import time
import random
from collections import deque

# 尝试导入模型
try:
    from games.draw_guess.cnn_model import DrawCNN
except ImportError:
    from draw_guess.cnn_model import DrawCNN

class DrawGuessAdapter:
    def __init__(self):
        # 1. 路径设置
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, 'draw_guess', 'draw_model.pth')
        label_path = os.path.join(current_dir, 'draw_guess', 'labels.txt')
        
        # 2. 加载模型和标签
        self.model_loaded = False
        self.labels = []
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        if os.path.exists(label_path) and os.path.exists(model_path):
            try:
                with open(label_path, 'r') as f:
                    # 读取并过滤空行
                    self.labels = [line.strip() for line in f.read().splitlines() if line.strip()]
                if len(self.labels) > 0:
                    self.model = DrawCNN(len(self.labels)).to(self.device)
                    self.model.load_state_dict(torch.load(model_path, map_location=self.device))
                    self.model.eval()
                    self.model_loaded = True
            except Exception as e:
                print(f">>> [你画我猜] 加载出错: {e}")
                self.labels = ["apple", "book", "car"] 
        else:
            print(">>> [你画我猜] 无模型文件或标签文件")
            self.labels = ["apple", "book", "car"]

        # 3. MediaPipe
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)
        self.mp_draw = mp.solutions.drawing_utils
        
        # 4. 画布设置 (统一标准分辨率)
        self.width = 1280
        self.height = 720
        self.canvas = np.full((self.height, self.width, 3), 255, dtype=np.uint8)
        
        # 5. 笔触与工具变量
        self.xp, self.yp = 0, 0
        self.brush_thickness = 10     
        self.eraser_thickness = 80    
        self.prev_cx, self.prev_cy = 0, 0
        self.eraser_cx, self.eraser_cy = 0, 0 
        self.smooth_factor = 0.5      
        self.prev_thickness = 10      
        self.points_queue = deque(maxlen=4) 

        # 6. 游戏状态与UI
        self.prediction = "..."       
        self.status_text = "Ready"    
        self.frame_count = 0

        # 选题系统变量
        self.state = 'SELECTING' 
        self.selection_start_time = time.time()
        self.selection_duration = 3.0 
        self.target_topic = random.choice(self.labels) if self.labels else "No Topic"
        self.current_display_topic = "..." 

        # UI颜色定义
        self.c_ink = (0, 0, 0)
        self.c_eraser = (255, 255, 255)
        self.c_ui_bg = (60, 60, 80)  
        self.c_ui_border = (100, 100, 140)
        self.c_text_light = (240, 240, 240)
        self.c_text_accent = (0, 200, 255) 
        self.c_btn_clear = (80, 80, 220)

    def predict(self):
        if not self.model_loaded: return
        try:
            img_gray = cv2.cvtColor(self.canvas, cv2.COLOR_BGR2GRAY)
            img_inverted = cv2.bitwise_not(img_gray)
            points = cv2.findNonZero(img_inverted)
            if points is not None:
                x, y, w, h = cv2.boundingRect(points)
                margin = 30
                x = max(0, x - margin); y = max(0, y - margin)
                w = min(self.width - x, w + 2 * margin); h = min(self.height - y, h + 2 * margin)
                img_crop = img_inverted[y:y+h, x:x+w]
                if w > h:
                    pad_top = (w - h) // 2; pad_bottom = w - h - pad_top
                    img_square = cv2.copyMakeBorder(img_crop, pad_top, pad_bottom, 0, 0, cv2.BORDER_CONSTANT, value=0)
                else:
                    pad_left = (h - w) // 2; pad_right = h - w - pad_left
                    img_square = cv2.copyMakeBorder(img_crop, 0, 0, pad_left, pad_right, cv2.BORDER_CONSTANT, value=0)
                img_small = cv2.resize(img_square, (28, 28), interpolation=cv2.INTER_AREA)
                img_tensor = torch.from_numpy(img_small).float().div(255.0).unsqueeze(0).unsqueeze(0)
                with torch.no_grad():
                    img_tensor = img_tensor.to(self.device)
                    output = self.model(img_tensor)
                    probs = torch.softmax(output, dim=1)
                    p, idx = torch.max(probs, 1)
                    if p.item() > 0.1: self.prediction = self.labels[idx.item()]
        except Exception: pass 

    # --- 抽题画面绘制 ---
    def draw_selection_screen(self, img):
        # 1. 直接在传入的图片(这里是白板)上加深色遮罩
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (self.width, self.height), (20, 20, 30), -1) 
        alpha = 0.8 # 遮罩稍微深一点，突出中间
        img = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)

        # 2. 直接计算中心
        center_x, center_y = self.width // 2, self.height // 2
        box_w, box_h = 640, 360 
        box_x1, box_y1 = center_x - box_w // 2, center_y - box_h // 2
        box_x2, box_y2 = center_x + box_w // 2, center_y + box_h // 2

        # 3. 绘制弹窗背景
        shadow_offset = 10
        cv2.rectangle(img, (box_x1 + shadow_offset, box_y1 + shadow_offset), 
                      (box_x2 + shadow_offset, box_y2 + shadow_offset), (30, 30, 40), -1)
        
        cv2.rectangle(img, (box_x1, box_y1), (box_x2, box_y2), self.c_ui_bg, -1)
        cv2.rectangle(img, (box_x1, box_y1), (box_x2, box_y2), self.c_ui_border, 6) 
        cv2.rectangle(img, (box_x1+10, box_y1+10), (box_x2-10, box_y2-10), self.c_ui_border, 2) 

        # 4. 标题
        title_text = "Choosing Your Topic..."
        title_font = cv2.FONT_HERSHEY_DUPLEX
        title_scale = 1.3
        title_thickness = 2
        title_size = cv2.getTextSize(title_text, title_font, title_scale, title_thickness)[0]
        title_x = center_x - title_size[0] // 2
        title_y = box_y1 + 80 
        cv2.putText(img, title_text, (title_x, title_y), title_font, title_scale, self.c_text_light, title_thickness)

        # 5. 动态题目
        elapsed = time.time() - self.selection_start_time
        remaining = self.selection_duration - elapsed

        if remaining > 0.5:
            if self.frame_count % 4 == 0:
                self.current_display_topic = random.choice(self.labels)
            topic_to_show = self.current_display_topic
            topic_color = self.c_text_light
        else:
            topic_to_show = self.target_topic
            topic_color = self.c_text_accent 

        topic_font = cv2.FONT_HERSHEY_TRIPLEX
        topic_scale = 2.8
        topic_thickness = 4
        text_size = cv2.getTextSize(topic_to_show.upper(), topic_font, topic_scale, topic_thickness)[0]
        
        text_x = center_x - text_size[0] // 2
        text_y = center_y + text_size[1] // 2 + 20 

        cv2.putText(img, topic_to_show.upper(), (text_x, text_y), topic_font, topic_scale, (0,0,0), topic_thickness+4)
        cv2.putText(img, topic_to_show.upper(), (text_x, text_y), topic_font, topic_scale, topic_color, topic_thickness)

        return img

    def draw_topic_overlay(self, img):
        panel_x, panel_y = 20, 100 
        panel_w, panel_h = 250, 70

        overlay = img.copy()
        cv2.rectangle(overlay, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), self.c_ui_bg, -1)
        img = cv2.addWeighted(overlay, 0.7, img, 0.3, 0)
        cv2.rectangle(img, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), self.c_ui_border, 2)

        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(img, "YOUR TOPIC:", (panel_x + 15, panel_y + 25), font, 0.5, (180, 180, 180), 1)
        cv2.putText(img, self.target_topic.upper(), (panel_x + 15, panel_y + 55), cv2.FONT_HERSHEY_DUPLEX, 0.9, self.c_text_accent, 2)
        return img

    def draw_ui_overlay(self, img):
        if self.state != 'PLAYING': return img

        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.rectangle(img, (20, 20), (160, 80), self.c_btn_clear, -1)
        cv2.rectangle(img, (20, 20), (160, 80), self.c_ui_border, 2)
        cv2.putText(img, "CLEAR", (45, 62), cv2.FONT_HERSHEY_DUPLEX, 0.8, self.c_text_light, 2)
        
        panel_x, panel_y, panel_w, panel_h = 440, 15, 400, 90
        cv2.rectangle(img, (panel_x, panel_y), (panel_x+panel_w, panel_y+panel_h), self.c_ui_bg, -1)
        cv2.rectangle(img, (panel_x, panel_y), (panel_x+panel_w, panel_y+panel_h), self.c_ui_border, 2)
        cv2.putText(img, "AI GUESS:", (panel_x + 20, panel_y + 35), font, 0.6, (180, 180, 180), 1)
        
        res_color = self.c_text_light if self.model_loaded else (200, 0, 0)
        if self.prediction.lower() == self.target_topic.lower():
             res_color = (0, 255, 0)

        text_size = cv2.getTextSize(self.prediction, cv2.FONT_HERSHEY_DUPLEX, 1.3, 3)[0]
        text_x = panel_x + (panel_w - text_size[0]) // 2
        cv2.putText(img, self.prediction, (text_x, panel_y + 75), cv2.FONT_HERSHEY_DUPLEX, 1.3, res_color, 3)

        mode_x, mode_y, mode_w, mode_h = 900, 25, 300, 70
        cv2.rectangle(img, (mode_x, mode_y), (mode_x+mode_w, mode_y+mode_h), (240, 248, 255), -1) 
        cv2.rectangle(img, (mode_x, mode_y), (mode_x+mode_w, mode_y+mode_h), (176, 224, 230), 2)
        cv2.putText(img, "MODE:", (mode_x + 15, mode_y + 25), font, 0.5, (100, 100, 100), 1)
        
        status_color = (0, 120, 215)
        if "HOVER" in self.status_text: status_color = (100, 100, 100)
        if "DRAW" in self.status_text: status_color = (0, 180, 0)
        if "ERASER" in self.status_text: status_color = (0, 0, 255)
        if "Protected" in self.status_text: status_color = (255, 0, 0)
        
        cv2.putText(img, self.status_text, (mode_x + 15, mode_y + 55), font, 0.8, status_color, 2)
        img = self.draw_topic_overlay(img)
        return img

    def count_fingers(self, lm):
        pts = lm.landmark
        fingers = []
        if pts[4].x < pts[3].x: fingers.append(1)
        else: fingers.append(0)
        for id in [8, 12, 16, 20]:
            if pts[id].y < pts[id-2].y: fingers.append(1)
            else: fingers.append(0)
        total = sum(fingers)
        if abs(pts[4].x - pts[3].x) < 0.02: 
            if fingers[0] == 1: total -= 1
        return total

    def process(self, frame):
        self.frame_count += 1
        # 无论摄像头是640x480还是其他，统一拉伸到 1280x720
        # 这样就能保证坐标体系永远是对齐的
        frame = cv2.resize(frame, (self.width, self.height))
        # ================= 状态 1：抽题中 =================
        if self.state == 'SELECTING':
            if time.time() - self.selection_start_time > self.selection_duration:
                self.state = 'PLAYING'
                self.points_queue.clear()
                self.xp, self.yp = 0, 0
            
            # 复制一份 self.canvas (它是白色的) 作为底图
            white_bg = self.canvas.copy()
            return self.draw_selection_screen(white_bg)

        # ================= 状态 2：游戏中 (PLAYING) =================
        try:
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(img_rgb)
            
            pip_scale = 0.25 
            pip_w, pip_h = int(self.width * pip_scale), int(self.height * pip_scale)
            
            if results.multi_hand_landmarks:
                 for hand_landmarks in results.multi_hand_landmarks:
                    self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
            
            frame_small = cv2.resize(frame, (pip_w, pip_h))
            self.status_text = "..." 

            if results.multi_hand_landmarks:
                for lm in results.multi_hand_landmarks:
                    pts = lm.landmark
                    x1, y1 = int(pts[8].x * self.width), int(pts[8].y * self.height)
                    
                    is_near_edge = False
                    edge_margin = 40
                    if (x1 < edge_margin or x1 > self.width - edge_margin or 
                        y1 < edge_margin or y1 > self.height - edge_margin):
                        is_near_edge = True

                    finger_count = self.count_fingers(lm)
                    
                    dist_sq = (x1 - self.prev_cx)**2 + (y1 - self.prev_cy)**2
                    if dist_sq < 9: x1, y1 = self.prev_cx, self.prev_cy
                    dist = math.sqrt(dist_sq)
                    target_factor = np.interp(dist, [5, 60], [0.15, 0.7])
                    self.smooth_factor = 0.7 * self.smooth_factor + 0.3 * target_factor
                    cx = int(self.prev_cx * (1 - self.smooth_factor) + x1 * self.smooth_factor)
                    cy = int(self.prev_cy * (1 - self.smooth_factor) + y1 * self.smooth_factor)
                    
                    self.points_queue.append((cx, cy))
                    avg_x = int(sum(p[0] for p in self.points_queue) / len(self.points_queue))
                    avg_y = int(sum(p[1] for p in self.points_queue) / len(self.points_queue))
                    cx, cy = avg_x, avg_y
                    self.prev_cx, self.prev_cy = cx, cy

                    fingers = [
                        1 if pts[4].x < pts[3].x else 0,
                        1 if pts[8].y < pts[6].y else 0,
                        1 if pts[12].y < pts[10].y else 0,
                        1 if pts[16].y < pts[14].y else 0,
                        1 if pts[20].y < pts[18].y else 0
                    ]

                    # A. 清空
                    if finger_count >= 4:
                        if not is_near_edge:
                            self.canvas[:] = 255
                            self.status_text = "CLEARING..." 
                            self.prediction = "..."          
                            self.xp, self.yp = 0, 0
                        else: self.status_text = "Edge Protected"

                    # B. 移动
                    elif fingers[1] == 1 and fingers[2] == 1 and fingers[3] == 0 and fingers[4] == 0:
                        self.xp, self.yp = cx, cy
                        self.status_text = "HOVER"
                        self.points_queue.clear()

                    # C. 画画
                    elif fingers[1] == 1 and fingers[2] == 0 and fingers[3] == 0 and fingers[4] == 0:
                        self.status_text = "DRAWING"     
                        if self.xp == 0 and self.yp == 0: self.xp, self.yp = cx, cy
                        
                        target_thickness = int(np.interp(dist, [5, 50], [18, 6]))
                        self.brush_thickness = int(self.prev_thickness * 0.8 + target_thickness * 0.2)
                        self.prev_thickness = self.brush_thickness
                        
                        cv2.line(self.canvas, (self.xp, self.yp), (cx, cy), self.c_ink, self.brush_thickness)
                        cv2.circle(self.canvas, (cx, cy), self.brush_thickness//2, self.c_ink, -1)
                        self.xp, self.yp = cx, cy
                        
                        if self.frame_count % 15 == 0: self.predict()

                    # D. 橡皮擦
                    elif finger_count == 0:
                        if not is_near_edge:
                            self.status_text = "ERASER"      
                            ex, ey = int(pts[9].x * self.width), int(pts[9].y * self.height)
                            self.eraser_cx, self.eraser_cy = ex, ey
                            if self.xp == 0 and self.yp == 0: self.xp, self.yp = ex, ey
                            cv2.line(self.canvas, (self.xp, self.yp), (ex, ey), self.c_eraser, self.eraser_thickness)
                            cv2.circle(self.canvas, (ex, ey), self.eraser_thickness//2, self.c_eraser, -1)
                            self.xp, self.yp = ex, ey
                        else: self.status_text = "Edge Protected"
                    else:
                        self.status_text = "Waiting..."
                        self.points_queue.clear()

            final_view = self.canvas.copy()
            if results.multi_hand_landmarks:
                 if "HOVER" in self.status_text:
                    cv2.circle(final_view, (self.prev_cx, self.prev_cy), 8, self.c_text_accent, 2)
                 elif "ERASER" in self.status_text and "Protected" not in self.status_text:
                    cv2.circle(final_view, (self.eraser_cx, self.eraser_cy), self.eraser_thickness // 2, (180, 180, 180), 3)
                    cv2.circle(final_view, (self.eraser_cx, self.eraser_cy), 4, (180, 180, 180), -1)

            final_view = self.draw_ui_overlay(final_view)
            
            y_off, x_off = self.height - pip_h - 20, self.width - pip_w - 20
            cv2.rectangle(final_view, (x_off-4, y_off-4), (x_off+pip_w+4, y_off+pip_h+4), self.c_ui_border, -1)
            final_view[y_off:y_off+pip_h, x_off:x_off+pip_w] = frame_small
            return final_view

        except Exception as e:
            print(f"绘画处理出错: {e}")
            traceback.print_exc()
            return frame