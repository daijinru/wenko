# Change: Add Cognitive Object Layer (COL)

## Why

Wenko 当前的认知架构以 Execution 为中心：

```
Perception → Execution → Observer → ECS
```

所有"事情"（如：用户要做的项目、正在跟踪的目标、等待外部反馈的任务）没有独立的实体化存在。它们依附于 Execution（ExecutionContract），一旦执行结束，"事情"的逻辑就消散了。这意味着：

- 用户无法在没有活跃执行的情况下查看"正在进行的事情"
- 一个跨越多次对话的长期目标无法被建模为一个持续存在的实体
- Execution 结束后，"事情"的状态（如"等待对方回复"）无处安放
- 系统无法回答"我现在手头有哪些事情？"这类本质性问题

这不符合"外部大脑"的目标。外部大脑应该能：
1. **持有事情** — 即使没有任何执行在进行
2. **跟踪事情** — 跨越多次执行、多次对话
3. **等待外部世界** — 事情可以处于"等待"状态，不需要 Execution 来驱动

本提案引入 **Cognitive Object Layer (COL)**，将 Execution 降级为 CO 的执行子系统，将 Wenko 从 Execution-driven system 升级为 Object-driven cognitive system。

## What Changes

### 架构层级变更

新增 **Cognitive Object Layer** 作为 Wenko Cognitive Stack 的核心层，Execution 降级为 COL 的执行子系统：

| 层级 | 名称 | 职责 |
|------|------|------|
| L4 | **ECS Projection Layer** | CO 的人类交互投影，可丢弃视图 |
| **L3** | **Cognitive Object Layer (NEW)** | **系统认知中心：CO 生命周期管理** |
| | ↳ Execution Subsystem | CO 的执行子系统：ExecutionContract 状态机、Observer、ToolNode / ECSNode |
| L2 | Memory Layer | 事实记录（Working Memory + Long-term Memory） |
| L1 | Perception Layer | 输入规范化、情绪检测、意图识别 |

### 核心实体

- **新增** `CognitiveObject` 数据模型 — 事情的实体化表示，拥有稳定 ID、语义边界、状态机、生命周期
- **新增** `CognitiveObjectStatus` 枚举 — CO 的六状态生命周期（emerging → active → waiting → blocked → stable → archived）
- **新增** `CORegistry` 服务 — CO 的 CRUD、查询、状态迁移管理
- **新增** CO 持久化 — SQLite 表 `cognitive_objects` 和 `co_execution_links`

### 关系模型变更

- **降级** Execution Layer 为 COL 的执行子系统 — Execution 不再是独立层，而是 CO 调度执行的内部机制
- **新增** CO ↔ Execution 的归属关系 — ExecutionContract 始终为 CO 服务
- **修改** ExecutionContract — 新增可选 `cognitive_object_id` 字段，建立 Execution → CO 的归属关系
- **修改** ReasoningNode — 在推理时可引用关联的 CO 上下文
- **修改** MemoryNode — 执行摘要可关联到 CO

### 边界声明

- CO 是 **事情实体**，不是 Memory（事实记录）
- CO 是 **独立于 Execution** 的 — CO 可以在没有任何 Execution 的情况下存在
- Execution 是 **CO 的执行子系统** — 不是并列的独立层，而是 CO 调度执行的内部机制
- ECS 是 **CO 的投影接口**，不是 Execution 的进展弹窗
- CO 不是 Execution 日志的封装

### **BREAKING** 变更

- **Execution Layer 降级**：从独立的系统层级降级为 COL 的执行子系统
- ECS 的语义从"Execution 的人类交互接口"变为"CO 的投影接口"
- GraphState 新增 `active_cognitive_objects` 字段

## Impact

- Affected specs: `cognitive-object-layer`（新增能力）
- 间接影响: `execution-state-machine`（ExecutionContract 新增可选字段）, `execution-observation`（Observer 可投影 CO 关联信息）
- Affected code:
  - `workflow/core/state.py` — 新增 CO 数据模型
  - `workflow/cognitive_object.py` — 新增 CORegistry 服务（NEW）
  - `workflow/core/nodes/reasoning.py` — CO 上下文注入
  - `workflow/core/nodes/memory.py` — CO 关联记忆
  - `workflow/chat_db.py` — 新增 CO 持久化表
  - `workflow/main.py` — 新增 CO API 端点
  - `workflow/graph_runner.py` — CO 生命周期事件发射
