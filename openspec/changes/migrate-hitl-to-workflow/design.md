# HITL Migration Design - Electron New Window Architecture

## Context

Wenko 是一个情感记忆 AI 系统，其 Electron 客户端由以下部分组成：

1. **Main Process** (`main.cjs`): Electron 主进程，管理窗口和 IPC
2. **Live2D Window**: 主窗口，显示 Live2D 虚拟形象和聊天界面
3. **Workflow Window**: 通过快捷键打开的窗口，提供聊天历史和记忆管理

当前 HITL 表单直接在 Live2D Widget 的 `chat.ts` 中用原生 DOM 渲染。本设计将 HITL 迁移到独立的 Electron 窗口，通过 IPC 与 Live2D 通讯。

## Goals / Non-Goals

### Goals

- 建立基于 Electron IPC 的跨窗口通讯机制
- HITL 表单在独立窗口中渲染，提供更好的用户体验
- 保持与 Workflow 其他界面一致的 Classic Mac OS 9 风格
- 保持现有 HITL 功能完整性（所有字段类型、操作按钮）
- 窗口生命周期管理（打开、关闭、超时）

### Non-Goals

- 不改变后端 HITL API
- 不修改 HITL 的业务逻辑
- 不迁移聊天消息显示（保留在 Live2D Widget）

## Decisions

### Decision 1: 使用 Electron IPC 而非 PostMessage

**方案对比**:

| 方案 | 优点 | 缺点 |
|------|------|------|
| Window PostMessage | 标准 Web API | 窗口间需要引用，安全性较低 |
| Electron IPC | 原生支持多窗口，安全 | 需要 preload 脚本 |
| SharedWorker | 标准 Web API | Electron 支持有限 |

**决策**: 采用 **Electron IPC**

**理由**:
1. Electron IPC 是跨窗口通讯的标准方式
2. 通过 Main Process 中转，窗口间无需直接引用
3. `contextIsolation: true` 提供安全保障
4. 现有 `preload.cjs` 已暴露 `electronAPI`
5. 支持 `invoke/handle` 模式，便于请求-响应通讯

### Decision 2: IPC Channel 设计

```javascript
// IPC Channels
const HITL_CHANNELS = {
  // Live2D → Main: 请求打开 HITL 窗口
  OPEN_WINDOW: 'hitl:open-window',

  // HITL Window → Main: 提交表单响应
  SUBMIT: 'hitl:submit',

  // HITL Window → Main: 取消/关闭窗口
  CANCEL: 'hitl:cancel',

  // Main → Live2D: 返回 HITL 结果
  RESULT: 'hitl:result',

  // Main → HITL Window: 传递请求数据
  REQUEST_DATA: 'hitl:request-data',
};
```

**消息格式**:

```typescript
// hitl:open-window 请求
interface HITLOpenRequest {
  request: HITLRequest;  // HITL 表单定义
  sessionId: string;     // 会话 ID
}

// hitl:submit 请求
interface HITLSubmitRequest {
  requestId: string;
  sessionId: string;
  action: 'approve' | 'reject';
  data: Record<string, unknown> | null;
}

// hitl:result 响应
interface HITLResultResponse {
  success: boolean;
  message?: string;
  error?: string;
  continuationData?: HITLContinuationData;
}
```

### Decision 3: HITL 窗口生命周期

```
┌─────────────────────────────────────────────────────────────────┐
│                    HITL Window Lifecycle                         │
└─────────────────────────────────────────────────────────────────┘

                    ┌──────────────┐
                    │   Closed     │
                    └──────┬───────┘
                           │
              hitl:open-window
                           │
                           ▼
                    ┌──────────────┐
              ┌─────│   Opening    │
              │     └──────┬───────┘
              │            │
              │     window created
              │            │
              │            ▼
              │     ┌──────────────┐
              │     │   Active     │◄──────────────┐
              │     └──────┬───────┘               │
              │            │                       │
              │     ┌──────┴──────┐                │
              │     │             │                │
              │  submit        cancel         validation
              │     │             │             error
              │     ▼             ▼                │
              │  ┌──────┐    ┌──────┐              │
              │  │Submit│    │Cancel│              │
              │  └──┬───┘    └──┬───┘              │
              │     │           │                  │
              │     │  POST     │                  │
              │     │/hitl/     │                  │
              │     │respond    │                  │
              │     │           │                  │
              │     ▼           │                  │
              │  success?───No──┴──────────────────┘
              │     │
              │    Yes
              │     │
              │     ▼
              │  ┌──────────────┐
              │  │   Closing    │
              │  └──────┬───────┘
              │         │
              │   send result to Live2D
              │   close window
              │         │
              │         ▼
              └───▶┌──────────────┐
                   │   Closed     │
                   └──────────────┘
```

**窗口管理规则**:
1. 同一时间只允许一个 HITL 窗口存在
2. 窗口关闭时（用户点击关闭按钮）视为取消操作
3. 窗口支持 TTL 超时自动关闭
4. 提交成功后自动关闭窗口

### Decision 4: HITL 窗口配置

```javascript
// main.cjs 中的窗口创建
function createHITLWindow(request) {
  const hitlWindow = new BrowserWindow({
    width: 480,
    height: 600,
    title: request.title || 'HITL',
    parent: mainWindow,        // 设为主窗口子窗口
    modal: false,              // 非模态，允许操作主窗口
    show: false,               // 创建后不立即显示
    center: true,              // 居中显示
    resizable: true,
    minimizable: false,
    maximizable: false,
    titleBarStyle: 'hidden',   // 隐藏原生标题栏
    trafficLightPosition: { x: 10, y: 10 },
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
    }
  });

  hitlWindow.loadFile('dist/hitl/index.html');

  // 准备好后显示
  hitlWindow.once('ready-to-show', () => {
    hitlWindow.show();
  });

  return hitlWindow;
}
```

### Decision 5: 组件结构

```
electron/src/renderer/hitl/
├── index.html              # 入口 HTML
├── main.tsx                # React 入口
├── App.tsx                 # 主组件
├── components/
│   ├── hitl-form.tsx       # 表单容器
│   ├── hitl-field.tsx      # 字段渲染器
│   ├── hitl-actions.tsx    # 操作按钮
│   └── hitl-error.tsx      # 错误显示
├── hooks/
│   └── use-hitl-window.ts  # 窗口状态管理
├── lib/
│   └── ipc-client.ts       # IPC 客户端封装
├── types/
│   └── hitl.ts             # 类型定义
└── styles/
    └── globals.css         # 样式
```

### Decision 6: preload.cjs 扩展

```javascript
// preload.cjs
contextBridge.exposeInMainWorld('electronAPI', {
  // 现有方法
  send: (channel, ...args) => ipcRenderer.send(channel, ...args),
  invoke: (channel, ...args) => ipcRenderer.invoke(channel, ...args),

  // 新增: 监听主进程消息
  on: (channel, callback) => {
    const subscription = (event, ...args) => callback(...args);
    ipcRenderer.on(channel, subscription);
    return () => ipcRenderer.removeListener(channel, subscription);
  },

  // 新增: 一次性监听
  once: (channel, callback) => {
    ipcRenderer.once(channel, (event, ...args) => callback(...args));
  },
});
```

### Decision 7: 字段类型到组件映射

复用 Workflow 现有组件：

| HITL Field Type | Component | Source |
|-----------------|-----------|--------|
| `text` | `Input` | workflow/ui/input.tsx |
| `textarea` | `Textarea` | workflow/ui/textarea.tsx |
| `select` | Native `<select>` | 原生 + classic 样式 |
| `multiselect` | Checkbox Group | workflow/ui/checkbox.tsx |
| `radio` | Radio Group | 原生 + classic 样式 |
| `checkbox` | `Checkbox` | workflow/ui/checkbox.tsx |
| `number` | `Input type="number"` | workflow/ui/input.tsx |
| `slider` | `Slider` | workflow/ui/slider.tsx |
| `date` | `Input type="date"` | workflow/ui/input.tsx |
| `boolean` | `Checkbox` | workflow/ui/checkbox.tsx |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Electron Application                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                        Main Process (main.cjs)                      │ │
│  │                                                                      │ │
│  │   IPC Handlers:                                                     │ │
│  │   ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │ │
│  │   │hitl:open-window  │  │  hitl:submit     │  │  hitl:cancel    │  │ │
│  │   │                  │  │                  │  │                 │  │ │
│  │   │ Create HITL      │  │ Call /hitl/      │  │ Close window    │  │ │
│  │   │ Window           │  │ respond API      │  │ Send cancel     │  │ │
│  │   │ Send request     │  │ Send result to   │  │ result          │  │ │
│  │   │ data             │  │ Live2D           │  │                 │  │ │
│  │   │                  │  │ Close window     │  │                 │  │ │
│  │   └──────────────────┘  └──────────────────┘  └─────────────────┘  │ │
│  │                                                                      │ │
│  │   Window Management:                                                │ │
│  │   - mainWindow (Live2D)                                             │ │
│  │   - hitlWindow (HITL Form) - 单例                                   │ │
│  │   - workflowWindow (Memory Palace)                                  │ │
│  │                                                                      │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                              │                                           │
│           ┌──────────────────┴──────────────────┐                       │
│           │                                      │                       │
│           ▼                                      ▼                       │
│  ┌──────────────────────┐            ┌──────────────────────┐           │
│  │   Live2D Window      │            │    HITL Window       │           │
│  │   (Renderer Process) │            │   (Renderer Process) │           │
│  │                      │            │                      │           │
│  │  ┌────────────────┐  │            │  ┌────────────────┐  │           │
│  │  │ ShadowRoot     │  │            │  │   React App    │  │           │
│  │  │                │  │   IPC      │  │                │  │           │
│  │  │  chat.ts       │──┼────────────┼──│  HITLForm      │  │           │
│  │  │                │  │            │  │                │  │           │
│  │  │  - SSE hitl    │  │            │  │  - Fields      │  │           │
│  │  │    event       │  │            │  │  - Actions     │  │           │
│  │  │  - IPC open    │  │            │  │  - Submit      │  │           │
│  │  │  - Wait result │  │            │  │                │  │           │
│  │  │  - Continue    │  │            │  │  Classic Mac   │  │           │
│  │  │    dialog      │  │            │  │  OS 9 Theme    │  │           │
│  │  └────────────────┘  │            │  └────────────────┘  │           │
│  └──────────────────────┘            └──────────────────────┘           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Python Backend (8002)                           │
│                                                                          │
│  POST /chat         SSE: hitl event                                     │
│  POST /hitl/respond  → Response + continuation_data                     │
│  POST /hitl/continue → SSE: text events                                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### HITL Request Flow

```
1. User sends message in Live2D chat
   │
   ▼
2. Backend processes with LLM
   │
   ▼
3. LLM returns hitl_request in JSON
   │
   ▼
4. Backend sends SSE event: type=hitl
   │
   ▼
5. Live2D chat.ts receives hitl event
   │
   ▼
6. chat.ts calls electronAPI.invoke('hitl:open-window', { request, sessionId })
   │
   ▼
7. Main Process creates HITL window
   │
   ▼
8. Main Process sends request data to HITL window via IPC
   │
   ▼
9. HITL window renders form with Classic Mac OS 9 theme
```

### HITL Response Flow

```
1. User fills form and clicks Approve/Reject
   │
   ▼
2. HITL window calls electronAPI.invoke('hitl:submit', submitData)
   │
   ▼
3. Main Process calls POST /hitl/respond
   │
   ▼
4. Backend returns result with optional continuation_data
   │
   ▼
5. Main Process sends result to Live2D window via IPC
   │
   ▼
6. Main Process closes HITL window
   │
   ▼
7. Live2D receives result
   │
   ▼
8. If continuation_data present:
   │  Live2D calls POST /hitl/continue
   │  Displays streaming AI response
   │  May receive new HITL request (loop to step 5)
   │
   ▼
9. Chat continues normally
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 窗口创建开销 | HITL 交互频率低，开销可接受 |
| 窗口焦点问题 | 设为 mainWindow 子窗口，保持层级 |
| IPC 消息丢失 | 使用 invoke/handle 模式确保可靠性 |
| 用户关闭窗口 | 监听 'close' 事件，视为取消 |
| 多窗口状态同步 | 通过 Main Process 统一管理 |
| 窗口超时处理 | Main Process 设置 TTL 定时器 |

## Migration Strategy

### Phase 1: 基础设施

1. 扩展 `preload.cjs` 添加 `on` 方法
2. 在 `main.cjs` 中添加 HITL IPC handlers
3. 创建 HITL 窗口创建函数

### Phase 2: HITL 窗口应用

1. 创建 `electron/src/renderer/hitl/` 目录结构
2. 配置 Vite 多入口构建
3. 实现 HITL React 组件
4. 应用 Classic Mac OS 9 样式

### Phase 3: 集成 Live2D

1. 修改 `chat.ts`，使用 IPC 打开 HITL 窗口
2. 实现 IPC 结果监听
3. 处理 continuation 逻辑

### Phase 4: 测试和清理

1. 端到端测试完整流程
2. 移除 `chat.ts` 中的旧 HITL UI 代码
3. 更新文档

## Open Questions

1. ~~HITL 窗口是否应该模态？~~ → 否，允许用户查看 Live2D 对话
2. ~~窗口关闭按钮行为？~~ → 视为取消，发送 reject
3. 是否需要窗口位置记忆？→ 初版不需要，使用居中显示
