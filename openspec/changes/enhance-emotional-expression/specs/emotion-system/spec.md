# 情感系统增强 Spec Delta

## ADDED Requirements

### Requirement: Improved Heuristic Confidence Scoring

情感启发式检测 SHALL 根据匹配关键词数量动态计算置信度，而非使用固定值。

置信度计算规则 SHALL 为：
- 匹配 1 个关键词：confidence = 0.3
- 匹配 2 个关键词：confidence = 0.5
- 匹配 3 个及以上关键词：confidence = 0.7

#### Scenario: Single keyword match returns low confidence

- **GIVEN** 用户消息中仅包含 1 个情感关键词
- **WHEN** 启发式检测分析消息
- **THEN** 返回的 `confidence` SHALL 为 0.3

#### Scenario: Multiple keyword matches increase confidence

- **GIVEN** 用户消息中包含 3 个或以上同类情感关键词
- **WHEN** 启发式检测分析消息
- **THEN** 返回的 `confidence` SHALL 为 0.7
- **AND** 所有匹配的关键词 SHALL 记录在 `indicators` 中

### Requirement: Emotion History Tracking

系统 SHALL 在工作记忆中维护情感历史记录，追踪最近对话轮次的情感变化。

情感历史记录 SHALL 包含以下信息：
- `emotion`: 检测到的情感类型
- `confidence`: 检测置信度
- `turn`: 对话轮次序号

系统 SHALL 保留最近 10 轮的情感记录，超出时移除最早的记录。

#### Scenario: Append emotion to history after each turn

- **GIVEN** 一轮对话完成且情感检测产生结果
- **WHEN** 系统更新工作记忆
- **THEN** 系统 SHALL 将当前情感结果追加到 `emotion_history` 列表

#### Scenario: History limit enforced

- **GIVEN** `emotion_history` 已包含 10 条记录
- **WHEN** 新的情感记录追加
- **THEN** 系统 SHALL 移除最早的记录，保持列表长度不超过 10

### Requirement: Current-Turn Emotion Strategy

系统 SHALL 使用当前轮次的启发式情感检测结果来影响当前轮次的响应策略，消除两阶段延迟。

当 EmotionNode 检测到高置信度（≥ 阈值）情感时，该情感 SHALL 直接用于当前轮的策略选择。

#### Scenario: High-confidence heuristic emotion drives current turn strategy

- **GIVEN** EmotionNode 检测到情感 `sad`，置信度 0.7（≥ 阈值 0.5）
- **WHEN** ReasoningNode 构建 LLM prompt
- **THEN** 系统 SHALL 使用 `sad` 对应的响应策略（empathetic tone）
- **AND** 不等待下一轮才应用该策略

#### Scenario: Low-confidence heuristic falls back to last_emotion

- **GIVEN** EmotionNode 检测置信度 0.3（< 阈值 0.5）
- **AND** 上一轮 `last_emotion` 为 `curious`
- **WHEN** ReasoningNode 构建 LLM prompt
- **THEN** 系统 SHALL 使用 `curious` 对应的响应策略

### Requirement: Modulation Instruction Injection

系统 SHALL 将 EmotionNode 产生的 `modulation_instruction` 实际注入到 LLM 的 system prompt 中，作为情感调节指令。

`modulation_instruction` SHALL 作为 system prompt 的补充区段，不替换已有的策略参数。

#### Scenario: Modulation instruction appears in LLM prompt

- **GIVEN** EmotionNode 检测到情感为 `anxious`
- **AND** `modulation_instruction` 为 "User is anxious. Be calm, reassuring, and clear."
- **WHEN** 系统构建 LLM system prompt
- **THEN** prompt 中 SHALL 包含该 modulation_instruction 内容

#### Scenario: No modulation for neutral emotion

- **GIVEN** EmotionNode 检测到情感为 `neutral`
- **WHEN** 系统构建 LLM system prompt
- **THEN** prompt 中 MAY 省略 modulation_instruction 区段或使用默认指令

## MODIFIED Requirements

### Requirement: Deterministic Response Strategy Mapping

系统 SHALL 使用确定性规则引擎完成"情绪 → 响应策略"的映射，不使用 LLM 参与策略选择。

响应策略 SHALL 包含以下参数：
- `tone`: 语气指令（如 `professional`, `warm`, `empathetic`）
- `max_length`: 目标回复长度（字符数）
- `use_memory`: 是否在回复中引用长期记忆
- `proactive_question`: 是否主动向用户提问
- `formality`: 正式程度（`casual` | `formal`）
- `emoji_allowed`: 是否允许使用表情符号

`emoji_allowed` SHALL 根据情感类别设置：
- `positive` 类（happy, excited, grateful, curious）: `emoji_allowed = true`
- `seeking` 类（help_seeking, info_seeking, validation_seeking）: `emoji_allowed = true`
- `negative` 类和 `neutral`: `emoji_allowed = false`

策略映射 SHALL 完全确定性：相同的情绪输入必须产生相同的策略选择。

#### Scenario: Map neutral emotion to professional strategy

- **GIVEN** 检测到用户情绪为 `neutral`
- **WHEN** 策略引擎选择响应策略
- **THEN** 系统 SHALL 选择以下策略：
  - `tone`: `professional`
  - `max_length`: 300
  - `use_memory`: true
  - `proactive_question`: false
  - `emoji_allowed`: false

#### Scenario: Map happy emotion to warm strategy with emoji

- **GIVEN** 检测到用户情绪为 `happy`
- **WHEN** 策略引擎选择响应策略
- **THEN** 系统 SHALL 选择以下策略：
  - `tone`: `warm`
  - `max_length`: 250
  - `use_memory`: true
  - `proactive_question`: true
  - `emoji_allowed`: true

#### Scenario: Map sad emotion to empathetic strategy without emoji

- **GIVEN** 检测到用户情绪为 `sad`
- **WHEN** 策略引擎选择响应策略
- **THEN** 系统 SHALL 选择以下策略：
  - `tone`: `empathetic`
  - `max_length`: 400
  - `use_memory`: true
  - `proactive_question`: false
  - `emoji_allowed`: false

#### Scenario: Fallback for unknown emotion

- **GIVEN** 情绪类型为 `unknown` 或不在预定义列表中
- **WHEN** 策略引擎选择响应策略
- **THEN** 系统 SHALL 使用 `neutral` 对应的默认策略
