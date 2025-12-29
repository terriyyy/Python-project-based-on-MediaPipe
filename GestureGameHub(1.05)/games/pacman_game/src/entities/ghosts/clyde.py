import pygame
from typing import Tuple

from src.entities.ghost import Ghost
from src.map.tilemap import TileMap


class Clyde(Ghost):
    def __init__(self, spawn_px: pygame.Vector2, tilemap: TileMap) -> None:
        super().__init__(spawn_px, tilemap, color=(255, 170, 60))
        self.corner_target = (tilemap.rows - 1, 0)  # 左下

    def get_target(self, tilemap: TileMap, pacman, ghosts, global_phase: str) -> Tuple[int, int]:
        if global_phase == "SCATTER":
            return self.corner_target

        pr, pc = tilemap.pixel_to_grid(pacman.pos.x, pacman.pos.y)
        cr, cc = tilemap.pixel_to_grid(self.pos.x, self.pos.y)
        d = abs(cr - pr) + abs(cc - pc)

        # 经典味：距离<=8 就回角落，否则追
        if d <= 8:
            return self.corner_target
        return (pr, pc)
