# Change: 使用 shadcn/ui 重构 Electron Renderer

## Why

当前 renderer 代码存在以下问题：
1. **单文件过大**: `App.jsx` 超过 1000 行，包含所有业务逻辑和 UI 组件
2. **组件耦合严重**: 三个 Tab 页面的逻辑全部混在一起，状态管理混乱
3. **HTTP 客户端分散**: fetch 调用散落在各处，没有统一的错误处理和请求抽象
4. **UI 框架过时**: Ant Design 4.x 配合 React 19 存在兼容性问题，且 CSS 覆盖量大
5. **缺乏类型安全**: 纯 JavaScript 开发，缺少类型检查

使用 shadcn/ui 可以获得：
- 现代化的、可定制的组件库（基于 Radix UI + Tailwind CSS）
- 组件代码直接集成到项目中，完全可控
- 更好的 React 19 兼容性
- 更小的包体积

## What Changes

### 1. 技术栈升级
- 移除 Ant Design 4.x
- 引入 Tailwind CSS + shadcn/ui
- 添加 TypeScript 支持

### 2. 项目结构重构
```
electron/src/renderer/workflow/
├── index.html
├── main.tsx
├── App.tsx
├── lib/
│   └── api-client.ts          # HTTP 客户端抽象
├── hooks/
│   ├── use-health.ts          # 健康检查 hook
│   ├── use-chat-sessions.ts   # 聊天会话 hooks
│   ├── use-working-memory.ts  # 工作记忆 hooks
│   └── use-long-term-memory.ts # 长期记忆 hooks
├── components/
│   ├── ui/                    # shadcn/ui 组件
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   ├── tabs.tsx
│   │   ├── input.tsx
│   │   ├── badge.tsx
│   │   ├── alert.tsx
│   │   └── ...
│   ├── layout/
│   │   ├── app-header.tsx
│   │   └── app-layout.tsx
│   └── features/
│       ├── chat-history/
│       │   ├── chat-history-tab.tsx
│       │   ├── session-list.tsx
│       │   └── message-detail.tsx
│       ├── working-memory/
│       │   ├── working-memory-tab.tsx
│       │   ├── memory-list.tsx
│       │   └── memory-drilldown.tsx
│       └── long-term-memory/
│           ├── long-term-memory-tab.tsx
│           ├── memory-filter.tsx
│           ├── memory-list.tsx
│           └── memory-form-dialog.tsx
├── types/
│   └── api.ts                 # API 类型定义
└── styles/
    └── globals.css            # Tailwind 全局样式
```

### 3. HTTP 客户端抽象
创建统一的 API 客户端层：
- 集中管理 API_BASE 配置
- 统一错误处理和 toast 提示
- 类型安全的请求/响应
- 支持请求拦截和响应拦截

### 4. 组件化拆分
- 每个 Tab 页面独立成 feature 模块
- 抽取可复用的 UI 组件
- 使用 custom hooks 管理业务逻辑和状态

### 5. 样式系统
- 使用 Tailwind CSS 替代自定义 CSS
- 保留经典 Mac OS 9 风格作为可选主题
- 支持主题切换（经典/现代）

## Impact

- **Affected specs**: 无现有 spec（renderer 无 spec）
- **Affected code**:
  - `electron/src/renderer/workflow/*` - 完全重构
  - `electron/package.json` - 依赖变更
  - `electron/vite.config.js` - 构建配置更新
  - `electron/tailwind.config.js` - 新增
  - `electron/tsconfig.json` - 新增
- **Breaking changes**: 无外部接口变更，仅内部重构
