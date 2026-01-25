from __future__ import annotations

import pygame

from src.config import (
    TILE,
    COLOR_WALL,
    COLOR_PELLET,
    COLOR_POWER,
    COLOR_PACMAN,
    COLOR_GHOST_FRIGHT,
    COLOR_GHOST_EYES,
    PELLET_RADIUS,
    POWER_RADIUS,
)
from src.map.tilemap import TileMap
from src.entities.pacman import Pacman
from src.entities.ghost import Ghost, GhostState
from src.utils.directions import dir_to_vec, Dir


class Renderer:
    def __init__(self, tilemap: TileMap) -> None:
        self.tilemap = tilemap
        self.wall_rects = list(tilemap.iter_walls())

    def draw_world(self, screen: pygame.Surface) -> None:
        for rect in self.wall_rects:
            pygame.draw.rect(screen, COLOR_WALL, rect)

        for (r, c) in self.tilemap.pellets:
            cx = c * TILE + TILE // 2
            cy = r * TILE + TILE // 2
            pygame.draw.circle(screen, COLOR_PELLET, (cx, cy), PELLET_RADIUS)

        for (r, c) in self.tilemap.powers:
            cx = c * TILE + TILE // 2
            cy = r * TILE + TILE // 2
            pygame.draw.circle(screen, COLOR_POWER, (cx, cy), POWER_RADIUS)

    def draw_pacman(self, screen: pygame.Surface, pacman: Pacman) -> None:
        # ✅ 等边三角形：尖角方向 = 运动方向
        center = pygame.Vector2(pacman.pos.x, pacman.pos.y)

        v = dir_to_vec(pacman.dir)
        if v.length_squared() == 0:
            v = pygame.Vector2(1, 0)  # 没方向时默认朝右
        v = v.normalize()

        perp = pygame.Vector2(-v.y, v.x)

        # 控制三角形大小（可调）
        size = float(pacman.radius) * 1.3

        # 等边三角形几何：tip 在前，底边两点在后
        tip = center + v * size
        base_center = center - v * (size * 0.55)
        left = base_center + perp * (size * 0.75)
        right = base_center - perp * (size * 0.75)

        pygame.draw.polygon(
            screen,
            COLOR_PACMAN,
            [(int(tip.x), int(tip.y)), (int(left.x), int(left.y)), (int(right.x), int(right.y))],
        )

    def draw_ghosts(self, screen: pygame.Surface, ghosts: list[Ghost]) -> None:
        for g in ghosts:
            if g.state == GhostState.FRIGHTENED:
                col = COLOR_GHOST_FRIGHT
            elif g.state == GhostState.EYES:
                col = COLOR_GHOST_EYES
            else:
                col = g.color
            pygame.draw.circle(screen, col, (int(g.pos.x), int(g.pos.y)), int(g.radius))
