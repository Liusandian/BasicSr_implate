@echo off
REM 视频对比工具启动脚本 (Windows)

echo ========================================
echo 视频对比工具启动器
echo ========================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.7+
    pause
    exit /b 1
)

echo [信息] Python已安装
echo.

REM 检查依赖
echo [信息] 检查依赖包...
pip show PyQt5 >nul 2>&1
if errorlevel 1 (
    echo [警告] 缺少依赖包，正在安装...
    pip install -r requirements_video_tool.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
) else (
    echo [信息] 依赖包已安装
)

echo.
echo [信息] 启动视频对比工具...
echo.

REM 运行程序
python video_compare_tool.py

if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出
    pause
)

