# games/fruit_ninja_game.py
"""水果忍者游戏适配器 - 将原始Pygame水果忍者游戏集成到MediaPipe框架中"""
import cv2
import numpy as np
import pygame
import sys
import os
import random
import time
from .base_game import BaseGame


class FruitNinjaGame(BaseGame):
    """水果忍者游戏适配器 - 使用手指控制"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化 Pygame
        if not pygame.get_init():
            pygame.init()
        
        # 游戏窗口配置
        self.WIDTH = 600
        self.HEIGHT = 400
        self.FPS = 30
        
        # 创建 Pygame surface
        self.game_surface = pygame.Surface((self.WIDTH, self.HEIGHT))
        self.clock = pygame.time.Clock()
        
        # 画布配置
        self.canvas_w = 1280
        self.canvas_h = 720
        self.sidebar_w = 380
        
        # 手指位置
        self.finger_pos = None
        self.prev_finger_pos = None  # 上一帧的手指位置
        self.smooth_factor = 0.6  # 平滑系数，提高到0.6以获得更好的响应速度
        self.detection_lost_frames = 0  # 检测丢失的帧数
        self.max_lost_frames = 5  # 允许的最大丢失帧数，超过才重置位置
        
        # 游戏资源路径
        self.fruit_dir = os.path.join(os.path.dirname(__file__), 'FruitNinjia-main')
        
        # 加载背景和字体
        self.background = pygame.image.load(os.path.join(self.fruit_dir, 'images', 'background.jpg'))
        comic_ttf = os.path.join(self.fruit_dir, 'comic.ttf')
        if os.path.exists(comic_ttf):
            self.font = pygame.font.Font(comic_ttf, 42)
        else:
            self.font = pygame.font.Font(None, 42)
        
        # 游戏数据 - 基于原始项目的结构
        self.data = {}
        self.fruits = ['apple', 'banana', 'basaha', 'peach', 'sandia', 'boom']
        
        # 初始化水果数据
        for fruit in self.fruits:
            self.generate_random_fruits(fruit)
        
        # 游戏状态
        self.game_state = "WAITING"  # WAITING, PLAYING, GAMEOVER
        self.score = 0
        self.player_lives = 3
        self.game_over = False
        self.first_round = True
        
    def generate_random_fruits(self, fruit):
        """生成随机水果 - 基于原始项目逻辑"""
        fruit_path = os.path.join(self.fruit_dir, "images", "fruit_images", fruit + ".png")
        self.data[fruit] = {
            'img': pygame.image.load(fruit_path) if os.path.exists(fruit_path) else pygame.Surface((60, 60)),
            'x': random.randint(100, 500),
            'y': 400,
            'speed_x': random.randint(-3, 3) * 0.7,  # 降低到70%
            'speed_y': random.randint(-20, -15) * 0.7,  # 降低到70%
            'throw': False,
            't': 0,
            'hit': False,
        }

        # 炸弹出现频率降低50%，并进一步降低刷新频率
        if fruit == 'boom':
            if random.random() >= 0.912:  # 原来0.875，降低到70%频率：1-(1-0.875)*0.7 ≈ 0.912
                self.data[fruit]['throw'] = True
            else:
                self.data[fruit]['throw'] = False
        else:
            if random.random() >= 0.825:  # 原来0.75，降低到70%频率：1-(1-0.75)*0.7 ≈ 0.825
                self.data[fruit]['throw'] = True
            else:
                self.data[fruit]['throw'] = False
    
    def hide_cross_lives(self, x, y):
        """隐藏生命图标"""
        score_img = os.path.join(self.fruit_dir, 'images', 'score.png')
        if os.path.exists(score_img):
            self.game_surface.blit(pygame.image.load(score_img), (x, y))
    
    def draw_lives(self, display, x, y, lives, image_path):
        """绘制玩家的生命"""
        for i in range(lives):
            if os.path.exists(image_path):
                img = pygame.image.load(image_path)
                img_rect = img.get_rect()
                img_rect.x = int(x + 35 * i)
                img_rect.y = y
                display.blit(img, img_rect)
    
    def check_collision(self, value):
        """检测手指与水果的碰撞 - 基于原始项目，改进为轨迹检测"""
        if self.finger_pos is None:
            return False
        
        current_position = self.finger_pos
        
        # 扩大碰撞范围，从60x60扩大到80x80
        collision_margin = 10
        if not value['hit'] and \
           value['x'] - collision_margin < current_position[0] < value['x'] + 60 + collision_margin \
           and value['y'] - collision_margin < current_position[1] < value['y'] + 60 + collision_margin:
            return True
        
        # 轨迹碰撞检济：如果有上一帧位置，检测从上一帧到当前帧的路径
        if self.prev_finger_pos is not None and not value['hit']:
            # 计算路径上的多个采样点
            prev_x, prev_y = self.prev_finger_pos
            curr_x, curr_y = current_position
            
            # 计算移动距离
            distance = ((curr_x - prev_x) ** 2 + (curr_y - prev_y) ** 2) ** 0.5
            
            # 如果移动距离较大，在路径上采样多个点检测
            if distance > 10:  # 只在快速移动时检测轨迹
                steps = int(distance / 5)  # 每5像素采样一次
                for i in range(1, steps + 1):
                    t = i / (steps + 1)
                    check_x = prev_x + (curr_x - prev_x) * t
                    check_y = prev_y + (curr_y - prev_y) * t
                    
                    if value['x'] - collision_margin < check_x < value['x'] + 60 + collision_margin \
                       and value['y'] - collision_margin < check_y < value['y'] + 60 + collision_margin:
                        return True
        
        return False
    
    def pygame_surface_to_cv2(self, surface):
        """将Pygame Surface转换为OpenCV图像"""
        arr = pygame.surfarray.array3d(surface)
        arr = np.transpose(arr, (1, 0, 2))
        arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        return arr
    
    def draw_waiting_screen(self):
        """绘制等待开始界面"""
        self.game_surface.blit(self.background, (0, 0))
        
        # 加载logo图片
        logo1_path = os.path.join(self.fruit_dir, 'images', 'logo.png')
        logo2_path = os.path.join(self.fruit_dir, 'images', 'ninja.png')
        
        if os.path.exists(logo1_path):
            logo1 = pygame.image.load(logo1_path)
            self.game_surface.blit(logo1, (10, 10))
        
        if os.path.exists(logo2_path):
            logo2 = pygame.image.load(logo2_path)
            self.game_surface.blit(logo2, (320, 50))
        
        # 显示一些水果作为装饰
        if 'boom' in self.data:
            self.game_surface.blit(self.data['boom']['img'], (480, 190))
        if 'sandia' in self.data:
            self.game_surface.blit(self.data['sandia']['img'], (290, 255))
        if 'peach' in self.data:
            self.game_surface.blit(self.data['peach']['img'], (100, 260))
        
        # 提示文字
        small_font = pygame.font.Font(None, 30)
        text = small_font.render('Show your hand to start...', True, (255, 255, 255))
        self.game_surface.blit(text, (self.WIDTH // 2 - text.get_width() // 2, 350))
    
    def draw_playing_screen(self):
        """绘制游戏进行界面 - 基于原始项目"""
        # 背景
        self.game_surface.blit(self.background, (0, 0))
        
        # 绘制分数
        score_text = self.font.render('Score : ' + str(self.score), True, (255, 255, 255))
        self.game_surface.blit(score_text, (0, 0))
        
        # 绘制生命
        score_img_path = os.path.join(self.fruit_dir, 'images', 'score.png')
        self.draw_lives(self.game_surface, 350, 5, self.player_lives, score_img_path)
        
        # 绘制水果
        for key, value in self.data.items():
            if value['throw']:
                # 只绘制在屏幕内的水果
                if value['y'] <= 800:
                    self.game_surface.blit(value['img'], (value['x'], value['y']))
        
        # 绘制刀（手指位置）
        if self.finger_pos:
            pygame.draw.circle(self.game_surface, (255, 255, 0), 
                             (int(self.finger_pos[0]), int(self.finger_pos[1])), 15, 2)
            pygame.draw.circle(self.game_surface, (255, 255, 255), 
                             (int(self.finger_pos[0]), int(self.finger_pos[1])), 5)
    
    def draw_gameover_screen(self):
        """绘制游戏结束界面"""
        self.game_surface.blit(self.background, (0, 0))
        
        game_over_text = self.font.render('GAME OVER', True, (255, 0, 0))
        final_score_text = self.font.render('Score : ' + str(self.score), True, (255, 255, 255))
        
        self.game_surface.blit(game_over_text, 
                              (self.WIDTH // 2 - game_over_text.get_width() // 2, self.HEIGHT // 4))
        self.game_surface.blit(final_score_text, 
                              (self.WIDTH // 2 - final_score_text.get_width() // 2, self.HEIGHT // 2))
    
    def update_and_draw(self, frame, results):
        """主游戏循环 - 更新并绘制游戏画面"""
        # 1. 更新手指位置（带平滑处理和丢失缓冲）
        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            h, w, c = frame.shape
            index_finger = hand_landmarks.landmark[8]
            
            # 映射到游戏坐标（直接映射，不镜像）
            game_x = index_finger.x * self.WIDTH
            game_y = index_finger.y * self.HEIGHT
            
            # 平滑处理：使用指数加权移动平均
            if self.prev_finger_pos is not None:
                # 对新位置进行平滑
                smooth_x = self.prev_finger_pos[0] * (1 - self.smooth_factor) + game_x * self.smooth_factor
                smooth_y = self.prev_finger_pos[1] * (1 - self.smooth_factor) + game_y * self.smooth_factor
                self.finger_pos = (int(smooth_x), int(smooth_y))
            else:
                # 第一帧直接使用
                self.finger_pos = (int(game_x), int(game_y))
            
            # 保存当前位置作为下一帧的参考
            self.prev_finger_pos = self.finger_pos
            
            # 重置丢失计数器
            self.detection_lost_frames = 0
            
            # 如果在等待界面且检测到手，开始游戏
            if self.game_state == "WAITING":
                self.game_state = "PLAYING"
                if self.first_round:
                    self.first_round = False
                    self.player_lives = 3
                    self.score = 0
        else:
            # 如果没有检测到手，增加丢失帧计数
            self.detection_lost_frames += 1
            
            # 只有连续多帧检测不到才重置位置（避免短暂丢失导致闪烁）
            if self.detection_lost_frames > self.max_lost_frames:
                if self.game_state == "WAITING":
                    self.finger_pos = None
                    self.prev_finger_pos = None
                # 游戏进行中保持最后位置，不立即清除
            # 否则保持上一帧的位置，不做任何改变
        
        # 2. 根据游戏状态更新逻辑
        if self.game_state == "PLAYING" and not self.game_over:
            # 更新所有水果位置 - 基于原始项目逻辑
            for key, value in self.data.items():
                if value['throw']:
                    value['x'] += value['speed_x']
                    value['y'] += value['speed_y']
                    value['speed_y'] += (0.05 * value['t'] * 0.7)  # 重力加速度降低到70%
                    value['t'] += 1

                    if value['y'] > 800:
                        # 水果掉出屏幕，重新生成
                        self.generate_random_fruits(key)
                    else:
                        # 检测手指碰撞
                        if self.check_collision(value):
                            if key == 'boom':
                                # 切到炸弹
                                self.player_lives -= 1
                                if self.player_lives == 0:
                                    self.hide_cross_lives(455, 15)
                                elif self.player_lives == 1:
                                    self.hide_cross_lives(420, 15)
                                elif self.player_lives == 2:
                                    self.hide_cross_lives(385, 15)

                                if self.player_lives < 0:
                                    self.game_over = True

                                half_fruit_path = os.path.join(self.fruit_dir, "images", "fruit_images", "xxxf.png")
                            else:
                                # 切到水果
                                half_fruit_path = os.path.join(self.fruit_dir, "images", "fruit_images", key + "-1" + ".png")
                                self.score += 1

                            # 更新水果图片和速度
                            if os.path.exists(half_fruit_path):
                                value['img'] = pygame.image.load(half_fruit_path)
                            value['speed_x'] += 10
                            value['hit'] = True
                else:
                    self.generate_random_fruits(key)
        
        # 3. 根据游戏状态绘制不同内容
        if self.game_state == "WAITING":
            self.draw_waiting_screen()
        elif self.game_state == "PLAYING":
            if self.game_over:
                self.draw_gameover_screen()
            else:
                self.draw_playing_screen()
        
        # 4. 转换Pygame surface到OpenCV图像
        game_image = self.pygame_surface_to_cv2(self.game_surface)
        
        # 5. 创建最终画布
        canvas = np.zeros((self.canvas_h, self.canvas_w, 3), dtype=np.uint8)
        canvas[:] = (20, 20, 20)
        
        # 6. 放置游戏画面（左侧居中）
        game_area_w = self.canvas_w - self.sidebar_w
        scale = min((game_area_w - 40) / self.WIDTH, (self.canvas_h - 40) / self.HEIGHT)
        new_w = int(self.WIDTH * scale)
        new_h = int(self.HEIGHT * scale)
        game_resized = cv2.resize(game_image, (new_w, new_h))
        
        offset_x = (game_area_w - new_w) // 2
        offset_y = (self.canvas_h - new_h) // 2
        canvas[offset_y:offset_y+new_h, offset_x:offset_x+new_w] = game_resized
        
        # 游戏画面边框
        cv2.rectangle(canvas, (offset_x-2, offset_y-2), 
                     (offset_x+new_w+2, offset_y+new_h+2), (255, 200, 0), 2)
        
        # 7. 绘制右侧边栏
        sidebar_x = self.canvas_w - self.sidebar_w
        
        # 边栏背景
        cv2.rectangle(canvas, (sidebar_x, 0), (self.canvas_w, self.canvas_h), (40, 40, 40), -1)
        cv2.line(canvas, (sidebar_x, 0), (sidebar_x, self.canvas_h), (100, 100, 100), 2)
        
        # 摄像头预览（放在边栏顶部）
        camera_h = 200
        camera_w = self.sidebar_w - 20
        camera_preview = cv2.resize(frame, (camera_w, camera_h))
        # 镜像翻转摄像头画面，使其更自然
        camera_preview = cv2.flip(camera_preview, 1)
        canvas[10:10+camera_h, sidebar_x+10:sidebar_x+10+camera_w] = camera_preview
        # 摄像头画面边框
        cv2.rectangle(canvas, (sidebar_x+10, 10), (sidebar_x+10+camera_w, 10+camera_h), (100, 200, 255), 2)
        
        # 摄像头标签
        cv2.putText(canvas, 'CAMERA', (sidebar_x + 20, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # 游戏标题（位置下移）
        cv2.putText(canvas, 'FRUIT NINJA', (sidebar_x + 40, camera_h + 50), 
                   cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 215, 0), 2)
        
        # 游戏状态（位置下移）
        status_y = 300
        state_color = (0, 255, 0) if self.game_state == "PLAYING" else (255, 255, 0)
        cv2.putText(canvas, f'State: {self.game_state}', (sidebar_x + 20, status_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, state_color, 2)
        
        # 分数和生命（位置下移）
        info_y = 360
        cv2.putText(canvas, f'Score: {self.score}', (sidebar_x + 20, info_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(canvas, f'Lives: {self.player_lives}', (sidebar_x + 20, info_y + 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # 游戏说明
        instructions = [
            'CONTROLS:',
            '- Use index finger',
            '- Slice fruits',
            '- Avoid bombs',
            '',
            'RULES:',
            '- Cut bombs = -1 life',
            '- Missing fruits is OK',
            ''
        ]
        
        inst_y = 480
        for line in instructions:
            if line:
                cv2.putText(canvas, line, (sidebar_x + 20, inst_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            inst_y += 30
        
        # 手指位置指示
        if self.finger_pos and self.game_state != "WAITING":
            finger_info = f'Finger: ({int(self.finger_pos[0])}, {int(self.finger_pos[1])})'
            cv2.putText(canvas, finger_info, (sidebar_x + 20, self.canvas_h - 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
        
        return canvas
