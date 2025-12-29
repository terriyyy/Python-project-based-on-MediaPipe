# games/maze_game.py
import cv2
import numpy as np
import time
import random
from .base_game import BaseGame

class MazeGame(BaseGame):
    def __init__(self):
        super().__init__()
        # --- 游戏核心配置 ---
        self.level = 1
        self.max_levels = 15
        self.last_move_time = 0
        self.move_interval = 0.5
        
        # 计时器相关
        self.start_time = time.time()       
        self.global_start_time = 0          
        self.final_total_time = 0           
        
        # --- 视觉动画属性 ---
        self.visual_pos = [0.0, 0.0] 
        self.trail = [] 
        
        # --- 画面配置 ---
        self.canvas_w, self.canvas_h = 1280, 720
        self.sidebar_w = 380
        self.maze_area_w = self.canvas_w - self.sidebar_w
        
        self.game_state = "INTRO" 
        self.init_level()

    def start_game(self):
        self.game_state = "PLAYING"
        current_t = time.time()
        self.start_time = current_t        
        self.global_start_time = current_t 

    def init_level(self):
        """初始化关卡"""
        self.cols = 10 + (self.level // 2)
        self.rows = 8 + (self.level // 2)
        
        # 生成迷宫
        raw_maze = self.generate_maze(self.cols, self.rows)
        
        # 起终点
        start_x, start_y = 0, 0
        end_x, end_y = self.cols - 1, self.rows - 1

        # 随机镜像
        if random.choice([True, False]):
            raw_maze = np.fliplr(raw_maze)
            start_x = self.cols - 1 - start_x
            end_x = self.cols - 1 - end_x

        if random.choice([True, False]):
            raw_maze = np.flipud(raw_maze)
            start_y = self.rows - 1 - start_y
            end_y = self.rows - 1 - end_y

        self.maze = raw_maze
        self.player_pos = [start_x, start_y]
        self.end_pos = [end_x, end_y]
        
        # 重置视觉坐标与逻辑坐标一致
        self.visual_pos = [float(start_x), float(start_y)]
        self.trail = []
        
        if not hasattr(self, 'game_state'): 
            self.game_state = "INTRO"
        elif self.game_state != "INTRO":
            self.game_state = "PLAYING"
            self.start_time = time.time() 

    def generate_maze(self, w, h):
        """DFS 算法生成迷宫"""
        maze = np.zeros((h, w), dtype=int)
        stack = [(0, 0)]
        maze[0, 0] = 1
        
        while stack:
            current = stack[-1]
            x, y = current
            neighbors = []
            for dx, dy in [(-2,0), (2,0), (0,-2), (0,2)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and maze[ny, nx] == 0:
                    neighbors.append((nx, ny, dx//2, dy//2))
            
            if neighbors:
                nx, ny, wx, wy = random.choice(neighbors)
                maze[ny, nx] = 1
                maze[y + wy, x + wx] = 1
                stack.append((nx, ny))
            else:
                stack.pop()
        
        maze[h-1, w-1] = 1 
        maze[h-1, w-2] = 1
        maze[h-2, w-1] = 1
        return maze

    def detect_gesture(self, landmarks):
        """识别食指方向"""
        wrist = landmarks.landmark[0]
        index_tip = landmarks.landmark[8]
        dx = index_tip.x - wrist.x
        dy = index_tip.y - wrist.y
        threshold = 0.1 
        
        if abs(dx) > abs(dy):
            return "RIGHT" if dx > threshold else "LEFT" if dx < -threshold else "NONE"
        else:
            return "DOWN" if dy > threshold else "UP" if dy < -threshold else "NONE"

    def draw_arrow(self, img, command, center_x, center_y, size=50):
        """绘制动态方向箭头"""
        if command == "NONE":
            cv2.circle(img, (center_x, center_y), 20, (100, 100, 100), 2)
            return

        color = (0, 255, 255) 
        thickness = 5
        
        if command == "UP":
            p1 = (center_x, center_y + size)
            p2 = (center_x, center_y - size)
            arrow_p1 = (center_x - 20, center_y - size + 20)
            arrow_p2 = (center_x + 20, center_y - size + 20)
        elif command == "DOWN":
            p1 = (center_x, center_y - size)
            p2 = (center_x, center_y + size)
            arrow_p1 = (center_x - 20, center_y + size - 20)
            arrow_p2 = (center_x + 20, center_y + size - 20)
        elif command == "LEFT":
            p1 = (center_x + size, center_y)
            p2 = (center_x - size, center_y)
            arrow_p1 = (center_x - size + 20, center_y - 20)
            arrow_p2 = (center_x - size + 20, center_y + 20)
        elif command == "RIGHT":
            p1 = (center_x - size, center_y)
            p2 = (center_x + size, center_y)
            arrow_p1 = (center_x + size - 20, center_y - 20)
            arrow_p2 = (center_x + size - 20, center_y + 20)

        cv2.line(img, p1, p2, color, thickness)
        cv2.line(img, p2, arrow_p1, color, thickness)
        cv2.line(img, p2, arrow_p2, color, thickness)

    def update_and_draw(self, frame, results):
        canvas = np.zeros((self.canvas_h, self.canvas_w, 3), dtype=np.uint8)
        canvas[:] = (30, 30, 30)

        # 处理手势
        command = "NONE"
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                command = self.detect_gesture(hand_landmarks)

        current_time = time.time()
        
        # --- 胜利检测前置 ---
        # 确保玩家看到圆圈滑入终点后再触发胜利
        if self.game_state == "PLAYING" and self.player_pos == self.end_pos:
            dx = self.visual_pos[0] - self.player_pos[0]
            dy = self.visual_pos[1] - self.player_pos[1]
            dist = (dx**2 + dy**2)**0.5
            
            if dist < 0.1: # 动画播放完毕
                self.level += 1
                if self.level > self.max_levels:
                    self.level -= 1
                    self.game_state = "ALL_CLEARED"
                    self.final_total_time = current_time - self.global_start_time
                else:
                    self.init_level()

        # --- 游戏逻辑更新 ---
        if self.game_state == "PLAYING":
            # 只有未到达终点逻辑坐标时才移动
            if self.player_pos != self.end_pos:
                if current_time - self.last_move_time > self.move_interval and command != "NONE":
                    px, py = self.player_pos
                    new_x, new_y = px, py
                    if command == "UP": new_y -= 1
                    elif command == "DOWN": new_y += 1
                    elif command == "LEFT": new_x -= 1
                    elif command == "RIGHT": new_x += 1
                    
                    if 0 <= new_x < self.cols and 0 <= new_y < self.rows:
                        if self.maze[new_y, new_x] == 1:
                            self.player_pos = [new_x, new_y]
                            self.last_move_time = current_time

        # --- 视觉动画插值 ---
        target_x, target_y = self.player_pos
        self.visual_pos[0] += (target_x - self.visual_pos[0]) * 0.2
        self.visual_pos[1] += (target_y - self.visual_pos[1]) * 0.2
        
        if abs(self.visual_pos[0] - target_x) < 0.01: self.visual_pos[0] = float(target_x)
        if abs(self.visual_pos[1] - target_y) < 0.01: self.visual_pos[1] = float(target_y)

        # --- 更新残影队列 ---
        self.trail.append(tuple(self.visual_pos))
        if len(self.trail) > 8:
            self.trail.pop(0)

        # --- 绘图部分 ---

        # A. 绘制左侧迷宫区
        padding = 40
        available_w = self.maze_area_w - 2 * padding
        available_h = self.canvas_h - 2 * padding
        cell_size = min(available_w // self.cols, available_h // self.rows)
        
        offset_x = padding + (available_w - self.cols * cell_size) // 2
        offset_y = padding + (available_h - self.rows * cell_size) // 2

        # 迷宫
        for r in range(self.rows):
            for c in range(self.cols):
                x1 = offset_x + c * cell_size
                y1 = offset_y + r * cell_size
                x2, y2 = x1 + cell_size, y1 + cell_size
                
                if self.maze[r, c] == 1:
                    cv2.rectangle(canvas, (x1, y1), (x2, y2), (50, 50, 50), -1)
                    cv2.rectangle(canvas, (x1, y1), (x2, y2), (40, 40, 40), 1)
                else:
                    cv2.rectangle(canvas, (x1, y1), (x2, y2), (60, 40, 40), -1) 
                    cv2.line(canvas, (x1, y1), (x2, y1), (100, 80, 80), 2)
                    cv2.line(canvas, (x1, y1), (x1, y2), (100, 80, 80), 2)

        # 终点
        ex, ey = self.end_pos
        cx = offset_x + ex * cell_size + cell_size // 2
        cy = offset_y + ey * cell_size + cell_size // 2
        cv2.circle(canvas, (cx, cy), cell_size // 3, (0, 0, 200), -1)
        cv2.circle(canvas, (cx, cy), cell_size // 5, (0, 0, 255), -1)

        # --- [修改] 绘制清爽的残影 ---
        # 不再使用全屏 addWeighted，而是直接画圆，防止画面变灰变糊
        # 且最大半径限制为角色的一样大 (cell_size // 3)，避免“臃肿”
        for i, (tx, ty) in enumerate(self.trail):
            tcx = int(offset_x + tx * cell_size + cell_size // 2)
            tcy = int(offset_y + ty * cell_size + cell_size // 2)
            
            progress = (i + 1) / len(self.trail) 
            # 半径从0渐变到接近角色大小，但不超过角色
            radius = int((cell_size // 3.2) * progress) 
            
            # 颜色：深绿 -> 亮绿，模拟能量衰减
            # 头部 alpha 高，尾部 alpha 低
            color = (0, int(200 * progress), 0)
            cv2.circle(canvas, (tcx, tcy), radius, color, -1)

        # --- [修改] 绘制角色本体 ---
        vpx, vpy = self.visual_pos
        pcx = int(offset_x + vpx * cell_size + cell_size // 2)
        pcy = int(offset_y + vpy * cell_size + cell_size // 2)
        
        # 外圈光环
        cv2.circle(canvas, (pcx, pcy), cell_size // 3, (0, 255, 0), -1)
        # 内圈高光（白色核心），增加科技感
        cv2.circle(canvas, (pcx, pcy), cell_size // 6, (200, 255, 200), -1)
        # 描边
        cv2.circle(canvas, (pcx, pcy), cell_size // 3 + 1, (255, 255, 255), 1)

        # B. 绘制右侧侧边栏
        sidebar_x = self.maze_area_w
        cv2.rectangle(canvas, (sidebar_x, 0), (self.canvas_w, self.canvas_h), (20, 20, 20), -1)
        cv2.line(canvas, (sidebar_x, 0), (sidebar_x, self.canvas_h), (100, 100, 100), 2)

        # 摄像头
        cam_w = self.sidebar_w - 20
        cam_h = int(cam_w * 0.75) 
        cam_resized = cv2.resize(frame, (cam_w, cam_h))
        cv2.rectangle(canvas, (sidebar_x + 10 - 2, 10 - 2), 
                      (sidebar_x + 10 + cam_w + 2, 10 + cam_h + 2), (255, 255, 255), 2)
        canvas[10:10+cam_h, sidebar_x+10:sidebar_x+10+cam_w] = cam_resized

        # 状态信息
        info_start_y = 10 + cam_h + 40
        self.draw_arrow(canvas, command, sidebar_x + self.sidebar_w // 2, info_start_y + 40)
        
        text_y = info_start_y + 130
        line_height = 50
        font = cv2.FONT_HERSHEY_TRIPLEX

        cv2.putText(canvas, f"LEVEL: {self.level}/{self.max_levels}", 
                    (sidebar_x + 20, text_y), font, 0.8, (255, 255, 255), 1)
        
        if self.game_state == "ALL_CLEARED":
            time_text = f"TOTAL: {int(self.final_total_time)}s"
            time_color = (0, 255, 255) 
        else:
            elapsed = int(current_time - self.start_time)
            time_text = f"TIME: {elapsed}s"
            time_color = (200, 200, 200)

        cv2.putText(canvas, time_text, 
                    (sidebar_x + 20, text_y + line_height), font, 0.8, time_color, 1)

        status_text = "MOVE: READY" if (current_time - self.last_move_time > self.move_interval) else "MOVE: WAIT"
        color = (0, 255, 0) if "READY" in status_text else (0, 0, 255)
        cv2.putText(canvas, status_text, 
                    (sidebar_x + 20, text_y + line_height * 2), font, 0.7, color, 1)

        # 3. 胜利显示
        if self.game_state == "ALL_CLEARED":
            overlay = canvas.copy()
            cv2.rectangle(overlay, (0, 0), (self.canvas_w, self.canvas_h), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, canvas, 0.3, 0, canvas)
            cv2.putText(canvas, "VICTORY!", (self.canvas_w//2 - 200, self.canvas_h//2 - 50), 
                        font, 3, (0, 215, 255), 5)
            time_str = f"Total Time: {self.final_total_time:.1f} s"
            cv2.putText(canvas, time_str, (self.canvas_w//2 - 220, self.canvas_h//2 + 50), 
                        font, 1.5, (255, 255, 255), 2)

        if self.game_state == "INTRO":
            overlay = canvas.copy()
            cv2.rectangle(overlay, (0, 0), (self.canvas_w, self.canvas_h), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, canvas, 0.4, 0, canvas)
            cv2.putText(canvas, "WAITING FOR START...", (self.canvas_w//2 - 200, self.canvas_h//2), 
                        cv2.FONT_HERSHEY_TRIPLEX, 1.5, (255, 255, 255), 2)

        return canvas