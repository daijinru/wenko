# Plan Reminder Window

## ADDED Requirements

### Requirement: Reminder Window Display

系统 SHALL 在计划到期时弹出独立的 Electron BrowserWindow 显示提醒内容。

提醒窗口 SHALL 包含以下信息：
- 计划标题
- 计划描述（如有）
- 目标时间
- 重复类型（如有）

提醒窗口 SHALL 提供以下操作按钮：
- 完成：标记计划为已完成
- 稍后提醒：延迟提醒（5分钟/15分钟/1小时可选）
- 取消：关闭提醒但不修改计划状态

#### Scenario: 计划到期时弹出提醒窗口
- **WHEN** 计划到达目标时间
- **AND** 用户启用了弹窗提醒 (`system.reminder_window_enabled = true`)
- **THEN** 系统弹出提醒窗口显示计划详情
- **AND** 窗口置于最前端 (always-on-top)

#### Scenario: 用户点击完成按钮
- **WHEN** 用户在提醒窗口中点击"完成"按钮
- **THEN** 系统调用 `/plans/{id}/complete` API
- **AND** 关闭提醒窗口
- **AND** 从待处理提醒列表中移除该计划

#### Scenario: 用户选择稍后提醒
- **WHEN** 用户在提醒窗口中点击"稍后提醒"按钮
- **AND** 选择延迟时间（5分钟/15分钟/1小时）
- **THEN** 系统调用 `/plans/{id}/snooze` API
- **AND** 关闭提醒窗口
- **AND** 在指定时间后再次触发提醒

#### Scenario: 用户点击取消按钮
- **WHEN** 用户在提醒窗口中点击"取消"按钮
- **THEN** 系统调用 `/plans/{id}/dismiss` API
- **AND** 关闭提醒窗口

### Requirement: Reminder Window Lifecycle

提醒窗口 SHALL 遵循以下生命周期规则。

#### Scenario: 窗口关闭视为取消
- **WHEN** 用户通过窗口控件（关闭按钮或 Cmd+W）关闭提醒窗口
- **THEN** 系统将此操作视为"取消"
- **AND** 调用 `/plans/{id}/dismiss` API

#### Scenario: 多个计划同时到期
- **WHEN** 多个计划在同一轮询周期内到期
- **THEN** 系统依次弹出提醒窗口（排队显示）
- **AND** 前一个窗口关闭后再显示下一个

### Requirement: Reminder Window IPC Communication

Electron main process 与 reminder renderer 之间 SHALL 通过 IPC 通信。

#### Scenario: 主进程发送提醒数据
- **WHEN** 检测到计划到期
- **THEN** 主进程通过 `reminder:data` channel 发送计划数据到提醒窗口

#### Scenario: 渲染进程发送操作结果
- **WHEN** 用户在提醒窗口中执行操作
- **THEN** 渲染进程通过 `reminder:action` channel 发送操作类型和数据到主进程
