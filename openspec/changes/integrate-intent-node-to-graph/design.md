# Design: Intent Node for LangGraph Cognitive Architecture

## Context

The project has two parallel chat processing architectures:

1. **Legacy flow** (`chat_processor.py` + `main.py`):
   - Uses intent recognition to optimize prompts
   - Works but being phased out

2. **Graph flow** (`graph_runner.py` + `core/graph.py`):
   - LangGraph-based cognitive architecture
   - Currently missing intent recognition

The existing `IntentRecognizer` is well-tested and provides clear benefits:
- 50%+ token reduction for common patterns
- Two-layer cascading: regex → LLM fallback
- Comprehensive logging for observability

## Goals / Non-Goals

**Goals:**
- Integrate existing intent recognition into graph architecture
- Respect `system.intent_recognition_enabled` setting
- Minimize changes to existing intent recognizer code
- Maintain backward compatibility

**Non-Goals:**
- Rewrite the intent recognition system
- Add new intent types
- Change the two-layer architecture

## Decisions

### Decision 1: IntentNode as First Node

**What:** Place IntentNode before EmotionNode in the graph:
```
[Entry] → Intent → Emotion → Memory → Reasoning → ...
```

**Why:**
- Intent detection is input-dependent, not emotion-dependent
- Early intent detection allows all downstream nodes to use the result
- Emotion detection might benefit from knowing the intent

**Alternatives considered:**
- After EmotionNode: Would lose opportunity to optimize emotion detection
- Parallel to EmotionNode: Adds complexity, marginal benefit

### Decision 2: State Extension Pattern

**What:** Add intent-related fields to GraphState:

```python
class GraphState(BaseModel):
    # ... existing fields ...

    # Intent recognition results
    intent_result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Intent recognition result from IntentNode"
    )
```

**Why:**
- Follows existing state pattern
- Makes intent available to all downstream nodes
- Non-breaking change (new optional field)

### Decision 3: Conditional Execution

**What:** IntentNode checks `system.intent_recognition_enabled` at runtime:
- If enabled: Run full recognition (Layer 1 + optional Layer 2)
- If disabled: Pass through with no changes

**Why:**
- Respects user configuration
- Zero overhead when disabled
- No graph restructuring needed

### Decision 4: Async Layer 2 Support

**What:** IntentNode supports async execution for Layer 2 LLM calls:

```python
async def compute(self, state: GraphState) -> Dict[str, Any]:
    if not is_intent_recognition_enabled():
        return {}

    # Layer 1: sync regex matching
    result = self.matcher.match(state.semantic_input.text)
    if result:
        return {"intent_result": result.model_dump()}

    # Layer 2: async LLM classification (optional)
    if self.layer2_enabled:
        result = await self.classifier.classify(...)
        if result:
            return {"intent_result": result.model_dump()}

    # Fallback: normal conversation
    return {"intent_result": IntentResult.normal().model_dump()}
```

**Why:**
- LangGraph supports async nodes
- Consistent with other async nodes (ReasoningNode, ToolNode)

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                       GraphState                             │
│  semantic_input.text: "提醒我明天下午3点开会"                 │
│  intent_result: None                                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      IntentNode                              │
│  1. Check: is_intent_recognition_enabled() → True            │
│  2. Layer 1: RuleBasedMatcher.match()                        │
│     - Pattern "提醒.*明天" matches rule "time_keyword"       │
│     - Return: {intent_type: "plan_reminder", confidence: 1.0}│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       GraphState                             │
│  semantic_input.text: "提醒我明天下午3点开会"                 │
│  intent_result: {                                            │
│    category: "hitl",                                         │
│    intent_type: "plan_reminder",                             │
│    confidence: 1.0,                                          │
│    source: "layer1"                                          │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    [EmotionNode, MemoryNode, ...]
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     ReasoningNode                            │
│  1. Check state.intent_result                                │
│  2. Get snippet: HITL_INTENT_SNIPPETS["plan_reminder"]       │
│  3. Build prompt with 300-char snippet vs 3K full instruction│
└─────────────────────────────────────────────────────────────┘
```

## Integration with ReasoningNode

The ReasoningNode needs to use intent_result for prompt optimization:

```python
async def compute(self, state: GraphState) -> Dict[str, Any]:
    # Build prompt with intent awareness
    intent_snippet = ""
    if state.intent_result:
        intent_snippet = get_intent_snippet(state.intent_result)

    prompt = self._build_prompt(
        state=state,
        intent_snippet=intent_snippet,
    )
    # ... rest of reasoning logic
```

This follows the same pattern as `chat_processor.build_system_prompt()`.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Layer 2 adds latency to graph | Default Layer 2 disabled in graph, use setting to enable |
| State bloat with intent data | Intent result is small (~200 bytes) |
| Graph complexity increases | Single node addition, clear responsibilities |

## Configuration

Uses existing settings from database:
- `system.intent_recognition_enabled`: Master switch
- Layer 2 settings can be added later if needed

## Logging

IntentNode will use existing logging patterns from `intent_recognizer.py`:
```
[Intent] Layer1: checking user message...
[Intent] Layer1: MATCHED plan_reminder (confidence=1.0, rule=time_keyword)
```
