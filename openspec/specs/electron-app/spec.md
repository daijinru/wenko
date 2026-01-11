# Electron Application

Electron 桌面应用能力规范。

## Requirements

### Requirement: Application Window Management

系统 SHALL 提供桌面应用窗口管理能力。

#### Scenario: Launch main window
- **GIVEN** 用户启动应用
- **WHEN** 应用初始化完成
- **THEN** 显示主应用窗口

#### Scenario: Launch Live2D window
- **GIVEN** 用户启动应用
- **WHEN** 启用 Live2D 功能
- **THEN** 显示透明的 Live2D 虚拟形象窗口

### Requirement: Workflow API Test Interface

系统 SHALL 提供工作流 API 测试界面。

#### Scenario: Test workflow execution
- **GIVEN** 用户在测试界面输入工作流 JSON
- **WHEN** 点击执行按钮
- **THEN** 调用后端 `/run` 接口并显示结果

#### Scenario: View available steps
- **GIVEN** 用户打开测试界面
- **WHEN** 查看步骤注册表
- **THEN** 显示所有可用步骤类型列表

### Requirement: Template Management UI

系统 SHALL 提供模板管理用户界面。

#### Scenario: Create template from UI
- **GIVEN** 用户在模板管理界面填写模板信息
- **WHEN** 点击创建按钮
- **THEN** 模板被保存并显示在列表中

#### Scenario: Edit existing template
- **GIVEN** 用户选择一个已有模板
- **WHEN** 修改并保存
- **THEN** 模板更新成功

#### Scenario: Delete template from UI
- **GIVEN** 用户选择一个模板
- **WHEN** 点击删除并确认
- **THEN** 模板被删除并从列表移除

#### Scenario: Search templates
- **GIVEN** 用户在搜索框输入关键词
- **WHEN** 触发搜索
- **THEN** 显示匹配的模板列表

### Requirement: Live2D Integration

系统 SHALL 集成 Live2D 虚拟形象显示。

#### Scenario: Display Live2D model
- **GIVEN** Live2D 模型文件存在于 `/public/live2d/`
- **WHEN** 启动 Live2D 窗口
- **THEN** 正确渲染虚拟形象

#### Scenario: Transparent window
- **GIVEN** Live2D 窗口启动
- **WHEN** 渲染完成
- **THEN** 窗口背景透明，仅显示虚拟形象

### Requirement: Backend Connection

系统 SHALL 与 Python 后端服务通信。

#### Scenario: Connect to backend
- **GIVEN** Python 后端服务运行在 `localhost:8080`
- **WHEN** 前端发起请求
- **THEN** 成功与后端通信

#### Scenario: Handle backend offline
- **GIVEN** Python 后端服务未启动
- **WHEN** 前端尝试连接
- **THEN** 显示连接错误提示

#### Scenario: Health check status
- **GIVEN** 用户查看服务状态
- **WHEN** 后端服务正常运行
- **THEN** 显示绿色健康状态指示

### Requirement: Static File Server

系统 SHALL 提供静态文件服务能力。

#### Scenario: Serve Live2D assets
- **GIVEN** 静态服务器启动
- **WHEN** 请求 Live2D 资源文件
- **THEN** 正确返回资源内容

#### Scenario: Express server integration
- **GIVEN** Electron 主进程
- **WHEN** 应用启动
- **THEN** 内嵌 Express 静态服务器启动
