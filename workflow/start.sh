#!/bin/bash

# Workflow 服务启动脚本
# 自动检查并清理端口占用，然后启动服务

PORT=8002
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 启动 Workflow API 服务..."
echo ""

# 检查端口是否被占用
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "⚠️  端口 $PORT 已被占用，正在清理..."
    
    # 获取占用端口的进程 PID
    PIDS=$(lsof -ti :$PORT)
    
    if [ ! -z "$PIDS" ]; then
        echo "   发现进程: $PIDS"
        kill -9 $PIDS 2>/dev/null
        sleep 1
        echo "✅ 已清理占用端口的进程"
    fi
else
    echo "✅ 端口 $PORT 可用"
fi

echo ""
echo "📦 使用 uv 启动服务..."
echo ""

# 切换到脚本目录并启动服务
cd "$SCRIPT_DIR"
uv run python main.py

