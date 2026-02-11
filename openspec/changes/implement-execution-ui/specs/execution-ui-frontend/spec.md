# Execution UI Frontend

前端执行感知 UI 能力规范——实现 `execution-ui-philosophy` 定义的认知视图。

**Related capabilities**: `execution-ui-philosophy`（哲学规范）, `electron-app`（应用框架）

## ADDED Requirements

### Requirement: Execution Stage Display

系统 SHALL 在对话界面实时展示当前执行状态，使用叙事语言（非工程术语）向用户传达"现在在做什么"。

- 数据来源 SHALL 为 SSE `execution_state` 事件中的 `human` 字段
- 展示内容 SHALL 包含行动描述和当前状态标签
- 终态行动（已完成/出了问题/已拒绝/已停止）SHALL 在短暂展示后自动消失
- 非终态行动（准备中/进行中/需要关注）SHALL 持续展示直到状态变更
- 界面中 SHALL NOT 出现 execution_id、actor_category、snapshot、observer 等工程词汇

#### Scenario: User sees active execution
- **GIVEN** 系统正在执行一个行动（如发送邮件）
- **WHEN** 后端推送 `execution_state` SSE 事件且 `to_status` 为 `running`
- **THEN** 对话界面展示"正在发送邮件……"（使用 `human.行动` 和 `human.新状态`）

#### Scenario: User sees completed execution
- **GIVEN** 系统完成了一个行动
- **WHEN** 后端推送 `execution_state` SSE 事件且 `human.是否已结束` 为 `true`
- **THEN** 对话界面短暂展示"发送邮件——已完成"后自动消失

#### Scenario: User sees attention-needed execution
- **GIVEN** 系统执行遇到需要关注的情况
- **WHEN** 后端推送 `execution_state` SSE 事件且 `human.是否需要关注` 为 `true`
- **THEN** 对话界面持续展示"发送邮件——需要关注"并以醒目样式标记

#### Scenario: No engineering vocabulary visible
- **GIVEN** 任意 `execution_state` SSE 事件到达前端
- **WHEN** 事件数据被渲染到界面
- **THEN** 用户可见文本中不包含 execution_id、actor_category、from_status、to_status、snapshot、contract、topology、transition、observer 等工程字段名

### Requirement: Execution History View

系统 SHALL 在管理面板中提供执行历史视图，以时间线形式展示已发生的行动及其结果。

- 数据来源 SHALL 为 `GET /api/execution/{session_id}/timeline?human=true` 端点
- 每条历史条目 SHALL 展示行动描述和状态标签
- 不可逆操作 SHALL 有明确的视觉标记
- 历史列表 SHALL 支持刷新

#### Scenario: User views execution history
- **GIVEN** 用户打开管理面板的执行状态 Tab
- **WHEN** Tab 加载完成
- **THEN** 展示当前会话的行动时间线列表，每条包含行动名称和状态

#### Scenario: User sees irreversible action marker
- **GIVEN** 执行历史中包含一个不可逆行动
- **WHEN** 该行动条目被渲染
- **THEN** 条目上有醒目的不可逆标记（如"不可撤销"标签）

#### Scenario: Empty execution history
- **GIVEN** 当前会话没有执行历史
- **WHEN** 用户打开执行状态 Tab
- **THEN** 展示空状态提示（如"暂无执行记录"）

### Requirement: Action Explanation Display

系统 SHALL 支持用户查看单条行动的详细解释，回答"为什么做这步"和"结果如何"。

- 行动解释 SHALL 作为执行历史条目的展开详情
- 展示内容 SHALL 包含后果描述、不可逆标记、错误信息（如有）
- 展示内容 SHALL NOT 包含工程字段名

#### Scenario: User expands action detail
- **GIVEN** 执行历史中有一条已完成的行动
- **WHEN** 用户点击该条目展开
- **THEN** 展示行动的详细解释，包含结果描述和不可逆标记

#### Scenario: User sees failed action explanation
- **GIVEN** 执行历史中有一条失败的行动
- **WHEN** 用户展开该条目
- **THEN** 展示错误描述，帮助用户理解出了什么问题

### Requirement: SSE Execution Event Auto-Humanization

后端 SHALL 在发射 `execution_state` SSE 事件时自动附带人类化数据，使前端无需维护翻译逻辑。

- SSE `execution_state` 事件 SHALL 在原始 payload 基础上自动附带 `human` 字段
- `human` 字段 SHALL 由 `_humanize_execution_state_event()` 生成
- 原始 payload 字段（`execution_id`, `from_status`, `to_status` 等）SHALL 保持不变以兼容机器消费者

#### Scenario: SSE event carries human field
- **GIVEN** 一次执行状态转换发生
- **WHEN** 后端构造 `execution_state` SSE 事件
- **THEN** 事件 payload 同时包含原始字段和 `human` 字段

#### Scenario: Original payload unchanged
- **GIVEN** 后端附带 `human` 字段
- **WHEN** 机器消费者读取 SSE 事件
- **THEN** 原始字段（`execution_id`, `action_summary`, `from_status`, `to_status`, `is_terminal` 等）值不变

### Requirement: Execution State IPC Bridge

系统 SHALL 通过 Electron IPC 将执行状态从 Live2D 对话窗口传递到 React 管理面板。

- Live2D Widget SHALL 通过 `window.electronAPI.send()` 转发执行状态事件到 Main Process
- Main Process SHALL 将执行状态事件转发到 Workflow 窗口
- IPC channel 名称 SHALL 在 preload.cjs 白名单中注册

#### Scenario: Execution state forwarded to workflow panel
- **GIVEN** Live2D Widget 收到 `execution_state` SSE 事件
- **WHEN** Widget 通过 IPC 发送人类化数据
- **THEN** React Workflow Panel 通过 IPC listener 接收到相同数据

#### Scenario: Workflow panel offline
- **GIVEN** Workflow 管理面板窗口未打开
- **WHEN** Live2D Widget 通过 IPC 发送执行状态
- **THEN** 系统不报错（Main Process 静默忽略无接收者的转发）
