# 操作留痕：团队管理功能开发
- 时间：执行当前任务期间（详见 Git 历史）
- 触发原因：Serena 编辑工具暂未启用代码变更写入能力，本次需大规模修改/新增 Python 与 Vue 代码，只能降级使用 Codex CLI 的 `apply_patch` 方式编辑。
- 影响范围：
  - `api.py`
  - `biz/service/review_service.py`
  - `biz/utils/im/team_webhook.py`
  - `frontend/src/api/teams.ts`
  - `frontend/src/views/admin/TeamsView.vue`
  - `frontend/src/router/index.ts`
  - `frontend/src/layouts/AdminLayout.vue`
- 回滚思路：
  1. 数据库：如需回滚团队功能，可删除 `teams` 与 `team_members` 表，并移除相关 API/前端入口。
  2. 代码：使用版本控制回退上述文件的改动即可恢复既有逻辑。
- 验证：已通过 `python3 -m compileall` 对关键后端文件进行语法校验，建议补充前端 `npm run lint` 与后端业务级联调验证。