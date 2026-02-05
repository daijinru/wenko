# Design: Optimize Electron Build System

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Electron Application                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────┐     ┌──────────────────┐     ┌───────────────────┐  │
│  │ Loading       │ ──► │ Main Process     │ ──► │ Renderer Windows  │  │
│  │ Window        │     │ (main.cjs)       │     │ (React Apps)      │  │
│  │ (loading.html)│     │                  │     │                   │  │
│  └───────────────┘     └──────────────────┘     └───────────────────┘  │
│                                 │                         ▲            │
│                                 │                         │            │
│                                 ▼                         │            │
│                        ┌──────────────────┐               │            │
│                        │ Environment      │               │            │
│                        │ Detection        │               │            │
│                        └──────────────────┘               │            │
│                                 │                         │            │
│           ┌─────────────────────┴─────────────────────┐   │            │
│           ▼                                           ▼   │            │
│  ┌─────────────────┐                       ┌─────────────────────┐     │
│  │ Development     │                       │ Production          │     │
│  │ Mode            │                       │ Mode                │     │
│  │                 │                       │                     │     │
│  │ loadURL()       │                       │ loadFile()          │     │
│  │ localhost:3000  │                       │ dist/...            │     │
│  └─────────────────┘                       └─────────────────────┘     │
│           ▲                                           ▲                │
└───────────┼───────────────────────────────────────────┼────────────────┘
            │                                           │
            ▼                                           ▼
    ┌───────────────┐                         ┌─────────────────┐
    │ Vite Dev      │                         │ Vite Build      │
    │ Server        │                         │ Output (dist/)  │
    │ :3000         │                         │                 │
    │               │                         │ ├── assets/     │
    │ - HMR         │                         │ └── src/        │
    │ - Fast Reload │                         │     └── renderer│
    └───────────────┘                         └─────────────────┘
```

## Component Design

### 1. Environment Detection Module

**位置**: `electron/main.cjs`

```javascript
// 环境检测逻辑
const isDev = !app.isPackaged && process.env.NODE_ENV !== 'production';

// 或者通过 electron-is-dev 包
const isDev = require('electron-is-dev');
```

**设计决策**: 使用 `app.isPackaged` 作为主要判断依据，因为：
- 打包后的应用 `app.isPackaged = true`
- 开发模式下 `app.isPackaged = false`
- 不需要额外的环境变量配置

### 2. URL/File Resolver

**位置**: `electron/main.cjs`

```javascript
/**
 * 获取渲染进程页面的 URL 或文件路径
 * @param {string} pageName - 页面名称 (workflow, hitl, image-preview, reminder)
 * @returns {string} URL (开发) 或文件路径 (生产)
 */
function getRendererPath(pageName) {
  if (isDev) {
    return `http://localhost:${DEV_SERVER_PORT}/src/renderer/${pageName}/index.html`;
  }
  return path.join(__dirname, `dist/src/renderer/${pageName}/index.html`);
}

/**
 * 加载渲染进程页面
 * @param {BrowserWindow} window - Electron 窗口
 * @param {string} pageName - 页面名称
 */
function loadRendererPage(window, pageName) {
  const pagePath = getRendererPath(pageName);
  if (isDev) {
    window.loadURL(pagePath);
  } else {
    window.loadFile(pagePath);
  }
}
```

**多页面映射**:

| 页面名称 | 开发模式 URL | 生产模式文件路径 |
|---------|-------------|----------------|
| workflow | `http://localhost:3000/src/renderer/workflow/index.html` | `dist/src/renderer/workflow/index.html` |
| hitl | `http://localhost:3000/src/renderer/hitl/index.html` | `dist/src/renderer/hitl/index.html` |
| image-preview | `http://localhost:3000/src/renderer/image-preview/index.html` | `dist/src/renderer/image-preview/index.html` |
| reminder | `http://localhost:3000/src/renderer/reminder/index.html` | `dist/src/renderer/reminder/index.html` |

### 3. Loading Window

**位置**: `electron/loading.html`

**设计要点**:
- 纯 HTML/CSS 实现，无 JavaScript 依赖
- 内联样式和动画，无外部资源请求
- 透明背景配合 Electron 透明窗口

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Loading...</title>
  <style>
    body {
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
      margin: 0;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    .loader {
      text-align: center;
      color: #fff;
    }
    .spinner {
      width: 50px;
      height: 50px;
      border: 3px solid rgba(255,255,255,0.3);
      border-top-color: #fff;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin: 0 auto 20px;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  </style>
</head>
<body>
  <div class="loader">
    <div class="spinner"></div>
    <p>Wenko 正在启动...</p>
  </div>
</body>
</html>
```

### 4. Startup Sequence

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Application Startup                           │
└──────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ app.whenReady()     │
                         └─────────────────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Show Loading Window │
                         └─────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
          ┌─────────────────┐             ┌─────────────────┐
          │ Development     │             │ Production      │
          └─────────────────┘             └─────────────────┘
                    │                               │
                    ▼                               ▼
          ┌─────────────────┐             ┌─────────────────┐
          │ Wait for Vite   │             │ Files Ready     │
          │ Dev Server      │             │ (immediate)     │
          │ (poll :3000)    │             └─────────────────┘
          └─────────────────┘                       │
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
                         ┌─────────────────────┐
                         │ Close Loading       │
                         │ Show Main Window    │
                         └─────────────────────┘
```

### 5. Dev Server Ready Detection

```javascript
const http = require('http');

/**
 * 检测 Dev Server 是否就绪
 * @param {number} port - 端口号
 * @param {number} maxAttempts - 最大尝试次数
 * @param {number} interval - 轮询间隔 (ms)
 * @returns {Promise<boolean>}
 */
async function waitForDevServer(port, maxAttempts = 30, interval = 500) {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      await new Promise((resolve, reject) => {
        const req = http.get(`http://localhost:${port}`, (res) => {
          resolve(true);
        });
        req.on('error', reject);
        req.setTimeout(1000, () => {
          req.destroy();
          reject(new Error('timeout'));
        });
      });
      return true;
    } catch (e) {
      await new Promise(r => setTimeout(r, interval));
    }
  }
  return false;
}
```

### 6. Vite Configuration for Multi-page

```javascript
// vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  base: './',

  resolve: {
    alias: {
      '@': resolve(__dirname, 'src/renderer/workflow'),
      '@hitl': resolve(__dirname, 'src/renderer/hitl'),
      '@reminder': resolve(__dirname, 'src/renderer/reminder'),
    },
  },

  build: {
    outDir: resolve(__dirname, 'dist'),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'src/renderer/workflow/index.html'),
        hitl: resolve(__dirname, 'src/renderer/hitl/index.html'),
        'image-preview': resolve(__dirname, 'src/renderer/image-preview/index.html'),
        reminder: resolve(__dirname, 'src/renderer/reminder/index.html'),
      },
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-dom/client'],
          'vendor-antd': ['antd'],
        },
      },
    },
  },

  server: {
    port: 3000,
    strictPort: true, // 确保使用指定端口
  },
});
```

## NPM Scripts Design

```json
{
  "scripts": {
    "dev": "concurrently -k \"npm run vite\" \"npm run electron:dev\"",
    "vite": "vite",
    "electron:dev": "wait-on http://localhost:3000 && electronmon .",
    "build": "vite build",
    "start": "npm run build && electron .",
    "pack": "npm run build && electron-builder --dir",
    "dist": "npm run build && electron-builder"
  }
}
```

**命令说明**:
- `npm run dev` - 开发模式，同时启动 Vite 和 Electron
- `npm run build` - 仅构建，不启动应用
- `npm run start` - 生产模式预览（构建后启动）

## Trade-offs

### 选择 Vite Dev Server vs Vite Build --watch

| 方面 | Dev Server | Build --watch |
|------|-----------|---------------|
| 热更新速度 | 极快 (HMR) | 较慢 (完整重建) |
| dist 目录稳定性 | 不需要 dist | 容易出现竞态 |
| 内存占用 | 较高 | 较低 |
| 开发体验 | 更好 | 一般 |
| 配置复杂度 | 中等 | 简单 |

**结论**: 选择 Dev Server，因为开发体验和稳定性更重要。

### Loading 窗口位置选择

| 方案 | 优点 | 缺点 |
|------|------|------|
| 独立 HTML 文件 | 无依赖，加载快 | 需要维护独立文件 |
| Splash Screen 包 | 功能丰富 | 增加依赖 |
| 主进程内联 HTML | 无额外文件 | 代码可读性差 |

**结论**: 选择独立 HTML 文件，简单且高效。

## Dependencies

需要添加的 npm 包:

```json
{
  "devDependencies": {
    "wait-on": "^7.2.0",
    "electron-is-dev": "^3.0.1"  // 可选
  }
}
```

## File Changes Summary

| 文件 | 变更类型 | 描述 |
|------|---------|------|
| `electron/main.cjs` | 修改 | 添加环境检测、URL resolver、Loading 窗口 |
| `electron/vite.config.js` | 修改 | 添加 manualChunks 配置 |
| `electron/package.json` | 修改 | 更新 scripts，添加依赖 |
| `electron/loading.html` | 新增 | Loading 窗口页面 |
