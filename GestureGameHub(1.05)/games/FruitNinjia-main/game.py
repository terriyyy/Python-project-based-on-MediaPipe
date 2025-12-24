# coding=utf-8
# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.


import pygame, sys
import os
import random
import time


def main(pos):
    # set the window size
    WIDTH = 600
    HEIGHT = 400
    FPS = 30  # gameDisplay的帧率，1/12秒刷新一次
    pygame.init()
    pygame.display.set_caption('Fruit Ninja')  # title
    gameDisplay = pygame.display.set_mode((WIDTH, HEIGHT))  # set the size of window
    clock = pygame.time.Clock()

    # colour may be used
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)

    background = pygame.image.load('images/background.jpg')  # background
    font = pygame.font.Font(os.path.join(os.getcwd(), 'comic.ttf'), 42)  # 字体



    # generate the position of the fruits randomly
    def generate_random_fruits(fruit):
        fruit_path = "images/fruit_images/" + fruit + ".png"
        data[fruit] = {
            'img': pygame.image.load(fruit_path),
            'x': random.randint(100, 500),
            'y': 400,
            'speed_x': random.randint(-3, 3),
            'speed_y': random.randint(-20, -15),
            'throw': False,
            't': 0,
            'hit': False,
        }

        # 炸弹出现频率降低50%
        if fruit == 'boom':
            if random.random() >= 0.875:  # 12.5%概率，是普通水果的一半
                data[fruit]['throw'] = True
            else:
                data[fruit]['throw'] = False
        else:
            if random.random() >= 0.75:  # 普通水果25%概率
                data[fruit]['throw'] = True
            else:
                data[fruit]['throw'] = False


    data = {}
    ring={'new_game':0,'quit':0,'dojo':0}
    fruits = {'apple', 'banana', 'basaha', 'peach', 'sandia', 'boom'}
    for fruit in fruits:
        generate_random_fruits(fruit)



    # draw the font
    font_name = pygame.font.match_font('comic.ttf')


    def draw_text(display, text, size, x, y):
        font = pygame.font.Font(font_name, size)
        text_surface = font.render(text, True, WHITE)
        text_rect = text_surface.get_rect()
        text_rect.midtop = (x, y)
        gameDisplay.blit(text_surface, text_rect)


    # 绘制玩家的生命
    def draw_lives(display, x, y, lives, image):
        for i in range(lives):
            img = pygame.image.load(image)
            img_rect = img.get_rect()
            img_rect.x = int(x + 35 * i)
            img_rect.y = y
            display.blit(img, img_rect)


    def hide_cross_lives(x, y):
        gameDisplay.blit(pygame.image.load("images/score.png"), (x, y))


    def show_gameover_screen():
        gameDisplay.blit(background, (0, 0))
        draw_text(gameDisplay, "FRUIT NINJA!", 90, WIDTH / 2, HEIGHT / 4)
        if not game_over:
            draw_text(gameDisplay, "Score : " + str(score), 50, WIDTH / 2, HEIGHT / 2)

        draw_text(gameDisplay, "Press a key to begin!", 64, WIDTH / 2, HEIGHT * 3 / 4)
        pygame.display.flip()
        waiting = True
        while waiting:
            clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                if event.type == pygame.KEYUP:
                    waiting = False
    
    def blitRotate(image, topleft, angle):

        rotated_image = pygame.transform.rotate(image, angle)
        new_rect = rotated_image.get_rect(center = image.get_rect(topleft = topleft).center)
        gameDisplay.blit(rotated_image, new_rect.topleft)
        

    def show_gamestart_screen():
        logo1 = pygame.image.load('images/logo.png')  # background
        logo2 = pygame.image.load('images/ninja.png')
        ring_new_game = pygame.image.load('images/new-game.png')
        ring_quit = pygame.image.load('images/quit.png')
        ring_dojo = pygame.image.load('images/dojo.png')
        gameDisplay.blit(background, (0, 0))
        gameDisplay.blit(logo1, (10, 10))
        gameDisplay.blit(logo2, (320, 50))
        gameDisplay.blit(data['boom']['img'], (480, 190))
        gameDisplay.blit(data['sandia']['img'], (290, 255))
        gameDisplay.blit(data['peach']['img'], (100, 260))

        # draw_text(gameDisplay, "Press a key to begin!", 64, WIDTH / 2, HEIGHT * 3 / 4)
        pygame.display.flip()

        waiting = True
        angle=0
        while waiting:
            angle += 2
            if angle>360:
                angle=angle//360
            blitRotate(ring_dojo,(40,200),angle)
            blitRotate(ring_new_game,(240,200),angle)
            blitRotate(ring_quit,(440,150),angle)
            
            pygame.display.flip()
            clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                if event.type == pygame.KEYUP:
                    waiting = False



    first_round = True
    game_over = True
    game_running = True
    while game_running:
        # pygame.mouse.set_pos(pos[0][0],pos[0][1])  # 注释掉以使用正常鼠标控制
        if game_over:
            if first_round:
                show_gamestart_screen()
                first_round = False
            game_over = False
            player_lives = 3
            draw_lives(gameDisplay, 350, 5, player_lives, 'images/score.png')
            score = 0

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                game_running = False

        gameDisplay.blit(background, (0, 0))
        gameDisplay.blit(font.render('Score : ' + str(score), True, (255, 255, 255)), (0, 0))
        draw_lives(gameDisplay, 350, 5, player_lives, 'images/score.png')

        for key, value in data.items():
            if value['throw']:
                value['x'] += value['speed_x']
                value['y'] += value['speed_y']
                value['speed_y'] += (0.05 * value['t'])
                value['t'] += 1

                if value['y'] <= 800:
                    gameDisplay.blit(value['img'], (value['x'], value['y']))
                else:
                    generate_random_fruits(key)

                current_position = pygame.mouse.get_pos()

                if not value['hit'] and value['x'] < current_position[0] < value['x'] + 60 \
                        and value['y'] < current_position[1] < value['y'] + 60:
                    if key == 'boom':
                        player_lives -= 1
                        if player_lives == 0:
                            hide_cross_lives(455, 15)
                        elif player_lives == 1:
                            hide_cross_lives(420, 15)
                        elif player_lives == 2:
                            hide_cross_lives(385, 15)

                        if player_lives < 0:
                            show_gameover_screen()
                            game_over = True

                        half_fruit_path = "images/fruit_images/xxxf.png"
                    else:
                        half_fruit_path = "images/fruit_images/" + key + "-1" + ".png"

                    value['img'] = pygame.image.load(half_fruit_path)
                    value['speed_x'] += 10
                    if key != 'boom':
                        score += 1
                    score_text = font.render('Score : ' + str(score), True, (255, 255, 255))
                    value['hit'] = True
            else:
                generate_random_fruits(key)

        pygame.display.update()
        clock.tick(FPS)

    pygame.quit()

if __name__ == '__main__':
    main()