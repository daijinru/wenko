## ADDED Requirements

### Requirement: 执行 UI 哲学

系统 SHALL 定义一套稳定、长期成立的人类执行感知模型，将所有 Observer 能力翻译为人类可理解的执行体验，不暴露工程概念。

该哲学 SHALL 回答四个根本性的人类感知问题：
1. 现在在做什么？
2. 刚才发生了什么？
3. 为什么要做这步？
4. 这件事是否已成为事实？

#### Scenario: 非工程用户理解活跃执行
- **GIVEN** 一个非技术用户在系统执行 tool call（如发送邮件）期间查看界面
- **WHEN** `ExecutionObserver.snapshot()`（`observation.py:56`）返回 `current_status="running"`, `action_summary="email.send"`
- **THEN** 用户看到叙事描述（如"正在给你的团队发送邮件"）和状态标签（"进行中"）
- **AND** 界面中不出现 snapshot / contract / topology / transition / observer 等工程术语

#### Scenario: 执行以叙事而非日志呈现
- **GIVEN** 一次执行包含多个行动，且已通过 `observer.timeline()`（`observation.py:223`）投影为 `ExecutionTimeline`
- **WHEN** 用户查看执行历史
- **THEN** 事件以因果叙事呈现（如"先查找了收件人，然后发送了报告"），而非时间戳日志
- **AND** 每个行动展示其意图（来自 `_generate_action_summary()`）和后果（来自 `consequence_view()`）

---

### Requirement: 人类执行感知对象

系统 SHALL 定义一组人类可感知的执行对象，映射到 Observer 能力：
- **执行（Execution）**：一次完整的现实交互（映射到 `ExecutionContract`，`state.py:106`）
- **行动（Action）**：执行中一步有意图的动作（映射到 `action_detail` + `_generate_action_summary()`，`observation.py:33-47`）
- **后果（Consequence）**：行动造成的现实变化（映射到 `ExecutionConsequenceView`，`observation.py:102-129`）
- **状态（State）**：执行的当前阶段（映射到 `ExecutionSnapshot.current_status`，`observation.py:85`，配合人类标签）
- **记忆影响（Memory Impact）**：系统会记住什么（映射到 MemoryNode `execution_fact`，`memory.py:132-145`）

系统 SHALL 将 Observer 状态值映射为人类可读的状态标签（在现有 `STATUS_TO_CONSEQUENCE`（`state.py:220-228`）之上增加一层）：
- PENDING → "准备中"
- RUNNING → "进行中"
- WAITING → "需要关注"
- COMPLETED → "已完成"
- FAILED → "出了问题"
- REJECTED → "已拒绝"
- CANCELLED → "已停止"

#### Scenario: 用户感知已完成行动的后果
- **GIVEN** 一个 tool call 已成功完成且 `has_side_effects=true`（`observation.py:110`）
- **WHEN** 用户查看该行动的后果
- **THEN** 后果展示现实中的变化（如"邮件已送达 12 位收件人"），来源于 `consequence_view.result`
- **AND** 标示操作是否不可逆（来自 `consequence_view.has_side_effects`）
- **AND** 标示是否经过人类确认（来自 `consequence_view.was_suspended`）

#### Scenario: 用户感知等待状态
- **GIVEN** 一次执行处于 WAITING 状态（`ExecutionSnapshot.is_resumable=true`，`observation.py:77`）
- **WHEN** 用户查看执行状态
- **THEN** 状态标签显示"需要关注"（而非"WAITING"）
- **AND** 用户理解系统正在等待其输入

---

### Requirement: 执行认知视图

系统 SHALL 定义五个稳定的认知视图来组织人类执行感知：

1. **执行舞台（Execution Stage）**— 回答"现在在做什么？"，由 `snapshot()`（`observation.py:56`）支撑
2. **行动解释（Action Explanation）**— 回答"为什么做？结果如何？"，由 `consequence_view()`（`observation.py:102`）支撑
3. **执行历史（Execution History）**— 回答"已经发生了什么？"，由 `timeline()`（`observation.py:223`）支撑
4. **执行结构（Execution Structure）**— 回答"行动之间什么关系？"，由 `topology()`（`observation.py:163`）支撑
5. **记忆影响（Memory Impact）**— 回答"什么被记住了？"，由 MemoryNode `execution_fact`（`memory.py:132`）支撑

这些视图 SHALL 被当作认知结构而非调试面板。用户 SHALL NOT 需要理解系统内部结构即可使用。

#### Scenario: 执行舞台展示当下觉知
- **GIVEN** 系统正在执行一个行动（`ExecutionSnapshot.current_status="running"`）
- **WHEN** 用户查看执行舞台
- **THEN** 看到当前行动的意图（来自 `action_summary`）、状态标签（"进行中"）、以及是否需要关注
- **AND** 数据来自 `observer.snapshot()` 的投影

#### Scenario: 执行历史展示有序事实
- **GIVEN** 会话中有多个行动已完成
- **WHEN** 用户查看执行历史
- **THEN** 看到已完成行动及其后果的有序列表
- **AND** 数据来自 `observer.timeline()` 投影的 `ExecutionTimeline`（`state.py:335`）
- **AND** 条目以事实呈现，而非系统事件

#### Scenario: 记忆影响展示被记住的事实
- **GIVEN** 执行已到达终态，MemoryNode 已通过 `_record_execution_summaries()`（`memory.py:110`）记录了 execution_fact
- **WHEN** 用户查看记忆影响
- **THEN** 看到哪些后果被提交到系统长期记忆
- **AND** 该视图通过展示"系统从交互中学到了什么"来建立用户信任

---

### Requirement: Observer 到 UI 语义映射

系统 SHALL 维护 Observer 能力与 UI 角色之间的语义映射：

| Observer 能力 | 代码位置 | UI 语义角色 | 语义责任 |
|-------------|---------|-----------|---------|
| `snapshot()` | `observation.py:56` | 执行状态 | 当下真相 |
| `consequence_view()` | `observation.py:102` | 行动解释 | 因果解释 |
| `timeline()` | `observation.py:223` | 执行历史 | 历史真相 |
| `topology()` | `observation.py:163` | 执行结构 | 结构理解 |
| resume alignment | `graph_runner.py:322-333` | 连续性守卫 | 连续性信任 |
| `execution_fact` | `memory.py:132` | 记忆影响 | 持久化证明 |

每个到达 UI 的 Observer 输出 MUST 经过此映射。Observer 数据 SHALL NOT 未经语义翻译直接暴露给用户。

#### Scenario: Observer snapshot 翻译为人类状态
- **GIVEN** Observer 产出 snapshot：`current_status="running"`, `action_summary="email.send"`（`observation.py:85-84`）
- **WHEN** 此数据到达 UI 层
- **THEN** 被翻译为 状态="进行中"，行动="正在发送邮件"
- **AND** 原始 Observer 字段（status enum, contract_id, execution_id）不展示给用户

#### Scenario: Observer consequence_view 翻译为人类解释
- **GIVEN** Observer 产出 consequence_view：`consequence_label="SUCCESS"`, `has_side_effects=true`（`observation.py:105,110`）
- **WHEN** 此数据到达 UI 层
- **THEN** 被翻译为叙事后果（如"邮件已送达"）并附带不可逆标示
- **AND** 原始 Observer 字段（consequence_label enum, has_side_effects boolean）不展示给用户

---

### Requirement: UI 边界规则

系统 SHALL 对所有人类可见的执行界面强制执行以下不可违反的约束：

1. **唯一来源**：UI MUST NOT 从 Observer 投影以外的任何来源构造执行状态
2. **只展示已验证事实**：UI MUST NOT 展示 Observer 未确认已发生的结果
3. **禁止工程词汇**：`snapshot`、`contract`、`topology`、`transition`、`observer`、`projection`、`state machine`、`node`、`actor_category`、原始 `execution_id` MUST NOT 出现在用户可见文本中
4. **叙事优先于日志**：事件 MUST 以因果叙事呈现，而非顺序日志
5. **Observer 不可见**：Observer 作为组件的存在 MUST 对用户不可见

#### Scenario: UI 拒绝非 Observer 的执行数据
- **GIVEN** UI 组件试图展示执行状态
- **WHEN** 数据来源是 tool 的原始输出（未经 Observer 投影）
- **THEN** 系统拒绝此数据路径
- **AND** 要求数据先经过 Observer 投影（`observation.py:50` 的 `ExecutionObserver`）

#### Scenario: UI 区分进行中与已完成事实
- **GIVEN** 一个行动当前处于 RUNNING 状态（`ExecutionConsequenceView.is_still_pending=true`，`state.py:288`）
- **WHEN** 用户查看执行舞台
- **THEN** 行动明确展示为进行中（"进行中……"）
- **AND** 不作为已完成事实呈现
- **AND** 不展示推测性结果
