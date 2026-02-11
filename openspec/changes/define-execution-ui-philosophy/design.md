# 设计：Wenko 执行感知 UI 哲学

## 背景

Wenko 的 `ExecutionObserver`（`workflow/observation.py:50`）是一个只读投影服务，将 `ExecutionContract` 状态机数据转换为结构化的观测模型：

| 观测模型 | 定义位置 | 用途 |
|---------|---------|------|
| `ExecutionSnapshot` | `workflow/core/state.py:231` | 某一时刻的执行状态快照 |
| `ExecutionConsequenceView` | `workflow/core/state.py:265` | ReasoningNode 的后果感知视图 |
| `TransitionRecord` | `workflow/core/state.py:294` | 单次状态转换记录 |
| `StateMachineTopology` | `workflow/core/state.py:324` | 状态机拓扑结构 |
| `ExecutionTimeline` | `workflow/core/state.py:335` | 会话级时间线 |

这些模型被以下消费者使用：

| 消费者 | 文件位置 | 调用方式 |
|-------|---------|---------|
| ReasoningNode | `reasoning.py:299-332` | `observer.consequence_views()` → 构造 LLM prompt |
| MemoryNode | `memory.py:110-145` | `observer.consequence_view()` → 存储 `execution_fact` |
| GraphRunner（resume） | `graph_runner.py:322-333` | `observer.snapshot()` → 恢复前校验 |
| GraphRunner（SSE） | `graph_runner.py:514-535` | `_build_execution_state_event()` → 推送 `execution_state` 事件 |
| HTTP API | `main.py:2199-2251` | `timeline()` / `snapshot()` / `topology()` → JSON 响应 |

Observer 已完成且稳定。缺失的是一套**人类感知模型**——把 Observer 输出翻译为非工程用户能理解、信任、操作的执行体验。

### 相关方
- **终端用户**：需要理解系统在做什么、为什么做
- **产品设计师**：基于本哲学构建 UI 表面
- **开发者**：实现 UI 时必须遵守 Observer → UI 边界

### 约束
- Observer 是**唯一执行真相来源** — UI 不得绕过
- 不引入新的 Observer 能力
- 不做前端实现或视觉设计决策
- 所有抽象必须可回溯到当前 Observer 实现

---

## 目标 / 非目标

### 目标
1. 定义一页纸的**执行 UI 哲学**：系统如何向人类呈现执行
2. 建立**人类执行感知对象**：替代工程词汇的命名概念
3. 规定**认知视图结构**：组织执行感知的稳定结构
4. 提供 **Observer → UI 语义映射表**
5. 声明**边界规则**：保护执行真相完整性

### 非目标
- ❌ 前端组件设计、布局或视觉样式
- ❌ 新增 Observer 方法或数据模型
- ❌ Debug / 开发者工具
- ❌ 阶段划分 / MVP 规划

---

## 第一部分：Wenko 执行 UI 哲学

### 核心理念

> Wenko 将执行呈现为**叙事**——一个在现实世界中采取行动的故事——而非系统操作日志。

人类与 Wenko 交互时，始终应该能回答四个问题：

| 问题 | 认知角色 | 感受 |
|-----|---------|------|
| **现在在做什么？** | 当下觉知 | 像在看某人工作 |
| **刚才发生了什么？** | 近期记忆 | 被告知做了什么 |
| **为什么要做这步？** | 因果理解 | 理解意图 |
| **这件事是否已成为事实？** | 现实承诺 | 知道什么是真的 |

这不是调试问题。这是一个人委托另一个人办事时自然会问的问题。Wenko 的 UI 存在就是为了回答它们——不多，不少。

### 执行是叙事，不是日志

日志说：`[13:42:01] transition: PENDING → RUNNING, actor: tool_node, contract_id: abc123`

叙事说：「正在给你的团队发送邮件……完成了。邮件已送达。」

区别是根本性的：
- **日志**服务于系统和开发者——详尽、技术性、顺序罗列
- **叙事**服务于人类——有选择、有意义、有因果

Wenko 的 UI 产出叙事。Observer 产出叙事所需的原始事实。

### 四个语义角色

UI 中每个执行事件严格扮演四种语义角色之一：

1. **执行（Execution）**— 容器。「一次完整的现实交互。」用户看到的是系统承担的一项连贯任务（例如"发送周报邮件"）。

2. **行动（Action）**— 意图。「系统决定做什么以及为什么。」行动是执行中的一步，有用户能理解的目的（例如"从记忆中查找收件人列表"）。

3. **后果（Consequence）**— 结果。「这个行动在现实中改变了什么。」后果是事实——描述"现在什么是真的而之前不是"（例如"邮件已送达 12 位收件人"）。

4. **记忆影响（Memory Impact）**— 持久化。「系统会记住什么。」告诉用户哪些后果被提交到系统的长期知识中（例如"已记住：2月10日发送了周报"）。

### Observer 的角色：隐形的神经系统

Observer 之于 UI，如同神经系统之于意识体验：
- 你不会感觉到单个神经元在放电——你感到"温暖"或"疼痛"
- 用户不会看到 snapshot 或 topology——他们看到"邮件正在发送"或"出了点问题"

Observer 提供原始信号。UI 提供意识体验。Observer 必须在 UI 中**隐身**——`snapshot`、`contract`、`topology`、`transition_record` 永远不应出现在用户可见的文本中。

---

## 第二部分：人类执行感知对象

这些是用户感知到的**命名概念**。每个都直接映射到 Observer 能力，但不使用工程词汇。

### 对象模型

```
执行（Execution）
├── 状态（State）："这件事在什么阶段？"
│   (准备中 / 进行中 / 需要关注 / 已完成 / 出了问题 / 已拒绝 / 已停止)
├── 行动（Action）[]
│   ├── 意图（Intent）："为什么要做这步？"
│   ├── 后果（Consequence）："做了之后怎么样？"
│   │   ├── 结果：成功 / 失败 / 进行中
│   │   ├── 现实变化："现在什么是真的？"
│   │   └── 不可逆：是 / 否
│   └── 时长（Duration）："花了多久？"
└── 记忆影响（Memory Impact）："系统记住了什么？"
    ├── 记录的事实[]
    └── 无（如果没有被提交）
```

### 对象定义与代码映射

| 人类对象 | 代表什么 | Observer 来源 | 代码位置 |
|---------|---------|-------------|---------|
| **执行** | 一次完整的现实交互 | `ExecutionContract`（身份 + 生命周期） | `state.py:106` |
| **状态** | 执行的当前阶段 | `ExecutionSnapshot.current_status` → 人类标签 | `state.py:240` → `observation.py:85` |
| **行动** | 执行中的一步有意图的动作 | `action_detail` + `_generate_action_summary()` | `observation.py:33-47` |
| **后果** | 行动造成的现实变化 | `ExecutionConsequenceView` | `observation.py:102-129` |
| **记忆影响** | 系统会记住什么 | MemoryNode `execution_fact` | `memory.py:132-145` |

### 状态标签映射

当前代码中已有 `STATUS_TO_CONSEQUENCE`（`state.py:220-228`），它映射的是**机器侧标签**（SUCCESS / FAILED / WAITING 等）。本哲学要求在 UI 层增加一层**人类语义标签**：

| Observer Status | 机器标签（现有） | 人类标签（本哲学定义） | 人类含义 |
|----------------|---------------|-------------------|---------|
| PENDING | NOT_STARTED | 准备中 | "正在准备行动" |
| RUNNING | IN_PROGRESS | 进行中 | "正在做" |
| WAITING | WAITING | 需要关注 | "等待你的输入" |
| COMPLETED | SUCCESS | 已完成 | "成功了" |
| FAILED | FAILED | 出了问题 | "没有成功" |
| REJECTED | REJECTED | 已拒绝 | "你选择了不继续" |
| CANCELLED | CANCELLED | 已停止 | "这件事被取消了" |

---

## 第三部分：执行认知视图

这些是**认知视图**——组织执行感知的稳定方式。它们不是屏幕布局或组件，而是用户理解执行所需的概念结构。

### 视图 1：执行舞台（Execution Stage）

**回答的问题**：「现在在做什么？」

展示当前活跃的执行：
- 系统正在做什么（行动意图）
- 处于什么状态（状态标签）
- 是否需要用户关注（WAITING → "需要关注"）

**Observer 支撑**：`snapshot()`（`observation.py:56-100`）→ 当前状态、行动摘要、等待计数

**数据流**：
```
ExecutionContract → observer.snapshot() → ExecutionSnapshot
  → UI 翻译层 →
    current_status="running" → "进行中"
    action_summary="email.send" → "正在发送邮件"
    is_resumable=true → "需要关注"
```

### 视图 2：行动解释（Action Explanation）

**回答的问题**：「为什么做这步？做完之后怎么样？」

对任一行动展示：
- 意图（"给团队发送邮件"）
- 后果（"邮件已送达" 或 "发送失败：地址未找到"）
- 是否不可逆（"此操作无法撤销"）
- 是否经过人类确认（"你批准了这个操作"）

**Observer 支撑**：`consequence_view()`（`observation.py:102-129`）→ consequence_label, has_side_effects, was_suspended, result

**数据流**：
```
ExecutionContract → observer.consequence_view() → ExecutionConsequenceView
  → UI 翻译层 →
    consequence_label="SUCCESS" → "已完成"
    has_side_effects=true → "此操作已产生不可逆影响"
    was_suspended=true → "经过你的确认"
    result="sent to 12 recipients" → "邮件已送达 12 位收件人"
```

### 视图 3：执行历史（Execution History）

**回答的问题**：「已经发生了什么？」

一个有序列表，展示已完成行动及其后果，呈现为事实的时间线——不是系统事件。每条回答：「做了什么，结果如何？」

**Observer 支撑**：`timeline()`（`observation.py:223-274`）→ 有序的 contracts 和 transition records

**数据流**：
```
List[ExecutionContract] → observer.timeline(session_id, contracts, trace) → ExecutionTimeline
  → UI 翻译层 →
    contracts[]: 每个 snapshot 翻译为行动 + 后果的叙事条目
    transitions[]: 过滤为人类有意义的事件（跳过内部系统转换）
    has_irreversible_completed → 标记"含不可逆操作"
```

### 视图 4：执行结构（Execution Structure）

**回答的问题**：「这些行动之间是什么关系？」

展示执行中行动之间的关系——顺序的、分支的、或依赖的。这不是状态机图。它是叙事结构：「先做了 X，然后做了 Y，Z 依赖于 Y 的结果。」

**Observer 支撑**：`topology()`（`observation.py:163-221`）→ 状态节点和边，翻译为叙事流

**数据流**：
```
ExecutionObserver.topology() → StateMachineTopology
  → UI 翻译层 →
    nodes[]: 每个 StateNode 翻译为行动阶段（"准备" → "执行" → "完成"）
    edges[]: 翻译为阶段间的自然过渡（"准备好之后，开始执行"）
    terminal_statuses → "结束点"
```

### 视图 5：记忆影响（Memory Impact）

**回答的问题**：「系统会记住什么？」

展示哪些后果被提交到长期记忆。这建立用户信任：他们可以看到系统从发生的事情中学到了什么。

**Observer 支撑**：MemoryNode `execution_fact` 条目（`memory.py:132-145`），通过 `consequence_view()` 在 consolidation 时生成

**数据流**：
```
ExecutionContract（terminal）→ observer.consequence_view() → ExecutionConsequenceView
  → MemoryNode._record_execution_summaries() →
    memory_manager.save_memory(key="execution:<id>", content=execution_memory)
  → UI 翻译层 →
    action_summary → "做了什么"
    consequence_label → "结果如何"
    irreversible → "是否产生了不可逆影响"
```

---

## 第四部分：Observer → UI 语义映射

### 完整映射表

| Observer 能力 | 代码位置 | UI 语义角色 | 语义责任 | 主要视图 |
|-------------|---------|-----------|---------|---------|
| `snapshot(contract)` | `observation.py:56` | 执行状态 | 当下真相：「现在的现实状态是什么？」 | 执行舞台 |
| `consequence_view(contract)` | `observation.py:102` | 行动解释 | 因果解释：「这个行动改变了什么？」 | 行动解释 |
| `consequence_views(contracts)` | `observation.py:131` | 批量解释 | 聚合因果：「这些行动一起产生了什么？」 | 执行历史 |
| `transition_records(contract)` | `observation.py:140` | 行动进程 | 阶段推进：「这个行动经历了哪些阶段？」 | 执行历史 |
| `topology()` | `observation.py:163` | 执行结构 | 结构理解：「事情是如何组织的？」 | 执行结构 |
| `timeline(session_id, ...)` | `observation.py:223` | 执行历史 | 历史真相：「已经发生了什么？」 | 执行历史 |
| resume alignment | `graph_runner.py:322-333` | 连续性守卫 | 连续性信任：「系统是否安全地继续了？」 | 执行舞台 |
| `_generate_action_summary()` | `observation.py:33` | 行动意图 | 意图描述：「系统决定做什么？」 | 所有视图 |
| `_build_execution_state_event()` | `graph_runner.py:514` | 实时状态推送 | 即时感知：「刚刚发生了状态变化」 | 执行舞台 |
| MemoryNode `execution_fact` | `memory.py:132` | 记忆影响 | 持久化证明：「什么被记住了？」 | 记忆影响 |

### 当前"人类标签"现状审计

当前代码中只有一处接近"人类标签"的映射：

**`STATUS_TO_CONSEQUENCE`**（`state.py:220-228`）：
```python
STATUS_TO_CONSEQUENCE = {
    COMPLETED: "SUCCESS",     # ← 仍是机器标签，不是人类语言
    FAILED: "FAILED",
    REJECTED: "REJECTED",
    WAITING: "WAITING",
    RUNNING: "IN_PROGRESS",
    PENDING: "NOT_STARTED",
}
```

这些标签被 ReasoningNode（`reasoning.py:321`）直接拼入 LLM prompt，并被 MemoryNode（`memory.py:133`）存入 `execution_fact`。它们是**机器可读的标签**，不是人类可理解的叙事。

**`_generate_action_summary()`**（`observation.py:33-47`）：
```python
# 输出示例：
# "email.send"        ← 技术性的 service.method 格式
# "ecs:form"           ← 内部系统前缀
# "tool_call"          ← 原始 action_type 回退
```

这是目前最接近"人类意图描述"的地方，但输出仍是技术格式。未来 UI 翻译层需要将其进一步转化为自然语言。

---

## 第五部分：边界规则

这些规则是**不可违反的约束**，适用于所有未来的人类可见执行界面。

### 规则 1：Observer 是唯一执行真相来源

UI 不得从 tool result 原始输出、LLM 回复、或任何非 Observer 投影来源构造执行状态。Observer 不提供的，UI 不展示。

**现状核查**：当前 ReasoningNode（`reasoning.py:299`）已遵守此规则——它不直接读取 `ExecutionContract` 字段，而是通过 `observer.consequence_views()` 获取语义化视图。

### 规则 2：只展示已验证的事实

UI 不得展示 Observer 未确认已发生的执行结果。推测性的、预测性的、或进行中的结果必须与已完成事实明确区分。

**现状核查**：`ExecutionConsequenceView.is_still_pending`（`state.py:288`）字段已提供此区分。UI 层应严格使用此字段。

### 规则 3：用户可见文本中不出现工程词汇

以下术语不得出现在任何用户可见文本中：`snapshot`、`contract`、`topology`、`transition`、`observer`、`projection`、`state machine`、`node`、`actor_category`、原始 `execution_id`。

**现状核查**：SSE 事件（`graph_runner.py:514-535`）的 payload 中包含 `execution_id`、`actor_category`、`from_status`、`to_status` 等工程字段。如果这些事件直接呈现给用户，需要经过翻译层。

### 规则 4：呈现叙事，而非日志

执行事件必须以因果叙事呈现（「做了这件事，因为……」），而非顺序日志（「13:42:01 PENDING→RUNNING」）。时间顺序存在，但服务于叙事结构，不是调试。

### 规则 5：Observer 不可见

Observer 作为系统组件的存在必须对用户不可见。用户应感觉自己在看系统行动——而非在看一个监控层报告系统状态。

---

## 风险 / 权衡

| 风险 | 缓解措施 |
|-----|---------|
| 哲学过于抽象，无法指导实现 | 每个视图有明确的 Observer 支撑和具体的数据流描述 |
| 人类标签失去了工程术语的精确性 | 映射表确保每个人类概念可回溯到精确的 Observer 能力和代码位置 |
| 边界规则限制未来灵活性 | 规则保护用户信任，这不可协商；例外需要显式设计评审 |
| 叙事框架可能不适合所有交互形态（如 API 消费者） | 哲学仅适用于人类可见表面；API/开发者表面可直接暴露 Observer |
| `_generate_action_summary()` 输出仍是技术格式 | 未来 UI 翻译层需增加 action_summary → 自然语言的规则，但不在本 proposal 范围内 |

## 开放问题

无。本 proposal 是自包含的哲学基础。实现问题（组件设计、状态管理、动画、响应式）属于未来引用本哲学的 UI 实现 proposal。
