# GestureGameHub - 手势体感游戏集合

GestureGameHub 是一个基于 MediaPipe 和 OpenCV 的手势识别游戏平台，通过摄像头捕捉手势或脸部动作控制游戏，提供沉浸式的体感交互体验。


## 📋 项目概述
该项目整合多款支持手势/体感控制的游戏，无需键盘鼠标即可操作。核心技术栈包括：
- **手势识别**：MediaPipe 实现实时手部关键点检测
- **Web 框架**：Flask 提供 Web 服务和页面展示
- **游戏开发**：Pygame 用于部分游戏逻辑实现
- **图像处理**：OpenCV 处理摄像头画面和游戏渲染
- **前端界面**：Bootstrap 构建响应式页面


## 🎮 现有游戏
1. **🧩 迷宫寻路**：伸出食指控制绿色光点，避开墙壁到达红色终点，共15关，难度递增
2. **🏃 酷跑大师**：通过头部动作控制角色（左摆/右摇切换车道、抬头跳跃、点头滑铲），躲避障碍物
3. **🟡 吃豆人**：经典街机复刻，手势控制吃豆人移动，吃掉所有豆子并躲避幽灵


## 🚀 安装与运行

### 环境要求
- Python 3.8+
- 摄像头（内置或外接）
- Windows 系统（兼容 `start.bat` 脚本）


### 快速启动（Windows）
双击运行 start.bat，脚本会自动安装依赖并启动服务
打开浏览器访问 http://127.0.0.1:5000 进入游戏大厅

### 增加新游戏
1. 创建游戏核心类
在 games 目录下创建游戏文件（如 mygame.py），继承基础游戏类 BaseGame 并实现核心方法
2. 注册游戏实例
在 app.py 的 get_game_instance 函数中添加新游戏的映射：
###
def get_game_instance(game_name):
    # ... 现有游戏映射 ...
    elif game_name == 'mygame':  # 新增
        from games.mygame import MyGame
        return MyGame()
    return None
###
3. 创建游戏模板页面
在 templates 目录下创建游戏页面（如 mygame.html），参考现有模板结构，核心包含：
游戏画面容器（视频流展示）
操作说明（手势控制方式）
导航按钮（返回大厅）
4. 配置游戏路由
在 app.py 的 play 路由中添加模板映射:
###
@app.route('/play/<game_name>')
def play(game_name):
    # ... 现有逻辑 ...
    elif game_name == 'mygame':  # 新增
        return render_template('mygame.html')
    # ... 其他映射 ...
###
5. 在游戏大厅添加入口
修改 templates/index.html，添加新游戏卡片