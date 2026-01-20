# Change: 优化长期记忆的自动保存和主动保存

## Why

当前系统中，AI 对话过程中识别的事实、结论和偏好需要用户手动保存到长期记忆。主动保存对话框的键名和值也是通用默认值，需要用户手动编辑。这增加了用户操作负担，降低了记忆系统的实用性。

## What Changes

### 1. 自动保存优化
- AI 在对话中识别到事实、偏好、结论时，自动保存到长期记忆
- 利用现有的 `memory_update` 机制，确保所有识别的信息都被保存
- 保存后通过 UI 提示用户（可选的 Toast 通知）

### 2. 主动保存优化（智能提取）
- "保存到长期记忆" 按钮点击后，调用 AI 分析消息内容
- AI 自动提取摘要作为键名，原文或结构化信息作为值
- 智能推断类别（preference/fact/pattern）
- 预填充到对话框，用户可修改后保存

### 3. 前端增强
- SaveMemoryDialog 组件增加"智能提取"按钮或自动提取模式
- 显示 AI 提取结果的加载状态
- 优化用户体验，减少手动输入

## Impact

- Affected specs: `ai-chat-memory`
- Affected code:
  - `workflow/chat_processor.py` - 自动保存逻辑已存在，确保正常工作
  - `workflow/main.py` - 新增智能提取 API 端点
  - `electron/src/renderer/workflow/components/features/chat-history/save-memory-dialog.tsx` - 智能提取 UI
  - `electron/src/renderer/workflow/lib/api-client.ts` - 新增 API 调用

## Related Changes

- `add-memory-emotion-system` - 现有记忆情感系统基础
- `improve-context-memory-retrieval` - 记忆检索优化
