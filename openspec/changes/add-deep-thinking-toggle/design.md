# Design: 深度思考模式开关

## Context

现代大模型（如 Claude 3.5 Sonnet、GPT-4o）支持"Extended Thinking"或"Reasoning"模式，允许模型在回答前进行更深入的推理。这种模式能显著提升复杂问题的回答质量，但会增加 token 消耗和响应延迟。

当前系统通过 OpenAI 兼容接口调用 LLM，需要支持用户灵活控制是否启用深度思考功能。

## Goals / Non-Goals

**Goals:**
- 提供用户可控的深度思考模式开关
- 开关关闭时有效减弱模型的思考行为
- 在 UI 中清晰展示模式的影响（token 消耗、等待时间）
- 保持与各种 OpenAI 兼容 API 的兼容性

**Non-Goals:**
- 不支持细粒度的 thinking budget 配置（保持简单）
- 不在本次变更中添加 token 使用统计功能
- 不针对特定模型做特殊适配（使用通用参数）

## Decisions

### 1. 存储位置：使用现有的 app_settings 表

**决策**: 复用现有的 `app_settings` 表存储开关状态

**理由**:
- 系统已有成熟的设置存储机制
- 与其他系统开关（如 `system.memory_emotion_enabled`）保持一致
- 无需新增数据库迁移

**设置键**: `llm.deep_thinking_enabled`
**默认值**: `false`（关闭）

### 2. 关闭深度思考的策略

当深度思考开关关闭时，采用多层策略减弱模型思考行为：

**策略 1: API 参数级别**
```python
request_body = {
    "model": config.model,
    "messages": messages,
    # 基础策略：降低温度减少发散思考
    "temperature": min(config.temperature, 0.3),
    # OpenAI o1/o3 系列：使用低推理努力
    "reasoning_effort": "low",
    # Claude API：不添加 thinking 参数即为关闭
    # DeepSeek：reasoning 模型无法关闭思考，只能通过模型选择
}
```

**策略 2: Prompt 级别**
在系统提示词末尾追加指令（仅当深度思考关闭时）：
```
请直接回答问题，不需要展示思考过程。保持简洁明了。
```

**策略 3: 输出后处理**
- 移除以 `<thinking>` 或类似标记包裹的内容
- 这是兜底策略，确保即使模型仍然输出思考内容也能过滤

### 3. 开启深度思考的策略

当深度思考开关开启时：

```python
request_body = {
    "model": config.model,
    "messages": messages,
    "temperature": config.temperature,  # 使用用户配置的温度
    # OpenAI o1/o3 系列模型
    "reasoning_effort": "high",
    # Claude API (extended thinking)
    "thinking": {
        "type": "enabled",
        "budget_tokens": 10000,  # 默认 10K tokens 思考预算
    },
}
```

### 4. API 兼容性处理

由于不同 LLM 提供商对深度思考的支持方式不同，采用渐进增强策略：

1. **基础兼容**（所有 API）：通过 temperature 和 prompt 控制
2. **增强兼容**（支持 reasoning 参数的 API）：添加 reasoning 相关参数
3. **错误容忍**：如果 API 不支持某个参数，捕获错误并回退到基础兼容模式

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 某些 API 不支持 thinking 参数 | 参数被忽略或报错 | 使用 try-catch 包裹，回退到 prompt 级别控制 |
| Prompt 级别控制效果有限 | 模型仍可能进行内部推理 | 可接受，用户主要关心的是 token 消耗，prompt 控制可减少输出的思考内容 |
| 用户不理解 token 消耗含义 | 产生意外费用 | 在 UI 中提供清晰的提示信息 |

## UI Design

在 LLM 配置区域添加开关，位于 `temperature` 设置之后：

```
┌─────────────────────────────────────────────────────┐
│ 深度思考模式                              [  开关  ] │
│ ─────────────────────────────────────────────────── │
│ 启用后，AI 将进行更深入的分析和推理，               │
│ 适合处理复杂问题。                                   │
│                                                     │
│ ⚠️ 请注意：此模式可能会消耗更多 tokens              │
│    并增加响应等待时间。                              │
└─────────────────────────────────────────────────────┘
```

## Open Questions

1. ~~是否需要支持 thinking budget 的精细控制？~~ **决定：不需要，保持简单的开/关即可**
2. ~~是否需要在对话界面显示当前模式？~~ **决定：暂不需要，仅在设置中显示**
