## ADDED Requirements

### Requirement: HITL Continuation

当用户响应 HITL 表单后（无论 approve 或 reject），系统 SHALL **自动**将响应传递给 AI，使 AI 能够继续对话。

#### Scenario: User approves HITL form and AI continues automatically

- **WHEN** 用户点击"确认"提交 HITL 表单
- **THEN** 系统**自动**触发 AI 继续对话（无需用户额外操作）
- **AND** AI 的响应显示在聊天界面中
- **AND** 对话可以继续进行

#### Scenario: User rejects HITL form and AI continues automatically

- **WHEN** 用户点击"跳过"拒绝 HITL 表单
- **THEN** 系统**自动**触发 AI 继续对话（与 approve 行为一致）
- **AND** AI 收到用户拒绝的信息
- **AND** AI 根据用户的拒绝行为做出适当响应（如换一种方式提问、跳过该话题等）

### Requirement: HITL Chain Support

系统 SHALL 支持 AI 在继续对话中发起新的 HITL 请求，形成交互链。

#### Scenario: AI initiates follow-up HITL after continuation

- **WHEN** AI 在继续对话中返回新的 HITL 请求
- **THEN** 系统渲染新的 HITL 表单
- **AND** 用户可以响应新的表单
- **AND** 循环继续直到 AI 不再发起 HITL 请求

#### Scenario: HITL chain depth limit

- **WHEN** HITL 链深度超过系统限制（默认 5 层）
- **THEN** 系统停止发起新的 HITL 请求
- **AND** AI 的文本响应正常显示

### Requirement: HITL Continuation API

系统 SHALL 提供 `/hitl/continue` SSE 端点，用于触发 AI 基于 HITL 响应的继续对话。

#### Scenario: Continuation endpoint returns streamed response

- **WHEN** 前端调用 `/hitl/continue` 端点
- **THEN** 系统返回 SSE 流式响应
- **AND** 响应格式与 `/chat` 端点一致（text, emotion, hitl, done 事件）

#### Scenario: Continuation with form data context

- **WHEN** 调用 `/hitl/continue` 并传递用户表单数据
- **THEN** AI 收到包含用户响应的上下文信息
- **AND** AI 能够引用用户选择的具体内容
