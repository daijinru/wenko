# Tasks: Migrate HITL to Electron New Window

## Phase 1: Electron 基础设施

- [x] **1.1** 扩展 preload.cjs
  - 文件: `electron/preload.cjs`
  - 添加 `on(channel, callback)` 方法用于监听 IPC 消息
  - 添加 `once(channel, callback)` 方法用于一次性监听
  - 返回 unsubscribe 函数用于清理监听

- [x] **1.2** 实现 HITL IPC Handlers
  - 文件: `electron/main.cjs`
  - 添加 `ipcMain.handle('hitl:open-window', ...)` 处理器
  - 添加 `ipcMain.handle('hitl:submit', ...)` 处理器
  - 添加 `ipcMain.handle('hitl:cancel', ...)` 处理器
  - 实现 HITL 窗口单例管理

- [x] **1.3** 创建 HITL 窗口函数
  - 文件: `electron/main.cjs`
  - 实现 `createHITLWindow(request)` 函数
  - 配置窗口属性（尺寸、样式、父窗口）
  - 监听窗口 `close` 事件处理取消逻辑
  - 实现窗口 TTL 超时自动关闭

## Phase 2: Vite 构建配置

- [x] **2.1** 配置 HITL 入口
  - 文件: `electron/vite.config.js`
  - 添加 `hitl` 入口点: `src/renderer/hitl/main.tsx`
  - 配置输出到 `dist/hitl/`
  - 确保共享组件和样式正确打包

- [x] **2.2** 创建 HITL 入口 HTML
  - 文件: `electron/src/renderer/hitl/index.html`
  - 复用 workflow 的基础结构
  - 引入 main.tsx

## Phase 3: HITL React 组件

- [x] **3.1** 创建 HITL 类型定义
  - 文件: `electron/src/renderer/hitl/types/hitl.ts`
  - 定义 HITLRequest, HITLField, HITLOption 等类型
  - 定义 IPC 消息类型

- [x] **3.2** 实现 IPC 客户端封装
  - 文件: `electron/src/renderer/hitl/lib/ipc-client.ts`
  - 封装 `window.electronAPI` 调用
  - 提供类型安全的 HITL IPC 方法
  - 处理 IPC 通讯错误

- [x] **3.3** 实现 useHITLWindow hook
  - 文件: `electron/src/renderer/hitl/hooks/use-hitl-window.ts`
  - 监听 `hitl:request-data` 接收表单数据
  - 管理表单状态、字段数据、错误状态
  - 实现 submit 方法调用 IPC
  - 实现 cancel 方法

- [x] **3.4** 实现 HITLField 组件
  - 文件: `electron/src/renderer/hitl/components/hitl-field.tsx`
  - 根据 field.type 渲染对应的表单控件
  - 支持所有 10 种字段类型
  - 处理 required 标记和 placeholder
  - 复用 workflow 的 UI 组件

- [x] **3.5** 实现 HITLForm 组件
  - 文件: `electron/src/renderer/hitl/components/hitl-form.tsx`
  - 渲染标题、描述、字段列表
  - 应用 Classic Mac OS 9 窗口样式
  - 显示错误消息

- [x] **3.6** 实现 HITLActions 组件
  - 文件: `electron/src/renderer/hitl/components/hitl-actions.tsx`
  - 渲染确认/跳过按钮
  - 应用 Classic 按钮样式
  - 处理 loading 状态

- [x] **3.7** 实现 App.tsx
  - 文件: `electron/src/renderer/hitl/App.tsx`
  - 组合 HITLForm 和 HITLActions
  - 使用 useHITLWindow hook
  - 应用全局样式

- [x] **3.8** 创建 main.tsx 入口
  - 文件: `electron/src/renderer/hitl/main.tsx`
  - React 根组件渲染
  - 引入样式

- [x] **3.9** 配置样式
  - 文件: `electron/src/renderer/hitl/styles/globals.css`
  - 复用 workflow 的 globals.css
  - 引入 classic-stylesheets

## Phase 4: 集成 Live2D

- [x] **4.1** 修改 chat.ts 发送 IPC
  - 文件: `electron/live2d/live2d-widget/src/chat.ts`
  - 在 SSE hitl 事件处理中调用 `electronAPI.invoke('hitl:open-window', ...)`
  - 保留旧代码作为回退（非 Electron 环境）

- [x] **4.2** 实现 IPC 结果监听
  - 文件: `electron/live2d/live2d-widget/src/chat.ts`
  - 使用 `electronAPI.on('hitl:result', ...)` 监听结果
  - 处理成功/失败/取消/超时情况

- [x] **4.3** 处理 continuation 逻辑
  - 文件: `electron/live2d/live2d-widget/src/chat.ts`
  - 在收到 result 后检查 continuation_data
  - 调用 triggerHITLContinuation 继续对话
  - 处理链式 HITL 请求

- [x] **4.4** 更新 window.d.ts 类型定义
  - 文件: `electron/live2d/live2d-widget/src/types/window.d.ts`
  - 添加 `on` 和 `once` 方法类型

## Phase 5: 测试和验证

- [ ] **5.1** 端到端测试 HITL 流程
  - 验证 HITL 请求正确打开新窗口
  - 验证所有字段类型正确渲染和交互
  - 验证 Approve/Reject 操作正确处理
  - 验证窗口关闭视为取消
  - 验证 continuation 对话正确显示

- [ ] **5.2** 验证样式一致性
  - 确认窗口使用 Classic Mac OS 9 样式
  - 确认按钮使用 primary/secondary 样式
  - 确认字体、颜色、边框与 Workflow 一致

- [ ] **5.3** 验证窗口生命周期
  - 确认窗口单例管理正常
  - 确认 TTL 超时自动关闭
  - 确认父子窗口关系正确

## Phase 6: 清理和文档

- [ ] **6.1** 移除 chat.ts 中的旧 HITL UI 代码（可选，待验证后执行）
  - 移除 createHITLForm 函数
  - 移除 createHITLFormHtml 函数
  - 移除 bindHITLFormEvents 函数
  - 移除 showHITLError 函数
  - 保留 HITL 类型定义
  - 保留 submitHITLResponse 函数（可能移到 Main Process）

- [ ] **6.2** 更新 chat.ts 导出
  - 确保 public API 不变
  - 清理未使用的导入

- [x] **6.3** 重新构建 live2d-widget（待用户手动执行）
  - 运行 `cd electron/live2d/live2d-widget && npm run build` 生成新的 dist

## Dependencies

```
Phase 1 (基础设施)
    │
    ├── Phase 2 (Vite 配置) ──┐
    │                         │
    └── Phase 3 (React 组件) ─┼── Phase 4 (集成)
                              │       │
                              │       ▼
                              │  Phase 5 (测试)
                              │       │
                              │       ▼
                              └── Phase 6 (清理)
```

- Phase 2 和 Phase 3 可在 Phase 1 完成后并行进行
- Phase 4 依赖 Phase 1, 2, 3 全部完成
- Phase 5 依赖 Phase 4 完成
- Phase 6 依赖 Phase 5 测试通过

## Parallelization

可并行的任务：
- 1.1, 1.2, 1.3 可部分并行（preload 和 IPC handlers）
- 2.1 和 2.2 可并行
- 3.1, 3.2 可在 Phase 1 完成后并行
- 3.4, 3.5, 3.6 可并行（独立组件）
- 4.1, 4.2, 4.3 需串行（依赖关系）
- 5.1, 5.2, 5.3 可并行（独立测试场景）

需串行的任务：
- 1.x → 2.x, 3.x（基础设施先于组件）
- 3.1 → 3.3 → 3.7 → 3.8（类型 → hook → App → 入口）
- Phase 4 → Phase 5 → Phase 6（集成 → 测试 → 清理）

## Implementation Notes

### 已完成的变更文件：

1. **electron/preload.cjs** - 新增 `on()` 和 `once()` IPC 监听方法
2. **electron/main.cjs** - 新增 HITL 窗口管理和 IPC handlers
3. **electron/vite.config.js** - 配置多入口构建（workflow + hitl）
4. **electron/src/renderer/hitl/** - 全新的 HITL React 应用
   - index.html
   - main.tsx
   - App.tsx
   - components/hitl-field.tsx
   - components/hitl-form.tsx
   - components/hitl-actions.tsx
   - hooks/use-hitl-window.ts
   - lib/ipc-client.ts
   - lib/utils.ts
   - types/hitl.ts
   - styles/globals.css
5. **electron/live2d/live2d-widget/src/chat.ts** - 修改 HITL 处理使用 IPC
6. **electron/live2d/live2d-widget/src/types/window.d.ts** - 更新 electronAPI 类型

### 构建步骤：

```bash
# 1. 构建 HITL 和 Workflow 应用
cd electron && npm run build

# 2. 重新构建 live2d-widget
cd electron/live2d/live2d-widget && npm run build

# 3. 启动应用
cd electron && npm run start
```
