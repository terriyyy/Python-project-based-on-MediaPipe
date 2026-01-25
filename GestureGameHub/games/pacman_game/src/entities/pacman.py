from __future__ import annotations

import pygame
from typing import Tuple

from src.config import PACMAN_SPEED, PACMAN_RADIUS, CENTER_EPS
from src.entities.base import Entity
from src.map.tilemap import TileMap
from src.utils.directions import Dir, dir_to_vec
from src.utils.grid import is_near_tile_center


class Pacman(Entity):
    # 允许转弯的"半对齐"阈值（越大越容易拐）
    TURN_EPS = 6.0
    # 贴墙吸附速度（像素/秒），越大越"吸中线"
    SNAP_SPEED = 240.0

    def __init__(self, spawn_px: Tuple[float, float]) -> None:
        super().__init__(spawn_px, PACMAN_SPEED, PACMAN_RADIUS)
        self.dir = Dir.LEFT
        self.next_dir = self.dir

    def reset(self, spawn_px: Tuple[float, float]) -> None:
        self.pos.update(spawn_px[0], spawn_px[1])
        self.dir = Dir.LEFT
        self.next_dir = self.dir

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_UP:
            self.next_dir = Dir.UP
        elif event.key == pygame.K_DOWN:
            self.next_dir = Dir.DOWN
        elif event.key == pygame.K_LEFT:
            self.next_dir = Dir.LEFT
        elif event.key == pygame.K_RIGHT:
            self.next_dir = Dir.RIGHT

    def update(self, dt: float, tilemap: TileMap) -> None:
        # 当前所在格子与中心点
        r, c = tilemap.pixel_to_grid(self.pos.x, self.pos.y)
        center = tilemap.grid_center_px(r, c)

        # 1) 贴墙吸附：水平走吸 y 到行中心；竖直走吸 x 到列中心
        self._snap_to_lane(dt, center)

        # 2) 转向：允许“半对齐转弯”
        #    - 转上下：只要求 x 接近列中心
        #    - 转左右：只要求 y 接近行中心
        if self._can_turn_now(self.next_dir, self.pos, center) and self._can_take_dir(self.next_dir, tilemap):
            self.dir = self.next_dir
        else:
            # 兼容：如果完全到中心附近，也允许转（原来的经典规则）
            if is_near_tile_center(self.pos, tilemap, eps=CENTER_EPS) and self._can_take_dir(self.next_dir, tilemap):
                self.dir = self.next_dir

        # 3) 前进：如果前方撞墙，就停在原地（但因为有吸附+半对齐转向，不会卡死）
        if self._can_take_dir(self.dir, tilemap):
            next_pos = self.pos + dir_to_vec(self.dir) * (self.speed * dt)
            tilemap.wrap_if_tunnel_row(next_pos)  # ✅ 提前
            if tilemap.can_move_circle(next_pos, self.radius):
                self.pos = next_pos


    def _snap_to_lane(self, dt: float, center: pygame.Vector2) -> None:
        # 只在有方向移动时吸附
        if self.dir in (Dir.LEFT, Dir.RIGHT):
            self.pos.y = self._approach(self.pos.y, center.y, self.SNAP_SPEED * dt)
        elif self.dir in (Dir.UP, Dir.DOWN):
            self.pos.x = self._approach(self.pos.x, center.x, self.SNAP_SPEED * dt)

    def _can_turn_now(self, want_dir: Dir, pos: pygame.Vector2, center: pygame.Vector2) -> bool:
        if want_dir in (Dir.UP, Dir.DOWN):
            return abs(pos.x - center.x) <= self.TURN_EPS
        if want_dir in (Dir.LEFT, Dir.RIGHT):
            return abs(pos.y - center.y) <= self.TURN_EPS
        return False

    def _can_take_dir(self, d: Dir, tilemap: TileMap) -> bool:
        if d == Dir.NONE:
            return False
        probe = self.pos + dir_to_vec(d) * 2.0
        return tilemap.can_move_circle(probe, self.radius)

    @staticmethod
    def _approach(cur: float, target: float, max_delta: float) -> float:
        if cur < target:
            return min(cur + max_delta, target)
        else:
            return max(cur - max_delta, target)
