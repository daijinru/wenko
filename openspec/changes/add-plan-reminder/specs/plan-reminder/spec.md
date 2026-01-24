# Capability: Plan Reminder

提供时间敏感的计划/提醒功能，允许用户通过自然对话或 Workflow 面板创建计划，并在指定时间通过 Live2D 主动提醒。

## ADDED Requirements

### Requirement: Plan Memory Type

系统 SHALL 支持 `plan` 类型的长期记忆，用于存储带有时间属性的计划和提醒。

#### Scenario: Plan category in memory system
- **WHEN** 用户创建一个计划
- **THEN** 系统将其存储为 `plan` 类别的记忆条目
- **AND** 条目包含目标时间、提醒偏移量、重复规则和状态字段

#### Scenario: Plan data structure
- **WHEN** 一个计划被创建
- **THEN** 该计划包含以下字段：id, session_id, title, description, target_time, reminder_offset_minutes, repeat_type, status, snooze_until, created_at, updated_at

---

### Requirement: Time Intent Recognition

LLM SHALL 识别用户消息中的时间意图，并在检测到计划/提醒意图时触发 HITL 表单。

#### Scenario: Detect time-related intent
- **WHEN** 用户消息包含时间表达式（如"明天下午3点"、"下周三"、"1月25日10点"）
- **AND** 消息表达了要做某事的意图
- **THEN** LLM 生成 HITL 请求，intent 为 `collect_plan`

#### Scenario: Ambiguous time expression
- **WHEN** 用户提供的时间表达不明确（如"下午开会"缺少日期）
- **THEN** HITL 表单允许用户补全具体日期时间

---

### Requirement: Plan Collection HITL Form

系统 SHALL 提供专门的 HITL 表单用于收集计划详情。

#### Scenario: Display plan form
- **WHEN** LLM 触发 `collect_plan` 意图的 HITL 请求
- **THEN** Electron 弹出计划收集表单窗口
- **AND** 表单包含：标题、描述、目标时间、提前提醒时间、重复类型

#### Scenario: Form field types
- **WHEN** 用户填写计划表单
- **THEN** 目标时间字段支持日期时间选择
- **AND** 提前提醒时间提供选项：立即/5分钟/10分钟/30分钟/1小时
- **AND** 重复类型提供选项：不重复/每天/每周/每月

#### Scenario: Save plan from form
- **WHEN** 用户提交计划表单（approve 或 edit 动作）
- **THEN** 系统将表单数据保存为 plan 类型的记忆条目
- **AND** 返回确认消息给 Live2D 继续对话

---

### Requirement: Plan CRUD API

后端 SHALL 提供完整的 CRUD API 端点用于管理计划。

#### Scenario: List plans
- **WHEN** 调用 `GET /plans` 端点
- **THEN** 返回计划列表，支持 status 和 page/limit 参数过滤
- **AND** 按 target_time 升序排列

#### Scenario: Create plan
- **WHEN** 调用 `POST /plans` 端点，携带计划数据
- **THEN** 创建新计划并返回完整的计划对象

#### Scenario: Get plan details
- **WHEN** 调用 `GET /plans/{id}` 端点
- **THEN** 返回指定计划的完整信息

#### Scenario: Update plan
- **WHEN** 调用 `PUT /plans/{id}` 端点，携带更新数据
- **THEN** 更新计划字段并返回更新后的计划对象

#### Scenario: Delete plan
- **WHEN** 调用 `DELETE /plans/{id}` 端点
- **THEN** 删除指定计划

#### Scenario: Query due plans
- **WHEN** Electron 进程调用 `GET /plans/due` 端点
- **THEN** 返回所有 status 为 pending 且 reminder_time <= 当前时间的计划
- **AND** reminder_time = target_time - reminder_offset_minutes

#### Scenario: Complete a plan
- **WHEN** 调用 `POST /plans/{id}/complete` 端点
- **THEN** 将该计划的 status 更新为 `completed`
- **AND** 如果是重复计划，创建下一个周期的计划实例

#### Scenario: Dismiss a plan
- **WHEN** 调用 `POST /plans/{id}/dismiss` 端点
- **THEN** 将该计划的 status 更新为 `dismissed`

#### Scenario: Snooze a plan
- **WHEN** 调用 `POST /plans/{id}/snooze` 端点，携带 snooze_minutes 参数
- **THEN** 将该计划的 snooze_until 设置为当前时间 + snooze_minutes
- **AND** 在 snooze_until 之前，该计划不会出现在 due plans 查询结果中

---

### Requirement: Electron Polling Service

Electron main process SHALL 定期轮询后端检查到期计划。

#### Scenario: Polling interval
- **WHEN** Electron 应用启动
- **THEN** 启动轮询服务，每 60 秒检查一次到期计划

#### Scenario: Send reminder event
- **WHEN** 轮询检测到有到期计划
- **THEN** 通过 IPC 发送 `plan:reminder` 事件到 renderer 进程
- **AND** 事件包含计划的 id, title, description, target_time

#### Scenario: Handle offline plans
- **WHEN** 应用启动时存在过期但未处理的计划
- **THEN** 首次轮询返回这些过期计划
- **AND** 按 target_time 排序，最早的优先

---

### Requirement: Live2D Reminder Display

Live2D 模块 SHALL 接收并显示计划提醒。

#### Scenario: Display reminder
- **WHEN** Live2D 接收到 `plan:reminder` 事件
- **THEN** Live2D 角色显示提醒消息（通过对话气泡）
- **AND** 提供交互按钮：完成、稍后提醒、取消

#### Scenario: User acknowledges reminder
- **WHEN** 用户点击"完成"按钮
- **THEN** 发送 IPC 事件触发 `POST /plans/{id}/complete`
- **AND** 隐藏提醒消息

#### Scenario: User snoozes reminder
- **WHEN** 用户点击"稍后提醒"按钮
- **THEN** 显示推迟选项（5分钟/15分钟/1小时）
- **AND** 用户选择后发送 IPC 事件触发 `POST /plans/{id}/snooze`

#### Scenario: User dismisses reminder
- **WHEN** 用户点击"取消"按钮
- **THEN** 发送 IPC 事件触发 `POST /plans/{id}/dismiss`
- **AND** 隐藏提醒消息，该计划不再提醒

---

### Requirement: Workflow Panel Plan Management

Workflow 面板 SHALL 提供计划管理页面，允许用户主动创建、查看、编辑和删除计划。

#### Scenario: View plan list
- **WHEN** 用户打开 Workflow 面板的 Plans 页面
- **THEN** 显示所有计划列表，按时间分组（今天/明天/本周/更晚）
- **AND** 每个计划项显示标题、目标时间和状态

#### Scenario: Create plan manually
- **WHEN** 用户点击"添加计划"按钮
- **THEN** 显示计划创建表单，包含标题、描述、目标时间、提醒偏移、重复类型
- **AND** 提交后调用 `POST /plans` 创建计划

#### Scenario: Edit existing plan
- **WHEN** 用户点击某个计划项进行编辑
- **THEN** 显示预填充的编辑表单
- **AND** 提交后调用 `PUT /plans/{id}` 更新计划

#### Scenario: Delete plan
- **WHEN** 用户点击删除按钮
- **THEN** 显示确认对话框
- **AND** 确认后调用 `DELETE /plans/{id}` 删除计划

#### Scenario: Filter by status
- **WHEN** 用户选择状态过滤器（全部/待执行/已完成/已取消）
- **THEN** 列表仅显示对应状态的计划
