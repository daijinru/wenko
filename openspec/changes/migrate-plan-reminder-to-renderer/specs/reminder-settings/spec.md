# Reminder Settings

## ADDED Requirements

### Requirement: Reminder Window Toggle

系统 SHALL 在 Settings 面板中提供弹窗提醒开关。

配置项：`system.reminder_window_enabled`
- 类型：boolean
- 默认值：true
- 说明：启用后，计划到期时弹出独立窗口提醒用户

#### Scenario: 启用弹窗提醒
- **WHEN** 用户在 Settings 中开启"弹窗提醒"开关
- **THEN** 系统保存 `system.reminder_window_enabled = true`
- **AND** 后续计划到期时将弹出提醒窗口

#### Scenario: 禁用弹窗提醒
- **WHEN** 用户在 Settings 中关闭"弹窗提醒"开关
- **THEN** 系统保存 `system.reminder_window_enabled = false`
- **AND** 后续计划到期时不弹出提醒窗口

### Requirement: OS Notification Toggle

系统 SHALL 在 Settings 面板中提供系统通知开关。

配置项：`system.os_notification_enabled`
- 类型：boolean
- 默认值：true
- 说明：启用后，计划到期时发送操作系统通知

#### Scenario: 启用系统通知
- **WHEN** 用户在 Settings 中开启"系统通知"开关
- **THEN** 系统保存 `system.os_notification_enabled = true`
- **AND** 后续计划到期时将发送系统通知

#### Scenario: 禁用系统通知
- **WHEN** 用户在 Settings 中关闭"系统通知"开关
- **THEN** 系统保存 `system.os_notification_enabled = false`
- **AND** 后续计划到期时不发送系统通知

### Requirement: Settings UI Integration

提醒设置 SHALL 在 Settings 面板的"系统功能开关"选项卡中显示。

#### Scenario: 设置界面展示
- **WHEN** 用户打开 Settings 面板的"系统功能开关"选项卡
- **THEN** 显示"弹窗提醒"开关及说明
- **AND** 显示"系统通知"开关及说明
- **AND** 两个开关独立控制，可以单独开启/关闭

### Requirement: Settings API Extension

后端 Settings API SHALL 支持新增的提醒配置项。

#### Scenario: 获取提醒设置
- **WHEN** 客户端请求 `GET /api/settings`
- **THEN** 响应中包含 `system.reminder_window_enabled` 和 `system.os_notification_enabled` 字段

#### Scenario: 更新提醒设置
- **WHEN** 客户端请求 `PUT /api/settings` 更新提醒配置
- **THEN** 系统保存新的配置值到数据库
- **AND** 返回成功响应
