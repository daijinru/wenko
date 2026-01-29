# Change: Add HITL Visual Display Type for AI Graphical Expression

## Why

当前 HITL 系统主要用于收集用户输入（表单类型），但 AI 缺乏向用户展示结构化视觉信息的能力。在许多对话场景中，AI 需要以图形化方式呈现数据，例如：

- 展示比较表格（产品对比、方案对比）
- 显示流程图、架构图（使用 ASCII art）
- 呈现数据表格（统计信息、列表数据）
- 绘制简单图表（进度条、树形结构）

目前 AI 只能通过纯文本描述这些信息，可读性差，用户体验不佳。通过新增 HITL Visual Display 类型，AI 可以在弹窗中渲染结构化的视觉内容，提升表达能力和用户理解效率。

## What Changes

- **ADDED**: 新增 HITL 请求类型 `visual_display`，用于 AI 图形化表达
- **ADDED**: 新增 `HITLDisplayField` 字段类型，包含 `table` 和 `ascii` 两种组件
- **ADDED**: 前端 `HITLDisplayField` 组件，渲染 table 和 ascii 内容
- **ADDED**: 新增 `HITLDisplayRequest` schema，区别于表单类型的 `HITLRequest`
- **MODIFIED**: HITL 弹窗 UI，支持根据请求类型渲染不同内容
- **ADDED**: Visual Display 数据持久化到工作记忆的上下文变量
- **MODIFIED**: 上下文变量对话框 replay 功能，支持 visual_display 类型的回放

## First Phase Scope

本次变更第一期仅实现：

1. **Table 组件**: 支持渲染二维表格数据
   - 表头 (headers)
   - 行数据 (rows)
   - 可选的列对齐方式 (alignment)
   - 可选的表格标题 (caption)

2. **ASCII 组件**: 支持渲染预格式化的 ASCII 艺术
   - 等宽字体渲染
   - 保留空格和换行
   - 可选的标题 (title)

## Future Phases (Out of Scope)

以下功能将在后续迭代中考虑：

- SVG 组件（矢量图形）
- HTML 组件（富文本渲染）
- Canvas 组件（动态绘图）
- 图表组件（bar chart, pie chart 等）

## Impact

- Affected specs: `hitl-visual-display` (new capability)
- Affected code:
  - `workflow/hitl_schema.py` - 新增 Visual Display 相关 schema
  - `workflow/hitl_handler.py` - 支持 visual_display 类型处理，持久化到工作记忆
  - `electron/src/renderer/hitl/types/hitl.ts` - 新增 TypeScript 类型定义
  - `electron/src/renderer/hitl/components/hitl-display-field.tsx` - 新增展示组件
  - `electron/src/renderer/hitl/components/hitl-display.tsx` - Visual Display 容器组件
  - `electron/src/renderer/hitl/App.tsx` - 根据类型路由渲染
  - `electron/src/renderer/workflow/components/features/working-memory/context-variable-dialog.tsx` - 支持 visual_display 类型 replay
