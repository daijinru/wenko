# Proposal: Optimize Electron Build System

## Summary

优化 Electron 构建工程，解决开发体验问题并增强多页面构建支持。

## Problem Statement

当前 Electron 构建工程存在以下问题：

### 1. 开发模式 dist 目录错误
- **问题描述**: 本地开发时频繁修改文件，会导致某个 dist 目录找不到从而报错
- **根本原因**: `npm run start` 使用 `vite build --watch` 配合 `electronmon`，但 Vite 的增量构建在某些情况下可能产生竞态条件（race condition）。当 Electron 尝试加载文件时，Vite 可能正在清理或重建 dist 目录（`emptyOutDir: true`）
- **影响**: 开发效率降低，需要频繁重启应用

### 2. 多页面构建优化不足
- **问题描述**: 当前多页面配置可以工作，但存在优化空间
- **当前配置**:
  - 4 个独立入口页面（workflow, hitl, image-preview, reminder）
  - 每个页面独立打包，未充分利用代码分割
- **改进方向**: 优化 chunk 分割策略，提升构建和加载性能

### 3. 缺少构建 Loading 状态
- **问题描述**: 构建过程中用户看不到任何进度提示，容易产生焦虑
- **期望行为**:
  - 首先显示一个构建 loading 界面
  - 构建完毕后再呈现实际内容
- **影响**: 用户体验不佳，尤其是首次启动或冷启动时

## Proposed Solution

### 方案一: 开发模式切换到 Vite Dev Server（推荐）

将开发模式从 `vite build --watch` + 静态文件加载改为 Vite Dev Server + HMR：

```
开发模式: Electron 加载 http://localhost:3000 (Vite Dev Server)
生产模式: Electron 加载打包后的静态文件
```

**优势**:
- 彻底解决 dist 目录竞态问题（开发时不需要 dist）
- 原生 HMR 支持，更快的热更新
- 更好的开发体验

### 方案二: 启动 Loading 窗口

添加轻量级的启动加载窗口：

```
1. 应用启动 → 显示 Loading 窗口（纯 HTML/CSS，无需构建）
2. 后台执行构建检查或等待 Vite 就绪
3. 就绪后 → 关闭 Loading，显示主窗口
```

### 方案三: 优化多页面构建配置

增强 Vite 的 Rollup 配置，优化代码分割：

```javascript
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        'vendor-react': ['react', 'react-dom'],
        'vendor-antd': ['antd'],
        // ... 更多分割策略
      }
    }
  }
}
```

## Scope

### In Scope
- 修改 Vite 构建配置以支持开发/生产模式分离
- 修改 Electron 主进程以支持开发模式加载 Dev Server
- 添加启动 Loading 窗口
- 优化多页面代码分割配置
- 更新 npm scripts

### Out of Scope
- Live2D Widget 的 Rollup 构建配置（保持现状）
- 后端 Python 服务的启动流程
- Electron Builder 打包配置

## Related Specs
- `electron-app` - Electron 应用窗口管理规范

## Risks and Mitigations

| 风险 | 缓解措施 |
|------|----------|
| Dev Server 端口冲突 | 添加端口检测和自动切换逻辑 |
| 开发/生产环境行为差异 | 充分测试两种模式，保持路径处理一致性 |
| Loading 窗口增加启动时间 | Loading 窗口使用纯静态 HTML，加载极快 |

## Success Criteria

1. 开发模式下频繁保存文件不再导致 dist 目录找不到的错误
2. 多页面构建产物大小减少 10% 以上（通过更好的代码分割）
3. 启动时显示 Loading 界面，构建完成后平滑过渡到主界面
4. `npm run dev` 和 `npm run build` 命令正常工作
