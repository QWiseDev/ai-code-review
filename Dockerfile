# =======================
# Frontend build stage
# =======================
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ENV NODE_ENV=production
ENV ROLLUP_WATCH=false
RUN npm run build

# =======================
# Backend runtime (single container: API + static)
# =======================
FROM python:3.11-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

# 如无编译需求可删除 gcc 安装，以进一步瘦身
RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# 先装依赖，最大化缓存命中
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=300 --retries=3 -i https://pypi.tuna.tsinghua.edu.cn/simple/ -r requirements.txt

# 复制后端代码
COPY . .

# 复制前端构建产物到后端可服务的路径（与原有习惯一致）
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

EXPOSE 5001
CMD ["python", "api.py"]