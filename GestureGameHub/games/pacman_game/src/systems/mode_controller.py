from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from src.config import PHASE_SCHEDULE, FRIGHT_DURATION


@dataclass
class ModeTick:
    phase: str
    phase_switched: bool
    fright_active: bool


class ModeController:
    def __init__(self) -> None:
        self._schedule = PHASE_SCHEDULE
        self._idx = 0
        self._phase = self._schedule[0][0]
        self._phase_elapsed = 0.0

        self._fright_left = 0.0
        self._eat_chain = 0  # 吃鬼连击：0->200,1->400,2->800,...

    def update(self, dt: float) -> Tuple[str, bool, bool]:
        phase_switched = False

        # frightened 计时
        if self._fright_left > 0:
            self._fright_left = max(0.0, self._fright_left - dt)

        # 正常 phase 计时（frightened 期间也继续走 schedule，简化）
        self._phase_elapsed += dt
        cur_phase, cur_dur = self._schedule[self._idx]
        if self._phase_elapsed >= cur_dur:
            self._idx = min(self._idx + 1, len(self._schedule) - 1)
            self._phase = self._schedule[self._idx][0]
            self._phase_elapsed = 0.0
            phase_switched = True

        return self._phase, phase_switched, (self._fright_left > 0)

    def trigger_frightened(self) -> None:
        self._fright_left = FRIGHT_DURATION

    def clear_frightened(self) -> None:
        self._fright_left = 0.0

    def reset_eat_chain(self) -> None:
        self._eat_chain = 0

    def consume_eat_chain(self) -> int:
        k = self._eat_chain
        self._eat_chain += 1
        return k
