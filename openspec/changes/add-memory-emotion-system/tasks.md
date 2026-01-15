# Tasks: Structured Memory and Emotion Recognition System

## 1. Database Schema Extension

- [x] 1.1 创建 `working_memory` 表
  - 字段: session_id, current_topic, context_variables (JSON), turn_count, last_emotion, created_at, updated_at
  - 索引: session_id (PRIMARY)

- [x] 1.2 创建 `long_term_memory` 表
  - 字段: id, session_id, category, key, value (JSON), confidence, source, created_at, last_accessed, access_count
  - 索引: id (PRIMARY), category, key, last_accessed

- [x] 1.3 创建 FTS5 全文检索虚拟表
  - 创建 `memory_fts` 虚拟表，关联 `long_term_memory`
  - 配置 `tokenize='unicode61 remove_diacritics 2'` 支持 Unicode
  - 创建同步触发器（INSERT/UPDATE/DELETE）

- [x] 1.4 编写数据库迁移脚本
  - 确保向后兼容现有 chat_history.db
  - 添加版本控制标记

## 2. Memory Manager Implementation

- [x] 2.1 创建 `workflow/memory_manager.py` 模块
  - 定义 Pydantic 模型: WorkingMemory, MemoryEntry, MemoryCategory

- [x] 2.2 实现工作记忆 CRUD 操作
  - `create_working_memory(session_id)`
  - `get_working_memory(session_id)`
  - `update_working_memory(session_id, updates)`
  - `delete_working_memory(session_id)`

- [x] 2.3 实现长期记忆 CRUD 操作
  - `create_memory_entry(entry)`
  - `get_memory_entry(id)`
  - `update_memory_entry(id, updates)`
  - `delete_memory_entry(id)`
  - `delete_all_memories()`

- [x] 2.4 实现记忆检索逻辑

  **2.4.1 关键词提取模块**
  - [x] 添加 `jieba` 依赖用于中文分词（可选，有 fallback）
  - [x] 实现 `extract_keywords(message, max_keywords=10)` 函数
  - [x] 定义中英文停用词表（精简版，约 50 词）
  - [x] 支持中英文混合文本处理
  - [x] 过滤短词（< 2 字符）和纯数字

  **2.4.2 候选召回模块**
  - [x] 实现 `recall_candidates_fts(keywords, limit)` - FTS5 检索
    - 构建 FTS5 MATCH 查询语句
    - 支持前缀匹配（`keyword*`）
    - 返回 BM25 评分
  - [x] 实现 `recall_candidates_like(keywords, limit)` - LIKE 降级检索
    - 使用 SQL LIKE 模糊匹配
    - 作为 FTS5 不可用时的 fallback
  - [x] 实现候选召回数量限制（默认 50，可配置）

  **2.4.3 相关性评分模块**
  - [x] 定义 `RetrievalResult` 数据类
  - [x] 定义评分权重配置 `SCORE_WEIGHTS`
    - keyword: 0.40
    - category: 0.20
    - recency: 0.15
    - frequency: 0.10
    - confidence: 0.15
  - [x] 定义类别权重配置 `CATEGORY_WEIGHTS`
    - preference: 1.5
    - fact: 1.2
    - pattern: 1.0
  - [x] 实现 `calculate_keyword_score(memory, keywords)` - 关键词匹配度
  - [x] 实现 `calculate_recency_score(last_accessed)` - 时间衰减（半衰期 7 天）
  - [x] 实现 `calculate_frequency_score(access_count, max_count)` - 对数归一化
  - [x] 实现 `is_topic_related(memory, topic)` - 主题相关性判断

  **2.4.4 主检索函数**
  - [x] 实现 `retrieve_relevant_memories(user_message, working_memory, limit, candidate_limit)`
    - Stage 1: 调用关键词提取
    - Stage 2: 候选召回（FTS5 优先，LIKE 兜底）
    - Stage 3: 计算综合相关性评分
    - Stage 4: 排序并返回 Top-N
  - [x] 支持工作记忆上下文加成（current_topic 相关记忆 1.3x）
  - [x] 实现空结果处理（返回空列表，不影响流程）

  **2.4.5 访问追踪**
  - [x] 实现 `update_memory_access(memory_ids)` - 批量更新访问记录
    - 更新 `last_accessed` 时间戳
    - 递增 `access_count`

- [x] 2.5 实现记忆生命周期管理
  - `cleanup_expired_working_memory(timeout_minutes=30)`
  - `evict_memories_by_threshold(threshold)` (可选，仅在配置 `MEMORY_EVICTION_THRESHOLD` 时启用)

- [ ] 2.6 编写 Memory Manager 单元测试
  - [ ] 工作记忆 CRUD 测试
  - [ ] 长期记忆 CRUD 测试
  - [ ] 关键词提取测试
  - [ ] FTS5 检索测试
  - [ ] LIKE 降级检索测试
  - [ ] 相关性评分测试
  - [ ] 完整检索流程测试
  - [ ] 访问追踪测试

## 3. Emotion Detection Module

- [x] 3.1 创建 `workflow/emotion_detector.py` 模块
  - 定义情绪类型枚举: EmotionType, EmotionCategory
  - 定义输出模型: EmotionResult

- [x] 3.2 实现情绪解析器
  - `parse_emotion_from_llm_output(json_str) -> EmotionResult`
  - JSON Schema 验证
  - 错误处理和 fallback 逻辑

- [x] 3.3 实现置信度阈值逻辑
  - 低置信度 (< 0.5) 降级为 neutral
  - 记录降级事件用于后续分析

- [ ] 3.4 编写 Emotion Detector 单元测试
  - 测试各种情绪类型解析
  - 测试 malformed JSON 处理
  - 测试置信度降级逻辑

## 4. Response Strategy Engine

- [x] 4.1 创建 `workflow/response_strategy.py` 模块
  - 定义 ResponseStrategy Pydantic 模型
  - 定义 EMOTION_STRATEGY_MAP 映射表

- [x] 4.2 实现策略选择器
  - `select_strategy(emotion: EmotionResult) -> ResponseStrategy`
  - 完全确定性实现
  - 未知情绪 fallback 到 neutral

- [x] 4.3 定义初始策略映射
  - neutral, happy, excited, grateful, curious
  - sad, anxious, frustrated, confused
  - help_seeking, info_seeking, validation_seeking

- [x] 4.4 实现策略参数到 prompt 注入
  - `build_strategy_prompt(strategy: ResponseStrategy) -> str`

- [ ] 4.5 编写 Response Strategy 单元测试
  - 测试所有情绪类型的策略映射
  - 验证确定性行为

## 5. LLM Integration Refactoring

- [x] 5.1 设计新的 LLM prompt 模板
  - 集成情绪识别任务
  - 集成策略指导回复生成
  - 定义 JSON 输出格式

- [x] 5.2 重构 `stream_chat_response` 函数
  - 注入工作记忆摘要
  - 注入相关长期记忆
  - 注入响应策略参数

- [x] 5.3 实现 LLM 输出解析
  - 解析 emotion 字段
  - 解析 response 字段
  - 解析 memory_update 建议

- [x] 5.4 实现两阶段策略机制
  - 首轮使用默认策略
  - 后续轮次使用检测到的情绪对应策略

- [x] 5.5 添加配置开关
  - `USE_MEMORY_EMOTION_SYSTEM` 环境变量
  - 支持回退到简单模式

## 6. API Endpoints

- [x] 6.1 添加长期记忆 API 端点
  - `GET /memory/long-term` - 列表（支持分页）
  - `GET /memory/long-term/{id}` - 详情
  - `DELETE /memory/long-term/{id}` - 删除单条
  - `DELETE /memory/long-term` - 清空所有

- [x] 6.2 添加工作记忆 API 端点
  - `GET /memory/working/{session_id}` - 获取会话工作记忆

- [ ] 6.3 编写 API 端点集成测试

## 7. Frontend Adaptation

- [x] 7.1 更新 `chat.ts` 适配新的 API 响应格式
  - 处理包含 emotion 和 response 的 JSON 结构
  - 向后兼容旧格式

- [x] 7.2 添加情绪指示器 UI
  - 显示当前检测到的情绪状态
  - 根据情绪类型显示对应图标或颜色
  - 显示置信度（可选）

## 8. Workflow Panel Memory Management

- [x] 8.1 扩展 Memory API 端点
  - `POST /memory/long-term` - 手动创建记忆条目
  - `PUT /memory/long-term/{id}` - 更新记忆条目
  - `POST /memory/long-term/batch-delete` - 批量删除
  - `GET /memory/long-term/export` - 导出为 JSON
  - `POST /memory/long-term/import` - 从 JSON 导入

- [x] 8.2 创建 Workflow 记忆管理前端组件
  - 在 App.jsx 中实现 MemoryTab 组件
  - 记忆列表展示（支持分页）
  - 记忆卡片展示
  - 记忆编辑对话框
  - 筛选和搜索栏
  - 批量操作工具栏

- [x] 8.3 实现记忆列表功能
  - 分页展示所有长期记忆条目
  - 按类别筛选（preference / fact / pattern）
  - 按时间/访问次数/置信度排序

- [x] 8.4 实现记忆 CRUD 操作 UI
  - 查看记忆详情（类别、键值、置信度、来源、访问统计）
  - 手动添加记忆（source 标记为 `user_stated`）
  - 编辑记忆（key、value、category、confidence）
  - 单条删除和批量删除

- [x] 8.5 实现导入/导出功能
  - 导出所有记忆为 JSON 文件
  - 从 JSON 文件导入记忆
  - 导入冲突处理（覆盖/跳过/合并）

- [ ] 8.6 编写 Workflow 记忆管理测试
  - API 端点测试
  - 前端组件单元测试
  - 导入/导出功能测试

## 9. Documentation and Testing

- [ ] 9.1 更新 chat_config.example.json
  - 添加新配置项说明

- [ ] 9.2 编写集成测试
  - 完整对话流程测试
  - 记忆存储和检索测试
  - 策略一致性测试

- [ ] 9.3 性能测试
  - 验证单次 LLM 调用延迟
  - 验证记忆检索性能
    - 测试 1000 条记忆下的检索延迟（目标 < 50ms）
    - 测试 10000 条记忆下的检索延迟（目标 < 100ms）
    - 测试 FTS5 vs LIKE 性能对比
  - 验证关键词提取性能（目标 < 10ms）

## Dependencies

- Task 2 依赖 Task 1（数据库 schema）
- Task 3, 4 可并行开发
- Task 5 依赖 Task 2, 3, 4
- Task 6 依赖 Task 2, 5
- Task 7 依赖 Task 5
- Task 8 依赖 Task 6（Memory API）
- Task 9 依赖所有前序任务

## Validation Criteria

- [ ] 所有单元测试通过
- [ ] 集成测试覆盖主要场景
- [x] 相同输入产生相同策略选择（确定性验证）
- [x] 回退机制正常工作
- [ ] 性能符合预期（响应延迟增加 < 100ms）

## Implementation Summary

### Completed Files

1. **workflow/chat_db.py** - Extended with V2 schema (working_memory, long_term_memory, memory_fts)
2. **workflow/memory_manager.py** - Complete memory management module with:
   - WorkingMemory and MemoryEntry dataclasses
   - CRUD operations for both memory types
   - Multi-stage retrieval algorithm (keyword extraction, FTS5/LIKE recall, relevance scoring)
   - Access tracking and lifecycle management
3. **workflow/emotion_detector.py** - Emotion detection module with:
   - EmotionType and EmotionCategory enums
   - LLM output parsing with JSON validation
   - Confidence threshold handling
4. **workflow/response_strategy.py** - Response strategy engine with:
   - Deterministic emotion-to-strategy mapping
   - Strategy prompt building
5. **workflow/chat_processor.py** - Chat processing integration with:
   - Context building with memory
   - Prompt templates for LLM
   - Response processing
6. **workflow/main.py** - Updated with:
   - Memory-aware chat processing
   - Complete Memory API endpoints (CRUD, batch, import/export)
7. **electron/live2d/live2d-widget/src/chat.ts** - Updated with:
   - Emotion event handling
   - Emotion indicator UI components
8. **electron/src/renderer/workflow/App.jsx** - Updated with:
   - Memory management Tab
   - Memory list, filter, and CRUD UI
   - Memory edit dialog
