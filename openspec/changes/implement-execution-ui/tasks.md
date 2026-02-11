## 1. 后端 SSE 人类化自动附带

在后端发射 `execution_state` SSE 事件时自动附带 `human` 字段。

- [x] 1.1 在 `workflow/graph_runner.py` 中，`_build_execution_state_event()` 返回的 payload 中自动调用 `_humanize_execution_state_event()` 并将结果作为 `human` 字段附带
- [x] 1.2 确认原始 payload 字段不变（`execution_id`, `action_summary`, `from_status`, `to_status`, `is_terminal` 等保持原值）——新增测试 `test_build_event_original_fields_unchanged` 验证
- [x] 1.3 在 `workflow/tests/test_execution_observation.py` 中新增 `TestSSEAutoHumanization` 测试类（3 个测试），验证 SSE 事件 payload 同时包含原始字段和 `human` 字段——98 passed

## 2. 前端类型定义

定义执行相关的 TypeScript 类型。

- [x] 2.1 新建 `electron/src/renderer/workflow/types/execution.ts`，定义了 `HumanExecutionState`、`ExecutionStateEvent`、`ExecutionTimelineItem`、`ExecutionTimeline`、`ExecutionSnapshot` 类型
- [x] 2.2 类型直接定义在 `types/execution.ts` 中，无需修改 `api.ts`（执行类型独立于通用 API 类型）

## 3. Electron IPC 桥接

建立 Live2D → Main Process → React Workflow 的执行状态传递通道。

- [x] 3.1 审查 `electron/preload.cjs`——`send` 和 `on` 方法不使用 channel 白名单，无需修改
- [x] 3.2 在 `electron/main.cjs` 中新增 `ipcMain.on('execution-state-update')` 监听，转发到 `workflowWindow.webContents.send()`；升级 workflow 窗口为模块级 `workflowWindow` 变量（含 singleton 管理和 `closed` 清理）
- [x] 3.3 IPC 转发链完整：chat.ts `window.electronAPI.send()` → main.cjs `ipcMain.on()` → `workflowWindow.webContents.send()` → use-execution.ts `window.electronAPI.on()`

## 4. Live2D SSE 事件处理

在 Live2D Widget 的 chat.ts 中新增 `execution_state` SSE 事件处理。

- [x] 4.1 在 `chat.ts` 的 `onmessage` 处理器中新增 `execution_state` 事件分支，解析 `data.human`
- [x] 4.2 通过 `window.electronAPI.send('execution-state-update', data.human)` 转发人类化数据到 Main Process
- [x] 4.3 新建 `electron/live2d/live2d-widget/src/execution-stage.ts`——执行舞台 overlay 渲染模块，支持状态色点（蓝/绿/橙/红）、非终态持续显示、终态 3 秒自动淡出、"需要关注"醒目背景
- [x] 4.4 chat.ts 的 `execution_state` 分支调用 `updateExecutionStage(data.human)` 更新 overlay
- [x] 4.5 审查确认——所有用户可见文本不包含工程词汇，仅使用中文状态标签和行动描述

## 5. React 执行状态 Hook

创建执行状态数据管理 hook。

- [x] 5.1 新建 `electron/src/renderer/workflow/hooks/use-execution.ts`——IPC 监听 `execution-state-update`、`fetchTimeline(sessionId)` 调用 `?human=true` API、维护 `timelineItems[]`/`loading`/`error`/`currentAction`/`realtimeEvents[]` 状态
- [x] 5.2 `useEffect` 返回 `unsubscribe()` 清理函数，组件卸载时移除 IPC listener

## 6. 执行历史 Tab 组件

在 React Workflow Panel 中新增执行历史 Tab。

- [x] 6.1 新建 `electron/src/renderer/workflow/components/features/execution/` 目录 + `index.ts` barrel export
- [x] 6.2 新建 `execution-tab.tsx`——主组件含会话选择器、实时状态条、时间线列表、空状态展示
- [x] 6.3 新建 `execution-timeline.tsx`——时间线列表组件，每条显示行动名称 + 状态 Badge + 不可逆 Badge + 展开详情
- [x] 6.4 新建 `execution-detail.tsx`——行动解释展开卡片，显示结果/错误/不可逆说明
- [x] 6.5 在 `App.tsx` 中新增 `TabsTrigger value="execution"` + `TabsContent`，导入 `ExecutionTab`
- [x] 6.6 风格一致——使用 Button、Badge（blue/green/orange/destructive/secondary variants）、Tailwind CSS 类名，与 logs-tab 等现有 Tab 对齐

## 7. 集成与边界验证

端到端验证，确保符合 `execution-ui-philosophy` 边界规则。

- [x] 7.1 验证唯一来源规则——执行数据仅来自 `?human=true` API（`use-execution.ts:55`）和 IPC `human` 字段（`use-execution.ts:39`），不从 LLM 回复中提取
- [x] 7.2 验证已验证事实规则——pending 状态显示为"准备中"（`execution-tab.tsx:27`、`execution-stage.ts:69`），不暗示行动已开始
- [x] 7.3 验证叙事优先规则——所有用户可见文本为叙事形式（"正在发送邮件……"、"发送邮件——已完成"），无状态机术语
- [x] 7.4 验证 Observer 不可见规则——用户感知为"系统正在做事"，无监控面板词汇
- [x] 7.5 `openspec validate implement-execution-ui --strict` — 通过
- [x] 7.6 `npx vite build` — 构建成功（2.12s），98 tests passed
