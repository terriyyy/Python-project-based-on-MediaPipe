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
                    self.labels = [line.strip() for line in f.read().splitlines() if line.strip()]
                if len(self.labels) > 0:
                    self.model = DrawCNN(len(self.labels)).to(self.device)
                    self.model.load_state_dict(torch.load(model_path, map_location=self.device))
                    self.model.eval()
                    self.model_loaded = True
                    print(f">>> [你画我猜] 模型加载成功！共 {len(self.labels)} 个题目。")
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

        self.state = 'SELECTING' # 状态: SELECTING (抽题) -> PLAYING (游戏) -> GAME_OVER (结算)
        self.selection_start_time = time.time()
        self.selection_duration = 3.0 
        
        # 游戏数据
        self.score = 0
        self.game_start_time = 0
        self.game_duration = 60.0 # 游戏限时 60 秒
        self.time_left = self.game_duration

        self.target_topic = random.choice(self.labels) if self.labels else "apple"
        self.current_display_topic = "..." 

        # UI颜色定义
        self.c_ink = (0, 0, 0)
        self.c_eraser = (255, 255, 255)
        self.c_ui_bg = (60, 60, 80)  
        self.c_ui_border = (100, 100, 140)
        self.c_text_light = (240, 240, 240)
        self.c_text_accent = (0, 200, 255) 
        self.c_text_correct = (0, 255, 0)
        self.c_btn_clear = (80, 80, 220)
        self.c_btn_skip = (220, 100, 80) # 跳过按钮颜色

    def reset_round(self):
        """重置回合（清空画布，换新题）"""
        self.canvas[:] = 255
        self.xp, self.yp = 0, 0
        self.points_queue.clear()
        self.prediction = "..."
        # 换一个不重复的题目
        new_topic = random.choice(self.labels)
        while new_topic == self.target_topic and len(self.labels) > 1:
            new_topic = random.choice(self.labels)
        self.target_topic = new_topic

    def check_correct_guess(self):
        """检查AI是否猜对"""
        if self.prediction.lower() == self.target_topic.lower():
            # 猜对了！
            self.score += 1
            print(f"✅ Correct! Score: {self.score}")
            self.reset_round()
            return True
        return False

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
                    if p.item() > 0.1: 
                        self.prediction = self.labels[idx.item()]
                        # 每次预测完立刻检查是否正确
                        self.check_correct_guess()
        except Exception: pass 

    # --- 抽题画面绘制 ---
    def draw_selection_screen(self, img):
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (self.width, self.height), (20, 20, 30), -1) 
        alpha = 0.8 
        img = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)

        center_x, center_y = self.width // 2, self.height // 2
        box_w, box_h = 640, 360 
        box_x1, box_y1 = center_x - box_w // 2, center_y - box_h // 2
        box_x2, box_y2 = center_x + box_w // 2, center_y + box_h // 2

        # 背景框
        cv2.rectangle(img, (box_x1, box_y1), (box_x2, box_y2), self.c_ui_bg, -1)
        cv2.rectangle(img, (box_x1, box_y1), (box_x2, box_y2), self.c_ui_border, 6) 

        # 标题
        title_text = "Get Ready!"
        if self.state == 'GAME_OVER':
            title_text = "Time's Up!"
        
        cv2.putText(img, title_text, (center_x - 100, box_y1 + 80), cv2.FONT_HERSHEY_DUPLEX, 1.5, self.c_text_light, 2)

        # 动态内容
        if self.state == 'SELECTING':
            elapsed = time.time() - self.selection_start_time
            remaining = self.selection_duration - elapsed
            if remaining > 0.5:
                if self.frame_count % 4 == 0:
                    self.current_display_topic = random.choice(self.labels)
                topic_to_show = self.current_display_topic
            else:
                topic_to_show = "START!"
            
            # 显示倒计时
            cv2.putText(img, f"{int(remaining)+1}", (center_x - 20, center_y + 50), cv2.FONT_HERSHEY_TRIPLEX, 3, self.c_text_accent, 4)

        elif self.state == 'GAME_OVER':
            # 结算画面
            cv2.putText(img, f"Final Score: {self.score}", (center_x - 180, center_y + 20), cv2.FONT_HERSHEY_TRIPLEX, 2, self.c_text_correct, 3)
            cv2.putText(img, "Show 'Palm' to Restart", (center_x - 160, center_y + 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 1)

        return img

    def draw_topic_overlay(self, img):
        # 左上角题目显示
        panel_x, panel_y = 20, 100 
        panel_w, panel_h = 250, 70

        overlay = img.copy()
        cv2.rectangle(overlay, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), self.c_ui_bg, -1)
        img = cv2.addWeighted(overlay, 0.7, img, 0.3, 0)
        cv2.rectangle(img, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), self.c_ui_border, 2)

        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(img, "DRAW THIS:", (panel_x + 15, panel_y + 25), font, 0.5, (180, 180, 180), 1)
        cv2.putText(img, self.target_topic.upper(), (panel_x + 15, panel_y + 55), cv2.FONT_HERSHEY_DUPLEX, 0.9, self.c_text_accent, 2)
        return img

    def draw_game_stats(self, img):
        # 绘制分数和倒计时
        cv2.putText(img, f"Score: {self.score}", (self.width - 250, 60), cv2.FONT_HERSHEY_DUPLEX, 1.2, self.c_text_correct, 2)
        
        time_color = self.c_text_light
        if self.time_left < 10: time_color = (0, 0, 255) 
        cv2.putText(img, f"Time: {int(self.time_left)}s", (self.width - 250, 110), cv2.FONT_HERSHEY_DUPLEX, 1.0, time_color, 2)
        
        return img

    def draw_ui_overlay(self, img):
        if self.state != 'PLAYING': return img

        # 1. Clear Button
        btn_clear_x, btn_clear_y = 20, 20
        cv2.rectangle(img, (btn_clear_x, btn_clear_y), (btn_clear_x+100, btn_clear_y+60), self.c_btn_clear, -1)
        cv2.putText(img, "CLEAR", (btn_clear_x+15, btn_clear_y+40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.c_text_light, 2)
        
        # 2. Skip Button
        btn_skip_x, btn_skip_y = 140, 20
        cv2.rectangle(img, (btn_skip_x, btn_skip_y), (btn_skip_x+100, btn_skip_y+60), self.c_btn_skip, -1)
        cv2.putText(img, "SKIP", (btn_skip_x+25, btn_skip_y+40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.c_text_light, 2)

        # 3. AI Guess Panel
        panel_x, panel_y, panel_w, panel_h = 440, 15, 400, 90
        cv2.rectangle(img, (panel_x, panel_y), (panel_x+panel_w, panel_y+panel_h), self.c_ui_bg, -1)
        cv2.putText(img, "AI GUESS:", (panel_x + 20, panel_y + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1)
        
        res_color = self.c_text_light
        if self.prediction.lower() == self.target_topic.lower(): res_color = (0, 255, 0)
        
        text_size = cv2.getTextSize(self.prediction, cv2.FONT_HERSHEY_DUPLEX, 1.3, 3)[0]
        text_x = panel_x + (panel_w - text_size[0]) // 2
        cv2.putText(img, self.prediction, (text_x, panel_y + 75), cv2.FONT_HERSHEY_DUPLEX, 1.3, res_color, 3)

        img = self.draw_topic_overlay(img)
        img = self.draw_game_stats(img) 
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
        frame = cv2.resize(frame, (self.width, self.height))

        # === 状态 1: 准备/抽题 ===
        if self.state == 'SELECTING':
            if time.time() - self.selection_start_time > self.selection_duration:
                self.state = 'PLAYING'
                self.game_start_time = time.time() 
                self.score = 0
                self.points_queue.clear()
                self.xp, self.yp = 0, 0
                self.reset_round() 
            
            white_bg = self.canvas.copy()
            return self.draw_selection_screen(white_bg)

        # === 状态 3: 游戏结算 ===
        if self.state == 'GAME_OVER':
            white_bg = self.canvas.copy()
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(img_rgb)
            if results.multi_hand_landmarks:
                for lm in results.multi_hand_landmarks:
                    if self.count_fingers(lm) >= 4: # 张开手掌重开
                         self.state = 'SELECTING'
                         self.selection_start_time = time.time()
            return self.draw_selection_screen(white_bg)

        # === 状态 2: 游戏中 (PLAYING) ===
        elapsed = time.time() - self.game_start_time
        self.time_left = max(0, self.game_duration - elapsed)
        if self.time_left <= 0:
            self.state = 'GAME_OVER'
        
        try:
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(img_rgb)
            
            if results.multi_hand_landmarks:
                for lm in results.multi_hand_landmarks:
                    pts = lm.landmark
                    x1, y1 = int(pts[8].x * self.width), int(pts[8].y * self.height)
                    
                    finger_count = self.count_fingers(lm)
                    
                    # 边缘检测防止误触
                    is_near_edge = False
                    edge_margin = 60 # 加大边缘保护区
                    if (x1 < edge_margin or x1 > self.width - edge_margin or 
                        y1 < edge_margin or y1 > self.height - edge_margin):
                        is_near_edge = True

                    # 平滑处理
                    dist_sq = (x1 - self.prev_cx)**2 + (y1 - self.prev_cy)**2
                    if dist_sq < 9: x1, y1 = self.prev_cx, self.prev_cy
                    self.points_queue.append((x1, y1))
                    avg_x = int(sum(p[0] for p in self.points_queue) / len(self.points_queue))
                    avg_y = int(sum(p[1] for p in self.points_queue) / len(self.points_queue))
                    cx, cy = avg_x, avg_y
                    self.prev_cx, self.prev_cy = cx, cy
                    
                    fingers = [1 if pts[4].x < pts[3].x else 0] + \
                              [1 if pts[id].y < pts[id-2].y else 0 for id in [8, 12, 16, 20]]

        
                    # 如果张开手掌 (手指>=4) 且不在边缘保护区 -> 清空
                    if finger_count >= 4:
                        if not is_near_edge:
                            self.canvas[:] = 255
                            self.prediction = "..."
                            self.xp, self.yp = 0, 0
                            self.status_text = "CLEARED (PALM)"
                        else:
                            self.status_text = "Protected Zone"

                    # 按钮检测 (食指点击)
                    elif fingers[1] == 1 and fingers[2] == 0: 
                        # CLEAR 按钮
                        if 20 < cx < 120 and 20 < cy < 80:
                            self.canvas[:] = 255
                            self.prediction = "..."
                            self.xp, self.yp = 0, 0
                            self.status_text = "CLEARED"
                        # SKIP 按钮
                        elif 140 < cx < 240 and 20 < cy < 80:
                            self.reset_round()
                            self.status_text = "SKIPPED"
                            time.sleep(0.2) 

                        # 绘画 (非按钮区域)
                        else:
                            if self.xp == 0 and self.yp == 0: self.xp, self.yp = cx, cy
                            cv2.line(self.canvas, (self.xp, self.yp), (cx, cy), self.c_ink, self.brush_thickness)
                            cv2.circle(self.canvas, (cx, cy), self.brush_thickness//2, self.c_ink, -1)
                            self.xp, self.yp = cx, cy
                            self.status_text = "DRAWING"
                            if self.frame_count % 15 == 0: self.predict()

                    # 移动 (食指+中指)
                    elif fingers[1] == 1 and fingers[2] == 1:
                        self.xp, self.yp = cx, cy
                        self.status_text = "HOVER"
                        self.points_queue.clear()
                    
                    # 橡皮 (拳头)
                    elif finger_count == 0:
                        ex, ey = int(pts[9].x * self.width), int(pts[9].y * self.height)
                        cv2.line(self.canvas, (self.xp, self.yp), (ex, ey), self.c_eraser, self.eraser_thickness)
                        cv2.circle(self.canvas, (ex, ey), self.eraser_thickness//2, self.c_eraser, -1)
                        self.xp, self.yp = ex, ey
                        self.status_text = "ERASER"
                    else:
                        self.xp, self.yp = 0, 0 

            # 合成画面
            final_view = self.canvas.copy()
            if results.multi_hand_landmarks:
                 if "HOVER" in self.status_text:
                    cv2.circle(final_view, (self.prev_cx, self.prev_cy), 8, self.c_text_accent, 2)
                 elif "ERASER" in self.status_text:
                    cv2.circle(final_view, (self.prev_cx, self.prev_cy), self.eraser_thickness // 2, (200,200,200), 2)

            final_view = self.draw_ui_overlay(final_view)
            
            pip_w, pip_h = 320, 180
            frame_small = cv2.resize(frame, (pip_w, pip_h))
            y_off, x_off = self.height - pip_h - 20, self.width - pip_w - 20
            cv2.rectangle(final_view, (x_off-4, y_off-4), (x_off+pip_w+4, y_off+pip_h+4), self.c_ui_border, -1)
            final_view[y_off:y_off+pip_h, x_off:x_off+pip_w] = frame_small
            
            return final_view

        except Exception as e:
            traceback.print_exc()
            return frame