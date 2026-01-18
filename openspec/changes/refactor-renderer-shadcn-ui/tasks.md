## 1. 基础设施配置

- [x] 1.1 安装 Tailwind CSS 及相关依赖 (`tailwindcss`, `postcss`, `@tailwindcss/postcss`)
- [x] 1.2 配置 `postcss.config.js` (Tailwind CSS v4 不再需要 tailwind.config.js)
- [x] 1.3 添加 TypeScript 支持 (`typescript`, `@types/react`, `@types/react-dom`)
- [x] 1.4 创建 `tsconfig.json` 配置文件
- [x] 1.5 更新 Vite 配置支持 TypeScript 和路径别名
- [x] 1.6 创建 `styles/globals.css` 引入 Tailwind 指令和 CSS 变量
- [x] 1.7 手动创建 shadcn/ui 组件 (button, card, dialog, tabs, input, badge, alert, checkbox, slider, spinner, textarea, confirm-dialog)

## 2. 核心抽象层

- [x] 2.1 创建 `types/api.ts` 定义 API 数据类型 (Session, Message, WorkingMemory, LongTermMemory 等)
- [x] 2.2 创建 `lib/api-client.ts` 实现 HTTP 客户端封装
  - 统一的 fetch 封装函数
  - 错误处理和 toast 提示
  - 类型安全的泛型支持
- [x] 2.3 创建 `lib/utils.ts` 存放工具函数 (cn, formatTime)
- [x] 2.4 创建 `hooks/use-toast.tsx` 实现消息提示 hook (含 ToastProvider)
- [x] 2.5 创建 `hooks/use-health.ts` 实现健康检查 hook
- [x] 2.6 创建 `components/layout/app-header.tsx` 头部组件
- [x] 2.7 创建 `components/layout/app-layout.tsx` 布局组件

## 3. 功能模块 - 聊天历史

- [x] 3.1 创建 `hooks/use-chat-sessions.ts` 封装聊天会话相关状态和操作
- [x] 3.2 创建 `components/features/chat-history/session-list.tsx` 会话列表组件
- [x] 3.3 创建 `components/features/chat-history/message-detail.tsx` 消息详情组件
- [x] 3.4 创建 `components/features/chat-history/save-memory-dialog.tsx` 保存记忆对话框
- [x] 3.5 创建 `components/features/chat-history/chat-history-tab.tsx` 聊天历史 Tab 主组件

## 4. 功能模块 - 工作记忆

- [x] 4.1 创建 `hooks/use-working-memory.ts` 封装工作记忆相关状态和操作
- [x] 4.2 创建 `components/features/working-memory/memory-list.tsx` 工作记忆列表组件
- [x] 4.3 创建 `components/features/working-memory/memory-drilldown.tsx` 工作记忆下探组件
- [x] 4.4 创建 `components/features/working-memory/transfer-dialog.tsx` 转存对话框
- [x] 4.5 创建 `components/features/working-memory/working-memory-tab.tsx` 工作记忆 Tab 主组件

## 5. 功能模块 - 长期记忆

- [x] 5.1 创建 `hooks/use-long-term-memory.ts` 封装长期记忆相关状态和操作
- [x] 5.2 创建 `components/features/long-term-memory/memory-filter.tsx` 过滤器组件
- [x] 5.3 创建 `components/features/long-term-memory/memory-list.tsx` 记忆列表组件
- [x] 5.4 创建 `components/features/long-term-memory/memory-form-dialog.tsx` 创建/编辑记忆对话框
- [x] 5.5 创建 `components/features/long-term-memory/long-term-memory-tab.tsx` 长期记忆 Tab 主组件

## 6. 整合与清理

- [x] 6.1 创建 `App.tsx` 整合所有模块
- [x] 6.2 更新 `main.tsx` 入口文件
- [x] 6.3 实现经典 Mac 主题 CSS 变量 (在 globals.css 中)
- [x] 6.4 主题切换功能 (通过 theme-classic class)
- [x] 6.5 TypeScript 检查通过 & Vite 构建成功
- [x] 6.6 移除 Ant Design 依赖 (`antd`, `@ant-design/icons`, `moment`)
- [x] 6.7 删除旧的 `App.jsx`, `App.css`, `main.jsx`
- [x] 6.8 更新 `package.json` 清理依赖，添加 `"type": "module"`
