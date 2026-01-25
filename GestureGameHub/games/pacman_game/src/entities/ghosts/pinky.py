import pygame
from typing import Tuple

from src.entities.ghost import Ghost
from src.map.tilemap import TileMap
from src.utils.directions import dir_to_vec


class Pinky(Ghost):
    def __init__(self, spawn_px: pygame.Vector2, tilemap: TileMap) -> None:
        super().__init__(spawn_px, tilemap, color=(255, 140, 200))
        self.corner_target = (0, 0)  # 左上

    def get_target(self, tilemap: TileMap, pacman, ghosts, global_phase: str) -> Tuple[int, int]:
        if global_phase == "SCATTER":
            return self.corner_target

        # ahead(4)：玩家前方 4 格（用像素偏移近似）
        v = dir_to_vec(pacman.dir)
        ahead_px = pacman.pos + v * (4 * 24)  # 4 tiles
        tr, tc = tilemap.pixel_to_grid(ahead_px.x, ahead_px.y)
        return (tr, tc)
