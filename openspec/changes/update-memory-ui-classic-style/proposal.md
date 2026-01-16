# Change: Workflow 面板记忆管理分层与经典 macOS 界面风格

## Why

当前 workflow 面板的记忆管理存在以下问题：

1. **记忆类型混合展示**：工作记忆（Working Memory）和长期记忆（Long-term Memory）在概念上是分离的，但当前 UI 没有明确区分，用户难以理解两者的用途和生命周期差异
2. **界面风格现代化过度**：当前使用紫色渐变、大圆角、重阴影的现代 UI 风格，与经典桌面应用的简洁实用风格不符
3. **视觉层次不清晰**：现代风格的视觉效果分散了用户对核心功能的注意力

本提案旨在：
- 将工作记忆和长期记忆在 UI 层面分开管理，提供独立的视图和操作
- 采用经典 macOS（如 Mac OS 9/Classic 风格）的界面设计，强调功能性和可用性

## What Changes

### 1. 记忆管理分层展示

- **ADDED**: 工作记忆面板 - 展示当前会话的工作记忆状态
  - 显示 session_id、current_topic、turn_count、last_emotion
  - 支持查看和清除当前工作记忆
  - 实时更新展示
  - **支持将工作记忆中的信息添加到长期记忆**（记忆转存功能）

- **MODIFIED**: 长期记忆面板 - 增强现有的记忆管理功能
  - 保持现有的 CRUD 功能
  - 改进视觉层次和信息密度
  - 采用经典列表/表格视图

### 2. 经典 macOS 界面风格

- **MODIFIED**: 整体视觉风格改造
  - 移除紫色渐变背景，使用经典灰色/米色背景
  - 采用凸起/凹陷的 3D 边框效果（bevel）
  - 使用经典系统字体（Chicago/Geneva 风格，回退到系统字体）
  - 窗口标题栏采用经典条纹样式
  - 按钮使用经典的凸起效果
  - 列表项使用经典的交替行颜色

### 3. 界面布局重构

- **MODIFIED**: Tab 结构调整
  - Tab 1: 聊天历史（保持现有）
  - Tab 2: 工作记忆（新增）
  - Tab 3: 长期记忆（从原 "记忆管理" 重命名）

## Design Principles

| 原则 | 实现方式 |
|------|---------|
| 功能优先 | 经典设计强调可用性，减少装饰性元素 |
| 信息密度 | 紧凑布局，单屏展示更多信息 |
| 视觉清晰 | 使用边框和阴影区分区域，而非渐变 |
| 怀旧美学 | 致敬 Mac OS 9 的经典设计语言 |

## Impact

### Affected Specs
- **NEW**: `workflow-memory-ui` - 记忆管理界面规范

### Affected Code

**前端 (React/CSS)**:
- `electron/src/renderer/workflow/App.jsx` - 添加工作记忆面板，重构 Tab 结构
- `electron/src/renderer/workflow/App.css` - 完全重写为经典 macOS 风格

**后端 (Python)**:
- `workflow/main.py` - 可能需要添加工作记忆查询 API（如果尚未实现）

### Visual Changes

**Before (现代风格)**:
- 紫色渐变背景
- 大圆角 (12px)
- 重阴影效果
- 平面化按钮

**After (经典 macOS 风格)**:
- 灰色/米色纯色背景
- 小圆角或直角
- 凸起/凹陷边框效果
- 3D 立体按钮

## Non-Goals

- 本提案**不**改变后端记忆管理逻辑
- 本提案**不**修改聊天历史 Tab 的功能
- 本提案**不**引入新的第三方 UI 库
