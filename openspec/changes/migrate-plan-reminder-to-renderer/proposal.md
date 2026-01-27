# Change: Migrate Plan Reminder to Electron Renderer Window

## Why

当前计划提醒功能在 Live2D widget (`electron/live2d/live2d-widget/src/chat.ts`) 中实现，存在以下问题：
1. **代码冗余**: Live2D 和 Electron renderer 都有提醒相关代码
2. **用户体验受限**: 提醒显示在 Live2D 气泡中，可能被用户忽略
3. **功能缺失**: 没有操作系统级别的通知集成（如 macOS 通知中心）
4. **配置不灵活**: 用户无法控制提醒方式

需要将提醒功能迁移到独立的 Electron 窗口，集成操作系统通知，并在 Settings 面板中添加提醒开关。

## What Changes

### 新增功能
- **Electron 提醒窗口**: 创建独立的 Electron BrowserWindow 用于展示计划提醒
- **操作系统通知集成**: 使用 Electron Notification API 发送系统通知
- **Settings 提醒开关**: 在系统功能开关中添加提醒相关配置项
  - `system.reminder_window_enabled` - 启用弹窗提醒
  - `system.os_notification_enabled` - 启用系统通知

### 代码清理
- **删除 Live2D 提醒代码**: 移除 `chat.ts` 中的 `PlanReminder` 相关代码（约 220 行）

### 修改现有逻辑
- **main.cjs 轮询逻辑**: 根据设置决定触发弹窗还是系统通知
- **preload.cjs**: 添加新的 IPC channel 用于提醒窗口

## Impact

- Affected specs: 新增 `plan-reminder-window`, `os-notification`, `reminder-settings`
- Affected code:
  - `electron/main.cjs` - 修改轮询逻辑，添加弹窗和通知触发
  - `electron/preload.cjs` - 添加提醒窗口相关 IPC channel
  - `electron/src/renderer/reminder/` - 新增提醒窗口 React 组件
  - `electron/live2d/live2d-widget/src/chat.ts` - 删除 PlanReminder 代码
  - `electron/src/renderer/workflow/components/features/settings/system-config-section.tsx` - 添加提醒开关
  - `electron/src/renderer/workflow/hooks/use-settings.ts` - 扩展 Settings 类型
  - `workflow/main.py` - 添加提醒设置到 Settings API
