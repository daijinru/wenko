# AI Chat Emotion Recognition and Response Strategy Specification

## ADDED Requirements

### Requirement: Structured Emotion Detection

系统 SHALL 使用 LLM 对用户消息进行情绪识别，并输出结构化的 JSON 结果。

情绪识别结果 SHALL 包含以下字段：
- `primary`: 主要情绪类型
- `category`: 情绪大类（`positive` | `negative` | `neutral` | `seeking`）
- `confidence`: 置信度（0.0 - 1.0）
- `indicators`: 识别依据列表

支持的情绪类型 SHALL 包括：
- **neutral**: 无明显情绪
- **positive 类**: `happy`, `excited`, `grateful`, `curious`
- **negative 类**: `sad`, `anxious`, `frustrated`, `confused`
- **seeking 类**: `help_seeking`, `info_seeking`, `validation_seeking`

LLM SHALL 仅负责情绪识别，不参与策略选择或系统决策。

#### Scenario: Detect positive emotion

- **GIVEN** 用户发送包含积极情绪的消息
- **WHEN** 系统分析消息内容
- **THEN** 系统 SHALL 返回情绪识别结果，包含：
  - `primary`: 具体情绪类型（如 `happy`）
  - `category`: `positive`
  - `confidence`: 0.0-1.0 的置信度值
  - `indicators`: 识别依据（如 `["感叹号", "积极词汇"]`）

#### Scenario: Detect negative emotion

- **GIVEN** 用户发送包含消极情绪的消息
- **WHEN** 系统分析消息内容
- **THEN** 系统 SHALL 返回情绪识别结果，包含：
  - `primary`: 具体情绪类型（如 `anxious`, `frustrated`）
  - `category`: `negative`
  - `confidence`: 0.0-1.0 的置信度值
  - `indicators`: 识别依据

#### Scenario: Fallback on low confidence

- **GIVEN** 情绪识别置信度低于阈值（0.5）
- **WHEN** 系统处理识别结果
- **THEN** 系统 SHALL 将情绪降级为 `neutral`
- **AND** 使用默认响应策略

#### Scenario: Handle malformed LLM output

- **GIVEN** LLM 返回的 JSON 格式不正确
- **WHEN** 系统尝试解析情绪识别结果
- **THEN** 系统 SHALL 将情绪标记为 `unknown`
- **AND** 使用 `neutral` 策略作为 fallback
- **AND** 记录解析错误日志

### Requirement: Deterministic Response Strategy Mapping

系统 SHALL 使用确定性规则引擎完成"情绪 → 响应策略"的映射，不使用 LLM 参与策略选择。

响应策略 SHALL 包含以下参数：
- `tone`: 语气指令（如 `professional`, `warm`, `empathetic`）
- `max_length`: 目标回复长度（字符数）
- `use_memory`: 是否在回复中引用长期记忆
- `proactive_question`: 是否主动向用户提问
- `formality`: 正式程度（`casual` | `formal`）
- `emoji_allowed`: 是否允许使用表情符号

策略映射 SHALL 完全确定性：相同的情绪输入必须产生相同的策略选择。

#### Scenario: Map neutral emotion to professional strategy

- **GIVEN** 检测到用户情绪为 `neutral`
- **WHEN** 策略引擎选择响应策略
- **THEN** 系统 SHALL 选择以下策略：
  - `tone`: `professional`
  - `max_length`: 300
  - `use_memory`: true
  - `proactive_question`: false

#### Scenario: Map sad emotion to empathetic strategy

- **GIVEN** 检测到用户情绪为 `sad`
- **WHEN** 策略引擎选择响应策略
- **THEN** 系统 SHALL 选择以下策略：
  - `tone`: `empathetic`
  - `max_length`: 400
  - `use_memory`: true
  - `proactive_question`: false（避免打扰用户）

#### Scenario: Map help_seeking emotion to helpful strategy

- **GIVEN** 检测到用户情绪为 `help_seeking`
- **WHEN** 策略引擎选择响应策略
- **THEN** 系统 SHALL 选择以下策略：
  - `tone`: `helpful`
  - `max_length`: 600
  - `use_memory`: true
  - `proactive_question`: true

#### Scenario: Fallback for unknown emotion

- **GIVEN** 情绪类型为 `unknown` 或不在预定义列表中
- **WHEN** 策略引擎选择响应策略
- **THEN** 系统 SHALL 使用 `neutral` 对应的默认策略

### Requirement: Strategy-Guided Response Generation

系统 SHALL 将响应策略参数注入到 LLM prompt 中，指导回复生成。

LLM SHALL 仅根据策略参数生成语言，不参与策略选择或修改。

回复生成 prompt SHALL 明确包含：
- 语气要求
- 长度限制
- 是否可引用记忆内容
- 是否应主动追问

#### Scenario: Generate response with empathetic tone

- **GIVEN** 策略指定 `tone: empathetic`
- **WHEN** LLM 生成回复
- **THEN** 回复内容 SHALL 体现理解和关心
- **AND** 避免使用冷淡或机械的语言

#### Scenario: Respect max_length constraint

- **GIVEN** 策略指定 `max_length: 300`
- **WHEN** LLM 生成回复
- **THEN** 回复长度 SHALL 接近但不显著超过 300 字符
- **AND** 允许 20% 的弹性空间

#### Scenario: Include memory reference when allowed

- **GIVEN** 策略指定 `use_memory: true`
- **AND** 存在相关的长期记忆
- **WHEN** LLM 生成回复
- **THEN** 回复 MAY 自然地引用记忆内容
- **AND** 引用应自然融入对话，不生硬

#### Scenario: Proactive question when enabled

- **GIVEN** 策略指定 `proactive_question: true`
- **WHEN** LLM 生成回复
- **THEN** 回复 SHOULD 包含一个相关的追问
- **AND** 追问应有助于深入了解用户需求

### Requirement: LLM Role Constraints

系统 SHALL 严格限制 LLM 的职责范围，确保系统行为可控。

LLM SHALL 仅负责：
1. 情绪识别（输出结构化 JSON）
2. 按既定策略生成语言

LLM SHALL NOT 参与：
- 策略选择或修改
- 系统状态判断
- 记忆管理决策（除了建议存储，最终由规则决定）
- 对话流程控制

#### Scenario: LLM attempts to modify strategy

- **GIVEN** LLM 输出中尝试建议不同的策略
- **WHEN** 系统处理 LLM 响应
- **THEN** 系统 SHALL 忽略策略建议
- **AND** 仅使用规则引擎选择的策略

#### Scenario: Consistent behavior across sessions

- **GIVEN** 相同的用户情绪和消息内容
- **WHEN** 在不同会话中处理相同输入
- **THEN** 系统 SHALL 选择相同的响应策略
- **AND** 回复风格应保持一致（虽然具体内容可能不同）

### Requirement: Response Style Consistency

系统 SHALL 确保回复风格在相同策略下保持一致，不随 LLM 版本或随机性变化。

#### Scenario: Consistent tone across conversations

- **GIVEN** 多次对话使用相同的 `tone` 策略参数
- **WHEN** 比较回复风格
- **THEN** 回复 SHALL 保持一致的语气特征
- **AND** 不应出现风格跳跃

#### Scenario: Predictable response structure

- **GIVEN** 策略参数完全相同
- **WHEN** 处理类似的用户消息
- **THEN** 回复结构 SHOULD 保持相似
- **AND** 包含或不包含追问的行为应一致
