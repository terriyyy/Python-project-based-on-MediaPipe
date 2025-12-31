import mediapipe as mp
import os
import joblib
import numpy as np
from collections import deque
import time

class GestureEngine:
    def __init__(self):
        self.window_size = 5
        self.history = deque(maxlen=self.window_size) # 滑动窗口
        self.model = None
        
        # 冷却系统
        self.last_cmd = None
        self.last_cmd_time = 0
        self.cooldown = 0.5 
        
        model_path = os.path.join(os.path.dirname(__file__), 'gesture_model_seq.pkl')
        if os.path.exists(model_path):
            try:
                self.model = joblib.load(model_path)
            except:
                pass
        else:
            pass

        self.labels = {
            0: "IDLE", 1: "LEFT", 2: "RIGHT", 3: "JUMP", 
            4: "ATTACK", 5: "SKILL_1", 6: "SKILL_2", 7: "HEAL"
        }

    def detect(self, results):
        if not self.model or not results.multi_hand_landmarks:
            return None

        # 1. 提取当前帧特征
        hand_lms = results.multi_hand_landmarks[0]
        row = []
        base_x = hand_lms.landmark[0].x
        base_y = hand_lms.landmark[0].y
        base_z = hand_lms.landmark[0].z

        for lm in hand_lms.landmark:
            row.extend([lm.x - base_x, lm.y - base_y, lm.z - base_z])
            
        # 2. 加入历史队列
        self.history.append(row)
        
        # 3. 数据不够 5 帧不预测
        if len(self.history) < self.window_size:
            return None

        # 4. 构造输入向量
        input_vec = np.array(self.history).flatten().reshape(1, -1)
        
        # 5. 预测
        try:
            pred_idx = self.model.predict(input_vec)[0]
            cmd = self.labels.get(pred_idx, "IDLE")
            
            current_time = time.time()
            
            # 静态动作：直接返回
            if pred_idx in [0, 1, 2, 7]:
                return cmd
            
            # 动态动作：冷却判定
            if current_time - self.last_cmd_time > self.cooldown:
                self.last_cmd_time = current_time
                return cmd
            
            return None 
            
        except:
            return None