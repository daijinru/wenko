# Proposal: enhance-context-variable-display

## Summary

为工作记忆的上下文变量（context_variables）提供更灵活的内容展示方式，改善用户查看和分析上下文数据的体验。

## Problem Statement

当前实现中，上下文变量的展示方式存在以下问题：

1. **位置不直观**：上下文变量按钮位于展开行的内容区域，需要先展开行才能看到
2. **展示空间受限**：使用 `<details>` 折叠展示，JSON 内容在表格内显示，空间有限
3. **缺乏可视化能力**：无法在独立窗口中查看完整内容，特别是当存在多个上下文变量时

## Proposed Solution

1. **移动按钮位置**：将"上下文变量"按钮从展开内容区移动到操作单元格，放在"清除"按钮右侧
2. **对话框展示**：点击按钮弹出对话框（Dialog），在对话框中以 Table 形式展示所有上下文变量的列表
3. **复用 HITL 窗口回显**：在 Table 的操作列添加"replay"按钮，点击后通过 Electron IPC 复用 HITL 窗口展示详情
   - 回显模式：只读，非编辑
   - 仅提供"关闭"操作

## Scope

### In Scope
- 修改 `memory-list.tsx` 组件，调整按钮位置
- 创建上下文变量对话框组件（含 Table 列表）
- 复用现有 HITL 窗口进行详情回显
- 添加 IPC 通信支持以只读模式打开 HITL 窗口

### Out of Scope
- 创建新的 Electron renderer 窗口
- 修改上下文变量的数据结构
- 修改后端 API
- 上下文变量的编辑功能（仅查看）

## Impact Analysis

### Files to Modify
- `electron/src/renderer/workflow/components/features/working-memory/memory-list.tsx`
- `electron/main.cjs` - 添加只读模式 HITL 窗口支持
- `electron/src/renderer/hitl/App.tsx` - 支持只读回显模式
- `electron/src/renderer/hitl/types/hitl.ts` - 添加只读模式类型

### Files to Create
- `electron/src/renderer/workflow/components/features/working-memory/context-variable-dialog.tsx`

### Dependencies
- 复用现有的 shadcn/ui 组件（Dialog, Button, Table）
- 复用现有的 HITL 窗口和 IPC 通信机制

## Success Criteria

1. 用户可以在操作列直接看到并点击"上下文"按钮
2. 点击按钮后弹出对话框，以 Table 形式展示所有上下文变量列表
3. 点击 Table 行的"replay"按钮可以在 HITL 窗口中查看该变量详情
4. HITL 窗口以只读模式展示，仅提供"关闭"按钮
5. 保持与现有 UI 风格一致
