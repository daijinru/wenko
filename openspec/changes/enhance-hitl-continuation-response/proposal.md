# Change: Enhance HITL Continuation Response Quality

## Why

当用户花费心力填写复杂的 HITL 表单（如旅行规划、活动策划、健康咨询等）后，AI 的 continuation 响应往往过于简短，仅仅确认收到信息而不提供实质性的建议、分析或帮助。这导致用户感觉"辛苦填写没有得到回报"，降低了 HITL 功能的价值感。

例如，用户填写了详细的旅行规划表单：
- 目的地：京都
- 出行日期：3月下旬（樱花季）
- 天数：5天
- 预算：中等
- 兴趣：寺庙、美食、传统文化

但 AI 的回复可能只是："好的，我了解了你的旅行偏好。"而不是提供具体的行程建议、必去景点推荐、预算分配建议等实质性内容。

## What Changes

- **MODIFIED**: HITL continuation 提示词模板，明确要求 AI 提供详尽、有价值的响应
- **ADDED**: 响应质量指导原则，根据表单类型和复杂度调整响应深度
- **ADDED**: 表单复杂度评估机制，用于判断所需的响应详细程度
- **MODIFIED**: `build_continuation_context` 函数，增强上下文指令以引导高质量响应
- **ADDED**: UI 加载提示，在 HITL 表单提交后显示"AI 正在分析您的信息..."

## Impact

- Affected specs: `hitl-interaction` (强化 continuation 响应质量要求)
- Affected code:
  - `workflow/chat_processor.py:HITL_CONTINUATION_PROMPT_TEMPLATE` - 更新提示词模板
  - `workflow/hitl_handler.py:build_continuation_context` - 增强上下文构建逻辑
  - `electron/live2d/live2d-widget/src/chat.ts` - 添加加载提示 UI
