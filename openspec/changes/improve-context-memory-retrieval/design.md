# Design: Context and Memory Retrieval Improvements

## Context

当前 Wenko 系统的记忆检索存在两个主要技术挑战：

1. **会话连续性断裂**：HITL 表单收集的结构化数据未能有效融入后续对话上下文
2. **记忆检索过于精确**：基于关键词的检索对用户表述的微小差异过于敏感

## Goals / Non-Goals

### Goals
- 确保 HITL 表单数据在整个会话生命周期内可访问
- 实现记忆检索的宽容匹配，提高命中率
- 保持系统简单性，避免引入重型依赖

### Non-Goals
- 不实现语义向量搜索（Embedding-based retrieval）
- 不引入机器学习模型进行意图理解
- 不修改数据库 schema

## Decisions

### Decision 1: HITL 数据存入工作记忆

**What**: 在 HITL 表单处理完成后，将表单数据以结构化方式存入 `working_memory.context_variables`

**Why**:
- 工作记忆已有完善的生命周期管理
- `context_variables` 字段设计用于存储会话级上下文
- 无需新增存储结构

**实现细节**:
```python
# hitl_handler.py
def _process_form_data(...):
    # 现有逻辑...

    # 新增：同步到工作记忆
    wm = memory_manager.get_or_create_working_memory(session_id)
    updated_ctx = wm.context_variables.copy()
    updated_ctx[f"hitl_{request.title}"] = {
        "fields": data,
        "timestamp": datetime.now().isoformat(),
    }
    memory_manager.update_working_memory(
        session_id,
        context_variables=updated_ctx,
    )
```

### Decision 2: 人称代词归一化

**What**: 在检索前对查询和记忆 key 进行人称代词统一处理

**Why**:
- "你喜欢的颜色" 和 "我喜欢的颜色" 语义等价
- 用户输入和系统存储可能使用不同人称
- 规则简单，无性能开销

**映射规则**:
```python
PRONOUN_NORMALIZE_MAP = {
    "你": "用户",
    "我": "用户",
    "您": "用户",
    "你的": "用户的",
    "我的": "用户的",
}
```

**处理流程**:
1. 检索时：用户输入 → 归一化 → 提取关键词
2. 存储时：key 保持原样（或可选归一化）
3. 匹配时：双方都归一化后比对

### Decision 3: 多层级候选召回

**What**: 在现有 FTS5 基础上增加 LIKE 子串匹配作为兜底

**Why**:
- FTS5 对中文分词依赖较重，短词可能丢失
- 子串匹配可以捕获 "颜色" 匹配 "你喜欢的颜色" 的情况
- 分层策略：精确 > FTS5 > 子串，逐层降级

**实现细节**:
```python
def retrieve_relevant_memories(user_message, ...):
    keywords = extract_keywords(user_message)
    normalized_keywords = [normalize_pronouns(kw) for kw in keywords]

    # Stage 2a: FTS5 with normalized keywords
    candidates = _recall_candidates_fts(normalized_keywords, limit)

    # Stage 2b: Substring fallback if FTS5 returns few results
    if len(candidates) < limit // 2:
        substring_candidates = _recall_candidates_substring(keywords, limit)
        candidates = merge_and_dedupe(candidates, substring_candidates)
```

### Decision 4: 部分匹配评分

**What**: 关键词部分匹配时给予非零分数

**Why**:
- 当前 `_calculate_keyword_score()` 只计算完全包含的关键词
- "颜色" 在 "你喜欢的颜色" 中应获得分数
- 部分匹配分数 = 匹配字符数 / 关键词长度

**评分公式调整**:
```python
def _calculate_keyword_score(memory, keywords):
    text = f"{memory.key} {memory.value}".lower()

    total_score = 0
    for kw in keywords:
        if kw in text:
            total_score += 1.0  # 完全匹配
        elif any(kw in part for part in text.split()):
            total_score += 0.7  # 词级部分匹配
        elif any(char in text for char in kw if len(char) > 1):
            total_score += 0.3  # 字符级部分匹配

    return total_score / len(keywords)
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 模糊匹配可能召回不相关记忆 | 通过评分排序，不相关的排名靠后 |
| 人称归一化可能丢失语义 | 仅用于匹配，存储保持原样 |
| 子串匹配性能开销 | 仅在 FTS5 结果不足时触发 |
| 工作记忆膨胀 | 设置 context_variables 大小上限 |

## Migration Plan

1. **Phase 1**: 实现人称归一化（低风险，纯增强）
2. **Phase 2**: 实现子串匹配兜底（中等风险，需测试性能）
3. **Phase 3**: HITL 数据持久化（中等风险，影响数据流）
4. **Phase 4**: 评分算法优化（低风险，可 A/B 测试）

**回滚方案**: 每个 Phase 可独立开关，通过配置禁用新功能

## Open Questions

1. 同义词表是否需要持久化配置？还是硬编码足够？
2. 工作记忆的 `context_variables` 大小上限设为多少合适？
3. 是否需要为不同类别的记忆设置不同的匹配策略？
