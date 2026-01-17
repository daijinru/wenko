# Tasks

## 1. Backend: HITL Continuation Endpoint

- [x] 1.1 创建 `/hitl/continue` SSE 端点，接收 HITL 响应并触发 LLM 继续对话
- [x] 1.2 在 `hitl_handler.py` 中添加 `build_continuation_context()` 构建 HITL 响应上下文
- [x] 1.3 修改 `HITLResponseResult` 添加 `continuation_data` 字段传递用户响应数据

## 2. Chat Processor: HITL Response Context

- [x] 2.1 在 `chat_processor.py` 添加 HITL 响应上下文模板
- [x] 2.2 创建 `build_hitl_continuation_prompt()` 将用户表单响应转为 LLM 可理解的格式
- [x] 2.3 支持在 continuation 中返回新的 HITL 请求（链式交互）

## 3. Frontend: Auto-trigger Continuation

- [x] 3.1 修改 `submitHITLResponse()` 在完成后**自动**调用 continuation 端点（approve 和 reject 都触发）
- [x] 3.2 处理 continuation SSE 响应，渲染 AI 回复
- [x] 3.3 支持 continuation 中返回的新 HITL 请求，形成交互链
- [x] 3.4 添加 loading 状态指示器，显示 AI 正在处理

## 4. Testing and Validation

- [ ] 4.1 测试 approve 后的 AI 自动继续对话
- [ ] 4.2 测试 reject 后的 AI 自动继续对话（验证 AI 能收到 reject 信息并适当响应）
- [ ] 4.3 测试连续多个 HITL 请求的链式交互
