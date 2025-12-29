from __future__ import annotations

from enum import Enum
import pygame


class Dir(Enum):
    NONE = 0
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4


_DIR_TO_VEC = {
    Dir.NONE: pygame.Vector2(0, 0),
    Dir.UP: pygame.Vector2(0, -1),
    Dir.DOWN: pygame.Vector2(0, 1),
    Dir.LEFT: pygame.Vector2(-1, 0),
    Dir.RIGHT: pygame.Vector2(1, 0),
}


def dir_to_vec(d: Dir) -> pygame.Vector2:
    return _DIR_TO_VEC[d].copy()


def opposite(d: Dir) -> Dir:
    if d == Dir.UP:
        return Dir.DOWN
    if d == Dir.DOWN:
        return Dir.UP
    if d == Dir.LEFT:
        return Dir.RIGHT
    if d == Dir.RIGHT:
        return Dir.LEFT
    return Dir.NONE
