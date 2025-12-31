import cv2
import mediapipe as mp
import pygame
import numpy as np
import os
import sys
import random

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, 'street_fighter', 'src'))
sys.path.append(os.path.join(current_dir, 'street_fighter')) # 导入 gesture_engine

from fighter import Fighter
from gesture_engine import GestureEngine # 引入新文件

class StreetFighterAdapter:
    def __init__(self):
        pygame.init()
        try: pygame.mixer.init()
        except: pass 
        
        self.gesture_engine = GestureEngine() # 初始化新引擎

        self.WIDTH = 1280
        self.HEIGHT = 720
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        
        base_path = os.path.join(current_dir, 'street_fighter', 'assets')
        bg_files = ['bg.jpg', 'bg1.jpg', 'bg2.jpg']
        chosen_bg = random.choice(bg_files)
        bg_path = os.path.join(base_path, 'images', chosen_bg)
        
        self.bg_image = pygame.image.load(bg_path).convert_alpha()
        self.bg_image = pygame.transform.scale(self.bg_image, (self.WIDTH, self.HEIGHT))
        self.victory_img = pygame.image.load(os.path.join(base_path, 'images', 'victory.png')).convert_alpha()
        
        warrior_sheet = pygame.image.load(os.path.join(base_path, 'images', 'warrior.png')).convert_alpha()
        wizard_sheet = pygame.image.load(os.path.join(base_path, 'images', 'wizard.png')).convert_alpha()
        
        WARRIOR_DATA = [162, 4, [72, 46]]
        WIZARD_DATA = [250, 3, [112, 97]]
        WARRIOR_STEPS = [10, 8, 1, 7, 7, 3, 7]
        WIZARD_STEPS = [8, 8, 1, 8, 8, 3, 7]
        
        class DummySound:
            def play(self): pass
        
        self.fighter_1 = Fighter(1, 200, 430, False, WARRIOR_DATA, warrior_sheet, WARRIOR_STEPS, DummySound())
        self.fighter_2 = Fighter(2, 980, 430, True, WIZARD_DATA, wizard_sheet, WIZARD_STEPS, DummySound())
        
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(model_complexity=0, max_num_hands=2, min_detection_confidence=0.5, min_tracking_confidence=0.5)
        
        self.round_over = False

    def draw_health_bar(self, health, x, y):
        ratio = health / 100
        pygame.draw.rect(self.screen, (255, 255, 255), (x - 2, y - 2, 404, 34))
        pygame.draw.rect(self.screen, (255, 0, 0), (x, y, 400, 30))
        pygame.draw.rect(self.screen, (255, 255, 0), (x, y, 400 * ratio, 30))

    def process(self, frame):
        # A. 识别
        frame_small = cv2.resize(frame, (640, 480))
        rgb = cv2.cvtColor(frame_small, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)
        
        # 调用新引擎
        cmd = self.gesture_engine.detect(results)
        
        if results.multi_hand_landmarks:
            for hand_lms in results.multi_hand_landmarks:
                mp.solutions.drawing_utils.draw_landmarks(frame_small, hand_lms, self.mp_hands.HAND_CONNECTIONS)

        # B. 游戏逻辑
        self.screen.blit(self.bg_image, (0, 0))
        self.draw_health_bar(self.fighter_1.health, 20, 20)
        self.draw_health_bar(self.fighter_2.health, self.WIDTH - 420, 20)
        
        if self.round_over == False:
            # P1 回血逻辑 (直接在这里处理)
            if cmd == "HEAL" and self.fighter_1.health < 100:
                self.fighter_1.health += 0.5

            # AI
            p1_x = self.fighter_1.rect.centerx
            p2_x = self.fighter_2.rect.centerx
            dist_x = abs(p1_x - p2_x)
            ai_cmd = None
            if dist_x < 100: ai_cmd = "RIGHT" if p1_x < p2_x else "LEFT"
            elif dist_x > 300: ai_cmd = "LEFT" if p1_x < p2_x else "RIGHT"
            else:
                dice = random.randint(0, 100)
                if dice < 2: ai_cmd = "JUMP"
                elif dice < 5: ai_cmd = "ATTACK"
                elif dice < 15: ai_cmd = "RIGHT" if random.random() > 0.5 else "LEFT"

            # 映射指令到 Fighter (SKILL_1 -> Attack 1, SKILL_2 -> Attack 2)
            # 注意：fighter.py 的 move 方法需要能处理这些字符串
            # 为了兼容，我们把它们映射回 fighter 能听懂的简单指令
            fighter_cmd = cmd
            if cmd == "SKILL_1": fighter_cmd = "ATTACK" # 映射到轻攻击/重攻击
            if cmd == "SKILL_2": fighter_cmd = "SKILL"  # 映射到 Skill (我们在 fighter.py 改过的 Attack 2)
            
            self.fighter_1.move(self.WIDTH, self.HEIGHT, self.fighter_2, self.round_over, fighter_cmd)
            self.fighter_2.move(self.WIDTH, self.HEIGHT, self.fighter_1, self.round_over, ai_cmd)
            
            self.fighter_1.update()
            self.fighter_2.update()
            
            if self.fighter_1.alive == False or self.fighter_2.alive == False:
                self.round_over = True
        else:
            # 结算
            vic_img = pygame.transform.scale(self.victory_img, (600, 150))
            cx, cy = self.WIDTH // 2, self.HEIGHT // 2
            self.screen.blit(vic_img, (cx - 300, cy - 200))
            font = pygame.font.SysFont(None, 100)
            text = font.render("PLAYER 1 WINS!" if self.fighter_1.alive else "COMPUTER WINS!", True, (0, 255, 0) if self.fighter_1.alive else (255, 0, 0))
            tr = text.get_rect(center=(cx, cy))
            self.screen.blit(text, tr)
            self.fighter_1.update()
            self.fighter_2.update()

        self.fighter_1.draw(self.screen)
        self.fighter_2.draw(self.screen)
        
        # C. 侧边栏
        game_view = pygame.surfarray.array3d(self.screen).transpose([1, 0, 2])
        game_view = cv2.cvtColor(game_view, cv2.COLOR_RGB2BGR)
        
        SIDEBAR_WIDTH = 400
        total_width = self.WIDTH + SIDEBAR_WIDTH
        combined_view = np.zeros((self.HEIGHT, total_width, 3), dtype=np.uint8)
        
        combined_view[0:self.HEIGHT, 0:self.WIDTH] = game_view
        combined_view[0:self.HEIGHT, self.WIDTH:total_width] = (30, 30, 35)
        
        ch, cw = frame_small.shape[:2]
        scale = SIDEBAR_WIDTH / cw
        nch = int(ch * scale)
        cam = cv2.resize(frame_small, (SIDEBAR_WIDTH, nch))
        combined_view[0:nch, self.WIDTH:total_width] = cam
        
        iy = nch + 40
        cv2.putText(combined_view, "NEURAL ENGINE:", (self.WIDTH + 20, iy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 150), 1)
        
        if cmd:
            color = (0, 255, 0)
            if cmd == "ATTACK": color = (0, 0, 255)
            elif "SKILL" in cmd: color = (0, 255, 255)
            elif cmd == "HEAL": color = (255, 0, 255)
            cv2.putText(combined_view, f"{cmd}", (self.WIDTH + 20, iy + 50), cv2.FONT_HERSHEY_SIMPLEX, 1.8, color, 3)
            if cmd == "HEAL":
                cv2.putText(combined_view, "+ HP RECOVERING", (self.WIDTH + 20, iy + 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)
        else:
            cv2.putText(combined_view, "SEARCHING...", (self.WIDTH + 20, iy + 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (80, 80, 80), 2)


        return combined_view