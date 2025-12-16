import cv2
from .core import CyberPunkGame # 引入刚才写的主逻辑

def game_logic():
    # 0 代表默认摄像头
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    # 实例化游戏核心
    game = CyberPunkGame()

    while True:
        success, frame = cap.read()
        if not success:
            break
        processed_frame = game.process(frame)

        # 编码推流
        ret, buffer = cv2.imencode('.jpg', processed_frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()