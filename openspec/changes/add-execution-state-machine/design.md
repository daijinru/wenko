# Design: Action / Agent Execution State Machine

## Context

Wenko 的认知图谱采用以推理为中心的 Node 执行流程：

```
IntentNode → EmotionNode → MemoryNode → ReasoningNode →（ToolNode / ECSNode / END）
                                                   ↘ ReasoningNode（循环）
```

当前系统在处理工具调用和 ECS 交互时，依赖以下简化机制：

1. **ToolNode** (`tool_node.py:42-49`) 通过字符串前缀（`"output:"`/`"failed:"`/`"system error:"`）区分成功与失败，无结构化状态字段
2. **ECSNode** (`ecs.py:21`) 仅设置 `status: "suspended"`，无更细粒度的生命周期描述
3. **GraphState.status** (`state.py:61`) 仅有 4 个值：`idle | processing | suspended | error`，无法描述执行进度
4. **ExecutionStep** 和 `execution_trace` (`state.py:40-46, 70`) 已定义但从未被使用

随着引入 agent 自动执行、不可逆操作（如发邮件、部署）、多步骤工具链和挂起等待（resume），这些机制暴露出关键问题：

- ReasoningNode 被迫解析自然语言 observation 来"猜测"执行是否成功
- 执行失败 vs 执行被拒绝 vs 执行超时无法被区分
- 不可逆操作无法标记，重试可能导致重复执行
- ECS 挂起后 resume 缺少对先前执行状态的校验

### Stakeholders
- ReasoningNode：需要读取结构化执行结果，而非解析自然语言
- ToolNode / ECSNode：需要产出结构化的执行事件
- GraphRunner：需要根据执行状态决定是否持久化、暂停或终止
- MemoryNode：需要存储执行级审计信息用于后续回顾

### Constraints
- 不重构现有 Node 流程的核心结构（图拓扑不变）
- 不将执行状态嵌入 Action 定义（概念分离）
- 不引入外部状态存储（继续使用 SQLite）
- 保持与现有 SSE 事件格式兼容

## Goals / Non-Goals

### Goals
1. 定义独立于意图/任务建模的执行状态管理机制
2. 提供最小但完整的执行状态枚举和合法迁移规则
3. 让 ReasoningNode 读取结构化执行状态而非猜测
4. 支持不可逆操作标记与重复执行防护
5. 支持挂起等待（suspend）与恢复（resume）的合法状态迁移
6. 激活已有的 `execution_trace` 基础设施

### Non-Goals
- 不设计具体任务管理模型（task planner / scheduler）
- 不引入 UI 或交互细节
- 不将执行状态机设计为线性脚本
- 不修改图拓扑（IntentNode → EmotionNode → MemoryNode → ReasoningNode 的顺序不变）

## Concept Definitions

### 1. Intent / Action（意图层 → 可执行单元）

**Intent** 是 ReasoningNode 的输出产物 —— 一个对"应该做什么"的声明。Intent 存在于认知层面，由 LLM 推理产生。

**Action** 是 Intent 被"具体化"后生成的可执行单元。一个 Intent 可能产生零个或多个 Action（例如 "查询天气" → 一个 MCP 工具调用；"发邮件并记录日志" → 两个 Action）。

Action 不包含执行状态 —— 它是对"做什么"的描述，不是对"做得怎样"的记录。

**职责边界：** Action 描述 *what*，不描述 *how* 或 *result*。

### 2. Execution Contract（执行合约）

**Execution Contract** 是 Action 被提交给执行层时生成的不可变合约对象。它将一个 Action 绑定到一次具体的执行尝试，并携带执行约束（如 `irreversible: true`、`timeout: 30s`）。

每个 Execution Contract 拥有唯一 ID（`execution_id`），且在其生命周期内只被一个 Execution State Machine 跟踪。

**职责边界：** Contract 描述"这次执行的约束和元数据"。它由产出 Action 的节点（ReasoningNode）创建，由执行节点（ToolNode / ECSNode）消费。

**依赖方向：** Contract 引用 Action（知道"做什么"），但 Action 不引用 Contract（不知道"怎么执行"）。

### 3. Execution State Machine（执行状态机）

**Execution State Machine** 是 Execution Contract 的生命周期追踪器。它记录一次执行从提交到结束的完整状态迁移历史。

**职责边界：** State Machine 记录 *fact*（事实），不做 *inference*（推理）。ReasoningNode 读取状态机的当前状态来决策，但不能修改它 —— 只有执行节点（ToolNode / ECSNode）和 GraphRunner 可以推进状态迁移。

**依赖方向：** State Machine 依附于 Contract（每个 Contract 有且仅有一个 State Machine）。ReasoningNode 只读访问。

### 依赖关系总结

```
Intent ──produces──> Action ──binds to──> Execution Contract
                                                │
                                         Execution State Machine
                                                │
                              ┌─────────────────┼─────────────────┐
                              │                 │                 │
                         ToolNode          ECSNode          GraphRunner
                       (writes state)   (writes state)   (reads & persists)
                              │
                       ReasoningNode
                       (reads state only)
```

## Execution State Machine Design

### State Enumeration

```python
class ExecutionStatus(str, Enum):
    """最小但完整的执行状态枚举"""

    # === 初始状态 ===
    PENDING = "pending"
    # 合约已创建，尚未提交给执行器。
    # 这是所有 Contract 的起始状态。

    # === 活跃状态 ===
    RUNNING = "running"
    # 执行器已接收并开始执行。
    # 对于 ToolNode：MCP 调用正在进行中。
    # 对于 ECSNode：ECS 请求已发送，等待系统确认。

    WAITING = "waiting"
    # 执行已到达需要外部输入的挂起点。
    # 专用于 ECS 场景：等待人类响应。
    # 这是一个稳定状态 —— 可以无限期停留。

    # === 终止状态（不可逆） ===
    COMPLETED = "completed"
    # 执行成功完成，结果可用。

    FAILED = "failed"
    # 执行遇到错误，无法完成。
    # 包含失败原因（error_message）。

    REJECTED = "rejected"
    # 执行被主动拒绝（如权限不足、人类审批不通过）。
    # 区别于 FAILED：REJECTED 表示"不应该做"，FAILED 表示"做了但没成功"。

    CANCELLED = "cancelled"
    # 执行被取消（如超时、用户中断、系统回收）。
    # 区别于 FAILED：CANCELLED 表示"主动放弃"，FAILED 表示"被动失败"。
```

### 合法状态迁移规则

```
PENDING ──start──> RUNNING
RUNNING ──succeed──> COMPLETED
RUNNING ──fail──> FAILED
RUNNING ──reject──> REJECTED
RUNNING ──suspend──> WAITING
RUNNING ──cancel──> CANCELLED
WAITING ──resume──> RUNNING
WAITING ──cancel──> CANCELLED
WAITING ──timeout──> CANCELLED
```

**状态迁移矩阵：**

| From \ To   | PENDING | RUNNING | WAITING | COMPLETED | FAILED | REJECTED | CANCELLED |
|-------------|---------|---------|---------|-----------|--------|----------|-----------|
| PENDING     | -       | start   | -       | -         | -      | -        | -         |
| RUNNING     | -       | -       | suspend | succeed   | fail   | reject   | cancel    |
| WAITING     | -       | resume  | -       | -         | -      | -        | cancel/timeout |
| COMPLETED   | -       | -       | -       | -         | -      | -        | -         |
| FAILED      | -       | -       | -       | -         | -      | -        | -         |
| REJECTED    | -       | -       | -       | -         | -      | -        | -         |
| CANCELLED   | -       | -       | -       | -         | -      | -        | -         |

**终止状态（不可离开）：** `COMPLETED`, `FAILED`, `REJECTED`, `CANCELLED`

**稳定等待状态：** `WAITING`（可无限期停留，通过 resume 回到 RUNNING）

### 关键约束

1. **单向终止**：终止状态不可回退。一旦 COMPLETED/FAILED/REJECTED/CANCELLED，该 Contract 生命周期结束。
2. **不可逆保护**：标记为 `irreversible: true` 的 Contract，若已到达 `COMPLETED`，不允许创建相同 Action 的新 Contract（需通过幂等键检查）。
3. **WAITING 唯一出口**：WAITING 状态只能通过 `resume`（回到 RUNNING）或 `cancel/timeout`（到达 CANCELLED）离开。不允许直接从 WAITING 到 COMPLETED。
4. **写入权限**：只有 ToolNode、ECSNode 和 GraphRunner 可以推进状态。ReasoningNode 只读。

### Data Model

```python
class ExecutionContract(BaseModel):
    """一次具体执行尝试的不可变合约"""

    # Identity
    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    action_type: str  # "tool_call" | "ecs_request"
    action_detail: Dict[str, Any]  # 具体动作描述

    # Constraints
    irreversible: bool = False
    idempotency_key: Optional[str] = None  # 用于防重复
    timeout_seconds: Optional[int] = None

    # State Machine
    status: ExecutionStatus = ExecutionStatus.PENDING
    transitions: List[Dict[str, Any]] = Field(default_factory=list)
    # Each transition: {"from": str, "to": str, "trigger": str, "timestamp": float, "actor": str}

    # Result
    result: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: float = Field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = Field(default_factory=lambda: datetime.now().timestamp())
```

## Integration with Node Flow

### Contract Generation

**谁创建 Contract？** ReasoningNode。

当 ReasoningNode 解析 LLM 输出并检测到 tool_call 或 ecs_request 时，它不再直接设置 `pending_tool_calls` 或 `ecs_request`，而是创建一个 `ExecutionContract`：

```python
# In ReasoningNode.compute():
# 当前行为（reasoning.py:138-181）：
#   return {"pending_tool_calls": [current_call], ...}
# 新行为：
#   contract = ExecutionContract(
#       action_type="tool_call",
#       action_detail=current_call,
#       irreversible=current_call.get("irreversible", False),
#       idempotency_key=f"{service}:{method}:{hash(args)}",
#   )
#   return {"pending_executions": [contract], ...}
```

**向后兼容：** 在过渡期，`pending_tool_calls` 和 `pending_executions` 可以共存。新代码优先读取 `pending_executions`，回退到 `pending_tool_calls`。

### ToolNode / ECSNode State Production

**ToolNode** 执行时推进 Contract 状态：

```python
# In ToolNode.execute():
for contract in state.pending_executions:
    contract.transition("start", actor="tool_node")  # PENDING → RUNNING

    try:
        result = await execute_mcp_tool(...)
        if result.success:
            contract.transition("succeed", actor="tool_node")
            contract.result = result.result
        else:
            contract.transition("fail", actor="tool_node")
            contract.error_message = result.error
    except Exception as e:
        contract.transition("fail", actor="tool_node")
        contract.error_message = str(e)
```

**ECSNode** 执行时将 Contract 推进到 WAITING：

```python
# In ECSNode.execute():
contract.transition("start", actor="ecs_node")    # PENDING → RUNNING
contract.transition("suspend", actor="ecs_node")  # RUNNING → WAITING
return {"status": "suspended"}
```

### ReasoningNode Consumption

ReasoningNode 读取 Contract 的结构化状态，不再解析自然语言 observation：

```python
# In ReasoningNode.compute():
for contract in state.completed_executions:
    if contract.status == ExecutionStatus.COMPLETED:
        # 确定性地知道执行成功
        observation = f"[SUCCESS] {contract.result}"
    elif contract.status == ExecutionStatus.FAILED:
        # 确定性地知道执行失败
        observation = f"[FAILED] {contract.error_message}"
    elif contract.status == ExecutionStatus.REJECTED:
        observation = f"[REJECTED] {contract.error_message}"
```

### State Change → ReasoningNode Re-entry

**事件驱动，非轮询。**

ToolNode 完成执行后，通过图拓扑的现有边 `tools → reasoning` 自然回到 ReasoningNode。无需轮询。

ECS resume 场景：GraphRunner 的 `resume()` 方法加载 checkpoint 后，将 Contract 状态从 WAITING → RUNNING → COMPLETED（注入用户响应），然后重新启动图执行。ReasoningNode 在下一次执行时直接读取已完成的 Contract。

**关键：不新增轮询机制。** 现有的图拓扑边（`tools → reasoning`）和 resume 流程（`resume() → 重新执行图`）已足够驱动状态变化后的 ReasoningNode 再入。

## Suspend and Resume

### 进入 WAITING 的条件

1. **ECS 请求**：ReasoningNode 检测到 LLM 输出包含 ecs_request，创建 `action_type="ecs_request"` 的 Contract → ECSNode 将其推进到 WAITING
2. **人类审批**：对于标记 `irreversible: true` 的 Contract，ToolNode 在执行前可选择性地将其推进到 WAITING（要求人类确认）
3. **外部等待**：执行器返回 "需要异步回调" 的信号时（未来扩展）

### Resume 触发方式

1. 用户通过 `/ecs/respond` 提交响应
2. `/ecs/continue` 端点触发 `GraphRunner.resume()`
3. `resume()` 加载 checkpoint → 校验 Contract 处于 WAITING 状态 → 注入用户响应 → 将 Contract 推进到 RUNNING → COMPLETED → 重新执行图

### 不可逆操作防重复

```python
def can_create_contract(action_detail: Dict, existing_contracts: List[ExecutionContract]) -> bool:
    """检查是否允许创建新的执行合约"""
    for existing in existing_contracts:
        if (existing.irreversible
            and existing.status == ExecutionStatus.COMPLETED
            and existing.idempotency_key == compute_idempotency_key(action_detail)):
            return False  # 相同的不可逆操作已成功执行，拒绝重复
    return True
```

**三层防护：**
1. **幂等键**：相同 `service + method + args_hash` 的不可逆操作，若已 COMPLETED，拒绝创建新 Contract
2. **状态校验**：resume 时校验 Contract 必须处于 WAITING 状态，不允许对已终止的 Contract 执行 resume
3. **执行追踪**：`execution_trace` 记录所有 Contract 的完整迁移历史，支持审计

## Memory and System Review

### MemoryNode Storage Levels

| 级别 | 内容 | 持久化位置 | 对人类可见 |
|------|------|-----------|-----------|
| **结果级** | 执行成功/失败 + 简要结果摘要 | `execution_trace` + Memory DB | 是 |
| **迁移级** | 完整状态迁移历史（含时间戳和 actor） | `execution_trace` | 仅诊断时 |
| **请求级** | 原始 Action 详情（参数、约束） | Contract 序列化 | 否（系统内部） |

### System-Level Review Support

`execution_trace` 已在 `GraphState` 中定义（`state.py:70`），本设计将其激活：

```python
# 每次状态迁移时自动追加
state.execution_trace.append(ExecutionStep(
    node_id="tool_node",
    action=f"transition:{contract.execution_id}:{from_status}→{to_status}",
    result=contract.result,
    metadata={
        "trigger": trigger,
        "actor": actor,
        "contract_id": contract.execution_id,
        "irreversible": contract.irreversible,
    }
))
```

### Information Hidden from Humans

- 原始 LLM prompt 中的系统指令（已有机制）
- Contract 的 `idempotency_key` 计算细节
- 状态迁移的内部 actor 标识
- 超时/取消的精确阈值配置

## Worked Example

### 场景：Agent 执行不可逆操作（发送邮件），挂起等待人类确认，resume 后完成

```
1. 用户输入："帮我给 bob@example.com 发一封会议邀请邮件"

2. IntentNode → EmotionNode → MemoryNode（正常流程）

3. ReasoningNode 解析 LLM 输出：
   - 检测到 tool_call: {service: "email", method: "send", args: {...}}
   - 检测到 irreversible 标记（发邮件不可撤回）
   - 创建 Contract:
     ExecutionContract(
       execution_id: "exec-001",
       action_type: "tool_call",
       action_detail: {service: "email", method: "send", ...},
       irreversible: true,
       idempotency_key: "email:send:hash(bob@example.com,meeting)",
       status: PENDING
     )
   - 同时创建确认用的 ECS Contract:
     ExecutionContract(
       execution_id: "exec-002",
       action_type: "ecs_request",
       action_detail: {type: "confirmation", message: "确认发送邮件给 bob@example.com?"},
       status: PENDING
     )
   - 返回: {"pending_executions": [exec-002], "deferred_executions": [exec-001]}

4. 图路由到 ECSNode（因为有 pending ecs_request）:
   - exec-002: PENDING → RUNNING → WAITING
   - GraphRunner 检测 status="suspended"
   - 序列化 GraphState（含两个 Contract）到 graph_checkpoints
   - 向前端发送 SSE event: ecs（确认表单）

5. 用户在前端点击"确认发送":
   - POST /ecs/respond → 存储响应
   - POST /ecs/continue → GraphRunner.resume()

6. GraphRunner.resume():
   - 加载 checkpoint
   - 校验 exec-002 处于 WAITING 状态 ✓
   - exec-002: WAITING → RUNNING → COMPLETED（用户确认）
   - exec-001: 从 deferred 移入 pending
   - 重新执行图

7. 图路由到 ToolNode:
   - 幂等键检查：exec-001 未曾 COMPLETED ✓
   - exec-001: PENDING → RUNNING
   - 调用 MCP email.send()
   - 成功 → exec-001: RUNNING → COMPLETED, result="邮件已发送"

8. 图路由回 ReasoningNode:
   - 读取 exec-001.status == COMPLETED
   - 读取 exec-001.result == "邮件已发送"
   - 生成回复："已成功发送会议邀请邮件给 bob@example.com"

9. execution_trace 记录:
   [
     {node_id: "reasoning", action: "create_contract:exec-001", ...},
     {node_id: "reasoning", action: "create_contract:exec-002", ...},
     {node_id: "ecs_node", action: "transition:exec-002:pending→running", ...},
     {node_id: "ecs_node", action: "transition:exec-002:running→waiting", ...},
     {node_id: "graph_runner", action: "transition:exec-002:waiting→running", ...},
     {node_id: "graph_runner", action: "transition:exec-002:running→completed", ...},
     {node_id: "tool_node", action: "transition:exec-001:pending→running", ...},
     {node_id: "tool_node", action: "transition:exec-001:running→completed", ...},
   ]
```

### 异常场景：Resume 后工具执行失败

```
续接步骤 7，假设 MCP email.send() 失败：

7'. ToolNode:
   - exec-001: PENDING → RUNNING
   - 调用 MCP email.send() → 抛出异常
   - exec-001: RUNNING → FAILED, error_message="SMTP connection refused"

8'. ReasoningNode:
   - 读取 exec-001.status == FAILED
   - 读取 exec-001.error_message == "SMTP connection refused"
   - 不再猜测，直接告知用户："发送失败，原因：SMTP 连接被拒绝。请检查邮件服务配置。"
   - 不会创建新的 exec-001 Contract（幂等键存在，但状态是 FAILED 非 COMPLETED，允许重试）

9'. 用户说 "重试":
   - ReasoningNode 创建新 Contract exec-003（相同 idempotency_key）
   - 幂等键检查：exec-001 是 FAILED 非 COMPLETED → 允许 ✓
   - 正常执行流程
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Contract 序列化增加 checkpoint 体积 | 限制 `transitions` 历史最大条数（如 50 条）；Contract 数据量远小于 `dialogue_history` |
| ReasoningNode 需要适配新的 Contract 读取逻辑 | 过渡期保持 `observation` 字段兼容，Contract 结果同时写入 `observation` |
| LLM 不理解 `irreversible` 标记 | 在 prompt 中定义约定；未标记的操作默认 `irreversible: false` |
| 状态迁移校验增加执行路径复杂度 | `transition()` 方法内部实现校验，对外暴露简单 API |
| 与现有 `pending_tool_calls` / `ecs_request` 字段的兼容 | 过渡期两套字段共存，优先读新字段；迁移完成后删除旧字段 |

## Open Questions

1. **`irreversible` 标记由谁设定？**
   - 选项 A：由 LLM 在 tool_call 输出中显式标记（需 prompt 约定）
   - 选项 B：由 MCP 工具注册时声明（更可靠但需修改注册协议）
   - 当前倾向选项 B，但可两者结合

2. **timeout 的默认值与粒度？**
   - 工具调用默认 30s？
   - ECS 等待默认无限期？
   - 是否需要支持自定义 timeout per contract？

3. **execution_trace 的清理策略？**
   - 保留当前会话所有 trace？
   - 按时间窗口清理？
   - 不在本提案范围，但需确认扩展点
