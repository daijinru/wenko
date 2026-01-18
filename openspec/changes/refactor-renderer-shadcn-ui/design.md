## Context

Wenko 的 Electron renderer 使用 React 19 + Ant Design 4 构建，当前存在代码组织混乱、维护困难的问题。需要重构以提升代码质量和开发体验。

### 约束条件
- 必须保持现有功能不变
- 需要兼容 Electron 38 环境
- 需要与 Python 后端 API 保持兼容
- 保留经典 Mac OS 9 视觉风格选项

## Goals / Non-Goals

### Goals
1. 使用 shadcn/ui + Tailwind CSS 替代 Ant Design
2. 将单一大文件拆分为模块化组件
3. 创建类型安全的 HTTP 客户端抽象
4. 使用 TypeScript 增强类型安全
5. 通过 custom hooks 分离业务逻辑

### Non-Goals
- 不改变后端 API 接口
- 不添加新功能
- 不改变应用的整体行为

## Decisions

### Decision 1: 使用 shadcn/ui 而非其他组件库

**选择**: shadcn/ui + Radix UI + Tailwind CSS

**替代方案**:
- **Ant Design 5.x**: 升级版本可解决部分兼容性问题，但仍是重量级框架，自定义困难
- **Material UI**: 风格固定，难以实现经典 Mac 风格
- **Chakra UI**: 较轻量但组件数量有限
- **纯手写组件**: 工作量大，无法复用社区经验

**理由**:
- shadcn/ui 组件代码直接集成到项目，完全可控
- 基于 Radix UI 的无障碍基础，质量有保证
- Tailwind CSS 易于自定义样式，可轻松实现经典 Mac 风格
- 社区活跃，React 19 兼容性好

### Decision 2: API 客户端架构

**选择**: 基于 fetch 的轻量级封装 + React Query 风格的 hooks

**替代方案**:
- **Axios**: 功能齐全但增加包体积
- **React Query / TanStack Query**: 功能强大但对于简单应用过于复杂
- **SWR**: 轻量但需要额外学习成本

**理由**:
- 当前应用 API 调用相对简单
- 使用原生 fetch 配合自定义封装足够
- 保持轻量，减少依赖
- 后续如需缓存/重试策略可逐步引入 React Query

### Decision 3: 状态管理策略

**选择**: React 内置状态 (useState/useReducer) + Custom Hooks

**替代方案**:
- **Redux/Zustand**: 全局状态管理库
- **Jotai/Recoil**: 原子化状态管理

**理由**:
- 当前应用状态相对简单，各 Tab 间状态独立
- Custom hooks 足以封装和复用状态逻辑
- 避免过度工程化
- 后续如需要可轻松迁移到状态管理库

### Decision 4: TypeScript 配置

**选择**: 严格模式 (strict: true) + 渐进式迁移

**策略**:
1. 新建 `tsconfig.json` 启用严格模式
2. 先定义 API 类型 (`types/api.ts`)
3. 从底层组件开始迁移
4. 最后迁移顶层 App 组件

### Decision 5: 样式主题系统

**选择**: Tailwind CSS 变量 + CSS 自定义属性

**实现**:
```css
/* globals.css */
@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 0 0% 0%;
    /* ... 现代主题变量 */
  }

  .theme-classic {
    --background: 0 0% 87%;  /* #dddddd */
    --foreground: 0 0% 0%;
    /* ... 经典 Mac 主题变量 */
  }
}
```

**理由**:
- 利用 Tailwind 的 CSS 变量系统
- 主题切换只需切换 CSS 类名
- 保持与 shadcn/ui 组件的兼容性

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|-----|-----|---------|
| 重构范围大，可能引入 bug | 高 | 分阶段实施，每阶段完成后测试 |
| shadcn/ui 组件样式与经典 Mac 风格差异 | 中 | 利用 Tailwind 完全自定义组件样式 |
| TypeScript 迁移增加工作量 | 中 | 类型定义优先，组件渐进迁移 |
| Tailwind CSS 学习曲线 | 低 | 项目简单，常用类名有限 |

## Migration Plan

### Phase 1: 基础设施 (tasks 1.x)
1. 配置 Tailwind CSS + TypeScript
2. 安装 shadcn/ui CLI 和基础组件
3. 创建 API 类型定义

### Phase 2: 核心抽象层 (tasks 2.x)
1. 实现 API 客户端封装
2. 创建基础 custom hooks
3. 搭建布局组件

### Phase 3: 功能模块迁移 (tasks 3.x)
1. 迁移聊天历史模块
2. 迁移工作记忆模块
3. 迁移长期记忆模块

### Phase 4: 整合与清理 (tasks 4.x)
1. 组装 App 组件
2. 移除 Ant Design 依赖
3. 清理旧代码和 CSS

### Rollback
- 保留原 `App.jsx` 和 `App.css` 直到新版本稳定
- Git 分支开发，便于回滚

## Open Questions

1. **是否需要保留经典 Mac 主题？** - 默认是，作为可选主题
2. **是否引入单元测试？** - 当前 scope 外，可后续添加
3. **是否需要 i18n 支持？** - 当前仅中文，暂不考虑
