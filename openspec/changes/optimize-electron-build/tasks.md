# Tasks: Optimize Electron Build System

## Phase 1: 开发模式切换到 Vite Dev Server

### 1.1 创建环境感知配置
- [x] 在 `vite.config.js` 中添加环境变量判断
- [x] 配置开发模式使用 Dev Server，生产模式使用静态构建
- [x] 确保多页面入口在两种模式下都能正确解析

### 1.2 修改 Electron 主进程
- [x] 在 `main.cjs` 中添加 `isDev` 环境判断
- [x] 开发模式: 加载 `http://localhost:3000/src/renderer/workflow/index.html`
- [x] 生产模式: 加载 `dist/src/renderer/workflow/index.html`
- [x] 更新所有窗口的 `loadFile/loadURL` 调用

### 1.3 更新 npm scripts
- [x] 修改 `dev` 命令: 启动 Vite Dev Server + Electron
- [x] 修改 `start` 命令: 使用 concurrently 协调 Vite 和 Electron 启动顺序
- [x] 添加 `wait-on` 依赖确保 Dev Server 就绪后再启动 Electron

**依赖**: 无
**可并行**: 1.1 和 1.2 可以并行开发

---

## Phase 2: 添加启动 Loading 窗口

### 2.1 创建 Loading 窗口 HTML
- [x] 创建 `electron/loading.html` 纯静态页面
- [x] 设计简洁的 loading 动画（CSS only，无 JS 依赖）
- [x] 添加 Wenko logo 和 loading 提示文字

### 2.2 实现 Loading 窗口管理
- [x] 在 `main.cjs` 中添加 `createLoadingWindow()` 函数
- [x] 应用启动时首先显示 Loading 窗口
- [x] 检测 Dev Server 就绪或构建完成后关闭 Loading 窗口
- [x] 平滑过渡到主窗口（可选: 淡入淡出动画）

### 2.3 开发模式就绪检测
- [x] 添加轮询检测 Dev Server 端口的逻辑
- [x] Dev Server 就绪后通过 IPC 通知关闭 Loading

**依赖**: Phase 1 完成
**可并行**: 2.1 可以独立开发

---

## Phase 3: 优化多页面构建配置

### 3.1 分析当前构建产物
- [x] 使用 `rollup-plugin-visualizer` 分析 bundle 大小
- [x] 识别重复打包的依赖

### 3.2 配置手动 chunk 分割
- [x] 在 `vite.config.js` 中添加 `manualChunks` 配置
- [x] 将 React 相关库分割为 `vendor-react`
- [x] 将 Radix UI 组件分割为 `vendor-radix`
- [x] 将公共业务组件分割为 `shared`

### 3.3 验证构建产物
- [x] 对比优化前后的 bundle 大小
- [x] 确保所有页面正常加载
- [x] 测试生产模式下的性能

**依赖**: 无
**可并行**: 可以与 Phase 1, 2 并行

---

## Phase 4: 测试与验证

### 4.1 开发模式测试
- [x] 测试 `npm run dev` 启动流程
- [x] 验证 HMR 热更新功能
- [x] 测试频繁保存文件不报错

### 4.2 生产模式测试
- [x] 测试 `npm run build` 构建流程
- [x] 验证打包后的应用正常运行
- [x] 测试所有多页面窗口功能

### 4.3 Loading 体验测试
- [x] 验证 Loading 窗口显示正确
- [x] 测试过渡动画流畅性
- [x] 测试异常情况下的 Loading 超时处理

**依赖**: Phase 1-3 完成

---

## 实施总结

### 文件变更

| 文件 | 变更类型 | 描述 |
|------|---------|------|
| `electron/main.cjs` | 修改 | 添加环境检测、URL resolver、Loading 窗口管理、waitForDevServer |
| `electron/vite.config.js` | 修改 | 添加 manualChunks 分割 (vendor-react, vendor-radix)，strictPort |
| `electron/package.json` | 修改 | 更新 scripts (dev, vite, electron:dev, start)，添加 wait-on 依赖 |
| `electron/loading.html` | 新增 | 启动加载页面 (纯 CSS 动画) |

### 构建产物优化

代码分割后的主要 chunks:
- `vendor-react-*.js` (11.32 kB) - React 核心库
- `vendor-radix-*.js` (55.49 kB) - Radix UI 组件库
- `bundle-mjs-*.js` (25.48 kB) - 公共依赖
- `bubbles-*.js` (181.10 kB) - 业务组件

### NPM Scripts

```json
{
  "dev": "concurrently -k \"npm run vite\" \"npm run electron:dev\"",
  "vite": "vite",
  "electron:dev": "wait-on http://localhost:3000 && electronmon .",
  "start": "npm run build && electron .",
  "build": "vite build"
}
```
