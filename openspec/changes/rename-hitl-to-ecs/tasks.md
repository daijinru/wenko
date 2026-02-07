## 1. 后端核心模块重命名

- [x] 1.1 创建 `workflow/ecs_schema.py`：将 `hitl_schema.py` 的所有内容复制并重命名（28 个类/枚举 + 3 个函数，所有 `HITL` 前缀 → `ECS`）
- [x] 1.2 创建 `workflow/ecs_handler.py`：将 `hitl_handler.py` 的所有内容复制并重命名（20+ 个函数，所有 `hitl` 变量/常量 → `ecs`，包括 `hitl_` 内存前缀 → `ecs_`）
- [x] 1.3 更新 `workflow/core/state.py`：`HITLRequest` → `ECSRequest`，`hitl_request` → `ecs_request`，`hitl_full_request` → `ecs_full_request`
- [x] 1.4 重命名 `workflow/core/nodes/hitl.py` → `workflow/core/nodes/ecs.py`：`HITLNode` → `ECSNode`
- [x] 1.5 更新 `workflow/core/nodes/reasoning.py`：所有 hitl 相关导入和引用
- [x] 1.6 更新 `workflow/core/nodes/image.py`：所有 hitl 相关导入和引用
- [x] 1.7 更新 `workflow/core/graph.py`：导入路径、节点注册名、条件路由
- [x] 1.8 更新 `workflow/graph_runner.py`：所有 hitl 导入、变量名、SSE 事件类型
- [x] 1.9 删除旧文件 `workflow/hitl_schema.py` 和 `workflow/hitl_handler.py` 和 `workflow/core/nodes/hitl.py`

## 2. 后端 API 层和配置

- [x] 2.1 更新 `workflow/main.py`：API 路由 `/hitl/*` → `/ecs/*`，模型类名 `HITL*` → `ECS*`，SSE 事件类型 `hitl` → `ecs`，所有 hitl 变量名
- [x] 2.2 更新 `workflow/chat_db.py`：配置键 `system.hitl_enabled` → `system.ecs_enabled`，添加一次性迁移逻辑
- [x] 2.3 更新 `workflow/core/prompts.py`：模板变量 `{hitl_instruction}` → `{ecs_instruction}`

## 3. Prompt 模板和意图系统

- [x] 3.1 更新 `workflow/chat_processor.py`：所有 `HITL_*` 常量 → `ECS_*`（`HITL_INSTRUCTION`、`HITL_INSTRUCTION_DISABLED`、`HITL_CONTINUATION_INSTRUCTION`、`HITL_BASE_FORMAT`、`HITL_INTENT_SNIPPETS`），`is_hitl_enabled()` → `is_ecs_enabled()`，`hitl_instruction` 变量名，prompt 模板中的 HITL 术语替换为 ECS
- [x] 3.2 更新 `workflow/intent_types.py`：`HITLIntent` → `ECSIntent`，`IntentCategory.HITL` → `IntentCategory.ECS`，`HITL_INTENT_MAP` → `ECS_INTENT_MAP`，`is_hitl` → `is_ecs`
- [x] 3.3 更新 `workflow/intent_rules.py`：`HITL_RULES` → `ECS_RULES`，`get_hitl_rules()` → `get_ecs_rules()`

## 4. Electron 主进程

- [x] 4.1 更新 `electron/main.cjs`：所有 IPC 通道 `hitl:*` → `ecs:*`，变量名 `hitlWindow` → `ecsWindow`、`currentHITLRequest` → `currentECSRequest` 等，函数名 `createHITLWindow` → `createECSWindow` 等，API URL，SSE 事件类型判断，页面加载路径 `'hitl'` → `'ecs'`

## 5. 前端渲染器（HITL → ECS 窗口）

- [x] 5.1 重命名目录 `electron/src/renderer/hitl/` → `electron/src/renderer/ecs/`
- [x] 5.2 重命名类型文件 `types/hitl.ts` → `types/ecs.ts`：所有 `HITL*` 接口/类型 → `ECS*`
- [x] 5.3 更新 `hooks/use-hitl-window.ts` → `hooks/use-ecs-window.ts`：`useHITLWindow` → `useECSWindow`，`HITLWindowState` → `ECSWindowState`
- [x] 5.4 重命名所有组件文件（`hitl-form.tsx` → `ecs-form.tsx`、`hitl-field.tsx` → `ecs-field.tsx` 等）并更新内部命名
- [x] 5.5 更新 `lib/ipc-client.ts`：函数名 `submitHITL` → `submitECS`、`cancelHITL` → `cancelECS`、`onHITLRequestData` → `onECSRequestData`，IPC 通道名
- [x] 5.6 更新 `App.tsx`：所有组件导入和引用
- [x] 5.7 更新 `index.html`：标题 `HITL` → `ECS`
- [x] 5.8 更新 `electron/vite.config.js`：路径别名 `@hitl` → `@ecs`，构建入口
- [x] 5.9 更新 `electron/tsconfig.json`：路径映射和 include

## 6. Workflow 渲染器中的 ECS 引用

- [x] 6.1 更新 `system-config-section.tsx`：设置键 `system.hitl_enabled` → `system.ecs_enabled`，标签文本
- [x] 6.2 更新 `use-settings.ts`：类型字段名
- [x] 6.3 更新 `context-variable-dialog.tsx`：所有 HITL 类型导入路径（`@hitl/` → `@ecs/`）、`HITLContextValue` → `ECSContextValue`、`isHITLContextValue` → `isECSContextValue`、`hitl_` 前缀检测 → `ecs_` 前缀、IPC 通道名

## 7. Live2D Widget

- [x] 7.1 更新 `electron/live2d/live2d-widget/src/chat.ts`：API URL 常量、调试日志函数、所有 50+ 处 HITL 接口/类型/变量/函数名、CSS 类名、HTML data 属性、IPC 通道名、SSE 事件类型

## 8. 文档更新

- [x] 8.1 更新 `README.md`：HITL 相关描述替换为 ECS
- [x] 8.2 更新 `README_CN.md`：HITL 相关描述替换为 ECS
- [x] 8.3 更新 `work_state_summary.md`：HITL 引用替换为 ECS

## 9. 验证

- [x] 9.1 全局搜索验证：`rg -i "hitl" --type py --type ts --type js` 排除 openspec/changes/ 和构建产物后，结果为空
- [x] 9.6 清理旧文件的 `__pycache__` 缓存
- [x] 9.2 Python 后端编译检查：`python -c "import main"` 无报错
- [x] 9.3 Electron 前端构建：`npm run build` 无报错
- [ ] 9.4 Live2D Widget 构建：构建无报错
- [ ] 9.5 运行时验证：启动后端服务，确认 `/ecs/respond` 端点可访问
