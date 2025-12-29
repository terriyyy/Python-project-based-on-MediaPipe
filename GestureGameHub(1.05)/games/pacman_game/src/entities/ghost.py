from __future__ import annotations

import random
from enum import Enum
from typing import Tuple

import pygame

from src.config import (
    GHOST_RADIUS,
    GHOST_SPEED,
    GHOST_FRIGHT_SPEED,
    GHOST_EYES_SPEED,
    CENTER_EPS,
)
from src.entities.base import Entity
from src.map.tilemap import TileMap
from src.utils.directions import Dir, dir_to_vec, opposite
from src.utils.grid import is_near_tile_center


class GhostState(Enum):
    NORMAL = 1
    FRIGHTENED = 2
    EYES = 3


# 方向 -> (dr, dc)
_DIR_TO_DRC = {
    Dir.UP: (-1, 0),
    Dir.DOWN: (1, 0),
    Dir.LEFT: (0, -1),
    Dir.RIGHT: (0, 1),
}


class Ghost(Entity):
    # 贴墙吸附：让鬼始终贴着通道中线走，避免圆形碰撞卡墙
    SNAP_SPEED = 260.0
    # 允许“半对齐转向”的阈值：不必严格等到中心点
    TURN_EPS = 6.0

    def __init__(self, spawn_px: pygame.Vector2, tilemap: TileMap, color: Tuple[int, int, int]) -> None:
        super().__init__((spawn_px.x, spawn_px.y), GHOST_SPEED, GHOST_RADIUS)
        self._spawn = spawn_px.copy()
        self.color = color
        self.state = GhostState.NORMAL
        self.dir = Dir.LEFT

        self.corner_target = (0, 0)

    def reset(self) -> None:
        self.pos.update(self._spawn.x, self._spawn.y)
        self.state = GhostState.NORMAL
        self.dir = Dir.LEFT

    def force_reverse(self) -> None:
        self.dir = opposite(self.dir)

    def get_speed(self) -> float:
        if self.state == GhostState.FRIGHTENED:
            return GHOST_FRIGHT_SPEED
        if self.state == GhostState.EYES:
            return GHOST_EYES_SPEED
        return GHOST_SPEED

    def update(
        self,
        dt: float,
        tilemap: TileMap,
        pacman: "Entity",
        ghosts: list["Ghost"],
        global_phase: str,
        fright_active: bool,
    ) -> None:
        # 1) 状态同步：frightened 覆盖 NORMAL（EYES 不受影响）
        if self.state == GhostState.NORMAL and fright_active:
            self.state = GhostState.FRIGHTENED
        elif self.state == GhostState.FRIGHTENED and (not fright_active):
            self.state = GhostState.NORMAL

        # 2) EYES 回到出生点附近 -> 复活
        if self.state == GhostState.EYES and self._is_at_spawn(tilemap):
            self.state = GhostState.NORMAL
            self.dir = Dir.LEFT

        # 3) 贴墙吸附：水平走吸 y，竖直走吸 x（解决撞墙卡住）
        cr, cc = tilemap.pixel_to_grid(self.pos.x, self.pos.y)
        center = tilemap.grid_center_px(cr, cc)
        self._snap_to_lane(dt, center)

        # 4) 决策：在“格子中心附近”或“下一步会撞墙”时重新选方向
        near_center = is_near_tile_center(self.pos, tilemap, eps=CENTER_EPS)
        will_hit_wall = not self._can_move_forward(tilemap, dt)

        if near_center or will_hit_wall:
            if self.state == GhostState.EYES:
                target = tilemap.pixel_to_grid(self._spawn.x, self._spawn.y)
                self.dir = self._choose_dir_to_target(tilemap, target, allow_reverse=True)
            elif self.state == GhostState.FRIGHTENED:
                self.dir = self._choose_random_dir(tilemap, allow_reverse=True)
            else:
                target = self.get_target(tilemap, pacman, ghosts, global_phase)
                self.dir = self._choose_dir_to_target(tilemap, target, allow_reverse=False)

        # 5) 移动：如果仍然被墙挡住，允许掉头兜底随机换路，避免停死
        speed = self.get_speed()
        if not self._try_move(tilemap, dt, speed):
            # 兜底：允许 reverse 随机找条能走的
            self.dir = self._choose_random_dir(tilemap, allow_reverse=True)
            self._try_move(tilemap, dt, speed)

    # ---------- Target / AI ----------

    def get_target(self, tilemap: TileMap, pacman: "Entity", ghosts: list["Ghost"], global_phase: str) -> Tuple[int, int]:
        """子类实现：CHASE/SCATTER 目标格子"""
        if global_phase == "SCATTER":
            return self.corner_target
        pr, pc = tilemap.pixel_to_grid(pacman.pos.x, pacman.pos.y)
        return (pr, pc)

    # ---------- Movement helpers ----------

    def _try_move(self, tilemap: TileMap, dt: float, speed: float) -> bool:
        next_pos = self.pos + dir_to_vec(self.dir) * (speed * dt)
        tilemap.wrap_if_tunnel_row(next_pos)  # ✅ 提前
        if tilemap.can_move_circle(next_pos, self.radius):
            self.pos = next_pos
            return True

        return False

    def _can_move_forward(self, tilemap: TileMap, dt: float) -> bool:
        speed = self.get_speed()
        next_pos = self.pos + dir_to_vec(self.dir) * (speed * dt)
        tilemap.wrap_if_tunnel_row(next_pos)  # ✅ 提前
        return tilemap.can_move_circle(next_pos, self.radius)


    def _snap_to_lane(self, dt: float, center: pygame.Vector2) -> None:
        # 水平走：吸 y 到行中心；竖直走：吸 x 到列中心
        max_delta = self.SNAP_SPEED * dt
        if self.dir in (Dir.LEFT, Dir.RIGHT):
            self.pos.y = self._approach(self.pos.y, center.y, max_delta)
        elif self.dir in (Dir.UP, Dir.DOWN):
            self.pos.x = self._approach(self.pos.x, center.x, max_delta)

    @staticmethod
    def _approach(cur: float, target: float, max_delta: float) -> float:
        if cur < target:
            return min(cur + max_delta, target)
        return max(cur - max_delta, target)

    def _is_at_spawn(self, tilemap: TileMap) -> bool:
        sr, sc = tilemap.pixel_to_grid(self._spawn.x, self._spawn.y)
        center = tilemap.grid_center_px(sr, sc)
        return (self.pos - center).length() <= (CENTER_EPS + 2.0)

    # ---------- Direction choice (grid-based, robust) ----------

    def _possible_dirs_grid(self, tilemap: TileMap) -> list[Dir]:
        cr, cc = tilemap.pixel_to_grid(self.pos.x, self.pos.y)
        dirs: list[Dir] = []
        for d in (Dir.UP, Dir.DOWN, Dir.LEFT, Dir.RIGHT):
            dr, dc = _DIR_TO_DRC[d]
            nr, nc = cr + dr, cc + dc
            if tilemap.in_bounds(nr, nc) and (not tilemap.is_wall(nr, nc)):
                dirs.append(d)
        return dirs

    def _choose_random_dir(self, tilemap: TileMap, allow_reverse: bool) -> Dir:
        candidates = self._possible_dirs_grid(tilemap)
        if not candidates:
            return opposite(self.dir)

        if (not allow_reverse) and opposite(self.dir) in candidates and len(candidates) > 1:
            candidates.remove(opposite(self.dir))

        return random.choice(candidates) if candidates else opposite(self.dir)

    def _choose_dir_to_target(self, tilemap: TileMap, target_rc: Tuple[int, int], allow_reverse: bool) -> Dir:
        candidates = self._possible_dirs_grid(tilemap)
        if not candidates:
            return opposite(self.dir)

        if (not allow_reverse) and opposite(self.dir) in candidates and len(candidates) > 1:
            candidates.remove(opposite(self.dir))

        if not candidates:
            return opposite(self.dir)

        cr, cc = tilemap.pixel_to_grid(self.pos.x, self.pos.y)
        tr, tc = target_rc

        best_dir = candidates[0]
        best_dist = 10**9

        # 稳定优先级（避免抖动）：按候选顺序比较
        for d in candidates:
            dr, dc = _DIR_TO_DRC[d]
            nr, nc = cr + dr, cc + dc
            dist = abs(nr - tr) + abs(nc - tc)
            if dist < best_dist:
                best_dist = dist
                best_dir = d

        return best_dir
