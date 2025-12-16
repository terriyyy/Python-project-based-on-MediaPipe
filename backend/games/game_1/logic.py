import cv2
import mediapipe as mp

def game_logic():
    """
    组员的游戏逻辑封装在这里
    """
    # 1. 初始化 (保持你原来的代码不变)
    cap = cv2.VideoCapture(0)
    
    mpHands = mp.solutions.hands
    hands = mpHands.Hands()
    mpDraw = mp.solutions.drawing_utils
    
    # 定义画笔风格
    handLmsStyle = mpDraw.DrawingSpec(color=(0, 0, 255), thickness=5, circle_radius=1)
    handLConStyle = mpDraw.DrawingSpec(color=(0, 255, 0), thickness=10, circle_radius=1)

    while True:
        ret, img = cap.read()
        if not ret:
            break
            
        # 2. 核心算法处理 (保持你原来的逻辑)
        # 转 RGB
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        result = hands.process(imgRGB)
        
        imgHeight = img.shape[0]
        imgWidth = img.shape[1]
        
        if result.multi_hand_landmarks:
            for handLms in result.multi_hand_landmarks:
                # 画线和点
                mpDraw.draw_landmarks(img, handLms, mpHands.HAND_CONNECTIONS, handLmsStyle, handLConStyle)
        # 3. 在我的这个代码中，原本需要cv2.imshow('img', img)，cv2.waitKey(1)，但是现在不要 cv2.imshow，而是转成流发给前端
        # cv2.imshow('img', img)  <-- 这句删掉
        # cv2.waitKey(1)          <-- 这句删掉

        # 编码成 JPG
        ret, buffer = cv2.imencode('.jpg', img)
        frame_bytes = buffer.tobytes()
        # 发送数据流 (这是固定写法，都需要这个)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()