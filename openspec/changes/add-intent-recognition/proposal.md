# Change: Add Multi-Layer Intent Recognition

## Why

Currently, the chat processor sends all user messages to the LLM with a complex prompt containing 4 memory save rules and 6 HITL form strategies. This approach:
- Consumes excessive tokens for every request (the HITL instruction alone is ~3K characters)
- Relies solely on LLM to match strategies, which can be inconsistent
- Has no visibility into which strategy was triggered

A multi-layer intent recognition system can pre-match user intent using lightweight methods (regex, keywords) before falling back to LLM, saving tokens and improving strategy hit rates.

## What Changes

- **Add Layer 1**: Regex/keyword-based intent matcher for high-confidence patterns
  - Memory rules: detect "I like/prefer", "my name is", "I think/believe", etc.
  - HITL triggers: detect greeting patterns, time-related keywords, question patterns

- **Add Layer 2**: LLM-based intent classifier for ambiguous cases
  - Uses a minimal prompt with just intent categories (not full strategy instructions)
  - Returns matched intent type and confidence score

- **Add fallback**: Normal conversation when no intent matches
  - Skip strategy-specific prompts, use simple system prompt

- **Add logging**: Print intent flow decisions for observability

## Impact

- Affected specs: New `intent-recognition` capability
- Affected code:
  - `workflow/chat_processor.py` - integrate intent recognizer before prompt building
  - New `workflow/intent_recognizer.py` - multi-layer intent recognition
  - New `workflow/intent_types.py` - intent type definitions
  - New `workflow/intent_rules.py` - regex/keyword rules configuration
  - `workflow/chat_config.example.json` - optional intent model configuration
