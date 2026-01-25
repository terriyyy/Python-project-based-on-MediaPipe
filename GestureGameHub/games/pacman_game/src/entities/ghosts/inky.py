import pygame
from typing import Tuple

from src.entities.ghost import Ghost
from src.map.tilemap import TileMap
from src.utils.directions import dir_to_vec


class Inky(Ghost):
    def __init__(self, spawn_px: pygame.Vector2, tilemap: TileMap) -> None:
        super().__init__(spawn_px, tilemap, color=(60, 220, 255))
        self.corner_target = (tilemap.rows - 1, tilemap.cols - 1)  # 右下

    def get_target(self, tilemap: TileMap, pacman, ghosts, global_phase: str) -> Tuple[int, int]:
        if global_phase == "SCATTER":
            return self.corner_target

        # 找到 Blinky（红鬼）
        blinky = None
        for g in ghosts:
            if g.__class__.__name__ == "Blinky":
                blinky = g
                break

        if blinky is None:
            pr, pc = tilemap.pixel_to_grid(pacman.pos.x, pacman.pos.y)
            return (pr, pc)

        # 经典：a = ahead(2)，target = a + (a - blinky)
        v = dir_to_vec(pacman.dir)
        a_px = pacman.pos + v * (2 * 24)
        ar, ac = tilemap.pixel_to_grid(a_px.x, a_px.y)

        br, bc = tilemap.pixel_to_grid(blinky.pos.x, blinky.pos.y)

        tr = ar + (ar - br)
        tc = ac + (ac - bc)

        # clamp
        tr = max(0, min(tilemap.rows - 1, tr))
        tc = max(0, min(tilemap.cols - 1, tc))
        return (tr, tc)
