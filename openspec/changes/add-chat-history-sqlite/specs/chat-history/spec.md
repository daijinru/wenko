## ADDED Requirements

### Requirement: Chat History SQLite Persistence
系统 SHALL 使用 SQLite 数据库持久化存储 Live2D AI 对话记录。

#### Scenario: Database auto-initialization
- **WHEN** Python 后端服务启动
- **THEN** 自动创建 `workflow/data/` 目录（如不存在）
- **AND** 自动创建 `chat_history.db` 数据库文件和表结构

#### Scenario: Save chat message
- **WHEN** 用户发送消息且提供 session_id
- **THEN** 用户消息和 AI 响应 SHALL 保存到数据库
- **AND** 消息关联到对应的 session

#### Scenario: Database portability
- **WHEN** 用户将 `workflow/data/` 目录复制到另一台机器
- **THEN** 应用 SHALL 能正常读取和使用已有的聊天记录
- **AND** 无需修改任何配置

### Requirement: Chat History REST API
系统 SHALL 提供 REST API 用于查询和管理聊天记录。

#### Scenario: List chat sessions
- **WHEN** 客户端请求 `GET /chat/history`
- **THEN** 返回所有会话列表
- **AND** 按 updated_at 降序排列
- **AND** 包含每个会话的消息数量

#### Scenario: Get session messages
- **WHEN** 客户端请求 `GET /chat/history/{session_id}`
- **THEN** 返回该会话的所有消息
- **AND** 按 created_at 升序排列

#### Scenario: Delete single session
- **WHEN** 客户端请求 `DELETE /chat/history/{session_id}`
- **THEN** 删除该会话及其所有关联消息
- **AND** 返回成功状态

#### Scenario: Clear all history
- **WHEN** 客户端请求 `DELETE /chat/history`
- **THEN** 删除所有会话和消息
- **AND** 返回删除的会话数量

### Requirement: Session Management
前端 SHALL 管理对话会话标识，支持会话持久化和新建。

#### Scenario: Persistent session ID
- **WHEN** 用户在 Live2D 窗口发起对话
- **THEN** session_id SHALL 存储在 localStorage
- **AND** 页面刷新后保持同一会话

#### Scenario: Create new session
- **WHEN** 用户点击"新建会话"按钮
- **THEN** 生成新的 session_id
- **AND** 后续消息关联到新会话

### Requirement: Chat History UI in Workflow
Workflow 管理界面 SHALL 提供聊天记录查看和管理功能。

#### Scenario: Display chat sessions list
- **WHEN** 用户切换到"聊天记录"标签页
- **THEN** 显示所有会话列表
- **AND** 每个会话显示标题、时间、消息数

#### Scenario: View session detail
- **WHEN** 用户点击某个会话
- **THEN** 显示该会话的消息时间线
- **AND** 区分用户消息和 AI 响应

#### Scenario: Delete session from UI
- **WHEN** 用户点击删除会话按钮
- **THEN** 显示确认弹窗
- **AND** 确认后删除会话并刷新列表
