# Electron Build System Specification

## Overview
Electron 应用的构建系统规范，定义开发模式、生产模式和启动流程的行为。

## ADDED Requirements

### Requirement: Development Mode with Vite Dev Server
开发模式下系统 SHALL 使用 Vite Dev Server 提供渲染进程页面，支持 HMR 热更新。

#### Scenario: Start development mode
- **Given** 用户执行 `npm run dev` 命令
- **When** Vite Dev Server 在端口 3000 启动完成
- **Then** Electron 主进程启动并加载 Dev Server 提供的页面
- **And** 页面支持 HMR 热更新

#### Scenario: Wait for Dev Server ready
- **Given** Electron 主进程正在启动
- **When** Vite Dev Server 尚未就绪
- **Then** 主进程轮询等待 Dev Server 端口可用
- **And** 等待超时后显示错误提示

---

### Requirement: Production Mode with Static Files
生产模式下系统 SHALL 从 dist 目录加载预构建的静态文件。

#### Scenario: Start production mode
- **Given** 应用已打包或通过 `npm run start` 启动
- **When** 主进程检测到生产环境
- **Then** 从 `dist/` 目录加载静态 HTML 文件

#### Scenario: Build static files
- **Given** 用户执行 `npm run build` 命令
- **When** Vite 构建完成
- **Then** 所有多页面入口输出到 `dist/src/renderer/` 目录
- **And** 公共依赖分割为独立 chunk

---

### Requirement: Loading Window on Startup
应用启动时系统 SHALL 显示 Loading 窗口，就绪后切换到主窗口。

#### Scenario: Show loading window
- **Given** 应用正在启动
- **When** 主窗口尚未准备就绪
- **Then** 显示 Loading 窗口，展示加载动画和提示文字

#### Scenario: Transition to main window
- **Given** Loading 窗口正在显示
- **When** 开发模式 Dev Server 就绪或生产模式文件加载完成
- **Then** 关闭 Loading 窗口
- **And** 显示主窗口

#### Scenario: Loading timeout
- **Given** Loading 窗口正在显示
- **When** 等待超过 30 秒仍未就绪
- **Then** 显示错误提示
- **And** 允许用户重试或退出

---

### Requirement: Multi-page Build Optimization
构建系统 SHALL 优化多页面构建配置，减少重复依赖打包。

#### Scenario: Chunk splitting for vendor libraries
- **Given** 构建配置启用 manualChunks
- **When** 执行 `npm run build`
- **Then** React 相关库打包为 `vendor-react` chunk
- **And** Ant Design 打包为 `vendor-antd` chunk
- **And** 公共业务代码打包为共享 chunk

#### Scenario: Multi-page entry points
- **Given** 项目包含多个渲染进程页面
- **When** 构建系统处理入口
- **Then** workflow, hitl, image-preview, reminder 四个页面独立打包
- **And** 共享 chunk 在页面间复用

---

### Requirement: Environment Detection
系统 MUST 自动检测运行环境（开发/生产）并选择对应的加载策略。

#### Scenario: Detect development environment
- **Given** 应用通过 `npm run dev` 或 `electronmon` 启动
- **When** 主进程检查 `app.isPackaged`
- **Then** 返回 false，使用开发模式配置

#### Scenario: Detect production environment
- **Given** 应用已打包或通过 `electron-builder` 构建
- **When** 主进程检查 `app.isPackaged`
- **Then** 返回 true，使用生产模式配置

---

### Requirement: Renderer Page URL Resolution
系统 SHALL 统一管理渲染进程页面的 URL/路径解析。

#### Scenario: Resolve page URL in development
- **Given** 运行在开发模式
- **When** 请求加载 workflow 页面
- **Then** 返回 `http://localhost:3000/src/renderer/workflow/index.html`

#### Scenario: Resolve page path in production
- **Given** 运行在生产模式
- **When** 请求加载 workflow 页面
- **Then** 返回 `dist/src/renderer/workflow/index.html` 的绝对路径
