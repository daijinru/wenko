## Context

当前 Wenko 系统的长期记忆保存存在两个优化点：

1. **自动保存**：`chat_processor.py` 中已实现 LLM 输出 `memory_update` 后自动保存的逻辑，但需要确保 prompt 指令足够明确，让 LLM 识别并保存所有有价值的信息。

2. **主动保存**：`SaveMemoryDialog` 组件的键名和值使用通用默认值，用户需手动编辑。优化方案是调用 AI 智能提取。

## Goals / Non-Goals

### Goals
- 提高记忆保存的自动化程度
- 减少用户手动输入的负担
- 智能提取消息摘要和关键信息

### Non-Goals
- 不改变现有的记忆存储结构
- 不影响现有的记忆检索算法
- 不添加新的记忆类别

## Decisions

### Decision 1: 自动保存依赖现有机制

**选择**：增强现有 LLM prompt，而非新增后处理逻辑

**理由**：
- `chat_processor.py` 的 `CHAT_PROMPT_TEMPLATE` 已包含 `memory_update` 指令
- `process_llm_response` 已实现 `_store_suggested_memories` 逻辑
- 只需优化 prompt 指令，确保 LLM 更积极地识别可保存信息

**替代方案**：
- 后处理分析：在 LLM 返回后额外分析消息内容（增加延迟和复杂度）
- 规则匹配：基于关键词规则识别（不够智能）

### Decision 2: 智能提取 API

**选择**：新增 `/memory/extract` API 端点

**理由**：
- 前端调用 API，后端使用 LLM 分析消息
- 返回结构化的 `{ key, value, category, confidence }` 数据
- 复用现有 LLM 调用基础设施

**API 设计**：
```
POST /memory/extract
Request:
{
  "content": "消息内容",
  "role": "user" | "assistant"
}

Response:
{
  "key": "智能提取的键名",
  "value": "消息摘要或原文",
  "category": "preference" | "fact" | "pattern",
  "confidence": 0.9
}
```

### Decision 3: 前端智能提取流程

**选择**：对话框打开时自动提取

**理由**：
- 用户点击"保存到长期记忆"时，对话框自动调用提取 API
- 显示加载状态，完成后预填充表单
- 用户可查看并修改后保存

**替代方案**：
- 手动触发按钮：用户需额外点击"智能提取"按钮（增加操作步骤）
- 延迟提取：用户开始编辑时才提取（体验不一致）

## Risks / Trade-offs

### 风险 1: LLM 提取质量
- **风险**：LLM 可能提取不准确的摘要
- **缓解**：用户可在对话框中修改；显示置信度供参考

### 风险 2: 自动保存过多
- **风险**：LLM 可能保存过多冗余信息
- **缓解**：依赖 LLM 的判断能力；后续可添加用户控制开关

### 风险 3: API 延迟
- **风险**：智能提取调用 LLM 会增加延迟
- **缓解**：显示加载状态；表单仍可手动填写

## Migration Plan

1. 后端增加 `/memory/extract` API
2. 前端 SaveMemoryDialog 集成智能提取
3. 优化 chat_processor.py 的 prompt 指令（可选）

无需数据迁移，向后兼容。

## Open Questions

- 是否需要添加自动保存的用户开关？（当前决定：暂不添加，依赖 LLM 判断）
- 智能提取失败时的 fallback 策略？（当前决定：使用现有默认值）
