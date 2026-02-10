# Change: Add Execution State Observation Layer

## Why

Wenko 已实现 ExecutionContract 执行状态机，但执行状态数据仅存在于内部 Python 对象和日志中。人类开发者与 ReasoningNode 缺乏统一的执行事实观测视角：挂起、恢复、失败路径难以被直观理解，调试复杂执行路径成本较高。需要一套只读观测层，将执行状态机暴露为结构化、可查询的观测数据。

## Phasing

### v1 — 认知层地基（必须）
- Execution Snapshot Projection — 观测层基础数据模型
- Execution Consequence View — ReasoningNode 感知现实执行后果的主要输入
- Resume Alignment Check — 防止 resume 导致非法执行路径
- Memory Execution Summary — 执行事实进入长期记忆

### v1-minimal — 极简实现，v2 强化
- Execution Timeline Query — v1 仅 per-execution 迁移历史（内部函数），v2 扩展为 session 级聚合 + HTTP API
- State Machine Topology — v1 内部工具函数用于测试断言，v2 暴露为 HTTP API

### v2 — 工程与产品能力
- Execution State SSE Event — 实时推送状态迁移事件到前端
- Observation HTTP API Endpoints — 外部消费者查询观测数据

## What Changes

**v1：**
- **新增 execution-observation 能力**：定义执行观测数据模型（`ExecutionSnapshot`、`ExecutionConsequenceView`、`TransitionRecord`）
- 新增 `ExecutionConsequenceView`：面向 ReasoningNode 的执行后果简化视图，作为 ReasoningNode 感知现实执行后果的主要输入
- 重构 `ReasoningNode._build_tool_result_from_contracts()` → `_build_tool_result_from_consequences()`，消费 ConsequenceView 而非直接读 Contract 字段
- 新增 `ExecutionObserver` 服务层（核心方法）：`snapshot()`、`consequence_view()`、`consequence_views()`
- 新增 GraphRunner 对齐检查：在 resume 前生成 ExecutionSnapshot + WAITING 数量验证
- 新增 MemoryNode 执行摘要记录：将终止态 contract 的结构化摘要写入 Memory

**v1-minimal：**
- 新增 per-execution `transition_records()` 方法
- 新增 `topology()` 静态方法（内部使用）
- 定义 `ExecutionTimeline`、`StateMachineTopology` 数据模型（为 v2 预留）

**v2：**
- 新增执行观测 HTTP API 端点：`/api/execution/{session_id}/timeline`、`/{execution_id}/snapshot`、`/topology`
- 新增 SSE 事件 `execution_state`：实时推送状态迁移事件到前端
- 完整 session 级时间线聚合

## Impact

- Affected specs: `execution-state-machine`（已有，不修改）, `execution-observation`（新增）
- Affected code:
  - `workflow/core/state.py` — 新增观测数据模型（含 ExecutionConsequenceView）
  - `workflow/observation.py` — 新增 `ExecutionObserver` 服务
  - `workflow/core/nodes/reasoning.py` — [v1] 重构执行后果感知路径，消费 ConsequenceView
  - `workflow/graph_runner.py` — [v1] 对齐检查，[v2] SSE 事件发射
  - `workflow/core/nodes/memory.py` — [v1] 新增执行摘要记录
  - `workflow/main.py` — [v2] 新增 API 端点
