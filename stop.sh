#!/bin/bash

# AI代码审查系统停止脚本

echo "🛑 正在停止AI代码审查系统..."

BACKEND_PORT=5001
FRONTEND_PORT=3000

# 停止后端服务
if lsof -i :$BACKEND_PORT > /dev/null 2>&1; then
    echo "⚠️  正在停止后端服务 (端口 $BACKEND_PORT)..."
    lsof -ti :$BACKEND_PORT | xargs kill -9 2>/dev/null
    echo "✅ 后端服务已停止"
else
    echo "ℹ️  后端服务未运行"
fi

# 停止前端服务
if lsof -i :$FRONTEND_PORT > /dev/null 2>&1; then
    echo "⚠️  正在停止前端服务 (端口 $FRONTEND_PORT)..."
    lsof -ti :$FRONTEND_PORT | xargs kill -9 2>/dev/null
    echo "✅ 前端服务已停止"
else
    echo "ℹ️  前端服务未运行"
fi

echo "✅ 系统已完全停止"
