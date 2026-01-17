# Change: Add HITL Continuation for Multi-turn Conversations

## Why

当前 HITL 实现只支持单轮交互：用户提交表单后，AI 无法获取用户的响应数据，也无法基于此继续对话或发起新的 HITL 请求。这限制了 AI 收集多项信息、确认复杂操作或进行引导式交互的能力。

一个完整的多轮对话场景应该是：
1. AI 发起 HITL 请求询问用户偏好
2. 用户填写并提交表单
3. AI 获取用户响应，基于此继续对话（如确认、追问或执行操作）
4. AI 可能发起新的 HITL 请求，形成交互链

## What Changes

- **ADDED**: HITL 响应后的 AI 继续对话能力
- **MODIFIED**: 前端 HITL 表单提交后自动触发后续对话
- **ADDED**: 后端 `/hitl/continue` 端点，将用户响应转发给 LLM 继续处理
- **ADDED**: LLM 提示词支持 HITL 响应上下文

## Impact

- Affected specs: `hitl-interaction` (新增继续对话能力)
- Affected code:
  - `workflow/main.py` - 新增 HITL 继续端点
  - `workflow/hitl_handler.py` - 新增响应上下文构建
  - `workflow/chat_processor.py` - 新增 HITL 响应处理提示词
  - `electron/live2d/live2d-widget/src/chat.ts` - 前端自动触发继续对话
