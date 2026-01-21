# Change: Enhance HITL Form Trigger Rate

## Why

当前HITL表单的触发概率过低。LLM仅在非常明确的场景（如用户明确要求选择）才会生成hitl_request，导致系统失去很多通过结构化表单收集用户信息的机会。情感记忆系统的核心价值之一是了解用户偏好，而HITL表单是收集高质量结构化偏好数据的最佳途径。

## What Changes

- **MODIFIED**: 扩展 HITL_INSTRUCTION 模板，增加更多触发场景
- **ADDED**: 主动询问策略（Proactive Inquiry Strategy）
- **ADDED**: 话题深化触发机制（Topic Deepening Triggers）
- **ADDED**: 情感响应表单触发（Emotion-driven Form Triggers）
- **ADDED**: 记忆补全触发（Memory Gap Detection Triggers）

## Impact

- Affected specs: `hitl-middleware`, `hitl-interaction`
- Affected code:
  - `workflow/chat_processor.py` - 修改 HITL_INSTRUCTION 模板
  - `workflow/hitl_handler.py` - 可能增加触发逻辑辅助函数
