"""Memory Manager Module

Provides structured memory management for the AI chat system:
- WorkingMemory: Session-scoped context and state
- LongTermMemory: Cross-session persistent knowledge

Includes multi-stage retrieval algorithm with FTS5 and relevance scoring.
"""

import json
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import chat_db

# Try to import jieba for Chinese tokenization, fallback to simple split
try:
    import jieba
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False


# ============ Enums and Constants ============

class MemoryCategory(str, Enum):
    """Memory category types."""
    PREFERENCE = "preference"
    FACT = "fact"
    PATTERN = "pattern"


class MemorySource(str, Enum):
    """Memory source types."""
    USER_STATED = "user_stated"
    INFERRED = "inferred"
    SYSTEM = "system"


# Stopwords for keyword extraction
CHINESE_STOPWORDS: Set[str] = {
    "的", "是", "在", "我", "有", "和", "就", "不", "人", "都",
    "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你",
    "会", "着", "没有", "看", "好", "自己", "这", "那", "什么",
    "了", "吗", "呢", "吧", "啊", "哦", "嗯", "呀", "哈",
}

ENGLISH_STOPWORDS: Set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "must", "shall",
    "i", "you", "he", "she", "it", "we", "they", "my", "your",
    "his", "her", "its", "our", "their", "this", "that", "these",
    "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above",
    "below", "between", "under", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very",
    "can", "just", "don", "now", "and", "but", "or", "if",
}

# Scoring weights
SCORE_WEIGHTS = {
    "keyword": 0.40,
    "category": 0.20,
    "recency": 0.15,
    "frequency": 0.10,
    "confidence": 0.15,
}

CATEGORY_WEIGHTS = {
    "preference": 1.5,
    "fact": 1.2,
    "pattern": 1.0,
}

# Default retrieval limits
DEFAULT_RETRIEVAL_LIMIT = 5
DEFAULT_CANDIDATE_LIMIT = 50


# ============ Data Classes ============

@dataclass
class WorkingMemory:
    """Session-scoped working memory."""
    session_id: str
    current_topic: Optional[str] = None
    context_variables: Dict[str, Any] = field(default_factory=dict)
    turn_count: int = 0
    last_emotion: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MemoryEntry:
    """Long-term memory entry."""
    id: str
    session_id: Optional[str]
    category: str
    key: str
    value: Any
    confidence: float = 0.5
    source: str = "inferred"
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0


@dataclass
class RetrievalResult:
    """Result from memory retrieval with scoring details."""
    memory: MemoryEntry
    score: float
    keyword_score: float
    category_boost: float
    recency_score: float
    frequency_score: float


# ============ Keyword Extraction ============

def extract_keywords(message: str, max_keywords: int = 10) -> List[str]:
    """Extract keywords from user message, supporting Chinese and English.

    Args:
        message: User message text
        max_keywords: Maximum number of keywords to return

    Returns:
        List of keywords, ordered by importance
    """
    keywords = []

    if HAS_JIEBA:
        # Use jieba for Chinese tokenization
        tokens = jieba.cut(message, cut_all=False)
    else:
        # Fallback: simple whitespace and punctuation split
        import re
        tokens = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z0-9]+', message)

    for token in tokens:
        if isinstance(token, str):
            token = token.strip().lower()
        else:
            continue

        # Skip empty and short tokens
        if len(token) < 2:
            continue

        # Skip stopwords
        if token in CHINESE_STOPWORDS or token in ENGLISH_STOPWORDS:
            continue

        # Skip pure short numbers
        if token.isdigit() and len(token) < 4:
            continue

        keywords.append(token)

    # Deduplicate while preserving order
    seen: Set[str] = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    return unique_keywords[:max_keywords]


# ============ Working Memory Operations ============

def create_working_memory(session_id: str) -> WorkingMemory:
    """Create new working memory for a session.

    Args:
        session_id: Session UUID

    Returns:
        Created WorkingMemory instance
    """
    now = datetime.utcnow().isoformat()

    with chat_db.get_connection() as conn:
        conn.execute("""
            INSERT INTO working_memory (session_id, context_variables, turn_count, created_at, updated_at)
            VALUES (?, '{}', 0, ?, ?)
        """, (session_id, now, now))
        conn.commit()

    return WorkingMemory(
        session_id=session_id,
        created_at=datetime.fromisoformat(now),
        updated_at=datetime.fromisoformat(now),
    )


def get_working_memory(session_id: str) -> Optional[WorkingMemory]:
    """Get working memory by session ID.

    Args:
        session_id: Session UUID

    Returns:
        WorkingMemory instance or None if not found
    """
    with chat_db.get_connection() as conn:
        cursor = conn.execute("""
            SELECT session_id, current_topic, context_variables, turn_count,
                   last_emotion, created_at, updated_at
            FROM working_memory
            WHERE session_id = ?
        """, (session_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return WorkingMemory(
            session_id=row["session_id"],
            current_topic=row["current_topic"],
            context_variables=json.loads(row["context_variables"] or "{}"),
            turn_count=row["turn_count"],
            last_emotion=row["last_emotion"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.utcnow(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.utcnow(),
        )


def get_or_create_working_memory(session_id: str) -> WorkingMemory:
    """Get working memory by session ID, creating if not exists.

    Args:
        session_id: Session UUID

    Returns:
        WorkingMemory instance
    """
    memory = get_working_memory(session_id)
    if memory:
        return memory
    return create_working_memory(session_id)


def update_working_memory(
    session_id: str,
    current_topic: Optional[str] = None,
    context_variables: Optional[Dict[str, Any]] = None,
    last_emotion: Optional[str] = None,
    increment_turn: bool = False,
) -> Optional[WorkingMemory]:
    """Update working memory fields.

    Args:
        session_id: Session UUID
        current_topic: New topic (None to keep unchanged)
        context_variables: New context variables (None to keep unchanged)
        last_emotion: New emotion (None to keep unchanged)
        increment_turn: Whether to increment turn count

    Returns:
        Updated WorkingMemory or None if not found
    """
    now = datetime.utcnow().isoformat()

    with chat_db.get_connection() as conn:
        # Build dynamic update query
        updates = ["updated_at = ?"]
        params: List[Any] = [now]

        if current_topic is not None:
            updates.append("current_topic = ?")
            params.append(current_topic)

        if context_variables is not None:
            updates.append("context_variables = ?")
            params.append(json.dumps(context_variables))

        if last_emotion is not None:
            updates.append("last_emotion = ?")
            params.append(last_emotion)

        if increment_turn:
            updates.append("turn_count = turn_count + 1")

        params.append(session_id)

        query = f"UPDATE working_memory SET {', '.join(updates)} WHERE session_id = ?"
        cursor = conn.execute(query, params)
        conn.commit()

        if cursor.rowcount == 0:
            return None

    return get_working_memory(session_id)


def delete_working_memory(session_id: str) -> bool:
    """Delete working memory for a session.

    Args:
        session_id: Session UUID

    Returns:
        True if deleted, False if not found
    """
    with chat_db.get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM working_memory WHERE session_id = ?",
            (session_id,)
        )
        conn.commit()
        return cursor.rowcount > 0


def cleanup_expired_working_memory(timeout_minutes: int = 30) -> int:
    """Clean up working memory entries that haven't been updated recently.

    Args:
        timeout_minutes: Inactivity timeout in minutes

    Returns:
        Number of entries deleted
    """
    with chat_db.get_connection() as conn:
        cursor = conn.execute("""
            DELETE FROM working_memory
            WHERE datetime(updated_at) < datetime('now', ? || ' minutes')
        """, (f"-{timeout_minutes}",))
        conn.commit()
        return cursor.rowcount


def list_working_memories(limit: int = 100) -> List[WorkingMemory]:
    """List all active working memory entries.

    Args:
        limit: Maximum number of entries to return

    Returns:
        List of WorkingMemory objects
    """
    with chat_db.get_connection() as conn:
        cursor = conn.execute("""
            SELECT session_id, current_topic, context_variables,
                   turn_count, last_emotion, created_at, updated_at
            FROM working_memory
            ORDER BY updated_at DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()

    result = []
    for row in rows:
        ctx_vars = {}
        if row[2]:
            try:
                ctx_vars = json.loads(row[2])
            except (json.JSONDecodeError, TypeError):
                ctx_vars = {}

        result.append(WorkingMemory(
            session_id=row[0],
            current_topic=row[1],
            context_variables=ctx_vars,
            turn_count=row[3] or 0,
            last_emotion=row[4],
            created_at=datetime.fromisoformat(row[5]) if row[5] else datetime.now(),
            updated_at=datetime.fromisoformat(row[6]) if row[6] else datetime.now(),
        ))

    return result


# ============ Long-term Memory Operations ============

def create_memory_entry(
    category: str,
    key: str,
    value: Any,
    session_id: Optional[str] = None,
    confidence: float = 0.5,
    source: str = "inferred",
) -> MemoryEntry:
    """Create a new long-term memory entry.

    Args:
        category: Memory category (preference, fact, pattern)
        key: Memory key/identifier
        value: Memory value (will be JSON serialized)
        session_id: Source session ID (optional)
        confidence: Confidence score (0.0 - 1.0)
        source: Memory source (user_stated, inferred, system)

    Returns:
        Created MemoryEntry instance
    """
    memory_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    value_json = json.dumps(value) if not isinstance(value, str) else value

    with chat_db.get_connection() as conn:
        conn.execute("""
            INSERT INTO long_term_memory
            (id, session_id, category, key, value, confidence, source, created_at, last_accessed, access_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (memory_id, session_id, category, key, value_json, confidence, source, now, now))
        conn.commit()

    return MemoryEntry(
        id=memory_id,
        session_id=session_id,
        category=category,
        key=key,
        value=value,
        confidence=confidence,
        source=source,
        created_at=datetime.fromisoformat(now),
        last_accessed=datetime.fromisoformat(now),
        access_count=0,
    )


def get_memory_entry(memory_id: str) -> Optional[MemoryEntry]:
    """Get a long-term memory entry by ID.

    Args:
        memory_id: Memory UUID

    Returns:
        MemoryEntry or None if not found
    """
    with chat_db.get_connection() as conn:
        cursor = conn.execute("""
            SELECT id, session_id, category, key, value, confidence, source,
                   created_at, last_accessed, access_count
            FROM long_term_memory
            WHERE id = ?
        """, (memory_id,))
        row = cursor.fetchone()

        if not row:
            return None

        # Try to parse JSON value
        try:
            value = json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            value = row["value"]

        return MemoryEntry(
            id=row["id"],
            session_id=row["session_id"],
            category=row["category"],
            key=row["key"],
            value=value,
            confidence=row["confidence"],
            source=row["source"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.utcnow(),
            last_accessed=datetime.fromisoformat(row["last_accessed"]) if row["last_accessed"] else datetime.utcnow(),
            access_count=row["access_count"],
        )


def update_memory_entry(
    memory_id: str,
    key: Optional[str] = None,
    value: Optional[Any] = None,
    category: Optional[str] = None,
    confidence: Optional[float] = None,
) -> Optional[MemoryEntry]:
    """Update a long-term memory entry.

    Args:
        memory_id: Memory UUID
        key: New key (None to keep unchanged)
        value: New value (None to keep unchanged)
        category: New category (None to keep unchanged)
        confidence: New confidence (None to keep unchanged)

    Returns:
        Updated MemoryEntry or None if not found
    """
    with chat_db.get_connection() as conn:
        updates = []
        params: List[Any] = []

        if key is not None:
            updates.append("key = ?")
            params.append(key)

        if value is not None:
            updates.append("value = ?")
            params.append(json.dumps(value) if not isinstance(value, str) else value)

        if category is not None:
            updates.append("category = ?")
            params.append(category)

        if confidence is not None:
            updates.append("confidence = ?")
            params.append(confidence)

        if not updates:
            return get_memory_entry(memory_id)

        params.append(memory_id)
        query = f"UPDATE long_term_memory SET {', '.join(updates)} WHERE id = ?"
        cursor = conn.execute(query, params)
        conn.commit()

        if cursor.rowcount == 0:
            return None

    return get_memory_entry(memory_id)


def delete_memory_entry(memory_id: str) -> bool:
    """Delete a long-term memory entry.

    Args:
        memory_id: Memory UUID

    Returns:
        True if deleted, False if not found
    """
    with chat_db.get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM long_term_memory WHERE id = ?",
            (memory_id,)
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_all_memories() -> int:
    """Delete all long-term memory entries.

    Returns:
        Number of entries deleted
    """
    with chat_db.get_connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM long_term_memory")
        count = cursor.fetchone()[0]
        conn.execute("DELETE FROM long_term_memory")
        conn.commit()
        return count


def list_memory_entries(
    category: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    order_by: str = "last_accessed",
    order_desc: bool = True,
) -> List[MemoryEntry]:
    """List long-term memory entries with optional filtering.

    Args:
        category: Filter by category (optional)
        limit: Maximum number of entries to return
        offset: Number of entries to skip
        order_by: Column to order by
        order_desc: Whether to order descending

    Returns:
        List of MemoryEntry instances
    """
    with chat_db.get_connection() as conn:
        query = "SELECT id, session_id, category, key, value, confidence, source, created_at, last_accessed, access_count FROM long_term_memory"
        params: List[Any] = []

        if category:
            query += " WHERE category = ?"
            params.append(category)

        order_dir = "DESC" if order_desc else "ASC"
        query += f" ORDER BY {order_by} {order_dir} LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        entries = []
        for row in rows:
            try:
                value = json.loads(row["value"])
            except (json.JSONDecodeError, TypeError):
                value = row["value"]

            entries.append(MemoryEntry(
                id=row["id"],
                session_id=row["session_id"],
                category=row["category"],
                key=row["key"],
                value=value,
                confidence=row["confidence"],
                source=row["source"],
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.utcnow(),
                last_accessed=datetime.fromisoformat(row["last_accessed"]) if row["last_accessed"] else datetime.utcnow(),
                access_count=row["access_count"],
            ))

        return entries


def count_memory_entries(category: Optional[str] = None) -> int:
    """Count total long-term memory entries.

    Args:
        category: Filter by category (optional)

    Returns:
        Total count
    """
    with chat_db.get_connection() as conn:
        if category:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM long_term_memory WHERE category = ?",
                (category,)
            )
        else:
            cursor = conn.execute("SELECT COUNT(*) FROM long_term_memory")
        return cursor.fetchone()[0]


# ============ Memory Retrieval ============

def _recall_candidates_fts(keywords: List[str], limit: int) -> List[MemoryEntry]:
    """Recall candidate memories using FTS5 full-text search.

    Args:
        keywords: List of keywords to search
        limit: Maximum candidates to return

    Returns:
        List of candidate MemoryEntry instances
    """
    if not keywords:
        return []

    # Build FTS5 MATCH query with OR
    match_query = " OR ".join(f'"{kw}"*' for kw in keywords)

    with chat_db.get_connection() as conn:
        try:
            cursor = conn.execute("""
                SELECT ltm.id, ltm.session_id, ltm.category, ltm.key, ltm.value,
                       ltm.confidence, ltm.source, ltm.created_at, ltm.last_accessed, ltm.access_count,
                       bm25(memory_fts) as rank
                FROM memory_fts
                JOIN long_term_memory ltm ON memory_fts.memory_id = ltm.id
                WHERE memory_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (match_query, limit))

            rows = cursor.fetchall()
        except Exception:
            # FTS5 query failed, return empty
            return []

        entries = []
        for row in rows:
            try:
                value = json.loads(row["value"])
            except (json.JSONDecodeError, TypeError):
                value = row["value"]

            entries.append(MemoryEntry(
                id=row["id"],
                session_id=row["session_id"],
                category=row["category"],
                key=row["key"],
                value=value,
                confidence=row["confidence"],
                source=row["source"],
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.utcnow(),
                last_accessed=datetime.fromisoformat(row["last_accessed"]) if row["last_accessed"] else datetime.utcnow(),
                access_count=row["access_count"],
            ))

        return entries


def _recall_candidates_like(keywords: List[str], limit: int) -> List[MemoryEntry]:
    """Recall candidate memories using SQL LIKE (fallback).

    Args:
        keywords: List of keywords to search
        limit: Maximum candidates to return

    Returns:
        List of candidate MemoryEntry instances
    """
    if not keywords:
        return []

    # Build LIKE conditions
    conditions = []
    params: List[Any] = []
    for kw in keywords:
        conditions.append("(key LIKE ? OR value LIKE ?)")
        params.extend([f"%{kw}%", f"%{kw}%"])

    where_clause = " OR ".join(conditions)

    with chat_db.get_connection() as conn:
        cursor = conn.execute(f"""
            SELECT id, session_id, category, key, value, confidence, source,
                   created_at, last_accessed, access_count
            FROM long_term_memory
            WHERE {where_clause}
            LIMIT ?
        """, params + [limit])

        rows = cursor.fetchall()

        entries = []
        for row in rows:
            try:
                value = json.loads(row["value"])
            except (json.JSONDecodeError, TypeError):
                value = row["value"]

            entries.append(MemoryEntry(
                id=row["id"],
                session_id=row["session_id"],
                category=row["category"],
                key=row["key"],
                value=value,
                confidence=row["confidence"],
                source=row["source"],
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.utcnow(),
                last_accessed=datetime.fromisoformat(row["last_accessed"]) if row["last_accessed"] else datetime.utcnow(),
                access_count=row["access_count"],
            ))

        return entries


def _calculate_keyword_score(memory: MemoryEntry, keywords: List[str]) -> float:
    """Calculate keyword match score for a memory.

    Args:
        memory: MemoryEntry to score
        keywords: List of keywords

    Returns:
        Score between 0.0 and 1.0
    """
    if not keywords:
        return 0.0

    # Combine key and value for matching
    value_str = str(memory.value) if not isinstance(memory.value, str) else memory.value
    text = f"{memory.key} {value_str}".lower()

    matched = sum(1 for kw in keywords if kw.lower() in text)
    return matched / len(keywords)


def _calculate_recency_score(last_accessed: datetime) -> float:
    """Calculate recency score with exponential decay (7-day half-life).

    Args:
        last_accessed: Last access timestamp

    Returns:
        Score between 0.0 and 1.0
    """
    days_elapsed = (datetime.utcnow() - last_accessed).days
    half_life = 7.0
    decay_rate = math.log(2) / half_life
    return math.exp(-decay_rate * max(0, days_elapsed))


def _calculate_frequency_score(access_count: int, max_count: int) -> float:
    """Calculate frequency score using log normalization.

    Args:
        access_count: Memory access count
        max_count: Maximum access count in candidate set

    Returns:
        Score between 0.0 and 1.0
    """
    if max_count <= 1:
        return 0.5
    return math.log(access_count + 1) / math.log(max_count + 1)


def _is_topic_related(memory: MemoryEntry, topic: str) -> bool:
    """Check if memory is related to current topic.

    Args:
        memory: MemoryEntry to check
        topic: Current topic string

    Returns:
        True if related
    """
    if not topic:
        return False

    topic_keywords = extract_keywords(topic, max_keywords=5)
    if not topic_keywords:
        return False

    value_str = str(memory.value) if not isinstance(memory.value, str) else memory.value
    text = f"{memory.key} {value_str}".lower()

    return any(kw.lower() in text for kw in topic_keywords)


def retrieve_relevant_memories(
    user_message: str,
    working_memory: Optional[WorkingMemory] = None,
    limit: int = DEFAULT_RETRIEVAL_LIMIT,
    candidate_limit: int = DEFAULT_CANDIDATE_LIMIT,
) -> List[RetrievalResult]:
    """Retrieve memories relevant to user message using multi-stage algorithm.

    Stage 1: Extract keywords from message
    Stage 2: Recall candidates (FTS5 primary, LIKE fallback)
    Stage 3: Calculate relevance scores
    Stage 4: Rank and return top-N

    Args:
        user_message: User's message text
        working_memory: Current session's working memory (optional)
        limit: Maximum results to return
        candidate_limit: Maximum candidates to recall

    Returns:
        List of RetrievalResult sorted by relevance score
    """
    # Stage 1: Keyword extraction
    keywords = extract_keywords(user_message)

    # Add topic keywords from working memory
    if working_memory and working_memory.current_topic:
        topic_keywords = extract_keywords(working_memory.current_topic)
        keywords = list(set(keywords + topic_keywords))

    if not keywords:
        return []

    # Stage 2: Candidate recall (FTS5 first, LIKE fallback)
    candidates = _recall_candidates_fts(keywords, candidate_limit)
    if not candidates:
        candidates = _recall_candidates_like(keywords, candidate_limit)

    if not candidates:
        return []

    # Stage 3: Relevance scoring
    results = []
    max_access_count = max((c.access_count for c in candidates), default=1) or 1

    for memory in candidates:
        keyword_score = _calculate_keyword_score(memory, keywords)
        category_boost = CATEGORY_WEIGHTS.get(memory.category, 1.0)
        recency_score = _calculate_recency_score(memory.last_accessed)
        frequency_score = _calculate_frequency_score(memory.access_count, max_access_count)

        # Topic relevance boost
        topic_boost = 1.0
        if working_memory and working_memory.current_topic:
            if _is_topic_related(memory, working_memory.current_topic):
                topic_boost = 1.3

        # Calculate final score
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

    # Stage 4: Sort and return top-N
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


def update_memory_access(memory_ids: List[str]) -> int:
    """Update access tracking for retrieved memories.

    Args:
        memory_ids: List of memory UUIDs that were accessed

    Returns:
        Number of memories updated
    """
    if not memory_ids:
        return 0

    now = datetime.utcnow().isoformat()

    with chat_db.get_connection() as conn:
        placeholders = ",".join("?" * len(memory_ids))
        cursor = conn.execute(f"""
            UPDATE long_term_memory
            SET last_accessed = ?, access_count = access_count + 1
            WHERE id IN ({placeholders})
        """, [now] + memory_ids)
        conn.commit()
        return cursor.rowcount


def evict_memories_by_threshold(max_count: int) -> int:
    """Evict old memories when count exceeds threshold.

    Eviction priority:
    1. Lowest confidence
    2. Oldest last_accessed

    Args:
        max_count: Maximum number of memories to keep

    Returns:
        Number of memories evicted
    """
    current_count = count_memory_entries()
    if current_count <= max_count:
        return 0

    to_delete = current_count - max_count

    with chat_db.get_connection() as conn:
        # Get IDs of memories to delete
        cursor = conn.execute("""
            SELECT id FROM long_term_memory
            ORDER BY confidence ASC, last_accessed ASC
            LIMIT ?
        """, (to_delete,))

        ids_to_delete = [row["id"] for row in cursor.fetchall()]

        if ids_to_delete:
            placeholders = ",".join("?" * len(ids_to_delete))
            conn.execute(f"DELETE FROM long_term_memory WHERE id IN ({placeholders})", ids_to_delete)
            conn.commit()

        return len(ids_to_delete)
