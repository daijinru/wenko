## ADDED Requirements

### Requirement: MCP Service Registration

系统 SHALL 允许用户注册新的 MCP 服务器配置。

每个 MCP 服务器配置 SHALL 包含以下信息：
- 唯一标识符 (自动生成的 UUID)
- 服务名称 (用户定义的显示名称)
- 启动命令 (如 `uvx`, `npx`, `python` 等)
- 命令参数列表
- 环境变量 (可选)
- 启用状态标志

#### Scenario: 成功注册新服务

- **GIVEN** 用户在 MCP 管理界面点击"添加服务"
- **WHEN** 用户填写有效的服务名称和启动命令
- **AND** 用户提交表单
- **THEN** 系统创建新的服务配置记录
- **AND** 服务出现在服务列表中，状态为"已停止"
- **AND** API 返回新创建服务的完整信息

#### Scenario: 注册失败 - 名称重复

- **GIVEN** 已存在名为"文件系统服务"的 MCP 服务
- **WHEN** 用户尝试注册另一个同名服务
- **THEN** 系统拒绝注册
- **AND** 返回错误信息提示名称已存在

---

### Requirement: MCP Service Lifecycle Management

系统 SHALL 提供 MCP 服务的启动、停止和重启功能。

#### Scenario: 启动服务

- **GIVEN** 存在一个状态为"已停止"的 MCP 服务
- **WHEN** 用户点击"启动"按钮
- **THEN** 系统使用配置的命令和参数启动子进程
- **AND** 服务状态变为"运行中"
- **AND** UI 实时显示状态更新

#### Scenario: 停止服务

- **GIVEN** 存在一个状态为"运行中"的 MCP 服务
- **WHEN** 用户点击"停止"按钮
- **THEN** 系统向子进程发送终止信号
- **AND** 服务状态变为"已停止"
- **AND** 进程资源被正确释放

#### Scenario: 启动失败处理

- **GIVEN** 存在一个配置了无效命令的 MCP 服务
- **WHEN** 用户尝试启动该服务
- **THEN** 系统捕获启动错误
- **AND** 服务状态变为"错误"
- **AND** 返回错误信息说明失败原因

#### Scenario: 重启服务

- **GIVEN** 存在一个状态为"运行中"的 MCP 服务
- **WHEN** 用户点击"重启"按钮
- **THEN** 系统先停止再启动该服务
- **AND** 服务状态最终为"运行中"

---

### Requirement: MCP Service Status Monitoring

系统 SHALL 监控并展示每个 MCP 服务的实时状态。

服务状态 SHALL 包括：
- `stopped` - 服务未运行
- `running` - 服务正常运行中
- `error` - 服务启动失败或异常退出

#### Scenario: 状态轮询更新

- **GIVEN** 用户打开 MCP 管理界面
- **WHEN** 界面加载完成
- **THEN** 系统立即获取所有服务的当前状态
- **AND** 每 5 秒自动刷新状态
- **AND** UI 显示每个服务的状态指示器

#### Scenario: 进程异常退出检测

- **GIVEN** 一个 MCP 服务正在运行
- **WHEN** 服务进程异常退出
- **THEN** 系统检测到进程终止
- **AND** 服务状态自动更新为"已停止"或"错误"

---

### Requirement: MCP Service Configuration Update

系统 SHALL 允许用户更新已注册服务的配置。

#### Scenario: 更新服务配置

- **GIVEN** 存在一个状态为"已停止"的 MCP 服务
- **WHEN** 用户修改服务名称或命令参数
- **AND** 用户保存更改
- **THEN** 系统更新数据库中的配置
- **AND** 更改立即生效

#### Scenario: 更新运行中的服务

- **GIVEN** 存在一个状态为"运行中"的 MCP 服务
- **WHEN** 用户尝试修改其配置
- **THEN** 系统提示需要先停止服务
- **OR** 系统自动重启服务以应用新配置

---

### Requirement: MCP Service Deletion

系统 SHALL 允许用户删除已注册的 MCP 服务。

#### Scenario: 删除已停止的服务

- **GIVEN** 存在一个状态为"已停止"的 MCP 服务
- **WHEN** 用户点击"删除"按钮并确认
- **THEN** 系统从数据库中移除服务配置
- **AND** 服务从列表中消失

#### Scenario: 删除运行中的服务

- **GIVEN** 存在一个状态为"运行中"的 MCP 服务
- **WHEN** 用户点击"删除"按钮并确认
- **THEN** 系统先停止服务进程
- **AND** 然后从数据库中移除配置
- **AND** 服务从列表中消失

---

### Requirement: MCP Management REST API

系统 SHALL 提供 RESTful API 用于程序化管理 MCP 服务。

#### Scenario: GET /api/mcp/servers - 获取服务列表

- **WHEN** 客户端发送 GET 请求到 `/api/mcp/servers`
- **THEN** 系统返回所有已注册服务的列表
- **AND** 每个服务包含配置信息和当前状态
- **AND** HTTP 状态码为 200

#### Scenario: POST /api/mcp/servers - 注册服务

- **WHEN** 客户端发送 POST 请求到 `/api/mcp/servers`
- **AND** 请求体包含有效的服务配置
- **THEN** 系统创建新服务并返回完整信息
- **AND** HTTP 状态码为 201

#### Scenario: POST /api/mcp/servers/{id}/start - 启动服务

- **WHEN** 客户端发送 POST 请求到 `/api/mcp/servers/{id}/start`
- **AND** 服务存在且当前为停止状态
- **THEN** 系统启动服务并返回更新后的状态
- **AND** HTTP 状态码为 200

#### Scenario: POST /api/mcp/servers/{id}/stop - 停止服务

- **WHEN** 客户端发送 POST 请求到 `/api/mcp/servers/{id}/stop`
- **AND** 服务存在且当前为运行状态
- **THEN** 系统停止服务并返回更新后的状态
- **AND** HTTP 状态码为 200

#### Scenario: DELETE /api/mcp/servers/{id} - 删除服务

- **WHEN** 客户端发送 DELETE 请求到 `/api/mcp/servers/{id}`
- **AND** 服务存在
- **THEN** 系统停止服务（如果运行中）并删除配置
- **AND** HTTP 状态码为 204

---

### Requirement: MCP Management UI Tab

Workflow 控制面板 SHALL 包含一个专用的 MCP 服务管理标签页。

#### Scenario: 显示 MCP 标签页

- **GIVEN** 用户打开 Workflow 控制面板
- **WHEN** 界面加载完成
- **THEN** 顶部标签栏显示"MCP 服务"选项
- **AND** 点击后显示 MCP 服务管理界面

#### Scenario: 服务列表展示

- **GIVEN** 用户在 MCP 标签页
- **WHEN** 存在已注册的 MCP 服务
- **THEN** 每个服务以卡片形式展示
- **AND** 卡片显示服务名称、命令、状态指示器
- **AND** 卡片包含操作按钮（启动/停止、编辑、删除）

#### Scenario: 添加服务对话框

- **GIVEN** 用户在 MCP 标签页
- **WHEN** 用户点击"添加服务"按钮
- **THEN** 弹出注册对话框
- **AND** 对话框包含服务名称、命令、参数、环境变量输入字段
- **AND** 用户可提交或取消操作

---

### Requirement: Application Shutdown Cleanup

系统 SHALL 在应用关闭时正确清理所有 MCP 服务进程。

#### Scenario: 正常关闭清理

- **GIVEN** 存在运行中的 MCP 服务
- **WHEN** FastAPI 应用收到 shutdown 信号
- **THEN** 系统向所有运行中的服务进程发送终止信号
- **AND** 等待进程退出（设置超时）
- **AND** 确保无孤儿进程残留
