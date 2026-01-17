# Change: Improve Session Context Understanding and Memory Retrieval

## Why

当前系统在会话上下文理解和长期记忆检索方面存在两个核心问题：

### 问题 1：会话上下文丢失
- 用户通过 HITL 表单提交的行程安排等结构化信息，在后续对话中 AI 无法有效回忆
- 工作记忆 (Working Memory) 虽然存储了 `context_variables`，但未将 HITL 表单数据持久化到其中
- AI 在处理 continuation 时，无法获取之前表单提交的完整上下文

### 问题 2：长期记忆检索匹配过于严格
- 当前使用关键词精确匹配 + FTS5 全文搜索
- 记忆 key 为 "你喜欢的颜色"，用户输入 "我喜欢的颜色" 或 "喜欢的颜色" 或 "颜色" 均无法命中
- 人称代词差异（你/我）、前缀省略、语义等价表达等常见情况未能处理
- 导致用户必须使用与存储完全一致的表述才能触发记忆

## What Changes

### 1. HITL 表单数据持久化到工作记忆

- **MODIFIED**: `hitl_handler._process_form_data()` - 将表单数据存储到工作记忆的 `context_variables`
- **MODIFIED**: `chat_processor.build_hitl_continuation_prompt()` - 在继续对话时注入完整的工作记忆上下文
- 确保 AI 在后续对话中能访问之前表单收集的所有信息

### 2. 记忆检索模糊匹配增强

- **ADDED**: 人称代词归一化处理
  - "你喜欢的颜色" / "我喜欢的颜色" / "喜欢的颜色" 统一处理
  - 替换规则：你→我、我→你、您→我 等双向映射

- **ADDED**: 前缀/后缀容错匹配
  - "喜欢的颜色" 可以匹配 "你喜欢的颜色"
  - 使用子串匹配作为 FTS5 的补充策略

- **ADDED**: 同义词/近义词扩展（轻量级）
  - 常见同义词映射表（如：颜色/色彩、喜欢/喜爱）
  - 可配置的同义词扩展开关

### 3. 记忆检索评分算法优化

- **MODIFIED**: `memory_manager.retrieve_relevant_memories()` - 增加模糊匹配评分维度
- **ADDED**: 部分匹配分数计算 - 关键词部分匹配时给予降级分数而非零分
- **MODIFIED**: 评分权重调整 - 允许配置各维度权重

## Impact

### Affected Specs
- **MODIFIED**: `ai-chat-memory` - 增加模糊检索和上下文持久化需求

### Affected Code

**后端 (Python)**:
- `workflow/memory_manager.py`
  - 新增 `normalize_pronouns()` 函数
  - 新增 `expand_synonyms()` 函数
  - 修改 `_calculate_keyword_score()` 支持模糊匹配
  - 修改 `retrieve_relevant_memories()` 增加候选扩展逻辑

- `workflow/hitl_handler.py`
  - 修改 `_process_form_data()` 同步写入工作记忆

- `workflow/chat_processor.py`
  - 修改 continuation prompt 构建逻辑

**新增配置文件**:
- `workflow/memory_config.py` (可选) - 同义词表、权重配置等

### Backward Compatibility
- 完全向后兼容，现有记忆数据无需迁移
- 新功能为增量增强，不破坏现有匹配逻辑

## Non-Goals

- 本提案**不**实现语义向量搜索（需要 embedding 模型，增加复杂度）
- 本提案**不**修改记忆存储结构（使用现有 schema）
- 本提案**不**引入外部 NLP 库依赖（使用轻量级规则实现）
