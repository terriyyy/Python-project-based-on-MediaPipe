基于 FastAPI (后端) 和 Vue 3 (前端) 的前后端分离项目。
目录
环境准备
项目下载与安装
启动项目
核心架构说明
(如何添加你的游戏)
常见问题 (Troubleshooting)
一、
环境准备
确保你的电脑安装了以下软件：
Python 3.8 或更高版本
Node.js 
Git: 下载地址 (用于代码同步)
VS Code (推荐): 建议安装 Vetur 或 Vue - Official 插件，以及 Python 插件。
二、
项目下载与安装 (部署到本地)
1. 克隆项目代码
打开终端 (CMD / PowerShell / Git Bash)，运行以下命令将代码下载到本地：
git clone https://github.com/YourName/python-group-work.git

cd python-group-work
2. 后端环境配置 (Backend)

后端负责运行 Python 逻辑和处理摄像头画面。

cd backend

1. 创建虚拟环境
Windows:
python -m venv venv
Mac/Linux:
python3 -m venv venv

2. 激活虚拟环境 （激活后终端前会有 (venv) 标志)
Windows PowerShell:
.\venv\Scripts\Activate
Windows CMD:
.\venv\Scripts\activate.bat
Mac/Linux:
source venv/bin/activate

3. 安装项目依赖 (OpenCV, MediaPipe, FastAPI 等)
pip install -r requirements.txt
3. 前端环境配置 (Frontend)

前端负责展示网页界面。

# 新开一个终端窗口 (保持后端终端不动)
cd frontend

# 安装前端依赖 
npm install
启动项目

开发时需要同时启动两个终端窗口。
-------------------------------------------------
终端 1：启动后端
确保已激活虚拟环境 (venv)：
cd backend
python main.py

Uvicorn running on http://0.0.0.0:8000 时，后端启动成功。
------------------------------------------------------
终端 2：启动前端
npm run serve
App running at: http://localhost:8080/ 时，前端启动成功。

打开浏览器访问 http://localhost:8080 即可看到项目首页。

核心架构说明
前端 (Vue)：不需要修改，自动向后端询问，动态生成卡片。

后端 (FastAPI)：会自动扫描 backend/games/ 文件夹。

视频流原理：后端将 Python 处理好的每一帧图片转换成 JPG 数据流 (MJPEG)，前端通过 <img src="..."> 标签直接播放，无需复杂的 WebSocket。

----------------------------------------------------------------------------------------------------------------------
(如何添加你的游戏)

按照以下规范提交代码，不要修改 main.py 或前端代码。
目录结构规范
代码应该放在 backend/games/ 下的一个独立文件夹中。假设你的游戏叫 game_face：

backend/games/game_face/  <-- 你的文件夹 (必须英文)
├── __init__.py           <-- 空文件 (必须有)
├── info.json             <-- 游戏身份证 (必须有)
├── logic.py              <-- 接口文件 (必须有)
├── core.py               <-- (可选) 你的核心算法逻辑
└── utils.py              <-- (可选) 你的工具函数

步骤 1：新建文件夹
在 backend/games/ 下新建你的文件夹，例如 game_face。并在里面新建一个空的 __init__.py。
步骤 2：创建 info.json
这是前端生成卡片的依据。请复制以下内容并修改：
{
  "id": "game_face",
  "title": "xxx",
  "description": "简短介绍...",
  "cover": "http://localhost:8000/static/demo.jpg", 
  "author": "你的名字",
  "route": "/game/game_face"
}

注意：id 必须和文件夹名字一致！route 必须是 /game/文件夹名。

封面图：如果想用自己的图，把图片放入 backend/static/，然后修改 cover 字段。

步骤 3：编写代码 
不能使用 cv2.imshow 和 cv2.waitKey
代码运行在服务器上，弹窗会导致服务器卡死。
推荐写法 (适配器模式)：
写你自己的逻辑 (core.py)：
只要定义一个 process(image) 函数，输入图片，返回画好线的图片即可。


# backend/games/game_face/core.py
import cv2
import mediapipe as mp

class FaceGame:
    def __init__(self):
        # 初始化你的模型
        self.face_mesh = mp.solutions.face_mesh.FaceMesh()
    
    def process(self, img):
        # 你的核心算法
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(img_rgb)
        # ... 画图逻辑 ...
        cv2.putText(img, "My Game", (50,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
        return img

写接口文件 (logic.py)：
这是固定格式，负责把你的代码接到后端视频流上。

# backend/games/game_face/logic.py
import cv2
from .core import FaceGame  # 引入你的类

def game_logic():
    # 打开摄像头 (Windows建议加 cv2.CAP_DSHOW)
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    # 实例化你的游戏
    game = FaceGame()

    while True:
        success, frame = cap.read()
        if not success:
            break
        
        # 调用你的处理函数
        processed_frame = game.process(frame)

        #下面是标准推流代码，不需要改动
        ret, buffer = cv2.imencode('.jpg', processed_frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    
    cap.release()
步骤 4：测试运行
重启后端终端 (Ctrl+C 停止，再 python main.py)。刷新前端网页，游戏卡片就会自动出现
常见问题 (Troubleshooting)
Q1: 运行 pip install 报错
检查: 是否激活了虚拟环境 (venv)
解决: 尝试升级 pip: python -m pip install --upgrade pip，或者使用镜像源: pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
Q2: 网页显示“游戏画面加载中...”但一直没有画面？
检查 1: 查看后端终端是否有报错（红色文字）。
检查 2: 文件名是否正确？比如代码里引用 utils 但文件名是 utitls。
检查 3: 摄像头是否被其他程序占用
解决: 尝试在 logic.py 中将 cv2.VideoCapture(0) 改为 cv2.VideoCapture(0, cv2.CAP_DSHOW)。
Q3: 修改了 info.json 没变化
解决: 后端只在启动时扫描一次文件。修改配置文件或添加新游戏后，必须重启后端服务。注意修改后端文件的话，一定要重启后端服务
