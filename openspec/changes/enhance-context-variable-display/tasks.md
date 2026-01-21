# Tasks: enhance-context-variable-display

## Phase 1: Workflow UI Changes

- [x] **1.1** 创建 `context-variable-dialog.tsx` 对话框组件
  - 使用 shadcn/ui Dialog
  - 以 Table 形式展示上下文变量列表（键名、类型、预览、操作）
  - 操作列包含"replay"按钮
  - 包含"关闭"按钮

- [x] **1.2** 修改 `memory-list.tsx` 添加上下文变量按钮
  - 在操作单元格添加"上下文"按钮（清除按钮右侧）
  - 移除展开行中的 `<details>` 上下文变量展示
  - 添加对话框状态管理和事件处理

- [x] **1.3** 更新 `MemoryListProps` 接口
  - 使用组件内部状态管理对话框（无需修改 Props）
  - 在组件内管理对话框状态

## Phase 2: HITL Readonly Mode Support

- [x] **2.1** 更新 `electron/src/renderer/hitl/types/hitl.ts`
  - 在 `HITLRequest` 接口添加 `readonly?: boolean` 属性

- [x] **2.2** 修改 `electron/src/renderer/hitl/App.tsx`
  - 检测 `request.readonly` 标识
  - 传递 readonly 属性到子组件

- [x] **2.3** 修改 `electron/src/renderer/hitl/components/hitl-field.tsx`
  - 支持 `readonly` 属性
  - 只读模式下禁用所有输入字段

- [x] **2.4** 修改 `electron/src/renderer/hitl/components/hitl-actions.tsx`
  - 只读模式下隐藏 approve/reject 按钮，仅显示关闭

## Phase 3: IPC Integration

- [x] **3.1** 修改 `electron/main.cjs`
  - 在 `hitl:open-window` handler 中支持 readonly 模式
  - 只读模式不设置 TTL 超时
  - 只读模式关闭时不发送取消消息到 Live2D

- [x] **3.2** 实现 `buildReplayFields()` 工具函数
  - 优先使用保存的 `fields_def` 恢复原始表单结构
  - 兼容旧数据格式（fallback 到 text/textarea）
  - 处理对象、数组、基本类型

- [x] **3.3** 在 `context-variable-dialog.tsx` 实现 IPC 调用
  - 点击"replay"按钮时调用 `hitl:open-window`
  - 传递 `readonly: true` 和转换后的 fields

## Phase 4: Validation

- [x] **4.1** 功能测试
  - 构建成功验证
  - 代码逻辑验证

- [x] **4.2** UI 验证
  - 主题样式一致（复用 classic-stylesheets）
  - 只读字段视觉效果正确

## Phase 5: Replay Enhancement (新增)

- [x] **5.1** 修改后端 `workflow/hitl_handler.py`
  - 在 `_persist_to_working_memory()` 中保存完整 `fields_def`
  - 保存原始 `form_data` (field_name -> value)
  - 保持向后兼容（旧数据仍可显示）

- [x] **5.2** 更新前端 `context-variable-dialog.tsx`
  - 识别 HITL 上下文值结构
  - 使用 `fields_def` 和 `form_data` 重建原始表单
  - 改进表格显示（显示字段数量和时间戳）

## Dependencies

- Task 1.1 必须在 1.2 之前完成 ✓
- Task 2.1-2.4 可并行进行 ✓
- Task 3.1 可与 Phase 2 并行进行 ✓
- Task 3.2-3.3 依赖 Phase 1 和 Phase 2 完成 ✓
- Task 4.1-4.2 依赖所有前置任务完成 ✓
- Task 5.1-5.2 为增强功能，需后端配合 ✓
