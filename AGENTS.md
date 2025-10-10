/# Repository Guidelines

## 项目结构与模块分工
- `api.py`：Flask 主入口，聚合路由与依赖注入，依赖 `biz` 层完成业务编排。
- `biz/`：按领域拆分的后端业务实现，`service/` 管工作流，`entity/` 存放数据模型，`gitlab/`、`github/`、`llm/` 负责外部平台与模型适配。
- `frontend/`：Vue 3 + TypeScript 前端，`src/api` 封装 HTTP 调度，`src/views` 与 `src/components` 负责页面与可复用模块。
- `conf/`、`data/`、`log/`：分别保存环境变量模板、持久化数据与运行日志；在本地调试时请勿将敏感文件提交。

## 构建、测试与开发命令
- `./start.sh`：一键启动前后端，适合本地首次体验，需先复制 `conf/.env.example`。
- `pip install -r requirements.txt` + `python api.py`：安装依赖并启动 Flask API，默认端口 `5001`。
- `cd frontend && npm install && npm run dev`：前端开发模式，Vite 默认监听 `3000` 并代理 `/api`。
- `docker-compose up -d` / `docker-compose logs -f`：容器化启动与查看日志，适合集成交付。
- `npm run lint`、`npm run type-check`：前端静态检查；后端推荐新增 `pytest` 后执行 `pytest -q`。

## 编码风格与命名规范
- Python 代码遵循 PEP 8，建议使用 4 空格缩进；新增模块沿用 `snake_case`，类名使用 `PascalCase`。
- Vue 组件文件命名采用 `PascalCase.vue`，组合式 API 中的局部变量使用 `camelCase`。
- 前端统一执行 `npm run lint -- --fix` 自动修复；后端建议引入 `ruff` 或 `black` 保持一致格式，提交前至少进行一次本地格式化。

## 测试准则
- 现有仓库尚未提供正式测试目录，新增测试请放在后端 `tests/`（`test_*.py`）与前端 `frontend/tests/`（使用 Vitest + Vue Test Utils）。
- 回归级用例需覆盖关键业务路径（如 MR 分析、GitLab/GitHub 回调处理），目标语句覆盖率 ≥70%。
- 本地执行：后端 `pytest --maxfail=1 --disable-warnings -q`，前端 `npx vitest run --coverage`（创建测试后生效）。

## 提交与合并请求规范
- Git 历史以约定式提交为主（如 `feat:`, `fix:`, `docs:`），说明应聚焦业务影响，可使用中英文混合描述。
- 单个提交保持自洽：包含实现、必要的配置与文档/测试调整，不要捆绑无关变更。
- Pull Request 需包含变更摘要、测试结论、关联 issue/MR 链接；涉及 UI 的更新附带截图或录屏；跨平台改动说明验证环境。

## 安全与配置提示
- 所有密钥存放于 `conf/.env`，请使用 `.env.example` 作为模板并在部署环境通过密钥管理系统注入。
- 日志默认落盘到 `log/`，生产部署建议接入集中日志（如 Loki/ELK）并配置轮转策略。
- 引入新第三方集成时，先在 `doc/` 下补充最小可行配置说明，避免重复踩坑。
