# app.py
from flask import Flask, render_template, Response, request, jsonify
import cv2
import importlib

app = Flask(__name__)

# 动态加载游戏模块，方便后续扩展
def get_game_instance(game_name):
    if game_name == 'maze':
        from games.maze_game import MazeGame
        return MazeGame()
    elif game_name == 'parkour': 
        from games.parkour_game import ParkourGame
        return ParkourGame()
    elif game_name == 'pacman':
        from games.pacman_adapter import PacmanGameAdapter
        return PacmanGameAdapter() 
    # 后续可以在这里添加 'fruit'...
    return None

# 当前运行的游戏实例
current_game = None

@app.route('/')
def index():
    """主页：游戏大厅"""
    return render_template('index.html')

# 接收前端“开始游戏”指令的接口
@app.route('/api/start_game', methods=['POST'])
def start_game_api():
    global current_game
    if current_game and hasattr(current_game, 'start_game'):
        current_game.start_game()
        return jsonify({"status": "started"})
    return jsonify({"status": "error"}), 400

@app.route('/play/<game_name>')
def play(game_name):
    """游戏页面：根据游戏名加载不同的模板"""
    global current_game
    current_game = get_game_instance(game_name)
    
    if not current_game:
        return "游戏未找到 / Game Not Found", 404
    
    # 针对 maze 游戏，渲染专属的 maze.html
    if game_name == 'maze':
        return render_template('maze.html')
    elif game_name == 'parkour':
        return render_template('parkour.html')
    
    elif game_name == 'pacman':
        return render_template('pacman.html')
    # 未来扩展：
    # elif game_name == 'fruit':
    #     return render_template('fruit.html')
        
    # 默认回退到通用模板
    return render_template('game.html', game_name=game_name)

def gen_frames():
    """视频流生成器"""
    global current_game
    # 打开摄像头
    cap = cv2.VideoCapture(0)
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        # 翻转摄像头，像照镜子一样
        frame = cv2.flip(frame, 1)

        # 如果有游戏实例，将这一帧画面交给游戏逻辑处理
        if current_game:
            # process方法返回处理后的游戏画面（包含了游戏UI和摄像头小窗口）
            final_frame = current_game.process(frame)
        else:
            final_frame = frame

        # 将图片编码为jpg格式流传输
        ret, buffer = cv2.imencode('.jpg', final_frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()

@app.route('/video_feed')
def video_feed():
    """前端img标签的src将指向这里"""
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True)