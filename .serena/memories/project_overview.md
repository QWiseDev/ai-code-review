# 项目概览
- 目的：提供基于 Flask 的后端与 Vue 3 前端的代码评审/工作流管理平台，集成 GitLab/GitHub 与 LLM 能力，支持工作流排程与队列。
- 技术栈：后端 Python (Flask)，业务模块位于 `biz/`；前端 Vue 3 + TypeScript + Vite；队列/worker 位于 `biz/queue/`；配置及数据目录分别是 `conf/`、`data/`、`log/`。
- 代码结构：`api.py` 为后端入口，`biz/` 细分 `service/`、`entity/`、`gitlab/` 等子模块；`frontend/` 存放前端源码，`frontend/src/api` 封装 HTTP 请求，`frontend/src/views`、`frontend/src/components` 提供页面与组件。
- 框架/依赖：强调复用主流生态与官方 SDK，禁止自研重复轮子，遵守仓库 AGENTS.md 治理规范。