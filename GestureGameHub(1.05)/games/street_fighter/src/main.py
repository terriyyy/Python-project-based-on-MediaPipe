import math
import pygame
from pygame import mixer
from pygame import font
import cv2
import numpy as np
import os
import sys
from fighter import Fighter

# --- 资源路径辅助函数 ---
# 用于处理打包成 exe 后资源文件的路径问题
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

mixer.init()
pygame.init()

# --- 游戏常量 ---
info = pygame.display.Info()
SCREEN_WIDTH = info.current_w
SCREEN_HEIGHT = info.current_h
FPS = 60
ROUND_OVER_COOLDOWN = 3000 # 回合结束后的冷却时间（毫秒）

# --- 颜色定义 ---
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)

# --- 初始化游戏窗口 ---
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.NOFRAME) # 无边框全屏模式
pygame.display.set_caption("Street Fighter")
clock = pygame.time.Clock()

# --- 加载资源 ---
# 背景图片 (使用 OpenCV 读取以便进行模糊处理)
bg_image = cv2.imread(resource_path("assets/images/bg1.jpg"))

# 胜利图片
victory_img = pygame.image.load(resource_path("assets/images/victory.png")).convert_alpha()
warrior_victory_img = pygame.image.load(resource_path("assets/images/warrior.png")).convert_alpha()
wizard_victory_img = pygame.image.load(resource_path("assets/images/wizard.png")).convert_alpha()

# 字体
menu_font = pygame.font.Font(resource_path("assets/fonts/turok.ttf"), 50)
menu_font_title = pygame.font.Font(resource_path("assets/fonts/turok.ttf"), 100)  # 标题字体更大
count_font = pygame.font.Font(resource_path("assets/fonts/turok.ttf"), 80)
score_font = pygame.font.Font(resource_path("assets/fonts/turok.ttf"), 30)

# 音乐和音效
pygame.mixer.music.load(resource_path("assets/audio/music.mp3"))
pygame.mixer.music.set_volume(0.5)
pygame.mixer.music.play(-1, 0.0, 5000) # 循环播放，有5秒淡入
sword_fx = pygame.mixer.Sound(resource_path("assets/audio/sword.wav"))
sword_fx.set_volume(0.5)
magic_fx = pygame.mixer.Sound(resource_path("assets/audio/magic.wav"))
magic_fx.set_volume(0.75)

# 加载战士精灵表 (Spritesheets)
warrior_sheet = pygame.image.load(resource_path("assets/images/warrior.png")).convert_alpha()
wizard_sheet = pygame.image.load(resource_path("assets/images/wizard.png")).convert_alpha()

# --- 定义动画帧数 ---
# 每个动作对应的帧数列表
WARRIOR_ANIMATION_STEPS = [10, 8, 1, 7, 7, 3, 7]
WIZARD_ANIMATION_STEPS = [8, 8, 1, 8, 8, 3, 7]

# --- 战士数据配置 ---
# [尺寸, 缩放比例, 偏移量]
WARRIOR_SIZE = 162
WARRIOR_SCALE = 4
WARRIOR_OFFSET = [72, 46]
WARRIOR_DATA = [WARRIOR_SIZE, WARRIOR_SCALE, WARRIOR_OFFSET]

WIZARD_SIZE = 250
WIZARD_SCALE = 3
WIZARD_OFFSET = [112, 97]
WIZARD_DATA = [WIZARD_SIZE, WIZARD_SCALE, WIZARD_OFFSET]

# 游戏变量
score = [0, 0]  # 玩家分数: [P1, P2]


def draw_text(text, font, color, x, y):
    """在屏幕上绘制文本"""
    img = font.render(text, True, color)
    screen.blit(img, (x, y))


def blur_bg(image):
    """使用 OpenCV 对背景进行高斯模糊"""
    image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR) # Pygame是RGB，OpenCV是BGR，需转换
    blurred_image = cv2.GaussianBlur(image_bgr, (15, 15), 0)
    return cv2.cvtColor(blurred_image, cv2.COLOR_BGR2RGB) # 转回 RGB


def draw_bg(image, is_game_started=False):
    """根据游戏状态绘制背景（菜单界面模糊，游戏中清晰）"""
    if not is_game_started:
        blurred_bg = blur_bg(image)
        # 将 OpenCV 图像转换为 Pygame Surface
        blurred_bg = pygame.surfarray.make_surface(np.transpose(blurred_bg, (1, 0, 2)))
        blurred_bg = pygame.transform.scale(blurred_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(blurred_bg, (0, 0))
    else:
        # 游戏中直接转换原始图像
        image = pygame.surfarray.make_surface(np.transpose(image, (1, 0, 2)))
        image = pygame.transform.scale(image, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(image, (0, 0))


def draw_button(text, font, text_col, button_col, x, y, width, height):
    """绘制按钮并返回其 Rect 对象以便进行点击检测"""
    pygame.draw.rect(screen, button_col, (x, y, width, height))
    pygame.draw.rect(screen, WHITE, (x, y, width, height), 2) # 边框
    text_img = font.render(text, True, text_col)
    text_rect = text_img.get_rect(center=(x + width // 2, y + height // 2))
    screen.blit(text_img, text_rect)
    return pygame.Rect(x, y, width, height)


def victory_screen(winner_img):
    """显示胜利画面，并提供重新开始选项"""
    # 循环等待用户点击
    while True:
        draw_bg(bg_image)

        # 1. 绘制胜利者图片 (放大显示)
        scale_factor = 2.5
        target_width = int(winner_img.get_width() * scale_factor)
        target_height = int(winner_img.get_height() * scale_factor)
        
        resized_winner = pygame.transform.scale(winner_img, (target_width, target_height))
        img_x = SCREEN_WIDTH // 2 - target_width // 2
        img_y = SCREEN_HEIGHT // 2 - target_height // 2 - 80 # 稍微往上放一点
        
        screen.blit(resized_winner, (img_x, img_y))

        # 2. 绘制 "VICTORY" 文字
        vic_text = "VICTORY!"
        draw_text(vic_text, menu_font_title, YELLOW, SCREEN_WIDTH // 2 - menu_font_title.size(vic_text)[0] // 2, 50)

        # 3. 绘制按钮
        button_width = 350
        button_height = 60
        spacing = 30
        
        # 计算按钮位置 (在图片下方)
        btn_start_y = img_y + target_height + 40
        
        # [重新开始] 按钮
        restart_rect = draw_button("RESTART GAME", menu_font, BLACK, GREEN, 
                                 SCREEN_WIDTH // 2 - button_width // 2, 
                                 btn_start_y, button_width, button_height)
        
        # [回到主菜单] 按钮
        menu_rect = draw_button("MAIN MENU", menu_font, BLACK, RED, 
                              SCREEN_WIDTH // 2 - button_width // 2, 
                              btn_start_y + button_height + spacing, button_width, button_height)

        # 4. 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if restart_rect.collidepoint(event.pos):
                    return "RESTART"  # 返回重启信号
                if menu_rect.collidepoint(event.pos):
                    return "MENU"     # 返回菜单信号

        pygame.display.update()
        clock.tick(FPS)


def draw_gradient_text(text, font, x, y, colors):
    """
    绘制渐变文字效果
    通过轻微偏移多次绘制不同颜色的文字来实现
    """
    offset = 2
    for i, color in enumerate(colors):
        img = font.render(text, True, color)
        screen.blit(img, (x + i * offset, y + i * offset))


def main_menu():
    """主菜单逻辑"""
    animation_start_time = pygame.time.get_ticks()

    while True:
        draw_bg(bg_image, is_game_started=False) # 绘制模糊背景

        # 计算文字缩放动画（呼吸效果）
        elapsed_time = (pygame.time.get_ticks() - animation_start_time) / 1000
        scale_factor = 1 + 0.05 * math.sin(elapsed_time * 2 * math.pi)
        scaled_font = pygame.font.Font("assets/fonts/turok.ttf", int(100 * scale_factor))

        # 绘制标题
        title_text = "STREET FIGHTER"
        colors = [BLUE, GREEN, YELLOW]
        shadow_color = BLACK
        title_x = SCREEN_WIDTH // 2 - scaled_font.size(title_text)[0] // 2
        title_y = SCREEN_HEIGHT // 6

        shadow_offset = 5
        draw_text(title_text, scaled_font, shadow_color, title_x + shadow_offset, title_y + shadow_offset)
        draw_gradient_text(title_text, scaled_font, title_x, title_y, colors)

        # 按钮布局配置
        button_width = 280
        button_height = 60
        button_spacing = 30

        start_button_y = SCREEN_HEIGHT // 2 - (button_height + button_spacing) * 1.5 + 50
        scores_button_y = SCREEN_HEIGHT // 2 - (button_height + button_spacing) * 0.5 + 50
        exit_button_y = SCREEN_HEIGHT // 2 + (button_height + button_spacing) * 0.5 + 50

        # 绘制按钮
        start_button = draw_button("START GAME", menu_font, BLACK, GREEN, SCREEN_WIDTH // 2 - button_width // 2,
                                   start_button_y, button_width, button_height)
        scores_button = draw_button("SCORES", menu_font, BLACK, GREEN, SCREEN_WIDTH // 2 - button_width // 2,
                                    scores_button_y, button_width, button_height)
        exit_button = draw_button("EXIT", menu_font, BLACK, GREEN, SCREEN_WIDTH // 2 - button_width // 2,
                                  exit_button_y, button_width, button_height)

        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if start_button.collidepoint(event.pos):
                    return "START"
                if scores_button.collidepoint(event.pos):
                    return "SCORES"
                if exit_button.collidepoint(event.pos):
                    pygame.quit()
                    exit()

        pygame.display.update()
        clock.tick(FPS)


def scores_screen():
    """比分显示界面"""
    while True:
        draw_bg(bg_image)

        scores_title = "SCORES"
        draw_text(scores_title, menu_font_title, RED, SCREEN_WIDTH // 2 - menu_font_title.size(scores_title)[0] // 2, 50)

        score_font_large = pygame.font.Font("assets/fonts/turok.ttf", 60)  # 分数使用更大的字体
        p1_text = f"P1: {score[0]}"
        p2_text = f"P2: {score[1]}"
        shadow_offset = 5

        # 绘制 P1 分数
        p1_text_x = SCREEN_WIDTH // 2 - score_font_large.size(p1_text)[0] // 2
        p1_text_y = SCREEN_HEIGHT // 2 - 50
        draw_text(p1_text, score_font_large, BLACK, p1_text_x + shadow_offset, p1_text_y + shadow_offset)  # 阴影
        draw_gradient_text(p1_text, score_font_large, p1_text_x, p1_text_y, [BLUE, GREEN])  # 渐变

        # 绘制 P2 分数
        p2_text_x = SCREEN_WIDTH // 2 - score_font_large.size(p2_text)[0] // 2
        p2_text_y = SCREEN_HEIGHT // 2 + 50
        draw_text(p2_text, score_font_large, BLACK, p2_text_x + shadow_offset, p2_text_y + shadow_offset)  # 阴影
        draw_gradient_text(p2_text, score_font_large, p2_text_x, p2_text_y, [RED, YELLOW])  # 渐变

        return_button = draw_button("RETURN TO MAIN MENU", menu_font, BLACK, GREEN, SCREEN_WIDTH // 2 - 220, 700, 500, 50)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if return_button.collidepoint(event.pos):
                    return

        pygame.display.update()
        clock.tick(FPS)


def reset_game():
    """重置游戏：重新创建两个战士对象"""
    global fighter_1, fighter_2
    fighter_1 = Fighter(1, 200, 310, False, WARRIOR_DATA, warrior_sheet, WARRIOR_ANIMATION_STEPS, sword_fx)
    fighter_2 = Fighter(2, 700, 310, True, WIZARD_DATA, wizard_sheet, WIZARD_ANIMATION_STEPS, magic_fx)


def draw_health_bar(health, x, y):
    """绘制血条"""
    pygame.draw.rect(screen, BLACK, (x, y, 200, 20))
    if health > 0:
        pygame.draw.rect(screen, RED, (x, y, health * 2, 20))
    pygame.draw.rect(screen, WHITE, (x, y, 200, 20), 2)


def countdown():
    """游戏开始前的倒计时"""
    countdown_font = pygame.font.Font("assets/fonts/turok.ttf", 100)
    countdown_texts = ["3", "2", "1", "FIGHT!"]

    for text in countdown_texts:
        draw_bg(bg_image, is_game_started=True)

        text_img = countdown_font.render(text, True, RED)
        text_width = text_img.get_width()
        x_pos = (SCREEN_WIDTH - text_width) // 2

        draw_text(text, countdown_font, RED, x_pos, SCREEN_HEIGHT // 2 - 50)

        pygame.display.update()
        pygame.time.delay(1000) # 暂停1秒


def game_loop():
    """游戏主循环 (支持重新开始)"""
    global score
    
    # --- 外层循环：负责游戏的 重启 ---
    while True:
        reset_game()
        round_over = False
        winner_img = None
        game_started = True

        countdown()

        # --- 内层循环：负责 每一帧 的逻辑 ---
        while True:
            # 1. 绘制背景和UI
            draw_bg(bg_image, is_game_started=game_started)
            draw_text(f"P1: {score[0]}", score_font, RED, 20, 20)
            draw_text(f"P2: {score[1]}", score_font, RED, SCREEN_WIDTH - 220, 20)
            draw_health_bar(fighter_1.health, 20, 50)
            draw_health_bar(fighter_2.health, SCREEN_WIDTH - 220, 50)

            # 游戏中的退出按钮
            exit_button = draw_button("MENU", score_font, BLACK, YELLOW, SCREEN_WIDTH // 2 - 50, 20, 100, 40)

            # 2. 游戏逻辑
            if not round_over:
                fighter_1.move(SCREEN_WIDTH, SCREEN_HEIGHT, fighter_2, round_over)
                fighter_2.move(SCREEN_WIDTH, SCREEN_HEIGHT, fighter_1, round_over)

                fighter_1.update()
                fighter_2.update()

                # 胜负判定
                if not fighter_1.alive:
                    score[1] += 1
                    round_over = True
                    winner_img = wizard_victory_img
                elif not fighter_2.alive:
                    score[0] += 1
                    round_over = True
                    winner_img = warrior_victory_img
            else:
                action = victory_screen(winner_img)
                
                if action == "RESTART":
                    break  
                elif action == "MENU":
                    return

            # 3. 绘制角色
            fighter_1.draw(screen)
            fighter_2.draw(screen)

            # 4. 事件处理 (游戏进行中)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if exit_button.collidepoint(event.pos):
                        return

            pygame.display.update()
            clock.tick(FPS)


# --- 程序主入口 ---
while True:
    menu_selection = main_menu()

    if menu_selection == "START":
        game_loop()
    elif menu_selection == "SCORES":
        scores_screen()