# Window / timing
FPS = 60
WINDOW_TITLE = "Pacman (4 Ghosts)"

# Grid
TILE = 24
CENTER_EPS = 2.0  # px tolerance to treat as "at tile center"

# Movement (px/sec)
PACMAN_SPEED = 120.0
GHOST_SPEED = 70.0
GHOST_FRIGHT_SPEED = 65.0
GHOST_EYES_SPEED = 140.0
# Scoring
PELLET_SCORE = 10
POWER_SCORE = 50
EAT_GHOST_BASE = 200

# Game
START_LIVES = 1  # 只有一条命，掉命立即重开

# Debug-friendly safe time
START_SAFE_TIME = 5.0    # 开局安全期（秒）
RESPAWN_SAFE_TIME = 3.0  # 复活安全期（秒）

FRIGHT_DURATION = 7.0  # seconds

# Global phase schedule (simple classic-ish)
PHASE_SCHEDULE = [
    ("SCATTER", 7.0),
    ("CHASE", 20.0),
    ("SCATTER", 7.0),
    ("CHASE", 20.0),
    ("SCATTER", 5.0),
    ("CHASE", 10**9),
]

# Colors (RGB)
COLOR_BG = (0, 0, 0)
COLOR_WALL = (0, 80, 220)
COLOR_PELLET = (240, 240, 240)
COLOR_POWER = (240, 240, 240)

COLOR_PACMAN = (255, 220, 0)

COLOR_GHOST_FRIGHT = (50, 80, 255)
COLOR_GHOST_EYES = (230, 230, 230)

COLOR_TEXT = (220, 220, 220)

# Render sizes
PELLET_RADIUS = 3
POWER_RADIUS = 6
PACMAN_RADIUS = 9
GHOST_RADIUS = 9
