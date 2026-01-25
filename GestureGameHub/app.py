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
    elif game_name == 'fruit':
        from games.fruit_ninja_game import FruitNinjaGame
        return FruitNinjaGame()
    elif game_name == 'street_fighter':
        from games.street_fighter_adapter import StreetFighterAdapter
        return StreetFighterAdapter()  
    elif game_name == 'draw_guess':
        from games.draw_guess_adapter import DrawGuessAdapter
        return DrawGuessAdapter()      
    elif game_name == 'gesture_draw':
        from games.gesture_draw_adapter import GestureDrawAdapter
        return GestureDrawAdapter()
    elif game_name == 'fingertip_catch':
        from games.fingertip_catch_adapter import FingertipCatchAdapter
        return FingertipCatchAdapter()
    return None

# 当前运行的游戏实例
current_game = None

@app.route('/')
def index():
    """主页：游戏大厅"""
    return render_template('index.html')

@app.route('/draw_guess')
def draw_guess_page():
    global current_game
    # 动态加载并初始化
    from games.draw_guess_adapter import DrawGuessAdapter
    current_game = DrawGuessAdapter()
    return render_template('draw_guess.html')

@app.route('/gesture_draw')
def gesture_draw_page():
    global current_game
    from games.gesture_draw_adapter import GestureDrawAdapter
    current_game = GestureDrawAdapter()
    return render_template('gesture_draw.html')

# 你画我猜专属视频流 (为了匹配 draw_guess.html 的 img src)
@app.route('/video_feed_draw')
def video_feed_draw():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
# 接收前端“开始游戏”指令的接口
@app.route('/api/start_game', methods=['POST'])
def start_game_api():
    global current_game
    data = request.get_json(silent=True) or {}
    game_name = data.get('game_name')
    # if no current_game, try to create one from provided game_name
    if current_game is None and game_name:
        inst = get_game_instance(game_name)
        if inst:
            # set as current game
            globals()['current_game'] = inst
    if current_game and hasattr(current_game, 'start_game'):
        try:
            current_game.start_game()
            return jsonify({"status": "started"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "error", "message": "no game instance"}), 400

@app.route('/api/clear_canvas', methods=['POST'])
def clear_canvas_api():
    global current_game
    data = request.get_json(silent=True) or {}
    game_name = data.get('game_name')
    if current_game is None and game_name:
        inst = get_game_instance(game_name)
        if inst:
            globals()['current_game'] = inst
    if current_game:
        if hasattr(current_game, 'canvas'):
            try:
                current_game.canvas[:] = 255
                if hasattr(current_game, 'strokes'):
                    current_game.strokes = []
                if hasattr(current_game, 'current_stroke'):
                    current_game.current_stroke = []
                # reset guide flags if any
                if hasattr(current_game, 'guide_hit_flags'):
                    current_game.guide_hit_flags = [False] * len(getattr(current_game, 'target', {}).get('guide_points', []))
                return jsonify({"status": "ok"})
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "error", "message": "no game instance"}), 400

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
    elif game_name == 'fruit':
        return render_template('fruit.html')   
    elif game_name == 'street_fighter':
        return render_template('street_fighter.html')
    elif game_name == 'draw_guess':
        return render_template('draw_guess.html')
    elif game_name == 'gesture_draw':
        return render_template('gesture_draw.html')
    elif game_name == 'fingertip_catch':
        return render_template('fingertip_catch.html')
    # 默认回退到通用模板
    return render_template('game.html', game_name=game_name)

def gen_frames():
    """视频流生成器"""
    global current_game
    # If the incoming video feed request specifies a game_name, ensure the generator
    # creates/attaches the correct game instance in this request context. This
    # avoids cases where the front-end img src triggers the video feed in a
    # different worker/process without a current_game set.
    try:
        from flask import request as _req
        game_name_q = _req.args.get('game_name')
        if current_game is None and game_name_q:
            inst = get_game_instance(game_name_q)
            if inst:
                globals()['current_game'] = inst
    except Exception:
        pass
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

def cleanup_all_resources(current_game=None):
    """全局资源清理：切换/退出游戏时调用"""
    # 1. 清理 Pygame 资源
    import pygame
    if pygame.get_init():
        pygame.quit()
    
    # 2. 清理 OpenCV/MediaPipe 资源
    import cv2
    cv2.destroyAllWindows()
    
    # 3. 清理游戏特定资源
    if current_game:
        # 释放摄像头
        if hasattr(current_game, 'cam'):
            current_game.cam.stop()
        # 释放模型
        if hasattr(current_game, 'model'):
            del current_game.model
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()