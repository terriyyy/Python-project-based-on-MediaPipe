import pygame

from src.game import Game
from src.config import FPS, WINDOW_TITLE


def main():
    pygame.init()
    pygame.display.set_caption(WINDOW_TITLE)

    game = Game()
    screen = pygame.display.set_mode((game.width, game.height))
    clock = pygame.time.Clock()

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                    continue

                # ✅ 只在这里允许重开：必须 game_over 且按下 R
                if event.key == pygame.K_r and game.game_over:
                    game = Game()
                    screen = pygame.display.set_mode((game.width, game.height))
                    continue

            # 其他事件交给 game（game_over 时它会忽略）
            game.handle_event(event)

        game.update(dt)
        game.draw(screen)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
