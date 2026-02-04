# Change: Integrate Intent Recognition Node into LangGraph

## Why

The current LangGraph cognitive architecture (`core/graph.py`) processes text input through:
```
Emotion → Memory → Reasoning → (Tools/HITL/END)
```

However, the intent recognition system (`intent_recognizer.py`) is only integrated in the legacy `chat_processor.py` flow, not in the new graph-based architecture. This creates two issues:

1. **Inconsistency**: The `graph_runner.py` bypasses intent recognition entirely, missing token optimization benefits
2. **Feature flag ignored**: The `system.intent_recognition_enabled` setting has no effect in the graph flow

The existing intent recognizer provides significant value:
- Layer 1 (regex/keyword): Fast, free pattern matching
- Layer 2 (LLM classifier): Handles ambiguous cases with minimal tokens
- Intent-specific prompt snippets: Reduces prompt size from ~5K to ~300 chars

## What Changes

- **Add IntentNode**: New graph node that wraps the existing `IntentRecognizer`
  - Runs before EmotionNode (intent affects how we process the message)
  - Respects `system.intent_recognition_enabled` setting
  - Updates `GraphState.semantic_input.intent` with recognition result

- **Update GraphOrchestrator**: Insert IntentNode at graph entry point
  - New flow: `Intent → Emotion → Memory → Reasoning → ...`
  - Optional bypass when intent recognition disabled

- **Extend GraphState**: Add fields for intent recognition results
  - `intent_result`: Full IntentResult object
  - `intent_snippet`: Prompt snippet to inject into reasoning

- **Update ReasoningNode**: Use intent snippet for prompt optimization
  - If intent matched, use small snippet instead of full HITL instruction
  - Maintain backward compatibility when intent recognition disabled

## Impact

- Affected specs:
  - `workflow-engine/spec.md` - Graph node ordering
  - New `graph-intent-node/spec.md` - Intent node specification

- Affected code:
  - New `workflow/core/nodes/intent.py` - IntentNode implementation
  - `workflow/core/graph.py` - Add intent node to workflow
  - `workflow/core/state.py` - Add intent-related state fields
  - `workflow/core/nodes/reasoning.py` - Use intent snippet in prompt building

- No breaking changes to existing flows
