# Tasks: Add Multi-Layer Intent Recognition

## 1. Core Infrastructure

- [x] 1.1 Create `workflow/intent_types.py` - define IntentType enum and IntentResult dataclass
- [x] 1.2 Create `workflow/intent_rules.py` - define regex/keyword rules for each intent type

## 2. Layer 1: Rule-Based Matcher

- [x] 2.1 Implement `RuleBasedMatcher` class in `intent_recognizer.py`
- [x] 2.2 Add memory intent rules (4 types):
  - `preference`: patterns like "我喜欢", "我偏好", "我爱"
  - `fact`: patterns like "我叫", "我是", "我在"
  - `pattern`: patterns like "我每天", "我通常", "我习惯"
  - `opinion`: patterns like "我认为", "我觉得", "我相信"
- [x] 2.3 Add HITL intent rules (6 strategies):
  - `proactive_inquiry`: greeting patterns like "你好", "嗨", "hello"
  - `topic_deepening`: topic mentions like "我喜欢...", "我对...感兴趣"
  - `emotion_driven`: emotion patterns like "心情很好", "很开心", "很难过"
  - `memory_gap`: request patterns like "推荐", "建议", "帮我"
  - `question_to_form`: question patterns that can be converted to forms
  - `plan_reminder`: time keywords like "明天", "下周", "提醒我"
- [x] 2.4 Add logging for Layer 1 matches

## 3. Layer 2: LLM-Based Classifier

- [x] 3.1 Create minimal intent classification prompt (< 500 tokens)
- [x] 3.2 Implement `LLMIntentClassifier` class
- [x] 3.3 Add config option for intent model (can use same model as main chat)
- [x] 3.4 Parse LLM response to extract intent type and confidence
- [x] 3.5 Add logging for Layer 2 classification

## 4. Integration with Chat Processor

- [x] 4.1 Create main `IntentRecognizer` class combining Layer 1 and Layer 2
- [x] 4.2 Add `recognize_intent()` function as main entry point
- [x] 4.3 Modify `chat_processor.py` to use intent recognition before prompt building
- [x] 4.4 Create intent-specific prompt snippets (much smaller than current full HITL_INSTRUCTION)
- [x] 4.5 Add fallback to simple conversation when no intent matches

## 5. Testing & Validation

- [x] 5.1 Create unit tests for rule-based matcher
- [x] 5.2 Create integration tests for full intent flow
- [x] 5.3 Add test cases for all 10 intent types (4 memory + 6 HITL)
- [x] 5.4 Verify token savings with sample conversations

## 6. Documentation & Config

- [x] 6.1 Update `chat_config.example.json` with intent recognition options
- [x] 6.2 Add logging format documentation in code comments
