#!/bin/bash

# AI代码审查系统启动脚本 - Vue.js前后端分离版本

echo "🚀 启动AI代码审查系统..."

# 检查Node.js和npm
if ! command -v node &> /dev/null; then
    echo "❌ Node.js未安装，请先安装Node.js"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ npm未安装，请先安装npm"
    exit 1
fi

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3未安装，请先安装Python3"
    exit 1
fi

# 安装后端依赖
echo "📦 安装后端依赖..."
pip3 install -r requirements.txt

# 安装前端依赖
echo "📦 安装前端依赖..."
cd frontend
npm install
cd ..

# 检查并清理端口占用
echo "🔍 检查端口占用情况..."
BACKEND_PORT=5001
FRONTEND_PORT=3000

# 检查并杀死占用后端端口的进程
if lsof -i :$BACKEND_PORT > /dev/null 2>&1; then
    echo "⚠️  检测到端口 $BACKEND_PORT 被占用，正在清理..."
    lsof -ti :$BACKEND_PORT | xargs kill -9 2>/dev/null
    sleep 1
fi

# 检查并杀死占用前端端口的进程
if lsof -i :$FRONTEND_PORT > /dev/null 2>&1; then
    echo "⚠️  检测到端口 $FRONTEND_PORT 被占用，正在清理..."
    lsof -ti :$FRONTEND_PORT | xargs kill -9 2>/dev/null
    sleep 1
fi

# 启动后端服务
echo "🔧 启动Flask后端服务 (端口5001)..."
python3 api.py &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端服务
echo "🎨 启动Vue.js前端服务 (端口3000)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "✅ 系统启动完成!"
echo "📱 前端地址: http://localhost:3000"
echo "🔌 后端API: http://localhost:5001"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待用户中断
trap "echo '🛑 正在停止服务...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait