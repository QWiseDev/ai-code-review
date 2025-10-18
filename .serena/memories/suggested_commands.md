# 常用命令
- 后端依赖安装：`pip install -r requirements.txt`
- 启动后端：`python api.py`（默认端口 5001）
- 前端依赖安装：`cd frontend && npm install`
- 前端开发模式：`cd frontend && npm run dev`（Vite 默认 3000，并代理 `/api`）
- 一键启动前后端：`./start.sh`
- Docker 启动：`docker-compose up -d`，查看日志：`docker-compose logs -f`
- 前端静态检查：`cd frontend && npm run lint`，类型检查：`npm run type-check`
- 后端推荐测试：`pytest --maxfail=1 --disable-warnings -q`（需自建 tests/）