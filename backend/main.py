import os
import json
import importlib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse

app = FastAPI()
#  1.挂载静态文件
# 确保 backend 目录下有 static 文件夹，并且里面有 demo.jpg
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")
# 2. CORS 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 3. 核心接口：自动扫描游戏列表
@app.get("/api/games")
def get_game_list():
    """
    扫描 backend/games 文件夹，读取所有 info.json
    """
    games_dir = "./games"
    games_list = []
    # 如果目录不存在，先创建
    if not os.path.exists(games_dir):
        os.makedirs(games_dir)
        return {"code": 200, "data": []}
    # 遍历 games 下的所有文件夹
    for folder_name in os.listdir(games_dir):
        folder_path = os.path.join(games_dir, folder_name)
        info_path = os.path.join(folder_path, "info.json")
        # 只有当它是文件夹，且里面有 info.json 时，才算有效游戏
        if os.path.isdir(folder_path) and os.path.exists(info_path):
            try:
                with open(info_path, "r", encoding="utf-8") as f:
                    game_info = json.load(f)
                    # 强行把 id 设为文件夹名字，防止 json 里写错
                    game_info['id'] = folder_name 
                    games_list.append(game_info)
            except Exception as e:
                print(f"读取 {folder_name} 失败: {e}")

    return {"code": 200, "data": games_list}
# 4. 视频流通用接口
@app.get("/api/stream/{game_id}")
async def video_feed(game_id: str):
    """
    根据 game_id 动态加载对应的 logic.py 并启动视频流
    """
    try:
        # 动态导入模块：例如 backend.games.game_1.logic
        module_path = f"games.{game_id}.logic"
        game_module = importlib.import_module(module_path)
        # 获取生成器函数
        return StreamingResponse(
            game_module.game_logic(), 
            media_type="multipart/x-mixed-replace;boundary=frame"
        )
    except ModuleNotFoundError:
        return {"error": f"Game module '{game_id}' not found"}
    except AttributeError:
        return {"error": "Game logic function not found"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # 启动后端服务
    uvicorn.run(app, host="0.0.0.0", port=8000)