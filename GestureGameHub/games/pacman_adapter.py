# games/pacman_adapter.py
"""吃豆人游戏适配器 - 将Pygame吃豆人游戏集成到MediaPipe框架中"""
import cv2
import numpy as np
import pygame
import sys
import os

# 将 pacman_game 添加到路径
pacman_game_dir = os.path.join(os.path.dirname(__file__), 'pacman_game')
sys.path.insert(0, pacman_game_dir)

from src.game import Game as PacmanGame
from src.config import FPS, TILE
from .base_game import BaseGame


class PacmanGameAdapter(BaseGame):
    """吃豆人游戏适配器 - 使用手势控制"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化 Pygame
        if not pygame.get_init():
            pygame.init()
        
        # 临时切换到 pacman_game 目录以正确加载资源
        original_cwd = os.getcwd()
        os.chdir(pacman_game_dir)
        try:
            # 创建吃豆人游戏实例
            self.pacman_game = PacmanGame()
        finally:
            # 恢复原工作目录
            os.chdir(original_cwd)
        
        # 创建 Pygame surface 用于渲染游戏
        self.game_surface = pygame.Surface((self.pacman_game.width, self.pacman_game.height))
        
        # 初始化时钟
        self.clock = pygame.time.Clock()
        
        # 画布配置
        self.canvas_w = 1280
        self.canvas_h = 720
        self.sidebar_w = 380
        
        # 手势识别配置
        self.last_command = "NONE"
        self.command_cooldown = 0.0
        self.command_interval = 0.5  # 500ms 冷却时间，每0.5秒判断一次手势
        
        # 游戏状态
        self.game_state = "INTRO"
        self.game_over_timer = 0  # 游戏结束后的计时器
        self.restart_delay = 3.0  # 游戏结束3秒后可以重启
        
    def start_game(self):
        """前端点击开始按钮时调用"""
        self.game_state = "PLAYING"
    
    def restart_game(self):
        """重启游戏，释放旧资源并重新创建实例"""
        # 1. 释放旧游戏的 Pygame 资源
        if hasattr(self, 'pacman_game'):
            pygame.event.clear()  # 清空事件队列
            if hasattr(self, 'game_surface'):
                self.game_surface = None  # 让垃圾回收器回收 Surface
            pygame.display.quit()  # 释放显示资源
            pygame.display.init()   # 重新初始化显示
        
        # 2. 原有重启逻辑（保留，增加异常处理）
        original_cwd = os.getcwd()
        pacman_game_dir = os.path.join(os.path.dirname(__file__), 'pacman_game')
        os.chdir(pacman_game_dir)
        try:
            self.pacman_game = PacmanGame()
            self.game_surface = pygame.Surface((self.pacman_game.width, self.pacman_game.height))
        finally:
            os.chdir(original_cwd)
        
        # 3. 强制重置所有计时/状态变量（避免残留）
        self.game_over_timer = 0.0
        self.last_command = "NONE"
        self.command_cooldown = 0.0
        self.game_state = "PLAYING"
    
    def detect_gesture(self, landmarks):
        """识别食指方向"""
        wrist = landmarks.landmark[0]
        index_tip = landmarks.landmark[8]
        dx = index_tip.x - wrist.x
        dy = index_tip.y - wrist.y
        threshold = 0.12
        
        if abs(dx) > abs(dy):
            return "RIGHT" if dx > threshold else "LEFT" if dx < -threshold else "NONE"
        else:
            return "DOWN" if dy > threshold else "UP" if dy < -threshold else "NONE"
    
    def apply_gesture_to_pacman(self, command):
        """将手势命令转换为游戏输入"""
        if command == "NONE":
            return
        
        # 创建虚拟键盘事件
        key_map = {
            "UP": pygame.K_UP,
            "DOWN": pygame.K_DOWN,
            "LEFT": pygame.K_LEFT,
            "RIGHT": pygame.K_RIGHT
        }
        
        if command in key_map:
            # 创建 KEYDOWN 事件
            event = pygame.event.Event(pygame.KEYDOWN, key=key_map[command])
            self.pacman_game.handle_event(event)
    
    def update_and_draw(self, frame, results):
        """核心方法：更新游戏逻辑并绘制画面"""
        import time
        
        # 1. 创建画布
        canvas = np.zeros((self.canvas_h, self.canvas_w, 3), dtype=np.uint8)
        canvas[:] = (20, 20, 20)
        
        # 2. 处理手势识别
        command = "NONE"
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                command = self.detect_gesture(hand_landmarks)
        
        # 3. 更新游戏逻辑
        if self.game_state == "PLAYING":
            # 应用手势命令（带冷却）
            current_time = time.time()
            if command != "NONE" and command != self.last_command:
                if self.command_cooldown <= current_time:
                    self.apply_gesture_to_pacman(command)
                    self.last_command = command
                    self.command_cooldown = current_time + self.command_interval
            
            # 检查是否游戏结束
            if self.pacman_game.game_over:
                self.game_over_timer += 1 / FPS
                # 3秒后自动重启游戏
                if self.game_over_timer >= self.restart_delay:
                    self.restart_game()
            else:
                # 游戏未结束，正常更新
                dt = self.clock.tick(FPS) / 1000.0
                self.pacman_game.update(dt)
            
            # 渲染游戏到 surface
            self.pacman_game.draw(self.game_surface)
            
            # 将 Pygame surface 转换为 OpenCV 图像
            game_image = self.pygame_surface_to_cv2(self.game_surface)
            
            # 计算游戏画面的位置（左侧居中）
            game_area_w = self.canvas_w - self.sidebar_w
            scale = min((game_area_w - 40) / game_image.shape[1], 
                       (self.canvas_h - 40) / game_image.shape[0])
            new_w = int(game_image.shape[1] * scale)
            new_h = int(game_image.shape[0] * scale)
            game_resized = cv2.resize(game_image, (new_w, new_h))
            
            # 居中放置
            offset_x = (game_area_w - new_w) // 2
            offset_y = (self.canvas_h - new_h) // 2
            canvas[offset_y:offset_y+new_h, offset_x:offset_x+new_w] = game_resized
            
            # 游戏画面边框
            cv2.rectangle(canvas, (offset_x-2, offset_y-2), 
                         (offset_x+new_w+2, offset_y+new_h+2), (0, 200, 200), 2)
        
        elif self.game_state == "INTRO":
            # 等待开始状态
            overlay = canvas.copy()
            cv2.rectangle(overlay, (0, 0), (self.canvas_w - self.sidebar_w, self.canvas_h), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, canvas, 0.3, 0, canvas)
            
            font = cv2.FONT_HERSHEY_TRIPLEX
            text = "CLICK START TO PLAY"
            text_size = cv2.getTextSize(text, font, 1.5, 2)[0]
            text_x = (self.canvas_w - self.sidebar_w - text_size[0]) // 2
            text_y = self.canvas_h // 2
            cv2.putText(canvas, text, (text_x, text_y), font, 1.5, (0, 255, 255), 2)
        
        # 4. 绘制右侧边栏
        sidebar_x = self.canvas_w - self.sidebar_w
        cv2.rectangle(canvas, (sidebar_x, 0), (self.canvas_w, self.canvas_h), (15, 15, 15), -1)
        cv2.line(canvas, (sidebar_x, 0), (sidebar_x, self.canvas_h), (100, 100, 100), 2)
        
        # 摄像头画面
        cam_w = self.sidebar_w - 20
        cam_h = int(cam_w * 0.75)
        cam_resized = cv2.resize(frame, (cam_w, cam_h))
        cv2.rectangle(canvas, (sidebar_x + 8, 8), 
                     (sidebar_x + 10 + cam_w + 2, 10 + cam_h + 2), (255, 255, 255), 2)
        canvas[10:10+cam_h, sidebar_x+10:sidebar_x+10+cam_w] = cam_resized
        
        # 方向指示
        info_start_y = 10 + cam_h + 50
        self.draw_arrow(canvas, command, sidebar_x + self.sidebar_w // 2, info_start_y)
        
        # 文字信息
        text_y = info_start_y + 100
        line_height = 45
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        cv2.putText(canvas, "PACMAN GAME", (sidebar_x + 20, text_y), 
                   font, 0.8, (0, 255, 255), 2)
        
        if self.game_state == "PLAYING":
            cv2.putText(canvas, f"Score: {self.pacman_game.score}", 
                       (sidebar_x + 20, text_y + line_height), font, 0.7, (255, 255, 255), 1)
            cv2.putText(canvas, f"Lives: {self.pacman_game.lives}", 
                       (sidebar_x + 20, text_y + line_height * 2), font, 0.7, (255, 255, 255), 1)
            cv2.putText(canvas, f"Pellets: {self.pacman_game.map.remaining_pellets()}", 
                       (sidebar_x + 20, text_y + line_height * 3), font, 0.7, (200, 200, 200), 1)
            
            # 游戏结束提示
            if self.pacman_game.game_over:
                overlay = canvas.copy()
                cv2.rectangle(overlay, (0, 0), (self.canvas_w - self.sidebar_w, self.canvas_h), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.7, canvas, 0.3, 0, canvas)
                
                victory = self.pacman_game.map.remaining_pellets() == 0
                text = "VICTORY!" if victory else "GAME OVER"
                color = (0, 255, 0) if victory else (0, 0, 255)
                text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_TRIPLEX, 2, 3)[0]
                text_x = (self.canvas_w - self.sidebar_w - text_size[0]) // 2
                cv2.putText(canvas, text, (text_x, self.canvas_h // 2 - 50), 
                           cv2.FONT_HERSHEY_TRIPLEX, 2, color, 3)
                
                # 显示重启倒计时
                remaining = max(0, self.restart_delay - self.game_over_timer)
                restart_text = f"Restarting in {remaining:.1f}s"
                restart_size = cv2.getTextSize(restart_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
                restart_x = (self.canvas_w - self.sidebar_w - restart_size[0]) // 2
                cv2.putText(canvas, restart_text, (restart_x, self.canvas_h // 2 + 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        else:
            cv2.putText(canvas, "Use hand gestures", 
                       (sidebar_x + 20, text_y + line_height), font, 0.6, (200, 200, 200), 1)
            cv2.putText(canvas, "to control Pacman", 
                       (sidebar_x + 20, text_y + line_height * 2), font, 0.6, (200, 200, 200), 1)
        
        return canvas
    
    def draw_arrow(self, img, command, center_x, center_y, size=50):
        """绘制方向箭头"""
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
        else:
            return
        
        cv2.line(img, p1, p2, color, thickness)
        cv2.line(img, p2, arrow_p1, color, thickness)
        cv2.line(img, p2, arrow_p2, color, thickness)
    
    def pygame_surface_to_cv2(self, surface):
        """将 Pygame Surface 转换为 OpenCV 图像"""
        # 获取 surface 的像素数据
        w, h = surface.get_size()
        buf = pygame.surfarray.array3d(surface)
        
        # Pygame 使用 (width, height, channels)，需要转置为 (height, width, channels)
        img = np.transpose(buf, (1, 0, 2))
        
        # Pygame 使用 RGB，OpenCV 使用 BGR
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        return img
