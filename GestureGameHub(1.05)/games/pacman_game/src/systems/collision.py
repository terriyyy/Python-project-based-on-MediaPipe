from __future__ import annotations

from dataclasses import dataclass

import pygame

from src.entities.ghost import Ghost, GhostState
from src.entities.pacman import Pacman


@dataclass
class CollisionResult:
    pacman_died: bool
    ate_ghost_count: int


def resolve_pacman_ghost_collisions(pacman: Pacman, ghosts: list[Ghost], fright_active: bool) -> CollisionResult:
    ate = 0
    died = False

    for g in ghosts:
        dist = (pacman.pos - g.pos).length()
        if dist <= (pacman.radius + g.radius - 2):
            if fright_active and g.state != GhostState.EYES:
                # 吃鬼：变成 eyes（回出生点）
                g.state = GhostState.EYES
                ate += 1
            else:
                # 碰到正常鬼：死亡（eyes 不伤人，给你个容错）
                if g.state != GhostState.EYES:
                    died = True
                    break

    return CollisionResult(pacman_died=died, ate_ghost_count=ate)
