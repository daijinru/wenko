# AI Chat Memory System Specification

## ADDED Requirements

### Requirement: Working Memory Management

系统 SHALL 为每个活跃会话维护结构化的工作记忆，包含当前对话上下文、临时变量和会话状态。

工作记忆 SHALL 包含以下字段：
- `session_id`: 会话唯一标识符
- `current_topic`: 当前讨论主题（可选）
- `context_variables`: 键值对形式的上下文变量
- `turn_count`: 当前会话对话轮次
- `last_emotion`: 上一轮检测到的用户情绪
- `created_at`: 创建时间
- `updated_at`: 最后更新时间

工作记忆 SHALL 在会话无活动 30 分钟后自动清理。

#### Scenario: Working memory creation on new session

- **GIVEN** 用户发起新会话
- **WHEN** 系统收到首条消息
- **THEN** 系统 SHALL 创建新的工作记忆记录
- **AND** 初始化 `turn_count` 为 1
- **AND** 设置 `created_at` 和 `updated_at` 为当前时间

#### Scenario: Working memory update on each turn

- **GIVEN** 存在活跃的工作记忆
- **WHEN** 用户发送新消息
- **THEN** 系统 SHALL 递增 `turn_count`
- **AND** 更新 `updated_at` 为当前时间
- **AND** 根据 LLM 分析结果更新 `current_topic` 和 `context_variables`

#### Scenario: Working memory auto-cleanup

- **GIVEN** 工作记忆存在
- **WHEN** 会话无活动超过 30 分钟
- **THEN** 系统 SHALL 自动删除该工作记忆
- **AND** 可选择将重要信息归档到长期记忆

### Requirement: Long-term Memory Storage

系统 SHALL 支持跨会话的长期记忆存储，用于保存用户偏好、重要事实和交互模式。

长期记忆条目 SHALL 包含以下字段：
- `id`: 记忆条目唯一标识符
- `session_id`: 来源会话 ID
- `category`: 记忆类别（`preference` | `fact` | `pattern`）
- `key`: 记忆键名
- `value`: 记忆内容（支持 JSON 结构）
- `confidence`: 置信度（0.0 - 1.0）
- `source`: 来源（`user_stated` | `inferred` | `system`）
- `created_at`: 创建时间
- `last_accessed`: 最后访问时间
- `access_count`: 访问次数

#### Scenario: Create long-term memory from user statement

- **GIVEN** 用户在对话中明确表达偏好或事实
- **WHEN** LLM 识别到可存储的信息并输出 `memory_update.should_store=true`
- **THEN** 系统 SHALL 创建长期记忆条目
- **AND** 设置 `source` 为 `user_stated`
- **AND** 设置 `confidence` 为 0.9 或更高

#### Scenario: Retrieve relevant long-term memories

- **GIVEN** 存在多条长期记忆
- **WHEN** 用户发送新消息
- **THEN** 系统 SHALL 检索与消息相关的长期记忆
- **AND** 按相关性评分排序
- **AND** 返回最多 N 条相关记忆（N 由配置参数 `MEMORY_RETRIEVAL_LIMIT` 控制，默认 5）

#### Scenario: Memory access tracking

- **GIVEN** 长期记忆被检索并使用
- **WHEN** 记忆内容被包含在 LLM 上下文中
- **THEN** 系统 SHALL 更新 `last_accessed` 为当前时间
- **AND** 递增 `access_count`

### Requirement: Memory Retrieval Algorithm

系统 SHALL 实现多策略记忆检索算法，结合关键词匹配、类别过滤和相关性评分。

检索算法 SHALL 包含以下阶段：
1. **关键词提取**: 从用户消息中提取关键词
2. **候选召回**: 基于关键词和类别进行初步筛选
3. **相关性评分**: 对候选记忆计算综合评分
4. **结果排序**: 按评分降序返回 Top-N 结果

相关性评分 SHALL 综合考虑以下因素：
- `keyword_score`: 关键词匹配度（0.0 - 1.0）
- `category_boost`: 类别权重加成
- `recency_score`: 时间衰减因子
- `frequency_score`: 访问频率因子
- `confidence`: 记忆置信度

#### Scenario: Keyword extraction from user message

- **GIVEN** 用户发送消息 "我喜欢用 Python 写代码"
- **WHEN** 系统执行关键词提取
- **THEN** 系统 SHALL 提取有意义的关键词，如 `["Python", "代码", "喜欢"]`
- **AND** 过滤停用词（如 "我"、"用"、"写"）
- **AND** 支持中英文混合提取

#### Scenario: Category-based candidate recall

- **GIVEN** 存在不同类别的长期记忆
- **WHEN** 用户消息涉及偏好表达（如 "我喜欢..."）
- **THEN** 系统 SHALL 优先召回 `preference` 类别的记忆
- **AND** 对 `preference` 类别应用 1.5x 的 `category_boost`

#### Scenario: Keyword matching with SQLite FTS

- **GIVEN** 长期记忆表配置了 SQLite FTS5 全文索引
- **WHEN** 执行关键词匹配检索
- **THEN** 系统 SHALL 使用 FTS5 的 `MATCH` 语法进行高效检索
- **AND** 支持前缀匹配（如 "Pyth*" 匹配 "Python"）
- **AND** 返回 BM25 相关性评分作为 `keyword_score`

#### Scenario: Fallback to LIKE matching

- **GIVEN** FTS5 索引不可用或查询失败
- **WHEN** 执行关键词匹配检索
- **THEN** 系统 SHALL 降级使用 SQL `LIKE` 模糊匹配
- **AND** 基于匹配关键词数量计算 `keyword_score`

#### Scenario: Relevance score calculation

- **GIVEN** 候选记忆集合已召回
- **WHEN** 计算综合相关性评分
- **THEN** 系统 SHALL 使用以下公式：
  ```
  score = (keyword_score * 0.4)
        + (category_boost * 0.2)
        + (recency_score * 0.15)
        + (frequency_score * 0.1)
        + (confidence * 0.15)
  ```
- **AND** `recency_score` 基于 `last_accessed` 计算时间衰减（半衰期 7 天）
- **AND** `frequency_score` 基于 `access_count` 的对数归一化

#### Scenario: Empty retrieval result

- **GIVEN** 没有记忆与用户消息匹配
- **WHEN** 检索完成
- **THEN** 系统 SHALL 返回空列表
- **AND** 不影响后续对话流程

#### Scenario: Working memory context boost

- **GIVEN** 当前会话有活跃的工作记忆
- **AND** 工作记忆中记录了 `current_topic`
- **WHEN** 执行记忆检索
- **THEN** 系统 SHALL 将 `current_topic` 相关关键词加入检索条件
- **AND** 对与当前主题相关的记忆应用 1.3x 的额外加成

### Requirement: Memory Lifecycle Management

系统 SHALL 提供长期记忆的生命周期管理，包括淘汰、删除和用户控制。

#### Scenario: Memory storage capacity

- **GIVEN** 长期记忆使用 SQLite 存储
- **WHEN** 系统运行在现有技术框架下
- **THEN** 系统 SHALL 支持 SQLite 数据库的最大存储容量（理论上限 281 TB，实际受磁盘空间限制）
- **AND** 单表行数上限为 2^64 行（约 1.8 × 10^19 条记录）
- **AND** 系统不设置人为的记忆条目数量上限

#### Scenario: Optional memory eviction for performance

- **GIVEN** 长期记忆条目数量增长导致检索性能下降
- **WHEN** 管理员配置了可选的淘汰策略
- **THEN** 系统 MAY 根据以下规则淘汰旧记忆：
  - 优先淘汰 `confidence` 最低的条目
  - 相同置信度时，淘汰 `last_accessed` 最早的条目
- **AND** 淘汰阈值由配置参数 `MEMORY_EVICTION_THRESHOLD` 控制（可选，默认不启用）

#### Scenario: User delete specific memory

- **GIVEN** 用户请求删除特定记忆
- **WHEN** API 收到删除请求
- **THEN** 系统 SHALL 永久删除指定记忆条目
- **AND** 返回删除成功确认

#### Scenario: User clear all memories

- **GIVEN** 用户请求清除所有记忆
- **WHEN** API 收到清除请求
- **THEN** 系统 SHALL 删除该用户的所有长期记忆
- **AND** 保留工作记忆直到会话结束

### Requirement: Memory API Endpoints

系统 SHALL 提供 RESTful API 用于记忆管理操作。

API 端点 SHALL 包括：
- `GET /memory/long-term` - 列出所有长期记忆
- `GET /memory/long-term/{id}` - 获取特定记忆详情
- `DELETE /memory/long-term/{id}` - 删除特定记忆
- `DELETE /memory/long-term` - 清除所有长期记忆
- `GET /memory/working/{session_id}` - 获取会话工作记忆

#### Scenario: List long-term memories with pagination

- **GIVEN** 存在多条长期记忆
- **WHEN** 客户端请求 `GET /memory/long-term?limit=10&offset=0`
- **THEN** 系统 SHALL 返回分页的记忆列表
- **AND** 包含总数和分页信息

#### Scenario: Get working memory for session

- **GIVEN** 存在活跃会话
- **WHEN** 客户端请求 `GET /memory/working/{session_id}`
- **THEN** 系统 SHALL 返回该会话的工作记忆内容
- **AND** 如会话不存在则返回 404
