from __future__ import annotations

from typing import Iterable, List, Set, Tuple

import pygame

from src.config import TILE


RC = Tuple[int, int]


class TileMap:
    def __init__(self, grid: List[List[str]], pellets: Set[RC], powers: Set[RC], tunnels: Set[RC]) -> None:
        self.grid = grid
        self.pellets = set(pellets)
        self.powers = set(powers)
        self.tunnels = set(tunnels)

        self.rows = len(grid)
        self.cols = len(grid[0]) if self.rows else 0

        # 哪些行存在 tunnel（简化：该行允许左右穿越）
        self._tunnel_rows = {r for (r, _c) in self.tunnels}

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.rows and 0 <= c < self.cols

    def is_tunnel_row(self, r: int) -> bool:
        return r in self._tunnel_rows

    def is_wall(self, r: int, c: int) -> bool:
        # ✅ tunnel 行：允许左右越界时不当墙（否则圆会被边界卡住）
        if 0 <= r < self.rows and self.is_tunnel_row(r) and (c < 0 or c >= self.cols):
            return False

        if not self.in_bounds(r, c):
            return True
        return self.grid[r][c] == "#"

    def pixel_to_grid(self, px: float, py: float) -> RC:
        c = int(px // TILE)
        r = int(py // TILE)
        r = max(0, min(self.rows - 1, r))
        c = max(0, min(self.cols - 1, c))
        return (r, c)

    def grid_center_px(self, r: int, c: int) -> pygame.Vector2:
        return pygame.Vector2(c * TILE + TILE / 2.0, r * TILE + TILE / 2.0)

    def eat_at(self, r: int, c: int) -> Tuple[bool, bool]:
        ate_pellet = (r, c) in self.pellets
        ate_power = (r, c) in self.powers
        if ate_pellet:
            self.pellets.remove((r, c))
        if ate_power:
            self.powers.remove((r, c))
        return ate_pellet, ate_power

    def remaining_pellets(self) -> int:
        return len(self.pellets) + len(self.powers)

    def iter_walls(self) -> Iterable[pygame.Rect]:
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == "#":
                    yield pygame.Rect(c * TILE, r * TILE, TILE, TILE)

    def wrap_if_tunnel_row(self, pos: pygame.Vector2) -> None:
        """✅ 真正传送：越过边界后把人放到对侧入口格子的中心"""
        r, _ = self.pixel_to_grid(pos.x, pos.y)
        if not self.is_tunnel_row(r):
            return

        w = self.cols * TILE
        # 入口中心点（不会让圆越界）
        left_entry_x = TILE / 2.0
        right_entry_x = w - TILE / 2.0

        if pos.x < 0:
            pos.x = right_entry_x
        elif pos.x >= w:
            pos.x = left_entry_x

    def can_move_circle(self, next_pos: pygame.Vector2, radius: float) -> bool:
        left = int((next_pos.x - radius) // TILE)
        right = int((next_pos.x + radius) // TILE)
        top = int((next_pos.y - radius) // TILE)
        bottom = int((next_pos.y + radius) // TILE)

        for r in range(top, bottom + 1):
            for c in range(left, right + 1):
                if self.is_wall(r, c):
                    wall_rect = pygame.Rect(c * TILE, r * TILE, TILE, TILE)
                    circle_rect = pygame.Rect(
                        next_pos.x - radius, next_pos.y - radius, radius * 2, radius * 2
                    )
                    if wall_rect.colliderect(circle_rect):
                        return False
        return True
