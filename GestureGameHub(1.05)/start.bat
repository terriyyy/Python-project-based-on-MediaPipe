@echo off
:: 解决中文乱码：设置控制台编码为UTF-8
chcp 65001 >nul 2>&1

echo ==============================================
echo 正在检查并安装所需依赖...
echo ==============================================

:: 检查是否存在requirements.txt
if not exist "requirements.txt" (
    echo 错误：未找到requirements.txt文件，请确认文件存在于项目根目录
    pause
    exit /b 1
)

:: 优先使用pip3，不强制升级已安装包（加快安装速度）
where pip3 >nul 2>&1
if %errorlevel% equ 0 (
    pip3 install -r requirements.txt --quiet
) else (
    where pip >nul 2>&1
    if %errorlevel% equ 0 (
        pip install -r requirements.txt --quiet
    ) else (
        echo 错误：未找到pip，请确保Python已正确安装并添加到环境变量
        pause
        exit /b 1
    )
)

:: 检查安装是否成功
if %errorlevel% equ 0 (
    echo ==============================================
    echo 依赖安装完成，正在启动应用...
    echo ==============================================
    :: 启动时指定Python编码为UTF-8，避免运行时乱码
    python -X utf8 app.py
    echo ==============================================
    echo 应用已退出，按任意键关闭窗口...
    pause
) else (
    echo 错误：依赖安装失败，请检查网络连接或requirements.txt内容
    pause
    exit /b 1
)