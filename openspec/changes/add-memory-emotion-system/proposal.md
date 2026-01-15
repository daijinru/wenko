# Change: Add Structured Memory and Emotion Recognition System

## Why

当前 live2d-ai-chat 功能使用简单的消息历史记录机制，存在以下局限：
1. **记忆管理粗放**: 仅通过 `MAX_HISTORY_LENGTH` 截断历史，无法区分重要信息与临时对话
2. **缺乏上下文理解**: 无法追踪跨会话的用户偏好、重要事实或长期关系
3. **回答风格不一致**: LLM 直接生成回复，缺乏统一的策略控制
4. **系统行为不可预测**: LLM 参与所有决策，导致行为难以测试和维护

本提案旨在引入结构化的记忆系统和基于规则的情绪响应机制，使系统行为稳定、可控、可维护。

## What Changes

### 1. 结构化记忆系统

- **ADDED**: Working Memory（工作记忆）- 当前会话的活跃上下文
  - 结构化存储当前对话主题、用户意图、临时变量
  - 会话结束后自动清理或选择性归档

- **ADDED**: Long-term Memory（长期记忆）- 跨会话的持久知识
  - 用户偏好（语言风格、兴趣领域、敏感话题）
  - 重要事实（用户告知的关键信息）
  - 交互模式（常见问题类型、使用习惯）

### 2. 情绪识别系统

- **ADDED**: 结构化情绪识别 - LLM 输出标准化情绪标签
  - 定义情绪分类体系（如: neutral, happy, sad, anxious, curious 等）
  - LLM 仅负责识别，不参与策略选择
  - 输出格式固定为 JSON Schema

### 3. 确定性响应策略

- **ADDED**: 情绪-策略映射规则引擎
  - 预定义的情绪到响应策略映射表
  - 策略包含：语气、回复长度、是否引用记忆、是否主动追问等参数
  - 规则完全确定性，无 LLM 参与

### 4. LLM 职责重新定义

- **MODIFIED**: LLM 调用流程
  - 输入: 用户消息 + 工作记忆摘要 + 相关长期记忆
  - 输出 1: 情绪识别结果（结构化 JSON）
  - 输出 2: 按指定策略生成的回复文本
  - LLM 不参与记忆管理、策略选择或系统状态判断

## Design Principles

本系统明确**不追求**拟人化表演，而追求：

| 目标 | 实现方式 |
|------|---------|
| 行为稳定 | 确定性规则引擎，相同输入产生相同策略选择 |
| 决策可控 | 所有策略预定义，可审计、可修改、可测试 |
| 回答风格一致 | 策略参数控制语气、长度、结构 |
| 架构可维护 | 职责分离：存储、识别、策略、生成各司其职 |

## Impact

### Affected Specs
- **NEW**: `ai-chat-memory` - 记忆系统规范
- **NEW**: `ai-chat-emotion` - 情绪识别与响应策略规范

### Affected Code

**后端 (Python)**:
- `workflow/chat_db.py` - 扩展数据库 schema，添加记忆表
- `workflow/main.py` - 重构聊天 API，集成记忆和情绪系统
- **NEW**: `workflow/memory_manager.py` - 记忆管理器
- **NEW**: `workflow/emotion_detector.py` - 情绪识别模块
- **NEW**: `workflow/response_strategy.py` - 响应策略引擎

**前端 (TypeScript)**:
- `electron/live2d/live2d-widget/src/chat.ts` - 适配新的 API 响应格式

### Database Schema Changes
- **NEW TABLE**: `working_memory` - 工作记忆存储
- **NEW TABLE**: `long_term_memory` - 长期记忆存储
- **NEW TABLE**: `response_strategies` - 响应策略配置（可选，也可用配置文件）

## Non-Goals

- 本提案**不**实现情感计算或复杂心理模型
- 本提案**不**追求 AI 自主决策或"涌现"行为
- 本提案**不**引入额外的 LLM 调用开销（合并为单次调用）
