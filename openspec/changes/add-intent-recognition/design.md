# Design: Multi-Layer Intent Recognition

## Context

The current chat processor includes extensive prompt instructions for:
- 4 memory save rules (~1.5K characters)
- 6 HITL form strategies (~3K characters)

This creates a ~5K character overhead for every LLM request, even for simple greetings or questions that don't need complex strategy handling.

## Goals / Non-Goals

**Goals:**
- Reduce token consumption by 50%+ for common conversation patterns
- Improve intent matching accuracy through specialized detection
- Provide visibility into intent flow via logging
- Maintain backward compatibility with existing behavior

**Non-Goals:**
- Complete replacement of LLM-based strategy selection
- Real-time rule learning or adaptation
- Multi-language support beyond Chinese (current focus)

## Decisions

### Decision 1: Two-Layer Architecture

**What:** Use a cascading recognition approach:
```
Layer 1 (Regex/Keyword) → Layer 2 (LLM Classifier) → Fallback (Normal Chat)
```

**Why:**
- Layer 1 is fast and free (no API calls)
- Layer 2 handles ambiguous cases with minimal token cost
- Fallback ensures graceful degradation

**Alternatives considered:**
- Single LLM-only approach: Higher accuracy but defeats token-saving goal
- Rule-only approach: Brittle, poor coverage for edge cases

### Decision 2: Intent Type Hierarchy

**What:** Define intents in two categories:

```python
class MemoryIntent(Enum):
    PREFERENCE = "preference"      # 用户偏好
    FACT = "fact"                  # 用户事实
    PATTERN = "pattern"            # 行为模式
    OPINION = "opinion"            # 个人观点

class HITLIntent(Enum):
    PROACTIVE_INQUIRY = "proactive_inquiry"   # 主动询问
    TOPIC_DEEPENING = "topic_deepening"       # 话题深化
    EMOTION_DRIVEN = "emotion_driven"         # 情感驱动
    MEMORY_GAP = "memory_gap"                 # 记忆补全
    QUESTION_TO_FORM = "question_to_form"     # 问答转表单
    PLAN_REMINDER = "plan_reminder"           # 计划提醒
```

**Why:** Maps directly to existing strategy implementations, minimal refactoring needed.

### Decision 3: Prompt Snippets over Full Instructions

**What:** Instead of including all 6 HITL strategies in every prompt, include only the matched strategy's instruction snippet.

**Example:**
```python
# Before: Always include full HITL_INSTRUCTION (~3K chars)
# After: Include only relevant snippet (~300 chars)

HITL_SNIPPETS = {
    "plan_reminder": """
    检测到时间相关意图。请生成计划提醒表单:
    - fields: title, description, target_datetime, reminder_offset, repeat_type
    - context.intent: collect_plan
    """,
    # ...
}
```

**Why:** Direct token savings without changing LLM behavior.

### Decision 4: Logging Format

**What:** Use structured logging with clear flow indicators:

```
[Intent] Layer1: checking user message...
[Intent] Layer1: MATCHED plan_reminder (confidence=1.0, rule=time_keyword)
[Intent] Using prompt snippet: plan_reminder

# or if Layer 1 misses:
[Intent] Layer1: no match
[Intent] Layer2: calling LLM classifier...
[Intent] Layer2: MATCHED topic_deepening (confidence=0.85)
[Intent] Using prompt snippet: topic_deepening

# or if both miss:
[Intent] Layer1: no match
[Intent] Layer2: no match (confidence=0.3 < threshold)
[Intent] Fallback: using normal conversation
```

**Why:** Easy to grep, clear decision chain, includes confidence scores.

## Data Flow

```
User Message
    │
    ▼
┌─────────────────────┐
│  Layer 1: Rules     │ ── Match ──► Intent + Confidence (1.0)
│  (regex/keywords)   │
└─────────────────────┘
    │ No Match
    ▼
┌─────────────────────┐
│  Layer 2: LLM       │ ── Match ──► Intent + Confidence (0.5-0.9)
│  (minimal prompt)   │
└─────────────────────┘
    │ No Match
    ▼
┌─────────────────────┐
│  Fallback           │ ──────────► No Intent (normal chat)
│  (simple prompt)    │
└─────────────────────┘
    │
    ▼
Build Prompt with Intent-Specific Snippet
    │
    ▼
Call Main LLM
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Layer 1 rules too rigid | Add comprehensive patterns, fallback to Layer 2 |
| Layer 2 adds latency | Use fast/cheap model, cache common patterns |
| Intent categories incomplete | Design for extensibility, add new intents easily |
| Breaking existing behavior | Feature flag to enable/disable intent recognition |

## Configuration

```json
{
  "intent_recognition": {
    "enabled": true,
    "layer2_model": "gpt-4o-mini",
    "layer2_confidence_threshold": 0.6,
    "log_level": "info"
  }
}
```

## Open Questions

- Should Layer 2 use the same model as main chat, or a dedicated cheaper model?
  - Proposal: Default to same model, allow override in config
- Should we cache Layer 2 results for similar messages?
  - Proposal: Defer to future optimization, measure first
