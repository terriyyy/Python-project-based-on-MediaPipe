import os
import pygame
from typing import Tuple

from src.config import (
    TILE,
    COLOR_BG,
    COLOR_TEXT,
    START_LIVES,
    PELLET_SCORE,
    POWER_SCORE,
    EAT_GHOST_BASE,
    START_SAFE_TIME,
    RESPAWN_SAFE_TIME,
)
from src.map.level_loader import load_level_txt
from src.map.tilemap import TileMap
from src.entities.pacman import Pacman
from src.entities.ghosts.blinky import Blinky
from src.entities.ghosts.pinky import Pinky
from src.entities.ghosts.inky import Inky
from src.entities.ghosts.clyde import Clyde
from src.systems.mode_controller import ModeController
from src.systems.collision import resolve_pacman_ghost_collisions
from src.rendering.renderer import Renderer


def _find_nearby_passable(tilemap: TileMap, r: int, c: int) -> Tuple[int, int]:
    if not tilemap.is_wall(r, c):
        return (r, c)
    for dist in range(1, 8):
        for dr in range(-dist, dist + 1):
            for dc in range(-dist, dist + 1):
                rr, cc = r + dr, c + dc
                if tilemap.in_bounds(rr, cc) and (not tilemap.is_wall(rr, cc)):
                    return (rr, cc)
    return (r, c)


class Game:
    def __init__(self) -> None:
        # 使用基于文件位置的相对路径（适合多人协作）
        current_dir = os.path.dirname(os.path.abspath(__file__))
        level_path = os.path.join(current_dir, "map", "levels", "level_01.txt")
        level = load_level_txt(level_path)
        self.map = TileMap(level.grid, level.pellets, level.powers, level.tunnels)

        self.pacman = Pacman(level.pacman_spawn_px)

        self.safe_left = START_SAFE_TIME

        pr, pc = self.map.pixel_to_grid(self.pacman.pos.x, self.pacman.pos.y)
        spawns_rc = [
            _find_nearby_passable(self.map, pr - 1, pc),
            _find_nearby_passable(self.map, pr, pc - 1),
            _find_nearby_passable(self.map, pr, pc + 1),
            _find_nearby_passable(self.map, pr + 1, pc),
        ]
        spawns_px = [self.map.grid_center_px(r, c) for (r, c) in spawns_rc]

        self.ghosts = [
            Blinky(spawns_px[0], self.map),
            Pinky(spawns_px[1], self.map),
            Inky(spawns_px[2], self.map),
            Clyde(spawns_px[3], self.map),
        ]

        self.mode = ModeController()

        self.score = 0
        self.lives = START_LIVES

        self.renderer = Renderer(self.map)

        self.rows = self.map.rows
        self.cols = self.map.cols
        self.width = self.cols * TILE
        self.height = self.rows * TILE + 32

        self.font = pygame.font.SysFont("consolas", 18)
        self.game_over = False

    def handle_event(self, event: pygame.event.Event) -> None:
        # ✅ Game Over 时不处理任何输入（重开交给 main.py）
        if self.game_over:
            return
        self.pacman.handle_event(event)

    def update(self, dt: float) -> None:
        if self.game_over:
            return

        if self.safe_left > 0:
            self.safe_left = max(0.0, self.safe_left - dt)

        phase, phase_switched, fright_active = self.mode.update(dt)

        self.pacman.update(dt, self.map)

        r, c = self.map.pixel_to_grid(self.pacman.pos.x, self.pacman.pos.y)
        ate_pellet, ate_power = self.map.eat_at(r, c)
        if ate_pellet:
            self.score += PELLET_SCORE
        if ate_power:
            self.score += POWER_SCORE
            self.mode.trigger_frightened()
            self.mode.reset_eat_chain()

        if self.safe_left <= 0:
            if phase_switched and not fright_active:
                for g in self.ghosts:
                    g.force_reverse()

            for g in self.ghosts:
                g.update(dt, self.map, self.pacman, self.ghosts, phase, fright_active)

            result = resolve_pacman_ghost_collisions(self.pacman, self.ghosts, fright_active)

            if result.ate_ghost_count > 0:
                for _ in range(result.ate_ghost_count):
                    k = self.mode.consume_eat_chain()
                    self.score += EAT_GHOST_BASE * (2 ** k)

            if result.pacman_died:
                self.lives -= 1
                if self.lives <= 0:
                    self.game_over = True
                    return
                # 立即重置位置
                self._reset_positions()
                self.safe_left = RESPAWN_SAFE_TIME

        if self.map.remaining_pellets() == 0:
            self.game_over = True

    def _reset_positions(self) -> None:
        """ 重置吃豆人和幽灵的位置 """
        # 使用基于文件位置的相对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        level_path = os.path.join(current_dir, "map", "levels", "level_01.txt")
        level = load_level_txt(level_path)
        
        # 重置吃豆人位置
        self.pacman.reset(level.pacman_spawn_px)
        
        # 重置每个幽灵的位置（使用它们原始的spawn点）
        for g in self.ghosts:
            g.reset()
        
        # 清除惊吓模式
        self.mode.clear_frightened()

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(COLOR_BG)

        self.renderer.draw_world(screen)
        self.renderer.draw_pacman(screen, self.pacman)
        self.renderer.draw_ghosts(screen, self.ghosts)

        hud_y = self.rows * TILE
        pygame.draw.rect(screen, (15, 15, 15), pygame.Rect(0, hud_y, self.width, 32))
        text = self.font.render(
            f"Score: {self.score}   Lives: {self.lives}   Pellets: {self.map.remaining_pellets()}",
            True,
            COLOR_TEXT,
        )
        screen.blit(text, (8, hud_y + 6))

        if self.safe_left > 0 and not self.game_over:
            tip = self.font.render(f"SAFE: {self.safe_left:.1f}s", True, COLOR_TEXT)
            screen.blit(tip, (8, hud_y - 24))

        if self.game_over:
            tip = self.font.render("GAME OVER (Press R to Restart)", True, COLOR_TEXT)
            screen.blit(tip, (8, hud_y - 24))
