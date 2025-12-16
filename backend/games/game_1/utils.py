import cv2
import numpy as np
import math

def calculate_aspect_ratio(landmarks, indices, width, height):
    """
    通用函数：计算眼睛 (EAR) 或嘴巴 (MAR) 的纵横比
    """
    # 获取关键点坐标
    pts = []
    for idx in indices:
        pt = landmarks[idx]
        pts.append(np.array([pt.x * width, pt.y * height]))

    # 计算垂直距离 (例如：上眼皮到下眼皮)
    v1 = np.linalg.norm(pts[1] - pts[5])
    v2 = np.linalg.norm(pts[2] - pts[4])
    
    # 计算水平距离
    h = np.linalg.norm(pts[0] - pts[3])

    # 防止除零
    if h == 0: return 0
    
    ratio = (v1 + v2) / (2.0 * h)
    return ratio

def estimate_head_pose(landmarks, img_w, img_h):
    """
    计算头部姿态 (Yaw, Pitch, Roll)
    """
    from .config import POSE_LANDMARKS
    
    # 准备 2D 图像点
    image_points = []
    for idx in POSE_LANDMARKS:
        lm = landmarks[idx]
        image_points.append([lm.x * img_w, lm.y * img_h])
    image_points = np.array(image_points, dtype="double")

    # 准备 3D 模型点 (通用人脸模型的标准位置)
    model_points = np.array([
        (0.0, 0.0, 0.0),             # 鼻尖
        (0.0, -330.0, -65.0),        # 下巴
        (-225.0, 170.0, -135.0),     # 左眼角
        (225.0, 170.0, -135.0),      # 右眼角
        (-150.0, -150.0, -125.0),    # 左嘴角
        (150.0, -150.0, -125.0)      # 右嘴角
    ])

    # 相机内参矩阵 (近似)
    focal_length = img_w
    center = (img_w / 2, img_h / 2)
    camera_matrix = np.array(
        [[focal_length, 0, center[0]],
         [0, focal_length, center[1]],
         [0, 0, 1]], dtype="double"
    )
    dist_coeffs = np.zeros((4, 1))

    # 解算 PnP
    success, rotation_vector, translation_vector = cv2.solvePnP(
        model_points, image_points, camera_matrix, dist_coeffs
    )

    #  计算欧拉角
    rmat, _ = cv2.Rodrigues(rotation_vector)
    angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
    
    # angles: (pitch, yaw, roll)
    pitch, yaw, roll = angles[0], angles[1], angles[2]
    
    return (pitch, yaw, roll), rotation_vector, translation_vector