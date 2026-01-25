from dataclasses import dataclass
from pathlib import Path
from typing import List, Set, Tuple

from src.config import TILE


Grid = List[List[str]]
RC = Tuple[int, int]


@dataclass(frozen=True)
class LevelData:
    grid: Grid
    pellets: Set[RC]
    powers: Set[RC]
    tunnels: Set[RC]
    pacman_spawn_px: Tuple[float, float]


def load_level_txt(path: str) -> LevelData:
    text = Path(path).read_text(encoding="utf-8").splitlines()
    text = [line.rstrip("\n") for line in text if line.strip("\n") != ""]
    if not text:
        raise ValueError("Empty level file")

    cols = max(len(line) for line in text)
    grid: Grid = []
    pellets: Set[RC] = set()
    powers: Set[RC] = set()
    tunnels: Set[RC] = set()

    pacman_spawn: RC | None = None

    for r, line in enumerate(text):
        row = list(line.ljust(cols))
        for c, ch in enumerate(row):
            if ch == "P":
                pacman_spawn = (r, c)
                row[c] = " "
            elif ch == ".":
                pellets.add((r, c))
                row[c] = " "
            elif ch == "o":
                powers.add((r, c))
                row[c] = " "
            elif ch == "T":
                tunnels.add((r, c))
                row[c] = " "
        grid.append(row)

    if pacman_spawn is None:
        raise ValueError("Level must contain a 'P' (pacman spawn).")

    pr, pc = pacman_spawn
    pacman_spawn_px = (pc * TILE + TILE / 2.0, pr * TILE + TILE / 2.0)

    return LevelData(
        grid=grid,
        pellets=pellets,
        powers=powers,
        tunnels=tunnels,
        pacman_spawn_px=pacman_spawn_px,
    )
