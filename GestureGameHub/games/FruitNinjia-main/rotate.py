import pygame

pygame.init()
screen = pygame.display.set_mode((300, 300))
clock = pygame.time.Clock()


def blitRotate2(surf, image, topleft, angle):

    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center = image.get_rect(topleft = topleft).center)
    surf.blit(rotated_image, new_rect.topleft)


image = pygame.image.load('images/new-game.png')

angle = 0
done = False
while not done:
    clock.tick(60)
    pos = (50,50)
    screen.fill(0)
    blitRotate2(screen, image, pos, angle)
    angle += 1
    pygame.display.flip()
    
pygame.quit()
exit()