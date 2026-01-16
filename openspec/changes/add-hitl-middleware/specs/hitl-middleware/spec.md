# HITL Middleware

Human-in-the-Loop 中间件能力规范，提供 AI 与用户之间的交互确认机制。

## ADDED Requirements

### Requirement: HITL Form Schema System

系统 SHALL 提供动态表单 Schema 系统，允许 AI 生成结构化表单请求。

#### Scenario: AI generates select form for preference collection
- **GIVEN** AI 需要收集用户的运动偏好
- **WHEN** AI 在响应中包含 `hitl_request` 字段
- **THEN** 系统生成包含 select 类型字段的表单 Schema
- **AND** Schema 包含 `id`, `type`, `title`, `fields`, `actions` 字段

#### Scenario: AI generates multi-field form
- **GIVEN** AI 需要收集用户多项信息
- **WHEN** AI 生成包含多个字段的 hitl_request
- **THEN** 表单 Schema 包含多个字段定义
- **AND** 每个字段包含 `name`, `type`, `label` 属性

#### Scenario: Schema validation on invalid format
- **GIVEN** AI 生成的 Schema 格式不正确
- **WHEN** 系统解析 hitl_request
- **THEN** 系统记录警告日志
- **AND** 降级为普通文本响应

### Requirement: HITL User Actions

系统 SHALL 支持三种用户操作响应 HITL 请求：approve、edit、reject。

#### Scenario: User approves HITL request
- **GIVEN** 前端显示 HITL 表单
- **WHEN** 用户填写表单并点击"确认"按钮
- **THEN** 系统发送 `action: approve` 到后端
- **AND** 后端处理表单数据并继续流程

#### Scenario: User edits and submits HITL request
- **GIVEN** 前端显示 HITL 表单
- **WHEN** 用户修改表单内容并点击"修改后提交"
- **THEN** 系统发送 `action: edit` 和修改后的数据到后端
- **AND** 后端使用修改后的数据继续流程

#### Scenario: User rejects HITL request
- **GIVEN** 前端显示 HITL 表单
- **WHEN** 用户点击"跳过"按钮
- **THEN** 系统发送 `action: reject` 到后端
- **AND** 后端跳过当前 HITL 请求继续对话

### Requirement: HITL Form Field Types

系统 SHALL 支持多种表单字段类型以覆盖常见输入场景。

#### Scenario: Render select field
- **GIVEN** Schema 包含 `type: select` 字段
- **WHEN** 前端渲染表单
- **THEN** 显示下拉选择框
- **AND** 选项来自 Schema 的 `options` 数组

#### Scenario: Render multiselect field
- **GIVEN** Schema 包含 `type: multiselect` 字段
- **WHEN** 前端渲染表单
- **THEN** 显示多选下拉框
- **AND** 用户可以选择多个选项

#### Scenario: Render text input field
- **GIVEN** Schema 包含 `type: text` 字段
- **WHEN** 前端渲染表单
- **THEN** 显示单行文本输入框

#### Scenario: Render textarea field
- **GIVEN** Schema 包含 `type: textarea` 字段
- **WHEN** 前端渲染表单
- **THEN** 显示多行文本输入框

#### Scenario: Render radio group field
- **GIVEN** Schema 包含 `type: radio` 字段
- **WHEN** 前端渲染表单
- **THEN** 显示单选按钮组

#### Scenario: Render checkbox group field
- **GIVEN** Schema 包含 `type: checkbox` 字段
- **WHEN** 前端渲染表单
- **THEN** 显示复选框组

#### Scenario: Render number input field
- **GIVEN** Schema 包含 `type: number` 字段
- **WHEN** 前端渲染表单
- **THEN** 显示数字输入框

#### Scenario: Render slider field
- **GIVEN** Schema 包含 `type: slider` 字段
- **WHEN** 前端渲染表单
- **THEN** 显示滑块选择器

### Requirement: HITL SSE Event

系统 SHALL 通过 SSE 事件通知前端 HITL 请求。

#### Scenario: Send HITL event via SSE
- **GIVEN** AI 响应包含 hitl_request
- **WHEN** 后端解析响应
- **THEN** 发送 `event: hitl` SSE 事件
- **AND** payload 包含完整的表单 Schema

#### Scenario: Frontend receives HITL event
- **GIVEN** 前端正在监听 SSE 事件
- **WHEN** 收到 `type: hitl` 事件
- **THEN** 暂停文本流显示
- **AND** 渲染 HITL 表单组件

### Requirement: HITL Response API

系统 SHALL 提供 API 端点处理用户对 HITL 请求的响应。

#### Scenario: Submit HITL response via API
- **GIVEN** 用户完成 HITL 表单操作
- **WHEN** 前端调用 `POST /hitl/respond`
- **THEN** 后端接收 request_id、session_id、action 和 data
- **AND** 返回处理结果和后续操作指示

#### Scenario: Handle expired HITL request
- **GIVEN** HITL 请求已超过 TTL（5 分钟）
- **WHEN** 用户提交响应
- **THEN** 后端返回错误信息
- **AND** 提示用户请求已过期

### Requirement: HITL Memory Integration

系统 SHALL 支持将 HITL 收集的数据保存到记忆系统。

#### Scenario: Save preference from HITL form
- **GIVEN** HITL 请求的 context.intent 为 `collect_preference`
- **WHEN** 用户 approve 表单
- **THEN** 系统将表单数据保存到长期记忆
- **AND** memory_category 来自 Schema 的 context.memory_category

#### Scenario: Skip memory save on reject
- **GIVEN** 用户 reject 了 HITL 请求
- **WHEN** 后端处理 reject action
- **THEN** 不保存任何数据到记忆系统
- **AND** 继续正常对话流程
