# Design: Execution State Observation Layer

## Context

Wenko 的执行状态机（`ExecutionContract`、`ExecutionStatus`、`_VALID_TRANSITIONS`）已完整实现，
能约束执行合法性并记录迁移历史。但当前系统缺少统一的观测层：

- `ExecutionContract.transitions` 列表仅在 Python 运行时可访问
- `execution_trace`（`GraphState.execution_trace`）仅在单次图执行生命周期内有效，无持久化 API
- GraphRunner 的 SSE 事件（`status`、`text`、`ecs`、`tool_result`）面向功能交互，而非状态机观测
- 挂起/恢复路径需要阅读 SQLite checkpoint 原始 JSON 才能理解

### Stakeholders

- **开发者**：需要调试复杂执行路径（挂起 → resume → 失败 → 重试）
- **ReasoningNode**：需要读取结构化执行历史来支持多轮决策
- **MemoryNode**：需要选择性记录执行事实用于长期回顾
- **前端 UI**：需要接收实时状态变更事件（未来可视化消费端）

### Constraints

- 观测层是**只读投影**，不修改执行状态
- 不重构现有 Node 执行架构和图拓扑
- 不替代日志系统（日志记录细节，观测记录事实）
- 不将观测层设计为流程控制层
- 继续使用 SQLite，不引入外部存储

### Core Architecture Principle: 观测层是 ReasoningNode 的现实感知层

**Execution Observation Layer 不仅服务于前端或开发者，
它同时是 ReasoningNode 感知"现实执行后果"的主要输入。**

ReasoningNode **不应**通过以下方式推断现实是否已发生：
- tool 返回值原始字符串（`contract.result` 裸读）
- ecs 原始 payload
- 隐式 graph 位置（通过"我在 tools → reasoning 边上"推断执行已完成）

ReasoningNode **应优先**通过观测层提供的结构化视图理解"世界已经变成什么样"：
- `ExecutionSnapshot` — 单个执行的当前后果
- `ExecutionConsequenceView` — 面向推理的执行后果摘要（专用简化视图）
- `is_terminal` / `irreversible` / `has_side_effects` / `is_resumable` 等派生属性

这一原则的直接推论：
1. `_build_tool_result_from_contracts()` 应重构为消费 `ExecutionConsequenceView`，而非直接读 Contract 字段
2. ReasoningNode 对执行后果的感知粒度由 Observer 控制，而非由 Contract 内部结构决定
3. 未来 ReasoningNode 可基于 `has_side_effects: true` 调整回复策略（如更谨慎的表述）

---

## Phasing: v1 / v2 Cut Line

本提案采用分阶段交付策略。v1 聚焦于认知层成立的地基 — 让 ReasoningNode 和系统内部能够正确感知执行现实；v2 扩展为工程与产品能力 — 让外部消费者（前端、CLI、调试工具）能够查询和订阅执行状态。

### v1 — 认知层地基（必须）

| 能力 | 核心价值 | 对应 Requirement |
|------|---------|-----------------|
| Execution Snapshot Projection | 观测层的基础数据模型，所有其他能力依赖它 | Execution Snapshot Projection |
| Execution Consequence View | ReasoningNode 感知现实的主要输入，替代直接读 Contract | Execution Consequence View for ReasoningNode |
| Resume Alignment Check | 防止 resume 导致非法执行路径 | Resume Alignment Check |
| Memory Execution Summary | 执行事实进入长期记忆，支持跨会话回顾 | Memory Execution Summary |

### v1-minimal — 可极简实现，v2 强化

| 能力 | v1 范围 | v2 强化方向 | 对应 Requirement |
|------|--------|-----------|-----------------|
| Execution Timeline Query | 仅 per-execution 迁移历史（从 contract.transitions 投影），不需要跨 contract 聚合 | 完整 session 级时间线 + 跨 contract 排序 + 聚合统计 | Execution Timeline Query |
| State Machine Topology | 内部工具函数（`ExecutionObserver.topology()`），不暴露 HTTP API | HTTP API 端点 + 前端可视化消费 | State Machine Topology Exposure |

### v2 — 工程与产品能力

| 能力 | 前置依赖 | 对应 Requirement |
|------|---------|-----------------|
| Execution State SSE Event | v1 Snapshot 数据模型 | Execution State SSE Event |
| Observation HTTP API Endpoints | v1 Snapshot + v1-minimal Timeline + v1-minimal Topology | Observation API Endpoints |

### 分阶段交付的关键约束

1. **v1 必须独立可交付**：v1 完成后，ReasoningNode 即可通过 ConsequenceView 感知执行现实，无需等待 v2
2. **v2 不修改 v1 的数据模型**：v2 仅新增 API 暴露和事件推送，不改变 v1 定义的观测数据结构
3. **v1 的 Observer 接口必须为 v2 预留扩展点**：`timeline()` 和 `topology()` 方法在 v1 中实现为内部函数，v2 仅需添加 HTTP 包装层

---

## Goals / Non-Goals

### Goals

**v1 Goals（认知层）：**
1. 定义执行观测数据模型（`ExecutionSnapshot`、`ExecutionConsequenceView`），作为 `ExecutionContract` 到外部视图的结构化投影
2. 提供单个 Contract 的执行快照（当前状态 + 约束元数据）
3. 为 ReasoningNode 提供专用的执行后果简化视图，替代直接读取 Contract 字段
4. 在 GraphRunner 中增加 resume 对齐检查（graph 位置 vs contract 状态）
5. MemoryNode 记录执行摘要到长期记忆

**v1-minimal Goals（极简，v2 强化）：**
6. 提供 per-execution 迁移历史查询（内部函数级）
7. 暴露状态机拓扑（内部函数级，用于调试断言）

**v2 Goals（工程与产品）：**
8. 通过 SSE 实时推送 `execution_state` 事件
9. 提供 HTTP API 端点暴露观测数据（timeline、snapshot、topology）

### Non-Goals

- 不设计产品 UI 视觉方案（数据结构 + API 优先）
- 不设计执行回放/重放引擎（仅提供数据，消费方自行回放）
- 不将观测层与任务建模耦合
- 不暴露 prompt 内容或推理内部过程

---

## Decisions

### Decision 1: 观测数据模型与 ExecutionContract 解耦

**选择：** 定义独立的观测数据模型（`ExecutionSnapshot`、`TransitionRecord`、`ExecutionTimeline`），
由 `ExecutionObserver` 从 `ExecutionContract` 投影生成，而非在 Contract 上添加观测字段。

**理由：**
- Contract 是执行层概念，观测是展示层概念
- 观测模型可以包含衍生字段（如 `is_stable`、`is_resumable`、`has_side_effects`）而不污染 Contract
- 观测模型的变更不影响执行逻辑

**备选方案：**
- A) 在 ExecutionContract 上增加 `@property` 观测字段 → 耦合过紧，Contract 职责膨胀
- B) 直接暴露 Contract 原始结构 → 泄露内部实现，消费方需理解状态机规则

### Decision 2: 观测层通过 API 暴露，不嵌入图拓扑 `[v2]`

**选择：** 新增独立的 FastAPI 端点，而非将观测逻辑嵌入 Node 或 GraphRunner 主流程。

**理由：**
- 观测是按需查询，不应影响正常执行路径的性能
- API 端点易于被前端、CLI、测试工具等多种消费方调用
- 与现有 SSE 事件流互补（SSE 推送实时变更，API 支持按需查询）

**v1 注：** v1 中 `ExecutionObserver` 的方法作为内部 Python 函数直接调用（ReasoningNode、GraphRunner 使用），不通过 HTTP 暴露。v2 仅需添加 FastAPI 路由包装。

### Decision 3: 状态机拓扑作为静态结构暴露 `[v1-minimal 内部 / v2 API]`

**选择：** `StateMachineTopology` 从 `_VALID_TRANSITIONS` 和 `TERMINAL_STATUSES` 投影生成，
作为常量在服务启动时计算一次。

**理由：**
- 状态机规则是编译时常量，运行时不变
- 调试和架构验证需要完整的合法/禁止迁移矩阵
- v1 中作为内部工具函数用于测试断言；v2 中暴露为 HTTP 端点

### Decision 4: SSE 事件 `execution_state` 仅在状态迁移时推送 `[v2]`

**选择：** 在 `ExecutionContract.transition()` 调用链路的下游（ToolNode、ECSNode、GraphRunner）
手动 yield SSE 事件，而非在 Contract 内部嵌入事件发射。

**理由：**
- Contract 是纯数据模型（Pydantic BaseModel），不应持有 IO 能力
- SSE 事件发射由 GraphRunner 统一管理（与现有 `text`、`emotion`、`ecs` 事件一致）
- 避免引入事件总线增加架构复杂度

**v1 注：** v1 不实现 SSE 事件。ReasoningNode 通过同步调用 `observer.consequence_views()` 获取执行后果，无需实时推送。

### Decision 5: MemoryNode 记录执行摘要，而非完整迁移历史

**选择：** MemoryNode 仅在 contract 到达终止态时记录摘要（执行类型、结果、是否不可逆、耗时），
不记录完整的 `transitions` 列表。

**理由：**
- 长期记忆关注"发生了什么"，而非"怎么发生的"
- 迁移历史通过 `execution_trace` 和 API 可按需查询
- 避免 Memory DB 存储膨胀

### Decision 6: ReasoningNode 通过专用简化视图感知执行后果

**选择：** 为 ReasoningNode 定义 `ExecutionConsequenceView`，作为 `ExecutionSnapshot` 的子集投影。
ReasoningNode 的 `_build_tool_result_from_contracts()` 重构为消费此视图，而非直接读取 Contract 字段。

**理由：**
- ReasoningNode 需要的是"执行后果"（成功/失败 + 是否不可逆 + 是否曾挂起），而非完整的观测快照
- 直接读 `contract.status` / `contract.result` 让 ReasoningNode 耦合 Contract 内部结构
- 专用视图可以控制 LLM 可见的信息边界（不暴露 `idempotency_key`、`timeout_seconds` 等系统细节）
- 简化视图更适合注入 prompt（字段少、语义明确、便于 LLM 理解）

**当前代码分析：**
`reasoning.py:294-316` 的 `_build_tool_result_from_contracts()` 直接读取：
- `contract.action_type` — 过滤 tool_call
- `contract.status` — 判断 COMPLETED/FAILED/REJECTED
- `contract.action_detail.get("method")` — 提取方法名
- `contract.result` / `contract.error_message` — 提取结果

这些字段全部可以由 `ExecutionConsequenceView` 提供，并附加派生语义：
- `was_suspended: bool` — 这个 contract 是否经历过 WAITING（即人类参与过确认）
- `has_side_effects: bool` — 是否产生了不可逆后果
- `consequence_label: str` — 面向 LLM 的后果标签（如 "SUCCESS"、"FAILED"、"REJECTED"、"CANCELLED"）

**备选方案：**
- A) ReasoningNode 直接调用 `observer.snapshot()` 获取完整 `ExecutionSnapshot` → 信息过多，LLM prompt 注入无用字段
- B) 保持现状直接读 Contract 字段 → 违反"观测层是现实感知层"原则

---

## Data Model Design

### 1. ExecutionSnapshot — 单个 Contract 的观测快照

```python
class ExecutionSnapshot(BaseModel):
    """只读观测视图：单个 ExecutionContract 的当前状态快照"""

    # Identity
    execution_id: str
    action_type: str  # "tool_call" | "ecs_request"
    action_summary: str  # 人类可读的 action 摘要（如 "email.send → bob@example.com"）

    # Current State
    current_status: str  # ExecutionStatus value
    entered_at: float  # 进入当前状态的时间戳
    duration_in_state_ms: float  # 在当前状态已停留的毫秒数

    # Derived Properties
    is_terminal: bool  # 是否在终止态
    is_stable: bool  # 是否在稳定态（WAITING 或终止态）
    is_resumable: bool  # 当前状态是否允许 resume（仅 WAITING）
    has_side_effects: bool  # 是否标记 irreversible

    # Constraints
    irreversible: bool
    idempotency_key: Optional[str]
    timeout_seconds: Optional[int]

    # Result (only if terminal)
    result: Optional[str]
    error_message: Optional[str]

    # Transition Count
    transition_count: int
    last_actor: Optional[str]  # 最近一次迁移的 actor
    last_trigger: Optional[str]  # 最近一次迁移的 trigger
```

### 2. TransitionRecord — 单次状态迁移记录

```python
class TransitionRecord(BaseModel):
    """观测视图：一次状态迁移的结构化记录"""

    execution_id: str
    sequence_number: int  # 迁移序号（从 0 开始）
    from_status: str
    to_status: str
    trigger: str  # "start" | "succeed" | "fail" | "suspend" | "resume" | ...
    actor: str  # "tool_node" | "ecs_node" | "graph_runner" | "reasoning"
    actor_category: str  # "agent" | "tool" | "human" | "system"
    timestamp: float
    is_terminal_transition: bool  # to_status 是否为终止态
```

### 3. ExecutionTimeline — 单个 Session 的执行时间线

```python
class ExecutionTimeline(BaseModel):
    """观测视图：单个 session 内所有 contract 的有序执行事件"""

    session_id: str
    contracts: List[ExecutionSnapshot]  # 按 created_at 排序
    transitions: List[TransitionRecord]  # 按 timestamp 排序
    total_contracts: int
    terminal_contracts: int
    active_contracts: int  # PENDING + RUNNING + WAITING
    has_suspended: bool  # 当前是否有 WAITING 状态的 contract
    has_irreversible_completed: bool  # 是否有已完成的不可逆操作

    # Timeline bounds
    started_at: Optional[float]  # 最早 contract 的 created_at
    ended_at: Optional[float]  # 最晚终止态的 entered_at（仅当所有 contract 终止时有值）
```

### 4. StateMachineTopology — 状态机拓扑结构

```python
class StateNode(BaseModel):
    """状态节点描述"""
    status: str
    is_terminal: bool
    is_initial: bool  # 是否为初始状态（PENDING）
    is_stable: bool  # WAITING 或终止态
    is_resumable: bool  # 是否可通过 resume 触发离开

class StateTransitionEdge(BaseModel):
    """合法迁移边"""
    from_status: str
    to_status: str
    trigger: str
    allowed_actors: List[str]  # 哪些 actor 被允许触发此迁移

class StateMachineTopology(BaseModel):
    """执行状态机的完整拓扑，用于调试与架构验证"""

    nodes: List[StateNode]
    edges: List[StateTransitionEdge]  # 合法迁移
    forbidden_transitions: List[Dict[str, str]]  # 禁止的迁移（from → to + reason）
    terminal_statuses: List[str]
    resumable_statuses: List[str]  # 可被 resume 的状态集合
    initial_status: str
```

### 5. ExecutionConsequenceView — ReasoningNode 专用的执行后果视图

```python
class ExecutionConsequenceView(BaseModel):
    """
    面向 ReasoningNode 的执行后果简化视图。

    设计目标：
    1. 仅包含 ReasoningNode 决策所需的字段，排除系统内部细节
    2. 所有字段语义明确，可直接注入 LLM prompt
    3. 提供派生属性帮助 LLM 理解"世界状态"而非"系统状态"
    """

    # Identity（精简版）
    execution_id: str
    action_type: str  # "tool_call" | "ecs_request"
    action_summary: str  # "email.send → bob@example.com"

    # Consequence（后果判定）
    consequence_label: str  # "SUCCESS" | "FAILED" | "REJECTED" | "CANCELLED" | "WAITING"
    result: Optional[str]  # 成功时的结果内容
    error_message: Optional[str]  # 失败时的错误描述

    # Reality Awareness（现实感知）
    has_side_effects: bool  # 此操作是否已在现实中产生不可逆后果
    was_suspended: bool  # 此操作是否经历过人类确认（WAITING → resume）
    is_still_pending: bool  # 此操作是否仍未完成（非终止态）

    # Duration
    total_duration_ms: Optional[float]  # 从创建到终止的总耗时
```

**consequence_label 映射规则：**

```python
def _compute_consequence_label(contract: ExecutionContract) -> str:
    STATUS_TO_CONSEQUENCE = {
        ExecutionStatus.COMPLETED: "SUCCESS",
        ExecutionStatus.FAILED: "FAILED",
        ExecutionStatus.REJECTED: "REJECTED",
        ExecutionStatus.CANCELLED: "CANCELLED",
        ExecutionStatus.WAITING: "WAITING",
        ExecutionStatus.RUNNING: "IN_PROGRESS",
        ExecutionStatus.PENDING: "NOT_STARTED",
    }
    return STATUS_TO_CONSEQUENCE[contract.status]
```

**was_suspended 计算规则：**

```python
def _was_suspended(contract: ExecutionContract) -> bool:
    """检查 contract 是否曾经进入过 WAITING 状态"""
    return any(t["to"] == "waiting" for t in contract.transitions)
```

**与 _build_tool_result_from_contracts() 的重构关系：**

```python
# 重构前 (reasoning.py:294-316)：直接读 contract 字段
def _build_tool_result_from_contracts(self, state: GraphState) -> str:
    for contract in state.completed_executions:
        if contract.status == ExecutionStatus.COMPLETED:
            results.append(f"[SUCCESS] Tool {method} output: {contract.result}")

# 重构后：通过 Observer 获取 ConsequenceView
def _build_tool_result_from_consequences(self, consequences: List[ExecutionConsequenceView]) -> str:
    for cv in consequences:
        if cv.action_type != "tool_call":
            continue
        label = cv.consequence_label
        side_effect_warning = " ⚠️ IRREVERSIBLE" if cv.has_side_effects else ""
        suspended_note = " (human-confirmed)" if cv.was_suspended else ""
        if label == "SUCCESS":
            results.append(f"[{label}{side_effect_warning}{suspended_note}] {cv.action_summary}: {cv.result}")
        elif label in ("FAILED", "REJECTED", "CANCELLED"):
            results.append(f"[{label}] {cv.action_summary}: {cv.error_message}")
```

**关键差异：**
- ReasoningNode 不再直接 import `ExecutionStatus` 或 `ExecutionContract`
- `has_side_effects` 让 LLM 知道"邮件已经发出去了，无法撤回"
- `was_suspended` 让 LLM 知道"用户已经确认过这个操作"
- `consequence_label` 用人类可读的大写标签替代枚举值比较

### 6. actor_category 映射规则

```python
ACTOR_CATEGORY_MAP = {
    "tool_node": "tool",
    "ecs_node": "system",
    "graph_runner": "system",
    "reasoning": "agent",
    "human": "human",
}
```

当 actor 不在映射表中时，默认 category 为 `"system"`。

---

## ExecutionObserver Service

```python
class ExecutionObserver:
    """
    只读服务：从 ExecutionContract 和 execution_trace 投影观测视图。
    不持有状态，不修改 Contract。
    """

    def snapshot(self, contract: ExecutionContract) -> ExecutionSnapshot:
        """投影单个 contract 为观测快照"""

    def consequence_view(self, contract: ExecutionContract) -> ExecutionConsequenceView:
        """投影单个 contract 为 ReasoningNode 专用的执行后果视图"""

    def consequence_views(self, contracts: List[ExecutionContract]) -> List[ExecutionConsequenceView]:
        """批量投影多个 contract 为执行后果视图（ReasoningNode 消费入口）"""

    def timeline(self, contracts: List[ExecutionContract],
                 trace: List[ExecutionStep]) -> ExecutionTimeline:
        """投影一组 contract 和 trace 为执行时间线"""

    @staticmethod
    def topology() -> StateMachineTopology:
        """返回状态机拓扑（静态常量）"""
```

### 数据来源

| 观测数据 | 数据来源 | 读取方式 |
|---------|---------|---------|
| `ExecutionSnapshot` | `ExecutionContract` 实例 | 直接读取字段 + 计算衍生属性 |
| `TransitionRecord` | `ExecutionContract.transitions` | 遍历 transitions 列表并映射 |
| `ExecutionTimeline` | `GraphState.pending_executions` + `completed_executions` + `execution_trace` | 合并并排序 |
| `ExecutionConsequenceView` | `ExecutionContract` 实例 | 读取字段 + 计算 `was_suspended` / `has_side_effects` / `consequence_label` |
| `StateMachineTopology` | `_VALID_TRANSITIONS` + `TERMINAL_STATUSES` | 启动时计算一次 |

### API 端点设计 `[v2]`

v1 中 `ExecutionObserver` 的方法作为内部 Python 函数被 ReasoningNode、GraphRunner、MemoryNode 直接调用。
v2 添加以下 HTTP 包装：

| 端点 | 方法 | 描述 | 数据来源 |
|------|------|------|---------|
| `/api/execution/{session_id}/timeline` | GET | 获取 session 的执行时间线 | 从 checkpoint 或当前 GraphState |
| `/api/execution/{execution_id}/snapshot` | GET | 获取单个 contract 快照 | 从 checkpoint 中查找 |
| `/api/execution/topology` | GET | 获取状态机拓扑 | 静态常量 |

---

## GraphRunner Alignment Strategy

### ReasoningNode 执行后果感知 — 核心集成点

这是观测层最重要的内部消费者。ReasoningNode 通过 `ExecutionConsequenceView` 理解"世界已经变成什么样"。

**集成路径：**

```
ToolNode/ECSNode 执行完成
    ↓ contracts 进入 completed_executions
GraphRunner 推进到 ReasoningNode
    ↓
ReasoningNode.compute() 被调用
    ↓
observer.consequence_views(state.completed_executions)
    ↓ 返回 List[ExecutionConsequenceView]
_build_tool_result_from_consequences(consequences)
    ↓ 生成结构化执行后果文本
注入 LLM prompt 的 【工具执行结果】 部分
```

**ReasoningNode 不再需要 import 的内容：**
- ~~`ExecutionStatus`~~ — 由 `consequence_label` 替代
- ~~`contract.status == ExecutionStatus.COMPLETED`~~ — 由 `cv.consequence_label == "SUCCESS"` 替代

**ReasoningNode 新获得的感知能力：**

| 新能力 | 来源字段 | LLM 决策影响 |
|--------|---------|-------------|
| 知道操作已不可逆 | `has_side_effects` | 回复时使用"已完成"而非"尝试" |
| 知道用户已确认过 | `was_suspended` | 不再重复确认同一操作 |
| 区分"做了没成功"和"被拒绝" | `consequence_label` | FAILED 可重试，REJECTED 不应重试 |
| 知道操作仍在等待 | `is_still_pending` | 提示用户耐心等待而非重新发起 |

**prompt 注入示例：**

```
【工具执行结果】

[SUCCESS ⚠️ IRREVERSIBLE (human-confirmed)] email.send → bob@example.com: 邮件已发送
[FAILED] calendar.create → 会议邀请: SMTP connection refused

请根据以上执行结果继续处理用户的请求。
注意：标记 ⚠️ IRREVERSIBLE 的操作已在现实中生效，无法撤回。
```

### Graph 位置与 Contract 状态的对应关系

| Graph 位置（Node） | 预期 Contract 状态 | 说明 |
|-------------------|-------------------|------|
| ReasoningNode 创建 contract | PENDING | 刚创建，尚未执行 |
| ToolNode 正在执行 | RUNNING | MCP 调用进行中 |
| ToolNode 完成 → 回到 ReasoningNode | COMPLETED / FAILED | 工具执行结束 |
| ECSNode 处理 | WAITING | 等待人类响应 |
| GraphRunner.resume() 开始 | WAITING（验证） | resume 前必须确认 |
| GraphRunner.resume() 完成 | COMPLETED | resume 注入结果 |

### 对齐检查逻辑（在 GraphRunner.resume() 中）

当前 `resume()` 已验证 contract 处于 `WAITING` 状态（`graph_runner.py:296-313`）。
新增以下检查：

1. **Checkpoint 存在性检查**：已实现（`graph_runner.py:287-293`）
2. **Contract 状态一致性检查**：已实现（检查 `WAITING`）
3. **新增 — 幂等性对齐检查**：resume 前检查是否已有相同 idempotency_key 的 COMPLETED contract（防止 resume 后执行已完成的不可逆操作）
4. **新增 — checkpoint 时间戳对齐**：记录 checkpoint 保存时间，resume 时验证 checkpoint 未过期（可选配置）

### 防止 resume 导致非法执行路径

现有机制已覆盖核心场景：
- 终止态 contract 不可 resume（`InvalidTransitionError`）
- checkpoint 不存在时拒绝 resume
- `InvalidTransitionError` 不再被吞没

新增机制：
- 观测层在 resume 前生成 `ExecutionSnapshot`，供日志和前端展示
- 如果 resume 的 contract 数量与 checkpoint 中 WAITING contract 数量不匹配，记录警告

---

## Suspend and Resume Observation

### WAITING / SUSPENDED 状态标识

在 `ExecutionSnapshot` 中：
- `is_stable: True` → 处于稳定态（WAITING 或终止态）
- `is_resumable: True` → 当前状态允许 resume（仅 WAITING）
- `current_status: "waiting"` → 明确标识

### 等待外部输入的展示

`ExecutionTimeline.has_suspended: True` 表示当前有 WAITING 状态的 contract。
每个 WAITING contract 的 `ExecutionSnapshot` 包含：
- `action_summary`：描述等待内容（如 "等待用户确认发送邮件"）
- `duration_in_state_ms`：已等待时长
- `last_trigger: "suspend"`、`last_actor: "ecs_node"` → 标识挂起原因

### resume 触发来源展示

resume 成功后，`TransitionRecord` 中：
- `trigger: "resume"`、`actor: "graph_runner"`、`actor_category: "system"`
- 紧随其后的 `trigger: "succeed"` 表示 resume 注入结果

### 失败后重试路径展示

当 contract FAILED 后用户请求重试：
1. 旧 contract 保持 FAILED 终止态
2. ReasoningNode 创建新 contract（新 `execution_id`，相同 `idempotency_key`）
3. 在 `ExecutionTimeline.transitions` 中，两个 contract 的迁移记录按时间排列
4. 消费方可通过 `idempotency_key` 关联同一 action 的多次尝试

---

## Memory and System Review

### MemoryNode 记录的执行观测信息

当 contract 到达终止态且 MemoryNode 被调用时（通过 `consolidate()`），记录：

```python
execution_memory = {
    "type": "execution_fact",
    "execution_id": contract.execution_id,
    "action_type": contract.action_type,
    "action_summary": observer.snapshot(contract).action_summary,
    "final_status": contract.status.value,
    "irreversible": contract.irreversible,
    "duration_ms": total_duration,  # created_at → 最后一次 transition timestamp
    "result_summary": contract.result[:200] if contract.result else None,
    "error_summary": contract.error_message[:200] if contract.error_message else None,
}
```

### 历史执行回放支持

- `execution_trace` 已持久化在 `graph_checkpoints` 中（作为 GraphState 的一部分序列化）
- `/api/execution/{session_id}/timeline` API 支持历史 session 查询
- 消费方（前端或 CLI）通过 `transitions` 有序列表即可回放状态迁移过程

### 系统级执行健康检查

`/api/execution/topology` 端点可用于验证：
- 状态机拓扑是否完整（所有状态节点可达或为初始/终止态）
- 是否存在死锁路径（某状态既非终止也无合法出口 → 当前设计不可能发生，作为断言验证）

### 对用户隐藏的执行细节

| 隐藏信息 | 原因 |
|---------|------|
| `idempotency_key` 的 MD5 计算细节 | 内部实现，无用户价值 |
| `actor` 标识（如 "tool_node", "graph_runner"） | 系统内部概念 |
| 完整 `action_detail` 字典 | 可能包含内部参数格式 |
| `transitions` 列表中的原始时间戳精度 | 对用户展示时间戳需格式化 |

面向用户展示时，使用 `action_summary`（人类可读）和 `actor_category`（"agent"/"tool"/"human"/"system"）
替代原始字段。

---

## SSE Event Design `[v2]`

### 新增事件类型：`execution_state`

```json
{
  "event": "execution_state",
  "data": {
    "execution_id": "exec-001",
    "action_summary": "email.send → bob@example.com",
    "from_status": "running",
    "to_status": "waiting",
    "trigger": "suspend",
    "actor_category": "system",
    "is_terminal": false,
    "is_resumable": true,
    "has_side_effects": true,
    "timestamp": 1707350400.123
  }
}
```

**发射时机：** 每次 `ExecutionContract.transition()` 被调用后，由调用方（ToolNode/ECSNode/GraphRunner）
在 yield SSE 事件时附带 `execution_state` 事件。

**与现有事件的关系：**
- `execution_state` 是新增的细粒度事件，与 `status`、`tool_result`、`ecs` 并列
- 前端可选择订阅此事件用于状态可视化，不订阅不影响核心功能
- 现有事件格式不变

---

## Worked Example

### 场景：Agent 执行不可逆操作（发送邮件），挂起等待确认，resume 后完成

**注：** 📊 标记观测层输出。`[v2]` 标记的 SSE 事件仅在 v2 中实现。

```
=== 阶段 1：用户输入 → 创建 Contract ===

T=0ms  用户输入: "帮我给 bob@example.com 发一封会议邀请邮件"
T=50ms IntentNode → EmotionNode → MemoryNode（正常流程）
T=200ms ReasoningNode 解析 LLM 输出：
        - 检测到 ecs_request（需人类确认不可逆操作）
        - 创建 Contract:
          exec-001: {type: "ecs_request", status: PENDING, irreversible: false}

        📊 [v1] ExecutionSnapshot @ T=200ms:
        ExecutionSnapshot(
          execution_id="exec-001",
          action_summary="确认发送邮件给 bob@example.com",
          current_status="pending",
          is_terminal=false, is_stable=false, is_resumable=false,
          has_side_effects=false, transition_count=0
        )

=== 阶段 2：ECSNode 挂起 ===

T=210ms ECSNode 处理 exec-001:
        exec-001: PENDING --start--> RUNNING (actor=ecs_node)
        exec-001: RUNNING --suspend--> WAITING (actor=ecs_node)

        📊 [v2] SSE 事件 #1: execution_state
        {execution_id: "exec-001", from: "pending", to: "running",
         trigger: "start", actor_category: "system"}

        📊 [v2] SSE 事件 #2: execution_state
        {execution_id: "exec-001", from: "running", to: "waiting",
         trigger: "suspend", actor_category: "system", is_resumable: true}

T=220ms GraphRunner 检测 status="suspended"
        → 保存 checkpoint（含 exec-001 序列化）
        → 向前端发送 SSE: ecs（确认表单）

        📊 [v1] ExecutionSnapshot @ T=220ms:
        ExecutionSnapshot(
          execution_id="exec-001",
          current_status="waiting",
          is_stable=true, is_resumable=true,
          duration_in_state_ms=10, transition_count=2,
          last_actor="ecs_node", last_trigger="suspend"
        )

=== 阶段 3：用户确认 → Resume ===

T=5000ms 用户在前端点击"确认发送"
         POST /ecs/respond → 存储响应
         POST /ecs/continue → GraphRunner.resume()

T=5010ms GraphRunner.resume():
         → 加载 checkpoint
         → [v1] 对齐检查：exec-001 status=WAITING ✓, WAITING count=1 ✓
         → exec-001: WAITING --resume--> RUNNING (actor=graph_runner)
         → exec-001: RUNNING --succeed--> COMPLETED (actor=graph_runner)

         📊 [v2] SSE 事件 #3: execution_state
         {execution_id: "exec-001", from: "waiting", to: "running",
          trigger: "resume", actor_category: "system"}

         📊 [v2] SSE 事件 #4: execution_state
         {execution_id: "exec-001", from: "running", to: "completed",
          trigger: "succeed", actor_category: "system", is_terminal: true}

=== 阶段 4：ReasoningNode 通过 ConsequenceView 感知确认结果 ===

T=5100ms ReasoningNode.compute() 被调用:
         → [v1] observer.consequence_views(state.completed_executions)
         → 获得 ConsequenceView:
           ExecutionConsequenceView(
             execution_id="exec-001",
             action_summary="确认发送邮件给 bob@example.com",
             consequence_label="SUCCESS",
             has_side_effects=false,  // ECS 确认本身不是不可逆操作
             was_suspended=true,     // 经历过 WAITING
             is_still_pending=false
           )

         → 确认通过，创建邮件发送 Contract:
         exec-002: {type: "tool_call", status: PENDING, irreversible: true,
                    idempotency_key: "email:send:a1b2c3d4"}

=== 阶段 5：ToolNode 执行不可逆操作 ===

T=5110ms ToolNode 处理 exec-002:
         → 幂等键检查：无已完成的 "email:send:a1b2c3d4" ✓
         → exec-002: PENDING --start--> RUNNING (actor=tool_node)

T=5500ms MCP email.send() 调用成功
         exec-002: RUNNING --succeed--> COMPLETED (actor=tool_node)

=== 阶段 6：ReasoningNode 通过 ConsequenceView 感知执行后果 ===

T=5600ms ReasoningNode.compute() 被调用:
         → [v1] observer.consequence_views(state.completed_executions)
         → 获得 ConsequenceView:
           ExecutionConsequenceView(
             execution_id="exec-002",
             action_summary="email.send → bob@example.com",
             consequence_label="SUCCESS",
             has_side_effects=true,   // irreversible=true + COMPLETED
             was_suspended=false,     // 直接执行，未挂起
             is_still_pending=false
           )

         → [v1] _build_tool_result_from_consequences() 生成:
           "[SUCCESS ⚠️ IRREVERSIBLE] email.send → bob@example.com: 邮件已发送"

         → LLM 读取结构化后果，生成回复:
           "已成功发送会议邀请邮件给 bob@example.com"

=== [v1] MemoryNode 执行摘要 ===

[
  {type: "execution_fact", action_summary: "确认发送邮件给 bob@example.com",
   final_status: "completed", irreversible: false, duration_ms: 4810},
  {type: "execution_fact", action_summary: "email.send → bob@example.com",
   final_status: "completed", irreversible: true, duration_ms: 400,
   result_summary: "邮件已发送"},
]

=== [v1-minimal] Per-Execution 迁移历史 ===

exec-001 transitions:
  #0 pending→running  (start, ecs_node)
  #1 running→waiting  (suspend, ecs_node)
  #2 waiting→running  (resume, graph_runner)
  #3 running→completed (succeed, graph_runner)

exec-002 transitions:
  #0 pending→running   (start, tool_node)
  #1 running→completed (succeed, tool_node)

=== [v2] 完整 Session 时间线 ===

ExecutionTimeline(
  session_id="session-abc",
  total_contracts=2,
  terminal_contracts=2,
  active_contracts=0,
  has_suspended=false,
  has_irreversible_completed=true,
  started_at=T+200ms,
  ended_at=T+5500ms,
  contracts=[
    ExecutionSnapshot(exec-001, "ecs_request", status="completed"),
    ExecutionSnapshot(exec-002, "tool_call", status="completed", irreversible=true),
  ],
  transitions=[
    TransitionRecord(exec-001, #0, pending→running, "start", "ecs_node", "system"),
    TransitionRecord(exec-001, #1, running→waiting, "suspend", "ecs_node", "system"),
    TransitionRecord(exec-001, #2, waiting→running, "resume", "graph_runner", "system"),
    TransitionRecord(exec-001, #3, running→completed, "succeed", "graph_runner", "system"),
    TransitionRecord(exec-002, #0, pending→running, "start", "tool_node", "tool"),
    TransitionRecord(exec-002, #1, running→completed, "succeed", "tool_node", "tool"),
  ]
)
```

---

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| 观测 API 查询 checkpoint 增加 SQLite 读压力 | checkpoint 数据量小（< 100KB per session）；可添加简单内存缓存 |
| SSE `execution_state` 事件增加前端处理负担 | 事件为可选订阅；前端不处理则忽略 |
| `ExecutionObserver` 与 `ExecutionContract` 数据结构变更需同步 | Observer 测试覆盖所有 Contract 字段；Contract 变更时 Observer 测试会失败 |
| `action_summary` 生成逻辑需要理解 `action_detail` 内容 | 提供默认摘要格式 `{service}.{method}`，支持自定义 |
| MemoryNode 执行摘要写入可能失败 | 摘要写入为 best-effort，失败不影响主流程 |

---

## Open Questions

1. **观测数据的持久化粒度？**
   - 当前：checkpoint 中已持久化完整 GraphState（含 contracts 和 trace）
   - 是否需要独立的观测数据表？→ 建议暂不引入，优先从 checkpoint 投影

2. **`action_summary` 的国际化？**
   - 当前系统主要面向中文用户
   - 建议 summary 生成逻辑支持模板，但 v1 使用硬编码中文

3. **前端消费 `execution_state` SSE 事件的时机？**
   - 本提案仅定义后端数据结构和事件格式
   - 前端 UI 组件设计不在本提案范围内
