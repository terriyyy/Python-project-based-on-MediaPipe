import cv2
import numpy as np
import mediapipe as mp
import torch
import os
import math
import traceback
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
        
        # 2. 加载模型
        self.model_loaded = False
        self.labels = []
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        if os.path.exists(label_path) and os.path.exists(model_path):
            try:
                with open(label_path, 'r') as f:
                    self.labels = f.read().splitlines()
                if len(self.labels) > 0:
                    self.model = DrawCNN(len(self.labels)).to(self.device)
                    self.model.load_state_dict(torch.load(model_path, map_location=self.device))
                    self.model.eval()
                    self.model_loaded = True
            except Exception as e:
                print(f"[你画我猜] 加载出错: {e}")
        else:
            print("[你画我猜] 无模型文件")

        # 3. MediaPipe
        self.mp_hands = mp.solutions.hands
        # 提高追踪稳定性
        self.hands = self.mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)
        self.mp_draw = mp.solutions.drawing_utils
        
        # 4. 画布设置
        self.width = 1280
        self.height = 720
        self.canvas = np.full((self.height, self.width, 3), 255, dtype=np.uint8)
        
        # 5. 笔触与工具变量
        self.xp, self.yp = 0, 0
        self.brush_thickness = 10     
        self.eraser_thickness = 80    # 橡皮擦直径
        
        # 动态平滑变量
        self.prev_cx, self.prev_cy = 0, 0
        # ✨ 新增：专门记录橡皮擦(掌心)的位置
        self.eraser_cx, self.eraser_cy = 0, 0 
        self.smooth_factor = 0.5      
        self.prev_thickness = 10      
        
        # 历史点队列
        self.points_queue = deque(maxlen=4) 

        # 状态
        self.prediction = "..."       
        self.status_text = "Ready"    
        
        # UI颜色
        self.c_ink = (0, 0, 0)
        self.c_eraser = (255, 255, 255)
        self.c_btn_clear = (255, 80, 80)
        self.c_btn_text = (255, 255, 255)
        self.c_panel_bg = (255, 255, 255)
        self.c_panel_border = (200, 200, 200)
        self.c_mode_text = (0, 120, 215) 
        self.c_cursor_hover = (255, 140, 0) # 橙色悬停光标
        self.c_cursor_eraser = (180, 180, 180) # 灰色橡皮光标

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

    def draw_ui_overlay(self, img):
        font = cv2.FONT_HERSHEY_SIMPLEX
        # Clear Button
        cv2.rectangle(img, (25, 25), (165, 85), (220, 220, 220), -1) 
        cv2.rectangle(img, (20, 20), (160, 80), self.c_btn_clear, -1)
        cv2.putText(img, "CLEAR", (45, 62), font, 0.9, self.c_btn_text, 2)
        
        # AI Panel
        panel_x, panel_y, panel_w, panel_h = 440, 15, 400, 90
        cv2.rectangle(img, (panel_x, panel_y), (panel_x+panel_w, panel_y+panel_h), self.c_panel_bg, -1)
        cv2.rectangle(img, (panel_x, panel_y), (panel_x+panel_w, panel_y+panel_h), self.c_panel_border, 2)
        cv2.putText(img, "AI GUESS:", (panel_x + 20, panel_y + 35), font, 0.6, (150, 150, 150), 1)
        res_color = (0, 0, 0) if self.model_loaded else (200, 0, 0)
        text_size = cv2.getTextSize(self.prediction, font, 1.5, 3)[0]
        text_x = panel_x + (panel_w - text_size[0]) // 2
        cv2.putText(img, self.prediction, (text_x, panel_y + 75), font, 1.5, res_color, 3)

        # Mode Panel
        mode_x, mode_y, mode_w, mode_h = 900, 25, 300, 70
        cv2.rectangle(img, (mode_x, mode_y), (mode_x+mode_w, mode_y+mode_h), (240, 248, 255), -1) 
        cv2.rectangle(img, (mode_x, mode_y), (mode_x+mode_w, mode_y+mode_h), (176, 224, 230), 2)
        cv2.putText(img, "MODE:", (mode_x + 15, mode_y + 25), font, 0.5, (100, 100, 100), 1)
        
        status_color = self.c_mode_text
        if "HOVER" in self.status_text: status_color = (100, 100, 100)
        if "DRAW" in self.status_text: status_color = (0, 180, 0)
        if "ERASER" in self.status_text: status_color = (0, 0, 255)
        if "Protected" in self.status_text: status_color = (255, 0, 0)
        
        cv2.putText(img, self.status_text, (mode_x + 15, mode_y + 55), font, 0.8, status_color, 2)
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
        try:
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(img_rgb)
            
            pip_scale = 0.25 
            pip_w, pip_h = int(self.width * pip_scale), int(self.height * pip_scale)
            frame_small = cv2.resize(frame, (pip_w, pip_h))
            
            if results.multi_hand_landmarks:
                 for hand_landmarks in results.multi_hand_landmarks:
                    self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                 frame_small = cv2.resize(frame, (pip_w, pip_h))

            self.status_text = "..." 

            if results.multi_hand_landmarks:
                for lm in results.multi_hand_landmarks:
                    pts = lm.landmark
                    # 食指指尖坐标 (用于绘画/悬停)
                    x1, y1 = int(pts[8].x * self.width), int(pts[8].y * self.height)
                    
                    # 边缘保护检查
                    is_near_edge = False
                    edge_margin = 40
                    if (x1 < edge_margin or x1 > self.width - edge_margin or 
                        y1 < edge_margin or y1 > self.height - edge_margin):
                        is_near_edge = True

                    finger_count = self.count_fingers(lm)

                    # 动态平滑处理 (针对食指)
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
                    # ---------------------------

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

                    # B. 移动 (HOVER)
                    elif fingers[1] == 1 and fingers[2] == 1 and fingers[3] == 0 and fingers[4] == 0:
                        self.xp, self.yp = cx, cy
                        self.status_text = "HOVER"
                        self.points_queue.clear()

                    # C. 画画 (DRAW)
                    elif fingers[1] == 1 and fingers[2] == 0 and fingers[3] == 0 and fingers[4] == 0:
                        self.status_text = "DRAWING"     
                        if self.xp == 0 and self.yp == 0: self.xp, self.yp = cx, cy
                        
                        target_thickness = int(np.interp(dist, [5, 50], [18, 6]))
                        self.brush_thickness = int(self.prev_thickness * 0.8 + target_thickness * 0.2)
                        self.prev_thickness = self.brush_thickness
                        
                        cv2.line(self.canvas, (self.xp, self.yp), (cx, cy), self.c_ink, self.brush_thickness)
                        cv2.circle(self.canvas, (cx, cy), self.brush_thickness//2, self.c_ink, -1)
                        self.xp, self.yp = cx, cy
                        
                        if hasattr(self, 'frame_count'): self.frame_count += 1
                        else: self.frame_count = 0
                        if self.frame_count % 15 == 0: self.predict()

                    # D. 橡皮擦 (ERASER)
                    elif finger_count == 0:
                        if not is_near_edge:
                            self.status_text = "ERASER"      
                            # 获取掌心坐标
                            ex, ey = int(pts[9].x * self.width), int(pts[9].y * self.height)
                            # ✨ 更新全局橡皮擦坐标用于显示
                            self.eraser_cx, self.eraser_cy = ex, ey
                            
                            if self.xp == 0 and self.yp == 0: self.xp, self.yp = ex, ey
                            
                            # 在画布上执行擦除 (画白线)
                            cv2.line(self.canvas, (self.xp, self.yp), (ex, ey), self.c_eraser, self.eraser_thickness)
                            cv2.circle(self.canvas, (ex, ey), self.eraser_thickness//2, self.c_eraser, -1)
                            # 移除了这里在小窗口画圈的代码，统一放到后面大窗口画
                            self.xp, self.yp = ex, ey
                        else: self.status_text = "Edge Protected"
                    
                    else:
                        self.status_text = "Waiting..."
                        self.points_queue.clear()

            # === 最终画面合成 ===
            final_view = self.canvas.copy()
            
            if results.multi_hand_landmarks:
                 # 悬停光标 (橙色小圆)
                 if "HOVER" in self.status_text:
                    cv2.circle(final_view, (self.prev_cx, self.prev_cy), 8, self.c_cursor_hover, 2)
                 # 只有在橡皮擦模式下才显示
                 elif "ERASER" in self.status_text and "Protected" not in self.status_text:
                    # 画一个空心圆，半径等于橡皮擦的一半
                    cv2.circle(final_view, (self.eraser_cx, self.eraser_cy), self.eraser_thickness // 2, self.c_cursor_eraser, 3)
                    # 画一个中心点辅助定位
                    cv2.circle(final_view, (self.eraser_cx, self.eraser_cy), 4, self.c_cursor_eraser, -1)

            final_view = self.draw_ui_overlay(final_view)
            y_off, x_off = self.height - pip_h - 20, self.width - pip_w - 20
            cv2.rectangle(final_view, (x_off-4, y_off-4), (x_off+pip_w+4, y_off+pip_h+4), (200, 200, 200), -1)
            final_view[y_off:y_off+pip_h, x_off:x_off+pip_w] = frame_small
            return final_view

        except Exception as e:
            print(f"绘画处理出错: {e}")
            traceback.print_exc()
            return frame