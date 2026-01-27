# OS Notification

## ADDED Requirements

### Requirement: System Notification Integration

系统 SHALL 使用 Electron Notification API 发送操作系统级别的通知。

#### Scenario: 发送系统通知
- **WHEN** 计划到达目标时间
- **AND** 用户启用了系统通知 (`system.os_notification_enabled = true`)
- **THEN** 系统发送操作系统通知
- **AND** 通知标题为"计划提醒"
- **AND** 通知内容为计划标题

#### Scenario: 点击系统通知打开提醒窗口
- **WHEN** 用户点击系统通知
- **AND** 用户启用了弹窗提醒 (`system.reminder_window_enabled = true`)
- **THEN** 系统弹出提醒窗口显示计划详情

#### Scenario: 仅系统通知模式
- **WHEN** 用户启用了系统通知 (`system.os_notification_enabled = true`)
- **AND** 用户禁用了弹窗提醒 (`system.reminder_window_enabled = false`)
- **THEN** 系统仅发送系统通知
- **AND** 点击通知不触发任何动作

### Requirement: Notification Cross-Platform Support

系统通知功能 SHALL 支持 macOS 和 Windows 平台。

#### Scenario: macOS 通知
- **WHEN** 应用运行在 macOS 系统上
- **THEN** 通知显示在 macOS 通知中心

#### Scenario: Windows 通知
- **WHEN** 应用运行在 Windows 系统上
- **THEN** 通知显示在 Windows 操作中心
