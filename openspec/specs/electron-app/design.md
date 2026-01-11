# Electron Application Design

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Electron Application                      │
├─────────────────────────────────────────────────────────────┤
│  Main Process                                                │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │  Window Manager │  │  Express Server │                   │
│  │  - Main Window  │  │  - Static Files │                   │
│  │  - Live2D Win   │  │  - Live2D Assets│                   │
│  └─────────────────┘  └─────────────────┘                   │
├─────────────────────────────────────────────────────────────┤
│  Renderer Process (React)                                    │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Ant Design UI                                           ││
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ││
│  │  │ Workflow Test │ │   Templates   │ │  Steps View   │ ││
│  │  └───────────────┘ └───────────────┘ └───────────────┘ ││
│  └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│                         HTTP                                 │
│                          ↓                                   │
│              Python Backend (localhost:8080)                 │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### Main Process (`main.js`)

负责：
- Electron 应用生命周期管理
- 创建和管理 BrowserWindow
- 启动内嵌 Express 静态服务器
- IPC 通信处理

### Renderer Process

使用 React 19 + Ant Design 4 构建：
- Workflow 测试面板：执行工作流、查看结果
- 模板管理：CRUD 操作、搜索、执行
- 步骤注册表：查看可用步骤

### Live2D Window

独立的透明窗口：
- 使用 Live2D Cubism SDK Web
- 背景透明 (`transparent: true`)
- 始终置顶可选

## Design Decisions

### D1: 前后端分离架构

**决策**: Electron 仅作为 UI 容器，核心逻辑在 Python 后端

**理由**:
- Python 生态更适合工作流引擎
- LangGraph 提供成熟的工作流能力
- 便于独立部署后端服务

### D2: Vite 作为构建工具

**决策**: 使用 Vite 而非 Webpack

**理由**:
- 更快的开发服务器启动
- 原生 ES 模块支持
- 更简洁的配置

### D3: 内嵌 Express 服务器

**决策**: 在 Electron 主进程中运行 Express

**理由**:
- 为 Live2D 资源提供 HTTP 服务
- 避免 file:// 协议的跨域限制
- 便于扩展本地 API 能力

## Window Configuration

### Main Window
```javascript
{
  width: 1200,
  height: 800,
  webPreferences: {
    nodeIntegration: false,
    contextIsolation: true
  }
}
```

### Live2D Window
```javascript
{
  transparent: true,
  frame: false,
  alwaysOnTop: true,
  webPreferences: {
    nodeIntegration: false,
    contextIsolation: true
  }
}
```
