from __future__ import annotations

import pygame
from typing import Tuple

from src.utils.directions import Dir, dir_to_vec


class Entity:
    def __init__(self, spawn_px: Tuple[float, float], speed: float, radius: float) -> None:
        self.pos = pygame.Vector2(spawn_px)
        self.speed = float(speed)
        self.radius = float(radius)

        self.dir: Dir = Dir.NONE

    def move_step(self, dt: float) -> pygame.Vector2:
        v = dir_to_vec(self.dir)
        return self.pos + v * (self.speed * dt)
