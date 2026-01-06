#!/bin/bash
# 视频对比工具启动脚本 (macOS/Linux)

echo "========================================"
echo "视频对比工具启动器"
echo "========================================"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到Python3，请先安装Python 3.7+"
    exit 1
fi

echo "[信息] Python已安装: $(python3 --version)"
echo ""

# 检查依赖
echo "[信息] 检查依赖包..."
if ! python3 -c "import PyQt5" &> /dev/null; then
    echo "[警告] 缺少依赖包，正在安装..."
    pip3 install -r requirements_video_tool.txt
    if [ $? -ne 0 ]; then
        echo "[错误] 依赖安装失败"
        exit 1
    fi
else
    echo "[信息] 依赖包已安装"
fi

echo ""
echo "[信息] 启动视频对比工具..."
echo ""

# 运行程序
python3 video_compare_tool.py

if [ $? -ne 0 ]; then
    echo ""
    echo "[错误] 程序异常退出"
    read -p "按Enter键退出..."
fi

