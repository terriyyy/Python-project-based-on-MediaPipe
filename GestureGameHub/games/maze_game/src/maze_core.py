# games/maze_game/src/maze_core.py
import numpy as np
import random
import time

class MazeCore:
    def __init__(self):
        self.level = 1
        self.max_levels = 15
        
        self.game_state = "INTRO" 
        self.start_time = 0
        self.total_time = 0
        self.transition_start_time = 0 
        
        self.cols = 10
        self.rows = 8
        self.maze = None
        self.player_pos = [0, 0]
        self.end_pos = [0, 0]
        
        self.init_level()

    def start_game(self):
        self.game_state = "PLAYING"
        self.start_time = time.time()

    def next_level(self):
        self.level += 1
        if self.level > self.max_levels:
            self.game_state = "ALL_CLEARED"
            self.total_time = time.time() - self.start_time
        else:
            self.game_state = "TRANSITION"
            self.transition_start_time = time.time()

    def init_level(self):
        # 1. 计算尺寸
        raw_cols = 10 + (self.level // 2)
        raw_rows = 8 + (self.level // 2)
        raw_cols = min(raw_cols, 25)
        raw_rows = min(raw_rows, 18)

        # 2. 生成基础迷宫 (此时保证全图连通)
        self.maze = self._generate_maze_dfs(raw_cols, raw_rows)
        
        # 3. 随机变形 (增加迷宫结构的不可预测性)
        if random.choice([True, False]): self.maze = np.fliplr(self.maze)
        if random.choice([True, False]): self.maze = np.flipud(self.maze)
        if random.choice([True, False]): self.maze = self.maze.T

        # 4. 获取最终尺寸
        self.rows, self.cols = self.maze.shape
        
        # 5. 【新增】随机选择 4 个角落之一作为起点
        # 角落索引: 0=左上, 1=右上, 2=左下, 3=右下
        corners = [
            [0, 0],                         # Top-Left
            [self.cols - 1, 0],             # Top-Right
            [0, self.rows - 1],             # Bottom-Left
            [self.cols - 1, self.rows - 1]  # Bottom-Right
        ]
        
        start_idx = random.randint(0, 3)
        # 终点选择对角线位置 (0<->3, 1<->2)
        end_idx = 3 - start_idx
        
        self.player_pos = corners[start_idx]
        self.end_pos = corners[end_idx]

        # 6. 【新增】智能开路：确保起终点绝对可用，且不被憋死
        self._force_open(self.player_pos)
        self._force_open(self.end_pos)

    def _force_open(self, pos):
        """强制打通某个坐标及其周围，防止死路"""
        x, y = pos
        self.maze[y, x] = 1 # 脚下变路
        
        # 打通一个邻居，保证能走出去
        # 优先向地图中心打通
        center_x, center_y = self.cols // 2, self.rows // 2
        dx = 1 if x < center_x else -1
        dy = 1 if y < center_y else -1
        
        # 简单策略：如果横向在界内，打通横向；否则打通纵向
        if 0 <= x + dx < self.cols:
            self.maze[y, x + dx] = 1
        elif 0 <= y + dy < self.rows:
            self.maze[y + dy, x] = 1

    def move_player(self, direction):
        if self.game_state != "PLAYING": return False
        
        px, py = self.player_pos
        new_x, new_y = px, py
        
        if direction == "UP": new_y -= 1
        elif direction == "DOWN": new_y += 1
        elif direction == "LEFT": new_x -= 1
        elif direction == "RIGHT": new_x += 1
        
        if 0 <= new_x < self.cols and 0 <= new_y < self.rows:
            if self.maze[new_y, new_x] == 1:
                self.player_pos = [new_x, new_y]
                if self.player_pos == self.end_pos:
                    return "WIN"
                return True
        return False

    def _generate_maze_dfs(self, w, h):
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
        return maze