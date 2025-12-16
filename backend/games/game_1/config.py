import cv2
import numpy as np

# --- 视觉风格颜色 (BGR 格式) ---
COLOR_CYAN = (255, 255, 0)      # 青色
COLOR_RED = (0, 0, 255)         # 警告红
COLOR_NEON_GREEN = (0, 255, 127)# 荧光绿
COLOR_TEXT = (255, 255, 255)    # 白色文字

# 左眼/右眼关键点用于计算 EAR
LEFT_EYE_IDXS = [362, 385, 387, 263, 373, 380]
RIGHT_EYE_IDXS = [33, 160, 158, 133, 153, 144]

# 嘴巴关键点用于计算 MAR
MOUTH_IDXS = [78, 308, 13, 14, 87, 317] # 左右角，上下唇中心，上下唇内侧

# 头部姿态估计用的 6 个关键点 (3D Model Points 对应点)
# 鼻尖1, 下巴152, 左眼角33, 右眼角263, 左嘴角61, 右嘴角291
POSE_LANDMARKS = [1, 152, 33, 263, 61, 291]