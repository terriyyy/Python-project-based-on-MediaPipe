import pygame
from typing import Tuple

from src.entities.ghost import Ghost
from src.map.tilemap import TileMap


class Blinky(Ghost):
    def __init__(self, spawn_px: pygame.Vector2, tilemap: TileMap) -> None:
        super().__init__(spawn_px, tilemap, color=(255, 60, 60))
        self.corner_target = (0, tilemap.cols - 1)  # 右上

    def get_target(self, tilemap: TileMap, pacman, ghosts, global_phase: str) -> Tuple[int, int]:
        if global_phase == "SCATTER":
            return self.corner_target
        pr, pc = tilemap.pixel_to_grid(pacman.pos.x, pacman.pos.y)
        return (pr, pc)
