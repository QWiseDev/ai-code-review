# 多阶段构建 - 前端构建
FROM node:18-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
# 清理npm缓存并安装依赖
RUN npm cache clean --force && npm ci
COPY frontend/ ./
# 设置环境变量解决构建问题
ENV NODE_ENV=production
ENV ROLLUP_WATCH=false
# 构建前端
RUN npm run build

# 后端运行环境
FROM python:3.11-slim AS app

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制并安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=300 --retries=3 -i https://pypi.tuna.tsinghua.edu.cn/simple/ -r requirements.txt

# 复制后端代码
COPY . .

# 复制前端构建产物
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 暴露端口
EXPOSE 5001

# 启动命令
CMD ["python", "api.py"]

# Worker镜像（用于后台任务）
FROM python:3.11-slim AS worker

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制并安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=300 --retries=3 -i https://pypi.tuna.tsinghua.edu.cn/simple/ -r requirements.txt

# 复制后端代码
COPY . .

# 启动RQ Worker
CMD ["python", "-m", "rq.cli", "worker", "--url", "redis://redis:6379"]