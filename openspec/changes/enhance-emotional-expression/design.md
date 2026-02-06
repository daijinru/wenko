# Design: 强化情感感知、情感表现与情感 UI 呈现

## Context

当前 Wenko 的情感系统具备基础的情绪检测和策略映射能力，但在以下方面存在明显不足：

1. **检测路径断裂**：EmotionNode（启发式）产生的 `modulation_instruction` 未在 `chat_processor.build_system_prompt()` 中使用，形成"检测了但没用"的局面
2. **策略延迟**：采用两阶段策略（上一轮的情感驱动下一轮），首轮总是 neutral，情感响应滞后一轮
3. **UI 未连接**：Live2D 情感指示器基础设施已就绪（`EMOTION_DISPLAY`、`createEmotionIndicator`），但 `createChatInput()` 中 `onEmotion` 传入 `undefined`

## Goals / Non-Goals

### Goals
- 让情感检测结果在当前轮即刻影响回复策略
- 将 modulation_instruction 实际注入 LLM prompt，强化情感表现
- 连接 Live2D 聊天 UI 的情感指示器，让用户看到 AI 感知到的情感
- 增加情感历史追踪，支持趋势展示
- 适度开放 emoji 使用，提升情感表现力

### Non-Goals
- 不更换情感分类体系（保持现有 12 种情绪类型）
- 不引入 Live2D 模型表情动画（需要模型资源支持，留作后续）
- 不引入额外的 LLM 调用（保持单次调用架构）
- 不修改记忆系统核心逻辑

## Decisions

### Decision 1: 情感感知 — 优化置信度与即时策略

**现状**：
- `extract_emotion_from_text()` 返回固定 confidence=0.3
- 默认阈值 0.5，导致几乎所有启发式检测被降级为 neutral
- 策略基于上一轮 `last_emotion`，首轮为 neutral

**方案**：
- 改进置信度计算：多关键词命中时递增（1个=0.3, 2个=0.5, 3个+=0.7）
- EmotionNode 的检测结果直接影响当前轮策略选择（通过 `emotional_context` 传递到 ReasoningNode）
- ReasoningNode 在构建 prompt 时，同时考虑 `emotional_context.current_emotion`（启发式）和上一轮的 `last_emotion`

```
用户消息 → EmotionNode(启发式) → emotional_context
                                        ↓
                                  ReasoningNode(构建prompt时)
                                  ├── emotional_context.modulation_instruction → 注入prompt
                                  └── response_strategy(emotion) → 策略参数注入prompt
```

**Rationale**: 不增加 LLM 调用次数，利用已有启发式检测的即时性，与 LLM 情感检测形成互补。

### Decision 2: 情感表现 — Modulation Instruction 注入

**现状**：
- `EmotionNode._get_modulation_instruction()` 生成了英文情感指令
- `chat_processor.py` 的 `SYSTEM_PROMPT_TEMPLATE` 中无 `{emotion_modulation}` 占位符

**方案**：
在 `chat_processor.build_system_prompt()` 中增加 emotion_modulation 区段：

```python
# 在 system prompt 末尾追加
if emotion_modulation:
    prompt += f"\n\n## 情感调节\n{emotion_modulation}"
```

ReasoningNode 负责将 `emotional_context.modulation_instruction` 传递给 chat_processor。

### Decision 3: 情感表现 — Emoji 策略

**现状**：所有情绪对应的 `emoji_allowed` 均为 `False`。

**方案**：
- `positive` 类（happy, excited, grateful, curious）: `emoji_allowed = True`
- `seeking` 类（help_seeking, info_seeking, validation_seeking）: `emoji_allowed = True`
- `negative` 类和 `neutral`: 保持 `emoji_allowed = False`

**Rationale**: 积极情感和寻求型场景使用 emoji 可增强亲和力，消极情感场景使用 emoji 可能显得不合适。

### Decision 4: 情感历史追踪

**方案**：
在 `WorkingMemory` 中增加 `emotion_history` 字段：

```python
class WorkingMemory:
    # 现有字段...
    emotion_history: List[Dict] = []  # [{emotion, confidence, turn}]
```

- 每轮对话后追加当前情感到 `emotion_history`
- 保留最近 10 轮记录
- 通过 working memory API 暴露给前端

### Decision 5: 情感 UI — 连接 Live2D 情感指示器

**现状**：
- `createChatInput()` 中 `onEmotion: undefined`
- `createEmotionIndicator()` 和 `updateEmotionIndicator()` 已实现

**方案**：
- 在 `createChatInput()` 中传入有效的 `onEmotion` 回调
- 接收 SSE `emotion` 事件后更新情感指示器的颜色、标签和置信度
- 情感指示器显示在 Live2D 聊天气泡区域

### Decision 6: 情感 UI — Workflow 面板情感历史

**方案**：
- 在 Workflow 面板的 Working Memory 区域增加"情感历史"展示
- 以简洁列表形式展示最近 10 轮的情感变化
- 每条记录显示：情感类型（带颜色标记）、置信度、轮次序号

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| 启发式置信度提升可能导致误判增加 | 错误的情感策略 | 仍保留阈值机制，仅在多关键词命中时提升 |
| modulation_instruction 与 strategy tone 可能冲突 | LLM 接收矛盾指令 | modulation_instruction 作为补充建议，strategy 参数作为硬约束 |
| emotion_history 增加 working memory 数据量 | API 响应变大 | 限制最近 10 轮，单条记录数据量极小 |

## Open Questions

无 — 当前方案均使用现有基础设施，无需引入新依赖或架构变更。
