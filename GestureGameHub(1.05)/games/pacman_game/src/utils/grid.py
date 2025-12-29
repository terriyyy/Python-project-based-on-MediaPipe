from __future__ import annotations

import pygame

from src.map.tilemap import TileMap


def is_near_tile_center(pos: pygame.Vector2, tilemap: TileMap, eps: float) -> bool:
    r, c = tilemap.pixel_to_grid(pos.x, pos.y)
    center = tilemap.grid_center_px(r, c)
    return (pos - center).length() <= eps
