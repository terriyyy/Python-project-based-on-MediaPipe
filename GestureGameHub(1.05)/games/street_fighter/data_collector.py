import cv2
import mediapipe as mp
import numpy as np
import csv
import os

# 定义标签 (包含动态动作了！)
LABELS = {
    0: "IDLE",       # 待机
    1: "LEFT",       # 大拇指左
    2: "RIGHT",      # 大拇指右
    3: "JUMP",       # 向上扇风
    4: "ATTACK",     # 向前出拳
    5: "SKILL_1",    # 向下切
    6: "SKILL_2",    # 向右划过
    7: "HEAL"        # 双手合十
}

def collect_data():
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7)
    cap = cv2.VideoCapture(0)
    
    file_path = os.path.join(os.path.dirname(__file__), 'gesture_data_seq.csv') # 新文件名
    
    # 初始化 CSV
    if not os.path.exists(file_path):
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            # 记录 63 个相对坐标 (21点 * 3维)
            header = [f'v{i}' for i in range(63)] + ['label']
            writer.writerow(header)

    print(f"=== 全动作数据采集 (Sequence Mode) ===")
    print(f"静态动作 (0,1,2,7): 按住键 -> 保持姿势 -> 松开")
    print(f"动态动作 (3,4,5,6): 按住键 -> 做一次完整动作 -> 松开")
    print(LABELS)

    while True:
        ret, frame = cap.read()
        if not ret: break
        
        # 镜像翻转，与游戏视角一致
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)
        
        display_frame = frame.copy()
        current_row = []

        if results.multi_hand_landmarks:
            # 默认取第一只手作为主手 (如果是HEAL需要两只手，这里简化逻辑，
            # HEAL通常两只手都在，我们只记录第一只检测到的手的主特征，或者你需要更复杂的逻辑
            # 为了简化动态识别，我们主要追踪一只手的运动轨迹)
            hand_lms = results.multi_hand_landmarks[0]
            
            # --- 关键：归一化 (相对坐标) ---
            base_x = hand_lms.landmark[0].x
            base_y = hand_lms.landmark[0].y
            base_z = hand_lms.landmark[0].z

            for lm in hand_lms.landmark:
                current_row.extend([lm.x - base_x, lm.y - base_y, lm.z - base_z])
            
            mp.solutions.drawing_utils.draw_landmarks(display_frame, hand_lms, mp_hands.HAND_CONNECTIONS)

        # 提示文本
        cv2.putText(display_frame, "Hold 0-7 to Record", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow('Data Collector', display_frame)
        
        key = cv2.waitKey(1)
        if key == ord('q'):
            break
        elif 48 <= key <= 55: # '0'-'7'
            label = key - 48
            if len(current_row) == 63: # 确保检测到了手
                with open(file_path, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(current_row + [label])
                print(f"Recording: {LABELS[label]}...")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    collect_data()