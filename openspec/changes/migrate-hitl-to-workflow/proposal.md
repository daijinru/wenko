# Change: Migrate HITL to Electron New Window with IPC Communication

## Why

当前 HITL (Human-in-the-Loop) 界面实现在 Live2D Widget 的 `chat.ts` 中，存在以下问题：

1. **代码耦合严重**: HITL 表单逻辑（约 500 行）嵌入在 chat 模块中，与 Live2D 渲染紧密耦合
2. **样式不统一**: Live2D Widget 使用内联 CSS 样式，与 Workflow 的 Classic Mac OS 9 主题风格不一致
3. **缺乏可维护性**: 原生 DOM 操作难以维护，无法复用 Workflow 的 React 组件生态
4. **用户体验受限**: 在 Live2D 小窗口中显示表单，空间有限，交互不便

采用 Electron 新窗口方案可以获得：
- 独立的 HITL 窗口，提供更好的表单交互体验
- 统一的 Classic Mac OS 9 视觉风格
- 复用现有的 shadcn/ui 组件（Button、Dialog、Input、Checkbox、Slider 等）
- 利用 Electron IPC 机制实现可靠的跨窗口通讯
- 更好的代码组织和可维护性

## What Changes

### 1. Electron IPC 通讯机制

建立 Live2D 窗口与 HITL 窗口之间的 IPC 通讯系统：

```
┌─────────────────────────────────────────────────────────────────┐
│                     Electron IPC Architecture                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐                      ┌─────────────────┐
│    Live2D       │                      │   HITL Window   │
│  Main Window    │                      │  (New Window)   │
│                 │                      │                 │
│  chat.ts        │                      │  React App      │
│  ↓              │                      │  ↑              │
│  electronAPI    │                      │  electronAPI    │
│  .invoke()      │                      │  .on()          │
└────────┬────────┘                      └────────┬────────┘
         │                                        │
         │  ipcRenderer                           │  ipcRenderer
         │                                        │
         └──────────────┬─────────────────────────┘
                        │
                        ▼
              ┌──────────────────────┐
              │    Main Process      │
              │    (main.cjs)        │
              │                      │
              │  IPC Handlers:       │
              │  - hitl:open-window  │
              │  - hitl:submit       │
              │  - hitl:cancel       │
              └──────────────────────┘
```

### 2. HITL 独立窗口

创建独立的 HITL 窗口应用：

```
electron/src/renderer/hitl/
├── index.html          # HITL 窗口入口 HTML
├── main.tsx            # React 入口
├── App.tsx             # HITL 表单主组件
├── components/
│   ├── hitl-form.tsx   # 表单组件
│   └── hitl-field.tsx  # 字段渲染组件
├── hooks/
│   └── use-hitl.ts     # HITL 状态管理
└── styles/
    └── globals.css     # 样式（复用 workflow 样式）
```

### 3. IPC 消息流程

```
1. AI 返回 HITL 请求
   │
   ▼
2. Live2D chat.ts 调用 electronAPI.invoke('hitl:open-window', request)
   │
   ▼
3. Main Process 创建新 BrowserWindow，加载 HITL 页面
   │
   ▼
4. HITL 窗口显示表单，用户填写
   │
   ▼
5. 用户点击确认/跳过
   │
   ▼
6. HITL 窗口调用 electronAPI.invoke('hitl:submit', response)
   │
   ▼
7. Main Process 转发结果给 Live2D 窗口，关闭 HITL 窗口
   │
   ▼
8. Live2D 处理后续逻辑（continuation 等）
```

### 4. Live2D Chat 端简化

`chat.ts` 中的 HITL 相关代码简化为：
- 接收 SSE `hitl` 事件
- 通过 IPC 请求打开 HITL 窗口
- 监听 IPC 响应处理后续逻辑

### 5. 样式统一

HITL 窗口采用 Workflow 的 Classic Mac OS 9 主题：
- 使用 `window` 和 `title-bar` CSS 类
- 使用 `classic-stylesheets` 提供的按钮样式
- 复用现有的 shadcn/ui 组件

## Impact

- **Affected specs**:
  - `hitl-middleware` (修改前端实现)
  - `hitl-interaction` (修改 UI 渲染位置)

- **Affected code**:
  - `electron/main.cjs` - 新增 HITL IPC 处理器和窗口创建
  - `electron/preload.cjs` - 扩展 electronAPI
  - `electron/live2d/live2d-widget/src/chat.ts` - 简化 HITL 处理，改用 IPC
  - `electron/src/renderer/hitl/*` - 新增 HITL 窗口应用
  - `electron/vite.config.js` - 新增 HITL 入口配置

- **Breaking changes**: 无外部 API 变更，仅内部实现重构
