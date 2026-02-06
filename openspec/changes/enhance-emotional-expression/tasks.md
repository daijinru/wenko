# Tasks: 强化情感感知、情感表现与情感 UI 呈现

## 1. 情感感知增强（后端）

- [x] 1.1 修改 `emotion_detector.py` 中 `extract_emotion_from_text()`，根据匹配关键词数量动态计算置信度（1个=0.3, 2个=0.5, 3个+=0.7），并在 `indicators` 中记录所有匹配关键词
- [x] 1.2 在 `memory_manager.py` 的 `WorkingMemory` 中增加 `emotion_history: List[Dict]` 字段，存储最近 10 轮情感记录（emotion, confidence, turn）
- [x] 1.3 在 `chat_processor.py` 的 `_update_working_memory_after_response()` 中每轮对话完成后，将检测到的情感追加到 `emotion_history`，超过 10 条时移除最早记录
- [x] 1.4 修改 `build_system_prompt()` 的策略选择逻辑：当 `emotional_context.current_emotion` 不为 neutral 且置信度 ≥ 阈值时，使用当前轮情感驱动策略；否则 fallback 到 `last_emotion`

## 2. 情感表现增强（后端）

- [x] 2.1 在 `chat_processor.py` 的 `build_system_prompt()` 中增加 `emotion_modulation` 参数，将 `modulation_instruction` 追加到 system prompt
- [x] 2.2 修改 ReasoningNode，将 `emotional_context.modulation_instruction` 传递到 chat_processor 的 prompt 构建中
- [x] 2.3 修改 `response_strategy.py` 中 positive 类（happy, excited, grateful, curious）和 seeking 类（help_seeking, info_seeking, validation_seeking）策略的 `emoji_allowed` 为 `True`

## 3. 情感 UI 增强（前端）

- [x] 3.1 修改 `chat.ts` 中 `createChatInput()` 函数，传入有效的 `onEmotion` 回调，将 SSE emotion 事件连接到 `updateEmotionIndicator()`
- [x] 3.2 在 `createChatInput()` 中创建并挂载 `createEmotionIndicator()` 到 `#waifu` 元素
- [x] 3.3 在工作记忆 API 响应中包含 `emotion_history` 字段（后端 `WorkingMemoryInfo` + 前端 `EmotionHistoryEntry` 类型）
- [x] 3.4 在 Workflow 面板的 Working Memory 区域增加 `EmotionHistory` 组件，展示最近情感变化（类型、颜色标记、置信度）

## 4. 验证

- [ ] 4.1 手动测试：发送带有明确情感的消息（如"太开心了！好棒！真的很感谢你！"），验证置信度为 0.7 且策略为 warm/positive
- [ ] 4.2 手动测试：验证 Live2D 聊天界面的情感指示器正确显示颜色、标签和置信度
- [ ] 4.3 手动测试：验证 Workflow 面板情感历史视图正确展示多轮情感变化
- [ ] 4.4 手动测试：验证 positive 类情感回复中出现 emoji，negative 类不出现
