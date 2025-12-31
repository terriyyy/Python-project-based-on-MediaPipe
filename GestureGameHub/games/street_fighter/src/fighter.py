import pygame
class Fighter:
    def __init__(self, player, x, y, flip, data, sprite_sheet, animation_steps, sound):
        self.player = player
        self.size = data[0]
        self.image_scale = data[1]
        self.offset = data[2]
        self.flip = flip
        self.animation_list = self.load_images(sprite_sheet, animation_steps)
        self.action = 0  # 0:idle #1:run #2:jump #3:attack1 #4: attack2 #5:hit #6:death
        self.frame_index = 0
        self.image = self.animation_list[self.action][self.frame_index]
        self.update_time = pygame.time.get_ticks()
        self.rect = pygame.Rect((x, y, 80, 180))
        self.vel_y = 0
        self.running = False
        self.jump = False
        self.attacking = False
        self.attack_type = 0
        self.attack_cooldown = 0
        self.attack_sound = sound
        self.hit = False
        self.health = 100
        self.alive = True

    def load_images(self, sprite_sheet, animation_steps):
        # extract images from spritesheet
        animation_list = []
        for y, animation in enumerate(animation_steps):
            temp_img_list = []
            for x in range(animation):
                temp_img = sprite_sheet.subsurface(x * self.size, y * self.size, self.size, self.size)
                temp_img_list.append(
                    pygame.transform.scale(temp_img, (self.size * self.image_scale, self.size * self.image_scale)))
            animation_list.append(temp_img_list)
        return animation_list

    # 修改后的 move 方法，增加了 gesture_override 参数
    def move(self, screen_width, screen_height, target, round_over, gesture_override=None):
        SPEED = 10
        GRAVITY = 2
        dx = 0
        dy = 0
        self.running = False
        self.attack_type = 0

        key = pygame.key.get_pressed()

        # ---优先使用手势指令 ---
        if gesture_override:
            current_action = gesture_override
        else:
            current_action = None

        # 只有在没有攻击且活着且回合未结束时才能移动
        if self.attacking == False and self.alive == True and round_over == False:
            # 玩家 1 控制 (手势)
            if self.player == 1:
                # 移动
                if key[pygame.K_a] or current_action == "LEFT":
                    dx = -SPEED
                    self.running = True
                if key[pygame.K_d] or current_action == "RIGHT":
                    dx = SPEED
                    self.running = True
                # 跳跃
                if (key[pygame.K_w] or current_action == "JUMP") and self.jump == False:
                    self.vel_y = -30
                    self.jump = True
                # 攻击
                # attack (修改后：支持 ATTACK 和 SKILL)
                if key[pygame.K_r] or key[pygame.K_t] or current_action in ["ATTACK", "SKILL"]:
                    self.attack(target)
                    
                    # 轻攻击
                    if key[pygame.K_r] or current_action == "ATTACK":
                        self.attack_type = 1
                    
                    # 重攻击 (技能)
                    if key[pygame.K_t] or current_action == "SKILL":
                        self.attack_type = 2  # 这会触发 Wizard 的魔法阵动画

            # 玩家 2 控制 (AI指令)
            if self.player == 2:
                # 左移
                if key[pygame.K_LEFT] or current_action == "LEFT":
                    dx = -SPEED
                    self.running = True
                # 右移
                if key[pygame.K_RIGHT] or current_action == "RIGHT":
                    dx = SPEED
                    self.running = True
                # 跳跃
                if (key[pygame.K_UP] or current_action == "JUMP") and self.jump == False:
                    self.vel_y = -30
                    self.jump = True
                # 攻击
                if key[pygame.K_m] or key[pygame.K_n] or current_action == "ATTACK":
                    self.attack(target)
                    # 默认轻攻击
                    if key[pygame.K_m] or current_action == "ATTACK":
                        self.attack_type = 1
                    if key[pygame.K_n]:
                        self.attack_type = 2

        # 应用重力
        self.vel_y += GRAVITY
        dy += self.vel_y

        # 边界检测
        if self.rect.left + dx < 0:
            dx = -self.rect.left
        if self.rect.right + dx > screen_width:
            dx = screen_width - self.rect.right
        if self.rect.bottom + dy > screen_height - 110:
            self.vel_y = 0
            self.jump = False
            dy = screen_height - 110 - self.rect.bottom

        # 面向对手
        if target.rect.centerx > self.rect.centerx:
            self.flip = False
        else:
            self.flip = True

        # 攻击冷却
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        # 更新位置
        self.rect.x += dx
        self.rect.y += dy

    def update(self):
        if self.health <= 0:
            self.health = 0
            self.alive = False
            self.update_action(6)  # 6:death
        elif self.hit:
            self.update_action(5)  # 5:hit
        elif self.attacking:
            if self.attack_type == 1:
                self.update_action(3)  # 3:attack1
            elif self.attack_type == 2:
                self.update_action(4)  # 4:attack2
        elif self.jump:
            self.update_action(2)  # 2:jump
        elif self.running:
            self.update_action(1)  # 1:run
        else:
            self.update_action(0)  # 0:idle

        animation_cooldown = 50
        self.image = self.animation_list[self.action][self.frame_index]
        if pygame.time.get_ticks() - self.update_time > animation_cooldown:
            self.frame_index += 1
            self.update_time = pygame.time.get_ticks()
        if self.frame_index >= len(self.animation_list[self.action]):
            if not self.alive:
                self.frame_index = len(self.animation_list[self.action]) - 1
            else:
                self.frame_index = 0
                if self.action == 3 or self.action == 4:
                    self.attacking = False
                    self.attack_cooldown = 20
                if self.action == 5:
                    self.hit = False
                    self.attacking = False
                    self.attack_cooldown = 20

    def attack(self, target):
        if self.attack_cooldown == 0:
            self.attacking = True
            self.attack_sound.play()
            attacking_rect = pygame.Rect(self.rect.centerx - (2 * self.rect.width * self.flip), self.rect.y,
                                         2 * self.rect.width, self.rect.height)
            if attacking_rect.colliderect(target.rect):
                target.health -= 10
                target.hit = True

    def update_action(self, new_action):
        if new_action != self.action:
            self.action = new_action
            self.frame_index = 0
            self.update_time = pygame.time.get_ticks()

    def draw(self, surface):
        img = pygame.transform.flip(self.image, self.flip, False)
        surface.blit(img, (self.rect.x - (self.offset[0] * self.image_scale), self.rect.y - (self.offset[1] * self.image_scale)))
