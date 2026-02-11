# implement-execution-ui

## Summary

在 Electron 前端实现人类可见的执行感知 UI，消费后端已完成的翻译层（`?human=true` API 和 `execution_state` SSE 事件），让用户能够实时感知系统执行状态。

## Motivation

后端翻译层（`ExecutionUITranslator`、`STATUS_TO_HUMAN_LABEL`、`_humanize_action_summary`、`_humanize_consequence`、`?human=true` API 端点、SSE 人类化方法）已全部实现并测试通过。然而 Electron 前端**零消费**这些数据——没有组件调用 `/api/execution/` 端点，没有代码处理 `execution_state` SSE 事件。

用户目前无法感知系统正在执行什么、已完成什么、是否需要关注，这与 `execution-ui-philosophy` 规范中定义的四个认知问题相矛盾。

## Scope

### In scope

1. **执行舞台（Execution Stage）**：Live2D 对话界面实时展示当前执行状态（优先级：高）
2. **执行历史（Execution History）**：Workflow 管理面板中新增执行历史 Tab（优先级：中）
3. **行动解释（Action Explanation）**：作为执行历史条目的展开详情（优先级：中）
4. **后端 SSE 人类化自动发射**：让后端在 SSE 发射时自动附带人类化数据，前端直接消费（方案 B）

### Out of scope

- 执行结构视图（Execution Structure）——后续迭代
- 记忆影响视图（Memory Impact）——后续迭代
- topology API 的人类化

## Impact

- **新增文件**：约 8-10 个前端文件（组件、hooks、类型定义）
- **修改文件**：`electron/live2d/live2d-widget/src/chat.ts`（SSE 事件处理）、`electron/src/renderer/workflow/App.tsx`（新增 Tab）、`workflow/graph_runner.py`（SSE 自动人类化）
- **不影响**：现有对话功能、记忆管理、MCP 服务、日志查看、设置

## Dependencies

- `define-execution-ui-philosophy`（已完成）——哲学规范和后端翻译层
- `add-execution-observation-layer`（进行中）——Observer 数据源
- `add-execution-state-machine`（已完成）——ExecutionContract 状态机

## Risks

1. Live2D 组件使用 Shadow DOM 和 ESM CDN import，与 React 技术栈分离，需要通过 CustomEvent 或 IPC 桥接执行状态
2. SSE `execution_state` 事件频率可能较高，需要防抖/合并策略避免 UI 闪烁
3. 前端无状态管理库（无 Redux/Zustand），需要设计轻量的执行状态共享方案
