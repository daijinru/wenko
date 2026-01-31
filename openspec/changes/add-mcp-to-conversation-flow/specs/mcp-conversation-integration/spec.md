## ADDED Requirements

### Requirement: MCP Tool Discovery

系统 SHALL 提供已注册 MCP 服务的工具发现能力，以便在对话中使用。

#### Scenario: 获取可用工具列表
- **WHEN** 对话流程开始构建 prompt
- **AND** 存在已注册且状态为 running 的 MCP 服务
- **THEN** 系统返回可用工具的描述信息列表

#### Scenario: 服务未运行时不可用
- **WHEN** 对话流程查询可用工具
- **AND** MCP 服务已注册但状态为 stopped 或 error
- **THEN** 该服务的工具不出现在可用列表中

---

### Requirement: MCP Intent Recognition

系统 SHALL 在意图识别流程中支持 MCP 工具调用意图的识别。

#### Scenario: 显式工具调用识别
- **WHEN** 用户消息包含"用 xxx 工具"、"调用 xxx"等显式调用模式
- **THEN** 系统识别为 MCP 意图
- **AND** 提取工具名称到意图结果中

#### Scenario: 关键词触发识别
- **WHEN** 用户消息匹配某 MCP 服务配置的 trigger_keywords
- **THEN** 系统识别为 MCP 意图
- **AND** 关联对应的 MCP 服务

#### Scenario: 无匹配时继续原有流程
- **WHEN** 用户消息不匹配任何 MCP 相关模式
- **THEN** 系统继续执行原有的 Memory/HITL/Normal 意图识别流程

---

### Requirement: MCP Tool Description Injection

系统 SHALL 根据意图识别结果，分层注入工具描述到 prompt 中以优化 token 使用。

#### Scenario: MCP 意图匹配时注入简短描述
- **WHEN** 意图识别结果为 MCP 类型
- **THEN** 系统在 prompt 中注入匹配工具的 Level 1 描述（工具名 + 一句话描述）
- **AND** 不注入完整的工具 Schema

#### Scenario: 无 MCP 意图时不注入
- **WHEN** 意图识别结果为非 MCP 类型（Memory/HITL/Normal）
- **THEN** 系统不在 prompt 中注入任何 MCP 工具描述

---

### Requirement: MCP Tool Execution

系统 SHALL 支持执行 LLM 返回的 MCP 工具调用请求。

#### Scenario: 成功执行工具调用
- **WHEN** LLM 响应包含 tool_call 字段
- **AND** 工具对应的 MCP 服务正在运行
- **THEN** 系统通过 stdio 向 MCP 服务发送调用请求
- **AND** 将工具返回结果注入到对话上下文

#### Scenario: 服务不可用时的友好提示
- **WHEN** LLM 请求调用某个工具
- **AND** 对应的 MCP 服务未运行
- **THEN** 系统返回友好的错误提示
- **AND** 不中断对话流程

#### Scenario: 工具调用超时处理
- **WHEN** MCP 工具调用超过配置的超时时间
- **THEN** 系统终止调用并返回超时提示
- **AND** 将超时信息注入到对话上下文继续对话

---

### Requirement: MCP Service Configuration Extension

系统 SHALL 扩展 MCP 服务配置，支持工具描述和触发关键词。

#### Scenario: 配置工具描述
- **WHEN** 用户注册或更新 MCP 服务
- **THEN** 用户可以提供 description 字段（可选）
- **AND** 该描述用于 prompt 中的工具说明

#### Scenario: 配置触发关键词
- **WHEN** 用户注册或更新 MCP 服务
- **THEN** 用户可以提供 trigger_keywords 列表（可选）
- **AND** 这些关键词用于 Layer 1 意图识别

#### Scenario: 默认值兼容
- **WHEN** MCP 服务配置未提供 description 或 trigger_keywords
- **THEN** 系统使用服务名称作为默认描述
- **AND** 触发关键词列表为空（仅通过显式调用触发）

---

### Requirement: MCP Tool Call Response Format

系统 SHALL 定义 LLM 输出中工具调用的标准格式。

#### Scenario: 工具调用请求格式
- **WHEN** LLM 决定调用 MCP 工具
- **THEN** LLM 在 JSON 响应中包含 tool_call 字段
- **AND** tool_call 包含 name（工具名）和 arguments（参数对象）

#### Scenario: 工具调用结果注入格式
- **WHEN** MCP 工具执行完成并返回结果
- **THEN** 系统以 role="tool" 的消息格式注入结果
- **AND** 包含 name（工具名）和 content（结果内容）
