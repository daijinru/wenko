# Change: 强化情感感知、情感表现与情感 UI 呈现

## Why

当前情感系统存在以下问题：
1. **情感感知不足**：启发式关键词检测（EmotionNode）能力有限，置信度固定为 0.3（低于默认阈值 0.5），导致几乎所有启发式检测结果都被降级为 neutral；缺少情感趋势追踪和情感历史
2. **情感表现单一**：响应策略虽然根据情绪调整语气和参数，但 `emoji_allowed` 始终为 false，表现力受限；EmotionNode 的 `modulation_instruction` 在 chat_processor 的实际 prompt 中未被使用
3. **情感 UI 缺失**：Live2D 情感指示器虽已实现（`createEmotionIndicator`、`updateEmotionIndicator`），但在默认聊天界面中 `onEmotion` 回调传入的是 `undefined`，未实际连接；无情感变化的视觉反馈（如 Live2D 表情切换）；Workflow 面板中仅以 Badge 显示 `last_emotion`，无趋势或详情

## What Changes

### 情感感知增强
- 提升启发式检测的置信度计算（多指标命中时递增）
- 引入情感历史追踪（记录近 N 轮情感，支持趋势分析）
- 当前轮情感直接用于当前轮策略选择（消除两阶段延迟）

### 情感表现增强
- 将 EmotionNode 的 `modulation_instruction` 实际注入 LLM prompt
- 根据情感类型启用 emoji（positive/seeking 类允许 emoji）
- 情感上下文（当前情感 + 最近趋势）注入回复生成，使 AI 回复更具情感连贯性

### 情感 UI 增强
- 连接 Live2D 聊天界面的情感指示器（将 SSE emotion 事件传递到 UI）
- 在 Live2D 聊天气泡中显示当前情感状态（颜色标记 + 标签）
- 在 Workflow 面板中增加情感历史视图（展示最近对话的情感变化趋势）

## Impact

- Affected specs: `ai-chat-emotion`（已有 change delta）、`electron-app`（Live2D 集成）
- Affected code:
  - `workflow/emotion_detector.py` — 置信度计算优化
  - `workflow/core/nodes/emotion.py` — 情感历史追踪
  - `workflow/response_strategy.py` — emoji 策略调整
  - `workflow/chat_processor.py` — modulation_instruction 注入
  - `workflow/memory_manager.py` — 情感历史存储
  - `workflow/graph_runner.py` — 情感事件增强
  - `electron/live2d/live2d-widget/src/chat.ts` — 连接情感指示器
  - `electron/src/renderer/workflow/` — 情感历史 UI 组件
