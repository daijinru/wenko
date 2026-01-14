# Live2D AI Chat

Live2D 虚拟形象 AI 对话能力规范。

## ADDED Requirements

### Requirement: Chat Input Interface

系统 SHALL 在 Live2D 窗口提供对话输入界面。

#### Scenario: Display chat input bar
- **GIVEN** Live2D 窗口已启动
- **WHEN** 窗口渲染完成
- **THEN** 在窗口底部显示对话输入栏，包含文本输入框和发送按钮

#### Scenario: Send message via button
- **GIVEN** 用户在输入框中输入了文本
- **WHEN** 用户点击发送按钮
- **THEN** 消息被发送到后端，输入框清空

#### Scenario: Send message via Enter key
- **GIVEN** 用户在输入框中输入了文本
- **WHEN** 用户按下 Enter 键
- **THEN** 消息被发送到后端，输入框清空

#### Scenario: Disable input during loading
- **GIVEN** 用户已发送消息
- **WHEN** 等待 AI 响应中
- **THEN** 输入框和发送按钮被禁用，显示加载状态

### Requirement: AI Response Display

系统 SHALL 在 Live2D 消息气泡中展示 AI 对话响应。

#### Scenario: Display streaming response
- **GIVEN** 用户发送了对话消息
- **WHEN** 后端返回 SSE 流式响应
- **THEN** 响应内容实时追加显示在消息气泡中

#### Scenario: Auto scroll message bubble
- **GIVEN** 消息气泡中正在显示流式响应
- **WHEN** 新内容追加时
- **THEN** 消息气泡自动滚动到最新内容

#### Scenario: Show error message
- **GIVEN** 用户发送了对话消息
- **WHEN** 后端返回错误或连接失败
- **THEN** 在消息气泡中显示错误提示

### Requirement: Chat History Management

系统 SHALL 管理对话历史上下文。

#### Scenario: Maintain conversation context
- **GIVEN** 用户与 AI 进行了多轮对话
- **WHEN** 用户发送新消息时
- **THEN** 请求中包含之前的对话历史，AI 可以理解上下文

#### Scenario: Clear history on session end
- **GIVEN** 用户关闭 Live2D 窗口或 Electron 应用
- **WHEN** 会话结束
- **THEN** 对话历史被清除

#### Scenario: Limit history length
- **GIVEN** 对话历史超过 10 轮
- **WHEN** 用户发送新消息
- **THEN** 仅保留最近 10 轮对话历史，防止请求过大

### Requirement: Chat Backend API

系统 SHALL 提供 Chat API 接口与远程 LLM 交互。

#### Scenario: Stream chat response
- **GIVEN** Python 后端服务运行中
- **WHEN** 收到 POST /chat 请求
- **THEN** 通过 SSE 返回流式 AI 响应

#### Scenario: Connect to remote LLM API
- **GIVEN** 配置文件 `workflow/chat_config.json` 存在且有效
- **WHEN** 后端调用远程 LLM API
- **THEN** 成功获取 LLM 响应

#### Scenario: Handle API connection error
- **GIVEN** 远程 LLM API 无法访问
- **WHEN** 后端尝试调用 API
- **THEN** 返回错误事件，提示网络连接失败

#### Scenario: Handle missing config
- **GIVEN** 配置文件 `workflow/chat_config.json` 不存在
- **WHEN** 后端尝试处理 Chat 请求
- **THEN** 返回错误事件，提示用户创建配置文件

### Requirement: Chat Configuration

系统 SHALL 通过配置文件管理 LLM API 设置。

#### Scenario: Load config from file
- **GIVEN** 配置文件 `workflow/chat_config.json` 存在
- **WHEN** 后端启动或处理 Chat 请求
- **THEN** 读取配置文件中的 API 设置

#### Scenario: Config file git ignored
- **GIVEN** 用户创建 `workflow/chat_config.json` 配置文件
- **WHEN** 执行 git 操作
- **THEN** 该配置文件不被纳入版本控制

#### Scenario: Example config provided
- **GIVEN** 用户首次设置项目
- **WHEN** 查看 `workflow/chat_config.example.json`
- **THEN** 可以参考示例创建自己的配置文件
