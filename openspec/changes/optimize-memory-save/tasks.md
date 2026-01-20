## 1. Backend - 智能提取 API

- [x] 1.1 在 `workflow/main.py` 中添加 `POST /memory/extract` 端点
- [x] 1.2 创建 `workflow/memory_extractor.py` 模块，实现 LLM 提取逻辑
- [x] 1.3 设计提取 prompt，指导 LLM 从消息中提取键名、摘要和类别
- [x] 1.4 添加 Pydantic 模型定义请求和响应结构

## 2. Frontend - SaveMemoryDialog 智能提取

- [x] 2.1 在 `api-client.ts` 中添加 `extractMemory` API 调用（使用通用 api.post）
- [x] 2.2 修改 `SaveMemoryDialog` 组件，对话框打开时自动调用提取 API
- [x] 2.3 添加加载状态 UI（Spinner 或骨架屏）
- [x] 2.4 提取成功后预填充表单字段
- [x] 2.5 提取失败时使用现有默认值，显示提示
- [x] 2.6 添加"使用原文"按钮，用户可恢复到原始消息内容

## 3. 自动保存优化

- [x] 3.1 审查 `chat_processor.py` 中的 `CHAT_PROMPT_TEMPLATE`
- [x] 3.2 增强 prompt 指令，确保 LLM 更积极识别可保存信息
- [x] 3.3 添加自动保存的 UI 通知（Toast 提示）
  - 后端：在 SSE 流中添加 `memory_saved` 事件
  - 前端：`chat.ts` 处理事件并调用 `showMemoryNotification`
  - UI：渐变背景的 Toast 通知，显示保存的记忆数量和键名

## 4. 测试与验证

- [ ] 4.1 测试智能提取 API 对不同类型消息的处理
- [ ] 4.2 验证 SaveMemoryDialog 的智能提取流程
- [ ] 4.3 验证自动保存在对话中的正常工作
- [ ] 4.4 边界情况测试：空消息、超长消息、特殊字符

## Dependencies

- 任务 2.x 依赖 1.x 完成
- 任务 3.x 可与 1.x、2.x 并行
- 任务 4.x 依赖所有实现完成
