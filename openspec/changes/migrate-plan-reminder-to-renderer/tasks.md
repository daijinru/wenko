# Tasks: Migrate Plan Reminder to Electron Renderer Window

## 1. Backend - Settings API Extension

- [x] 1.1 在 `workflow/chat_db.py` 的 `_DEFAULT_SETTINGS` 中添加 `system.reminder_window_enabled` (默认 true)
- [x] 1.2 在 `workflow/chat_db.py` 的 `_DEFAULT_SETTINGS` 中添加 `system.os_notification_enabled` (默认 true)

## 2. Frontend - Settings UI

- [x] 2.1 更新 `use-settings.ts` 的 `Settings` 类型，添加新配置项
- [x] 2.2 在 `system-config-section.tsx` 中添加"弹窗提醒"开关
- [x] 2.3 在 `system-config-section.tsx` 中添加"系统通知"开关

## 3. Electron - Reminder Window

- [x] 3.1 创建 `electron/src/renderer/reminder/` 目录结构 (index.html, main.tsx, App.tsx, styles/)
- [x] 3.2 创建 `ReminderWindow` React 组件，显示计划详情和操作按钮
- [x] 3.3 实现稍后提醒的时间选择 UI (5分钟/15分钟/1小时)
- [x] 3.4 配置 Vite 构建输出到 `dist/src/renderer/reminder/`

## 4. Electron - IPC Handlers

- [x] 4.1 preload.cjs 已有通用 IPC 方法 (send, invoke, on)，无需额外添加
- [x] 4.2 在 `main.cjs` 中添加 `createReminderWindow()` 函数
- [x] 4.3 在 `main.cjs` 中添加 `ipcMain.handle('reminder:complete')` 处理器
- [x] 4.4 在 `main.cjs` 中添加 `ipcMain.handle('reminder:snooze')` 处理器
- [x] 4.5 在 `main.cjs` 中添加 `ipcMain.handle('reminder:dismiss')` 处理器

## 5. Electron - OS Notification

- [x] 5.1 在 `main.cjs` 中添加 `showOSNotification(plan)` 函数
- [x] 5.2 实现通知点击回调，打开提醒窗口

## 6. Electron - 轮询逻辑修改

- [x] 6.1 修改 `pollDuePlans()` 函数，调用 Settings API 获取用户偏好
- [x] 6.2 根据 `system.reminder_window_enabled` 决定是否创建提醒窗口
- [x] 6.3 根据 `system.os_notification_enabled` 决定是否发送系统通知
- [x] 6.4 实现提醒排队机制（多个计划同时到期时依次显示）

## 7. Code Cleanup - 删除 Live2D 提醒代码

- [x] 7.1 删除 `chat.ts` 中的 `PlanReminder` interface
- [x] 7.2 删除 `chat.ts` 中的 `currentPlanReminder` 变量
- [x] 7.3 删除 `chat.ts` 中的 `setupPlanReminderListener()` 函数
- [x] 7.4 删除 `chat.ts` 中的 `showPlanReminder()` 函数
- [x] 7.5 删除 `chat.ts` 中的 `bindPlanReminderEvents()` 函数
- [x] 7.6 删除 `chat.ts` 中的 `showSnoozeOptions()` 函数
- [x] 7.7 删除 `chat.ts` 中的 `getCurrentPlanReminder()` 导出函数
- [x] 7.8 删除 `chat.ts` 模块加载时的 `setupPlanReminderListener()` 调用
- [x] 7.9 main.cjs 轮询逻辑已修改为使用新的 Reminder Window，不再发送 `plan:reminder` 到 Live2D

## 8. Testing and Validation

- [ ] 8.1 测试提醒窗口弹出和操作（完成/稍后/取消）
- [ ] 8.2 测试系统通知发送（macOS）
- [ ] 8.3 测试通知点击打开提醒窗口
- [ ] 8.4 测试 Settings 开关功能（单独开启/关闭各项）
- [ ] 8.5 测试多个计划同时到期的排队显示
- [ ] 8.6 验证 Live2D 提醒代码已完全移除且不影响其他功能
