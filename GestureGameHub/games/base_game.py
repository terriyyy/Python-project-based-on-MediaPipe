# games/base_game.py
import cv2
import mediapipe as mp

class BaseGame:
    def __init__(self):
        # 初始化 MediaPipe
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils

    def process(self, frame):
        """
        核心方法：
        1. 接收摄像头原始画面 frame
        2. 进行 MediaPipe 识别
        3. 更新游戏逻辑
        4. 绘制游戏画面
        5. 返回最终合成的图片
        """
        # 将BGR转RGB供MediaPipe使用
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(img_rgb)
        
        # 子类需要实现具体的 update_and_draw
        return self.update_and_draw(frame, results)

    def update_and_draw(self, frame, results):
        raise NotImplementedError("每个游戏必须实现这个方法")