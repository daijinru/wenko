# Change: Add Execution State Machine for Action / Agent Lifecycle

## Why

Wenko 的 ToolNode 和 ECSNode 缺少结构化的执行状态管理。当前 ToolNode 通过字符串前缀（`"output:"`/`"failed:"`）区分成功与失败，ReasoningNode 被迫解析自然语言来"猜测"执行结果。随着引入 agent 自动执行、不可逆操作和挂起等待，需要一套独立的执行状态机来描述和约束现实世界中的执行过程。

## What Changes

- **新增** `ExecutionStatus` 枚举和 `ExecutionContract` 数据模型（`core/state.py`）
- **新增** `execution-state-machine` 能力规范，定义执行合约、状态迁移、挂起/恢复的行为要求
- **修改** `ToolNode` 和 `ECSNode`，从产出字符串 observation 改为推进 Contract 状态
- **修改** `ReasoningNode`，从解析自然语言 observation 改为读取结构化 Contract 状态
- **修改** `GraphState`，新增 `pending_executions` / `completed_executions` 字段
- **激活** 已有的 `execution_trace` 基础设施，记录 Contract 状态迁移历史
- **修改** `GraphRunner`，在 checkpoint 中序列化/反序列化 Contract 状态

## Impact
- Affected specs: `cognitive-graph`（修改 ToolNode/ECSNode/ReasoningNode 行为）
- Affected code:
  - `workflow/core/state.py` — 新增模型定义
  - `workflow/core/nodes/tool_node.py` — Contract 状态推进
  - `workflow/core/nodes/ecs.py` — Contract 状态推进
  - `workflow/core/nodes/reasoning.py` — Contract 读取逻辑
  - `workflow/core/graph.py` — 路由条件适配
  - `workflow/graph_runner.py` — Checkpoint 序列化、resume 校验
