# Design: Structured Memory and Emotion Recognition System

## Context

当前系统使用简单的消息历史列表作为上下文，LLM 直接生成回复。这种设计：
- 无法区分临时信息与持久知识
- 无法保证回复风格一致性
- 难以测试和维护

本设计引入分层架构，将记忆管理、情绪识别、策略选择和语言生成分离。

## Goals / Non-Goals

### Goals
- 实现结构化的工作记忆和长期记忆
- 使用 LLM 进行情绪识别，输出结构化结果
- 使用确定性规则完成情绪到策略的映射
- 保证系统行为稳定、可测试、可审计

### Non-Goals
- 不实现复杂的情感计算模型
- 不追求 AI 自主决策
- 不增加 LLM 调用次数

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Message                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Memory Manager                                │
│  ┌─────────────────────┐    ┌─────────────────────────────────┐ │
│  │   Working Memory    │    │      Long-term Memory           │ │
│  │  - current_topic    │    │  - user_preferences             │ │
│  │  - context_vars     │    │  - important_facts              │ │
│  │  - turn_count       │    │  - interaction_patterns         │ │
│  └─────────────────────┘    └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Call (Single Request)                     │
│  Input:                                                          │
│    - user_message                                                │
│    - working_memory_summary                                      │
│    - relevant_long_term_memory                                   │
│    - emotion_detection_prompt                                    │
│    - response_generation_prompt (with strategy params)           │
│  Output (JSON):                                                  │
│    - emotion: { type, confidence, indicators }                   │
│    - response: string                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┴───────────────────┐
          ▼                                       ▼
┌─────────────────────┐             ┌─────────────────────────────┐
│  Emotion Detector   │             │    Response Strategy        │
│  - parse emotion    │────────────▶│    Engine (Deterministic)   │
│  - validate schema  │             │    - emotion → strategy     │
└─────────────────────┘             │    - apply constraints      │
                                    └─────────────────────────────┘
                                                  │
                                                  ▼
                                    ┌─────────────────────────────┐
                                    │      Final Response         │
                                    │  (Strategy-constrained)     │
                                    └─────────────────────────────┘
```

## Decisions

### Decision 1: Memory Structure

采用两层记忆架构：

**Working Memory (工作记忆)**
```python
class WorkingMemory(BaseModel):
    session_id: str
    current_topic: Optional[str] = None
    context_variables: Dict[str, Any] = {}
    turn_count: int = 0
    last_emotion: Optional[str] = None
    created_at: datetime
    updated_at: datetime
```

**Long-term Memory (长期记忆)**
```python
class MemoryEntry(BaseModel):
    id: str
    session_id: str  # 来源会话
    category: MemoryCategory  # preference | fact | pattern
    key: str
    value: Any
    confidence: float  # 0.0 - 1.0
    source: str  # user_stated | inferred | system
    created_at: datetime
    last_accessed: datetime
    access_count: int
```

**Alternatives Considered**:
- 向量数据库存储: 增加复杂度，当前规模不需要
- 图数据库: 过度设计，简单键值对足够

**Rationale**: SQLite + JSON 字段，简单可靠，与现有架构一致。

### Decision 2: Emotion Categories

定义有限的情绪分类体系（可扩展）：

| Category | Subcategories | Description |
|----------|---------------|-------------|
| `neutral` | - | 无明显情绪 |
| `positive` | `happy`, `excited`, `grateful`, `curious` | 积极情绪 |
| `negative` | `sad`, `anxious`, `frustrated`, `confused` | 消极情绪 |
| `seeking` | `help_seeking`, `info_seeking`, `validation_seeking` | 寻求型 |

**Emotion Detection Output Schema**:
```json
{
  "emotion": {
    "primary": "curious",
    "category": "positive",
    "confidence": 0.85,
    "indicators": ["question mark", "exploratory language"]
  }
}
```

**Rationale**: 有限分类确保策略映射完备，confidence 字段支持降级逻辑。

### Decision 3: Strategy Mapping (Deterministic)

使用配置文件定义策略映射，**无 LLM 参与**：

```python
# response_strategies.py

EMOTION_STRATEGY_MAP: Dict[str, ResponseStrategy] = {
    "neutral": ResponseStrategy(
        tone="professional",
        max_length=300,
        use_memory=True,
        proactive_question=False,
    ),
    "happy": ResponseStrategy(
        tone="warm",
        max_length=250,
        use_memory=True,
        proactive_question=True,
    ),
    "sad": ResponseStrategy(
        tone="empathetic",
        max_length=400,
        use_memory=True,
        proactive_question=False,
        # 不主动追问，避免打扰
    ),
    "anxious": ResponseStrategy(
        tone="calm_reassuring",
        max_length=350,
        use_memory=True,
        proactive_question=False,
    ),
    "confused": ResponseStrategy(
        tone="clear_explanatory",
        max_length=500,
        use_memory=True,
        proactive_question=True,
        # 主动澄清
    ),
    "help_seeking": ResponseStrategy(
        tone="helpful",
        max_length=600,
        use_memory=True,
        proactive_question=True,
    ),
    # ... 其他映射
}
```

**Strategy Parameters**:
```python
class ResponseStrategy(BaseModel):
    tone: str  # 语气指令，注入到 prompt
    max_length: int  # 目标长度
    use_memory: bool  # 是否引用长期记忆
    proactive_question: bool  # 是否主动追问
    formality: str = "casual"  # casual | formal
    emoji_allowed: bool = False
```

**Rationale**:
- 策略完全确定性，相同情绪 → 相同策略
- 易于测试：单元测试覆盖所有映射
- 易于调整：修改配置即可改变行为

### Decision 4: LLM Prompt Structure

单次 LLM 调用完成情绪识别和回复生成：

```python
CHAT_PROMPT_TEMPLATE = """
你是一个 AI 助手。请严格按照以下格式输出 JSON 响应。

## 输入信息
- 用户消息: {user_message}
- 工作记忆: {working_memory_summary}
- 相关长期记忆: {relevant_long_term_memory}

## 任务 1: 情绪识别
分析用户消息的情绪状态。

## 任务 2: 生成回复
按照以下策略参数生成回复：
- 语气: {tone}
- 目标长度: 约 {max_length} 字符
- 是否可以引用之前的记忆: {use_memory}
- 是否主动追问: {proactive_question}

## 输出格式 (严格 JSON)
```json
{
  "emotion": {
    "primary": "<emotion_type>",
    "category": "<positive|negative|neutral|seeking>",
    "confidence": <0.0-1.0>,
    "indicators": ["<indicator1>", "<indicator2>"]
  },
  "response": "<your response text>",
  "memory_update": {
    "should_store": <true|false>,
    "entries": [
      {
        "category": "<preference|fact|pattern>",
        "key": "<memory_key>",
        "value": "<memory_value>"
      }
    ]
  }
}
```
"""
```

**两阶段策略**:
1. **首次调用**: 使用默认策略（neutral）+ 情绪识别
2. **策略调整**: 如果检测到非 neutral 情绪，下一轮使用对应策略

**Alternative**: 两次 LLM 调用（先识别，后生成）
**Rationale**: 单次调用减少延迟和成本，使用"延迟策略"在下一轮应用。

### Decision 5: Memory Lifecycle

**Working Memory**:
- 创建: 会话开始
- 更新: 每轮对话后
- 清理: 会话结束后 30 分钟无活动自动清理
- 归档: 可选择将重要信息转存到长期记忆

**Long-term Memory**:
- 创建: LLM 建议 + 用户确认（或自动，基于 confidence）
- 访问: 每次对话检索相关记忆
- 衰减: 长期未访问的记忆降低优先级
- 删除: 用户显式删除或置信度过低自动清理

### Decision 6: Memory Retrieval Algorithm

采用多阶段检索架构，平衡检索效率和相关性准确度。

**检索流程图**:
```
┌─────────────────────────────────────────────────────────────────┐
│                      User Message                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Stage 1: Keyword Extraction                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Input: "我喜欢用 Python 写代码"                          │    │
│  │  Process:                                                │    │
│  │    1. Tokenization (jieba for Chinese, whitespace for EN)│    │
│  │    2. Stopword filtering                                 │    │
│  │    3. Keyword extraction                                 │    │
│  │  Output: ["Python", "代码", "喜欢"]                       │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Stage 2: Candidate Recall                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Primary: SQLite FTS5 full-text search                   │    │
│  │    - MATCH query with BM25 scoring                       │    │
│  │    - Prefix matching support ("Pyth*")                   │    │
│  │  Fallback: SQL LIKE matching                             │    │
│  │    - WHERE key LIKE '%keyword%' OR value LIKE '%keyword%'│    │
│  │  Limit: 50 candidates (configurable)                     │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Stage 3: Relevance Scoring                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  For each candidate memory:                              │    │
│  │                                                          │    │
│  │  keyword_score   = BM25 score (normalized to 0-1)        │    │
│  │  category_boost  = category_weights[memory.category]     │    │
│  │  recency_score   = exp(-λ * days_since_access)           │    │
│  │                    where λ = ln(2) / 7 (7-day half-life) │    │
│  │  frequency_score = log(access_count + 1) / log(max + 1)  │    │
│  │  confidence      = memory.confidence                     │    │
│  │                                                          │    │
│  │  final_score = (keyword_score   * 0.40)                  │    │
│  │              + (category_boost  * 0.20)                  │    │
│  │              + (recency_score   * 0.15)                  │    │
│  │              + (frequency_score * 0.10)                  │    │
│  │              + (confidence      * 0.15)                  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Stage 4: Result Ranking                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  1. Sort by final_score DESC                             │    │
│  │  2. Apply context boost (if working memory has topic)    │    │
│  │  3. Return Top-N (default N=5, configurable)             │    │
│  │  4. Update access tracking for returned memories         │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

**关键词提取实现**:
```python
import jieba
from typing import List, Set

# 中文停用词（精简版）
CHINESE_STOPWORDS: Set[str] = {
    "的", "是", "在", "我", "有", "和", "就", "不", "人", "都",
    "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你",
    "会", "着", "没有", "看", "好", "自己", "这", "那", "什么",
}

# 英文停用词（精简版）
ENGLISH_STOPWORDS: Set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "must", "shall",
    "i", "you", "he", "she", "it", "we", "they", "my", "your",
    "his", "her", "its", "our", "their", "this", "that", "these",
}

def extract_keywords(message: str, max_keywords: int = 10) -> List[str]:
    """
    从用户消息中提取关键词，支持中英文混合。

    Args:
        message: 用户消息文本
        max_keywords: 最大返回关键词数量

    Returns:
        关键词列表，按重要性排序
    """
    keywords = []

    # 使用 jieba 进行中文分词
    tokens = jieba.cut(message, cut_all=False)

    for token in tokens:
        token = token.strip().lower()

        # 跳过空白和短词
        if len(token) < 2:
            continue

        # 跳过停用词
        if token in CHINESE_STOPWORDS or token in ENGLISH_STOPWORDS:
            continue

        # 跳过纯数字（除非较长，可能是 ID）
        if token.isdigit() and len(token) < 4:
            continue

        keywords.append(token)

    # 去重并保持顺序
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    return unique_keywords[:max_keywords]
```

**SQLite FTS5 索引设计**:
```sql
-- 创建 FTS5 虚拟表用于全文检索
CREATE VIRTUAL TABLE memory_fts USING fts5(
    memory_id,      -- 关联到 long_term_memory.id
    key,            -- 记忆键名
    value_text,     -- 记忆内容（JSON 转文本）
    category,       -- 记忆类别
    tokenize='unicode61 remove_diacritics 2'  -- 支持 Unicode 分词
);

-- 同步触发器：插入
CREATE TRIGGER memory_fts_insert AFTER INSERT ON long_term_memory
BEGIN
    INSERT INTO memory_fts(memory_id, key, value_text, category)
    VALUES (NEW.id, NEW.key, json_extract(NEW.value, '$'), NEW.category);
END;

-- 同步触发器：删除
CREATE TRIGGER memory_fts_delete AFTER DELETE ON long_term_memory
BEGIN
    DELETE FROM memory_fts WHERE memory_id = OLD.id;
END;

-- 同步触发器：更新
CREATE TRIGGER memory_fts_update AFTER UPDATE ON long_term_memory
BEGIN
    DELETE FROM memory_fts WHERE memory_id = OLD.id;
    INSERT INTO memory_fts(memory_id, key, value_text, category)
    VALUES (NEW.id, NEW.key, json_extract(NEW.value, '$'), NEW.category);
END;
```

**检索查询实现**:
```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import math

@dataclass
class RetrievalResult:
    memory: MemoryEntry
    score: float
    keyword_score: float
    category_boost: float
    recency_score: float
    frequency_score: float

# 类别权重配置
CATEGORY_WEIGHTS = {
    "preference": 1.5,  # 偏好类记忆优先
    "fact": 1.2,        # 事实类记忆次之
    "pattern": 1.0,     # 模式类记忆基础权重
}

# 评分权重配置
SCORE_WEIGHTS = {
    "keyword": 0.40,
    "category": 0.20,
    "recency": 0.15,
    "frequency": 0.10,
    "confidence": 0.15,
}

def retrieve_relevant_memories(
    user_message: str,
    working_memory: Optional[WorkingMemory] = None,
    limit: int = 5,
    candidate_limit: int = 50,
) -> List[RetrievalResult]:
    """
    检索与用户消息相关的长期记忆。

    Args:
        user_message: 用户消息
        working_memory: 当前会话的工作记忆（可选）
        limit: 返回结果数量上限
        candidate_limit: 候选召回数量上限

    Returns:
        按相关性评分排序的检索结果列表
    """
    # Stage 1: 关键词提取
    keywords = extract_keywords(user_message)

    # 如果有工作记忆，加入当前主题关键词
    if working_memory and working_memory.current_topic:
        topic_keywords = extract_keywords(working_memory.current_topic)
        keywords = list(set(keywords + topic_keywords))

    if not keywords:
        return []

    # Stage 2: 候选召回（FTS5 优先，LIKE 兜底）
    candidates = recall_candidates_fts(keywords, candidate_limit)
    if not candidates:
        candidates = recall_candidates_like(keywords, candidate_limit)

    if not candidates:
        return []

    # Stage 3: 相关性评分
    results = []
    max_access_count = max(c.access_count for c in candidates) or 1

    for memory in candidates:
        # 计算各项得分
        keyword_score = calculate_keyword_score(memory, keywords)
        category_boost = CATEGORY_WEIGHTS.get(memory.category, 1.0)
        recency_score = calculate_recency_score(memory.last_accessed)
        frequency_score = calculate_frequency_score(
            memory.access_count, max_access_count
        )

        # 主题相关加成
        topic_boost = 1.0
        if working_memory and working_memory.current_topic:
            if is_topic_related(memory, working_memory.current_topic):
                topic_boost = 1.3

        # 综合评分
        final_score = (
            keyword_score * SCORE_WEIGHTS["keyword"]
            + category_boost * SCORE_WEIGHTS["category"]
            + recency_score * SCORE_WEIGHTS["recency"]
            + frequency_score * SCORE_WEIGHTS["frequency"]
            + memory.confidence * SCORE_WEIGHTS["confidence"]
        ) * topic_boost

        results.append(RetrievalResult(
            memory=memory,
            score=final_score,
            keyword_score=keyword_score,
            category_boost=category_boost,
            recency_score=recency_score,
            frequency_score=frequency_score,
        ))

    # Stage 4: 排序并返回 Top-N
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


def calculate_recency_score(last_accessed: datetime) -> float:
    """
    计算时间衰减得分，使用指数衰减，半衰期 7 天。
    """
    days_elapsed = (datetime.now() - last_accessed).days
    half_life = 7.0
    decay_rate = math.log(2) / half_life
    return math.exp(-decay_rate * days_elapsed)


def calculate_frequency_score(access_count: int, max_count: int) -> float:
    """
    计算访问频率得分，使用对数归一化。
    """
    if max_count <= 1:
        return 0.5
    return math.log(access_count + 1) / math.log(max_count + 1)
```

**Alternatives Considered**:
- **向量嵌入检索 (Embedding + Vector DB)**: 语义理解更强，但引入额外依赖（如 sentence-transformers），增加复杂度和延迟。当前规模下 FTS5 足够。
- **Elasticsearch**: 功能强大，但需要额外服务部署，不符合"本地优先"原则。
- **纯 SQL LIKE**: 性能较差，不支持相关性排序，仅作为 FTS5 的降级方案。

**Rationale**: SQLite FTS5 提供良好的全文检索能力，内置 BM25 评分，无需额外依赖，与现有 SQLite 架构一致。多阶段评分算法可调参优化，支持未来扩展。

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| 情绪识别准确率不足 | 策略选择错误 | 使用 confidence 阈值，低置信度时降级为 neutral |
| 长期记忆数据量增长 | 检索性能下降 | 使用数据库索引优化；可选配置淘汰策略用于极端场景 |
| 单次 LLM 调用 JSON 解析失败 | 无法获取情绪或回复 | Fallback: 返回原始文本，情绪标记为 unknown |
| 策略映射不完备 | 遇到未定义情绪 | Default fallback 到 neutral 策略 |

## Migration Plan

1. **Phase 1**: 添加数据库表结构（向后兼容）
2. **Phase 2**: 实现 Memory Manager（不影响现有流程）
3. **Phase 3**: 实现 Emotion Detector（与现有并行）
4. **Phase 4**: 集成 Response Strategy Engine
5. **Phase 5**: 切换到新流程，保留旧流程作为 fallback

**Rollback**: 配置开关 `USE_MEMORY_EMOTION_SYSTEM=false` 回退到简单模式。

### Decision 7: Workflow Panel Memory Management

在 workflow 管理面板中提供记忆条目的可视化管理界面，支持查看、编辑和删除操作。

**功能概述**:
```
┌─────────────────────────────────────────────────────────────────┐
│                    Workflow Panel - Memory Manager              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Filter: [All ▼] [preference] [fact] [pattern]         │    │
│  │  Search: [____________________] [🔍]                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  📌 preference | language_style                         │    │
│  │  Value: "喜欢简洁的回答风格"                              │    │
│  │  Confidence: 0.92  |  Accessed: 15 times                │    │
│  │  Created: 2024-01-10  |  Last: 2024-01-15               │    │
│  │  [Edit] [Delete]                                        │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │  📋 fact | programming_language                         │    │
│  │  Value: "主要使用 Python 和 TypeScript"                  │    │
│  │  Confidence: 0.95  |  Accessed: 8 times                 │    │
│  │  Created: 2024-01-08  |  Last: 2024-01-14               │    │
│  │  [Edit] [Delete]                                        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  [+ Add Memory]                      [Clear All] [Export JSON]  │
└─────────────────────────────────────────────────────────────────┘
```

**核心功能**:

| 功能 | 描述 |
|------|------|
| 记忆列表展示 | 分页展示所有长期记忆条目，支持按类别筛选和关键词搜索 |
| 记忆详情查看 | 展示记忆的完整信息：类别、键值、置信度、来源、访问统计 |
| 手动添加记忆 | 允许用户手动创建记忆条目，`source` 标记为 `user_stated` |
| 编辑记忆 | 修改记忆的 `key`、`value`、`category`、`confidence` 字段 |
| 删除记忆 | 单条删除或批量删除选中的记忆条目 |
| 导出/导入 | 支持 JSON 格式的记忆数据导出和导入 |

**API 扩展**:
```python
# 在现有 Memory API 基础上扩展

# 创建记忆（手动添加）
@app.post("/memory/long-term")
async def create_memory(entry: MemoryCreateRequest) -> MemoryEntry:
    """手动创建长期记忆条目"""
    pass

# 更新记忆
@app.put("/memory/long-term/{memory_id}")
async def update_memory(memory_id: str, entry: MemoryUpdateRequest) -> MemoryEntry:
    """更新指定记忆条目的内容"""
    pass

# 批量删除
@app.post("/memory/long-term/batch-delete")
async def batch_delete_memories(ids: List[str]) -> BatchDeleteResponse:
    """批量删除多条记忆"""
    pass

# 导出记忆
@app.get("/memory/long-term/export")
async def export_memories(format: str = "json") -> FileResponse:
    """导出所有记忆为 JSON 文件"""
    pass

# 导入记忆
@app.post("/memory/long-term/import")
async def import_memories(file: UploadFile) -> ImportResult:
    """从 JSON 文件导入记忆"""
    pass
```

**前端组件结构**:
```typescript
// workflow/components/MemoryManager.tsx

interface MemoryManagerProps {
  // 无需外部 props，组件内部管理状态
}

// 子组件
- MemoryList        // 记忆列表，支持分页和虚拟滚动
- MemoryCard        // 单条记忆卡片展示
- MemoryEditor      // 记忆编辑对话框
- MemoryFilter      // 筛选和搜索栏
- MemoryActions     // 批量操作工具栏
```

**Rationale**:
- 提供可视化管理界面，降低记忆系统的使用门槛
- 支持用户主动管理 AI 对其的"记忆"，增强可控性和透明度
- 符合 GDPR 等隐私法规对用户数据访问权的要求
- 导入/导出功能支持数据迁移和备份

## Open Questions

1. **长期记忆存储上限**: 系统不设置人为上限，完全依赖 SQLite 技术框架的最大容量：
   - SQLite 数据库最大容量: 281 TB
   - 单表最大行数: 2^64 行（约 1.8 × 10^19 条记录）
   - 实际容量受限于磁盘空间
   - 可选配置 `MEMORY_EVICTION_THRESHOLD` 用于性能优化场景

2. **用户可见性**: 是否向用户展示"我记住了 X"的反馈？建议: 可选功能，默认静默。

3. **隐私控制**: 用户是否可以查看/删除自己的长期记忆？建议: 必须支持，GDPR 合规。
