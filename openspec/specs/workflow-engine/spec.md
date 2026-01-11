# Workflow Engine

工作流执行引擎核心能力规范。

## Requirements

### Requirement: Workflow Execution

系统 SHALL 接收并执行包含步骤列表的工作流定义。

#### Scenario: Execute simple workflow
- **GIVEN** 一个包含多个步骤的工作流定义
- **WHEN** 用户调用 `/run` 端点
- **THEN** 系统按顺序执行每个步骤并返回执行结果

#### Scenario: Execute workflow with initial input
- **GIVEN** 工作流定义和初始输入数据
- **WHEN** 请求包含 `initial_input` 字段
- **THEN** 初始输入被设置为第一个步骤的输入

### Requirement: Step Registry

系统 SHALL 维护一个步骤注册表，记录所有可用的步骤类型。

#### Scenario: List available steps
- **GIVEN** 系统已启动
- **WHEN** 用户调用 `/steps` 端点
- **THEN** 返回所有已注册步骤类型的列表

#### Scenario: Register new step type
- **GIVEN** 一个新的步骤处理函数
- **WHEN** 使用 `step_registry.register()` 注册
- **THEN** 新步骤类型可在工作流中使用

### Requirement: Context Management

系统 SHALL 在工作流执行期间维护共享上下文。

#### Scenario: Share data between steps
- **GIVEN** 步骤 A 设置变量 `foo`
- **WHEN** 后续步骤 B 读取变量 `foo`
- **THEN** 步骤 B 能获取步骤 A 设置的值

#### Scenario: Set step output to variable
- **GIVEN** 步骤配置包含 `output_var` 字段
- **WHEN** 步骤执行完成
- **THEN** 步骤输出存储到指定变量名

### Requirement: Conditional Execution

系统 SHALL 支持基于条件的分支执行。

#### Scenario: Execute then branch when condition is true
- **GIVEN** 条件块定义: `{ "if": { "var": "flag", "equals": true }, "then": [...], "else": [...] }`
- **WHEN** 上下文中 `flag` 值为 `true`
- **THEN** 执行 `then` 分支的步骤

#### Scenario: Execute else branch when condition is false
- **GIVEN** 条件块定义: `{ "if": { "var": "flag", "equals": true }, "then": [...], "else": [...] }`
- **WHEN** 上下文中 `flag` 值为 `false`
- **THEN** 执行 `else` 分支的步骤

### Requirement: Error Handling

系统 SHALL 在步骤执行失败时提供清晰的错误信息。

#### Scenario: Unknown step type
- **GIVEN** 工作流包含未注册的步骤类型
- **WHEN** 执行该步骤
- **THEN** 返回包含未知步骤类型的错误信息

#### Scenario: Step execution error
- **GIVEN** 步骤执行过程中发生异常
- **WHEN** 异常被捕获
- **THEN** 返回包含错误详情的响应

### Requirement: Health Check

系统 SHALL 提供健康检查端点。

#### Scenario: Service health check
- **GIVEN** 服务正在运行
- **WHEN** 调用 `/health` 端点
- **THEN** 返回 `{ "status": "ok" }`
