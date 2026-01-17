# Design: HITL Continuation for Multi-turn Conversations

## Context

当前 HITL 系统实现了 AI 向用户发起表单请求的能力，但缺少闭环：用户响应后 AI 无法继续对话。这导致 HITL 只能用于简单的单次数据收集，无法支持：
- 确认用户选择后的操作执行
- 基于用户响应的追问或澄清
- 多步骤的引导式交互流程

### 相关模块

- `workflow/main.py:800-836` - 当前 `/hitl/respond` 端点
- `workflow/hitl_handler.py:104-154` - `process_hitl_response()` 处理逻辑
- `electron/live2d/live2d-widget/src/chat.ts:493-528` - 前端 `submitHITLResponse()`

## Goals / Non-Goals

### Goals
- 用户提交 HITL 表单后，AI 能获取响应数据并继续对话
- 支持链式 HITL 请求（AI 可在继续对话中发起新的 HITL）
- 保持现有 HITL 表单机制不变

### Non-Goals
- 不改变 HITL 表单的 Schema 结构
- 不实现复杂的状态机或工作流引擎
- 不支持 HITL 请求的撤销或修改

## Decisions

### Decision 1: 新增 `/hitl/continue` 端点 vs 修改 `/hitl/respond` 返回流

**选择**: 新增独立的 `/hitl/continue` SSE 端点

**原因**:
- `/hitl/respond` 是简单的 JSON 响应，改为 SSE 会破坏 API 语义
- 分离关注点：respond 处理用户输入验证和存储，continue 处理 AI 继续对话
- 前端可以选择是否触发 continuation（某些场景可能不需要）

### Decision 2: Continuation 触发方式

**选择**: 前端在 `submitHITLResponse` 完成后**自动**调用 continuation（无论 approve 或 reject）

**原因**:
- 对用户透明，无需额外操作
- 保持对话流畅性
- Reject 也需要 continuation，让 AI 能够响应用户的拒绝（如换一种方式提问、跳过该话题等）
- 自动调用确保多轮对话的连贯性，无需用户手动触发

### Decision 3: HITL 响应上下文格式

**选择**: 将用户响应转换为结构化的提示词注入

**格式示例**:
```
用户刚才通过表单提交了以下信息:
表单标题: 运动偏好
- 您最喜欢的运动: 篮球
- 运动频率: 每周3次

请根据用户的选择继续对话。
```

**原因**:
- LLM 易于理解结构化文本
- 保留表单语义（标题、字段标签）
- 支持所有字段类型

## Risks / Trade-offs

### Risk 1: 循环 HITL 请求
- **风险**: AI 可能在 continuation 中无限发起 HITL 请求
- **缓解**: 添加最大 HITL 链深度限制（建议 5 层）

### Risk 2: 会话状态复杂性
- **风险**: 多个 pending HITL 请求可能导致状态混乱
- **缓解**: 每次只允许一个活跃的 HITL 请求，新请求自动覆盖旧请求

### Risk 3: 用户体验
- **风险**: 快速连续的 HITL 可能让用户感到被"轰炸"
- **缓解**: 由 AI prompt 引导，避免无必要的 HITL 请求

## Migration Plan

无需迁移，新功能向后兼容现有实现。

## Resolved Decisions

1. **Reject 后是否也触发 continuation？**
   - **决定**: 是。无论用户 approve 还是 reject，都自动触发 continuation
   - AI 可以根据 reject 行为调整响应（如换一种方式提问、跳过该话题、表达理解等）

2. **Continuation 是否自动触发？**
   - **决定**: 是。前端在 HITL 响应完成后自动调用 continuation，无需用户额外操作
   - 这确保多轮对话的连贯性和流畅性

## Open Questions

1. Continuation 是否支持取消？
   - 建议: 当前不支持，后续可考虑添加取消按钮
