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
        self.start_time = time.time()       # 当前关卡开始时间
        self.global_start_time = 0          # [新增] 整个游戏开始的时间
        self.final_total_time = 0           # [新增] 通关后的总耗时记录
        
        # --- 画面配置 ---
        self.canvas_w, self.canvas_h = 1280, 720
        self.sidebar_w = 380
        self.maze_area_w = self.canvas_w - self.sidebar_w
        
        self.game_state = "INTRO" 
        self.init_level()

    def start_game(self):
        self.game_state = "PLAYING"
        current_t = time.time()
        self.start_time = current_t        # 重置当前关卡计时
        self.global_start_time = current_t # [新增] 记录游戏总开始时间

    def init_level(self):
        """初始化关卡"""
        # 1. 计算迷宫尺寸
        self.cols = 10 + (self.level // 2)
        self.rows = 8 + (self.level // 2)
        
        # 2. 生成基础迷宫
        raw_maze = self.generate_maze(self.cols, self.rows)
        
        # 3. 记录起终点
        start_x, start_y = 0, 0
        end_x, end_y = self.cols - 1, self.rows - 1

        # 4. 随机水平镜像
        if random.choice([True, False]):
            raw_maze = np.fliplr(raw_maze)
            start_x = self.cols - 1 - start_x
            end_x = self.cols - 1 - end_x

        # 5. 随机垂直镜像
        if random.choice([True, False]):
            raw_maze = np.flipud(raw_maze)
            start_y = self.rows - 1 - start_y
            end_y = self.rows - 1 - end_y

        # 6. 应用修改
        self.maze = raw_maze
        self.player_pos = [start_x, start_y]
        self.end_pos = [end_x, end_y]
        
        # 7. 重置状态
        if not hasattr(self, 'game_state'): 
            self.game_state = "INTRO"
        elif self.game_state != "INTRO":
            self.game_state = "PLAYING"
            self.start_time = time.time() # 仅重置当前关卡计时

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

        # --- 这是作弊触发区域 方便测试 ---
        # if self.game_state == "PLAYING" and (current_time - self.start_time) % 3 >= 2:
        #     cv2.putText(canvas, "DEBUG: SKIP!", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        #     self.player_pos = list(self.end_pos) # 瞬移到终点
        
        # --- 游戏逻辑更新 ---
        if self.game_state == "PLAYING":
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

            if self.player_pos == self.end_pos:
                self.level += 1
                if self.level > self.max_levels:
                    self.level -= 1
                    self.game_state = "ALL_CLEARED"
                    # 胜利瞬间，计算总耗时并锁定
                    self.final_total_time = current_time - self.global_start_time
                else:
                    self.init_level()

        # --- 绘图部分 ---

        # A. 绘制左侧迷宫区
        padding = 40
        available_w = self.maze_area_w - 2 * padding
        available_h = self.canvas_h - 2 * padding
        cell_size = min(available_w // self.cols, available_h // self.rows)
        
        offset_x = padding + (available_w - self.cols * cell_size) // 2
        offset_y = padding + (available_h - self.rows * cell_size) // 2

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

        # 玩家
        px, py = self.player_pos
        pcx = offset_x + px * cell_size + cell_size // 2
        pcy = offset_y + py * cell_size + cell_size // 2
        cv2.circle(canvas, (pcx, pcy), cell_size // 3, (0, 255, 0), -1)
        cv2.circle(canvas, (pcx, pcy), cell_size // 3 + 2, (255, 255, 255), 2)

        # B. 绘制右侧侧边栏
        sidebar_x = self.maze_area_w
        cv2.rectangle(canvas, (sidebar_x, 0), (self.canvas_w, self.canvas_h), (20, 20, 20), -1)
        cv2.line(canvas, (sidebar_x, 0), (sidebar_x, self.canvas_h), (100, 100, 100), 2)

        # 摄像头画面
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
        
        # 计时显示逻辑：如果是胜利状态，不再更新时间，或者显示总时间
        if self.game_state == "ALL_CLEARED":
            # 胜利后，侧边栏显示总耗时
            time_text = f"TOTAL: {int(self.final_total_time)}s"
            time_color = (0, 255, 255) # 金色
        else:
            # 游戏中，显示当前关卡耗时
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
            
            # 胜利标题
            cv2.putText(canvas, "VICTORY!", (self.canvas_w//2 - 200, self.canvas_h//2 - 50), 
                        font, 3, (0, 215, 255), 5)
            # 总耗时显示
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