# Design: Migrate Plan Reminder to Electron Renderer Window

## Context

当前系统已有计划提醒功能，实现分布在两处：
1. **Electron main.cjs**: 轮询后端 `/plans/due` API，通过 IPC 发送 `plan:reminder` 事件
2. **Live2D chat.ts**: 监听 `plan:reminder` 事件，在 Live2D 气泡中显示提醒 UI

问题：
- Live2D 气泡可能被用户忽略（窗口小、位置固定）
- 缺少操作系统级通知（用户可能不在电脑前时错过提醒）
- 代码分散在 Live2D widget 中，维护困难

## Goals / Non-Goals

**Goals:**
- 创建独立的 Electron 提醒窗口，提供更醒目的提醒体验
- 集成操作系统通知（macOS/Windows 通知中心）
- 允许用户在 Settings 中配置提醒方式
- 删除 Live2D 中的冗余提醒代码

**Non-Goals:**
- 不修改后端 Plans API
- 不修改计划创建/编辑流程
- 不添加声音提醒（可作为后续增强）

## Decisions

### Decision 1: 提醒窗口架构

**选择**: 创建新的 Electron BrowserWindow 用于显示提醒

**理由**:
- 与 HITL 窗口 / Image Preview 窗口架构一致
- 可以控制窗口大小、位置、always-on-top 等属性
- 使用 React 组件，与现有技术栈一致

**替代方案**:
- 在 Workflow 面板中显示：用户可能不会打开 Workflow 面板
- 使用 Electron dialog：过于简陋，交互能力有限

### Decision 2: 操作系统通知实现

**选择**: 使用 Electron Notification API

**理由**:
- Electron 内置支持，无需额外依赖
- 跨平台（macOS/Windows/Linux）
- 支持点击回调，可以打开提醒窗口

**实现**:
```javascript
const { Notification } = require('electron');

function showOSNotification(plan) {
  const notification = new Notification({
    title: '计划提醒',
    body: plan.title,
    silent: false,
  });

  notification.on('click', () => {
    // 打开提醒窗口
    createReminderWindow(plan);
  });

  notification.show();
}
```

### Decision 3: 提醒触发策略

**选择**: 根据用户设置组合触发

| 设置 | 行为 |
|------|------|
| 弹窗 + 通知都开启 | 先发系统通知，用户点击后打开弹窗 |
| 仅弹窗开启 | 直接弹出提醒窗口 |
| 仅通知开启 | 仅发送系统通知（点击无动作） |
| 都关闭 | 不触发提醒 |

### Decision 4: Settings 存储

**选择**: 复用现有 Settings API，添加新的配置项

新增配置项：
- `system.reminder_window_enabled` (boolean, default: true)
- `system.os_notification_enabled` (boolean, default: true)

## Data Flow

```
1. Electron main.cjs 轮询 /plans/due API
2. 发现到期计划时：
   a. 读取 Settings API 获取用户偏好
   b. 根据设置决定触发方式：
      - system.reminder_window_enabled → 创建 Reminder Window
      - system.os_notification_enabled → 发送系统通知
3. Reminder Window 显示计划详情和操作按钮
4. 用户操作（完成/稍后/取消）通过 IPC 传回 main process
5. main process 调用 Plans API 更新状态
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 用户可能觉得弹窗打扰 | 默认开启但可在 Settings 关闭 |
| macOS 通知权限问题 | Electron 会自动处理权限请求 |
| 多个计划同时到期 | 合并显示或排队显示（v1 先排队） |

## Migration Plan

1. **Phase 1**: 创建新的提醒窗口和 OS 通知功能
2. **Phase 2**: 添加 Settings 开关
3. **Phase 3**: 修改 main.cjs 轮询逻辑使用新触发方式
4. **Phase 4**: 删除 Live2D 中的 PlanReminder 代码
5. **Phase 5**: 测试验证

无需数据迁移，配置项使用默认值。

## Open Questions

1. ~~是否需要支持声音提醒？~~ → 暂不支持，后续可增强
2. ~~多个计划同时到期时如何处理？~~ → v1 排队显示，后续可优化为合并
