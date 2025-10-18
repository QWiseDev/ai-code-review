# 编码规范
- Python 遵循 PEP 8，使用 4 空格缩进，模块命名 snake_case，类名 PascalCase；新增代码需补充必要中文注释或文档。
- Vue 组件文件命名使用 PascalCase，组合式 API 内变量 camelCase；前端需要执行 `npm run lint -- --fix` 进行格式化。
- 文档与注释统一使用中文，新文件保存为 UTF-8 (无 BOM)。
- 变更需记录偏差说明、证据及回滚策略，优先使用 Serena 工具链操作，降级需留痕。
- 禁止引入非主流/非官方 SDK 的自研实现，优先复用标准化生态。