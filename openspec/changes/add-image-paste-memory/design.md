# Design: 图片粘贴和文本识别到长期记忆

## Context

Live2D AI Chat 当前仅支持文本输入。用户需要从图片中提取信息时，需要手动输入，效率低下。通过集成 Vision LLM 能力，可以直接分析图片中的文本并保存到长期记忆系统。

### 现有系统
- 聊天系统：`chat.ts` (前端) + `main.py` `/chat` API (后端)
- 记忆系统：`memory_manager.py` + `memory_extractor.py`
- HITL 系统：`hitl_handler.py` + `hitl_schema.py`
- LLM 配置：`chat_config.json`（OpenAI 兼容 API）

## Goals / Non-Goals

### Goals
- 支持用户通过 Ctrl+V 粘贴图片到聊天输入区
- 使用 Vision LLM 分析图片中的文本内容
- 通过 HITL 流程让用户确认后保存到长期记忆
- 复用现有的记忆系统和 HITL 基础设施

### Non-Goals
- 不支持实时 OCR（仅调用 Vision API）
- 不支持图片编辑或标注
- 不支持多图片批量处理
- 不支持非文本内容识别（如物体识别）

## Decisions

### 1. Vision API 选择

**决定**: 使用 OpenAI GPT-4o-mini with vision 作为默认，支持配置切换。

**理由**:
- 与现有 `chat_config.json` 配置兼容
- GPT-4o-mini 成本低，识别准确度高
- 可通过同一配置文件切换到其他 Vision API

**配置示例**:
```json
{
  "api_base": "https://api.openai.com/v1",
  "api_key": "sk-...",
  "model": "gpt-4o-mini",
  "vision_model": "gpt-4o-mini"  // 可选，默认使用 model
}
```

### 2. 图片传输格式

**决定**: 使用 Base64 编码直接传输。

**理由**:
- 简单直接，无需额外的文件存储
- 与 Vision API 要求的格式兼容
- 图片压缩后大小可控（限制为 4MB）

**替代方案**（未采用）:
- 上传到文件服务器返回 URL：增加复杂度和延迟

### 3. 用户交互流程

**决定**: 采用两步确认流程。

**流程**:
```
1. 粘贴图片 → 显示预览 + "分析"按钮
2. 点击"分析" → 调用 Vision API
3. 显示提取的文本 + 记忆建议
4. HITL 表单让用户确认/编辑
5. 确认后保存到长期记忆
```

**理由**:
- 避免意外粘贴触发 API 调用（节省成本）
- 给用户机会取消操作
- 复用现有 HITL 流程，保持一致性

### 4. 记忆提取策略

**决定**: 组合 Vision + LLM 两阶段处理。

**阶段 1 - Vision 分析**:
```
Prompt: 请识别并提取图片中的所有文本内容。
        如果是截图、笔记或文档，请完整提取。
        如果没有文本，请回复"无文本内容"。
```

**阶段 2 - 记忆提取**:
复用现有 `memory_extractor.py`，从提取的文本中识别 key/value/category。

**理由**:
- 分离关注点：Vision 专注提取，LLM 专注理解
- 复用现有记忆提取逻辑
- 便于单独测试和调优

## API Design

### POST /chat/image

**请求**:
```json
{
  "image": "data:image/png;base64,iVBORw0...",
  "session_id": "uuid-...",
  "action": "analyze_for_memory"  // analyze_only | analyze_for_memory
}
```

**响应** (SSE):
```
event: text
data: {"type": "text", "payload": {"content": "图片中识别到以下文本：..."}}

event: hitl
data: {"type": "hitl", "payload": {"id": "...", "title": "保存到长期记忆", ...}}

event: done
data: {"type": "done"}
```

## Risks / Trade-offs

### 1. API 成本

**风险**: Vision API 调用成本高于纯文本。

**缓解**:
- 要求用户明确点击"分析"按钮
- 图片压缩减少 token 消耗
- 使用 gpt-4o-mini（成本较低）

### 2. 识别准确度

**风险**: 手写、模糊或复杂排版图片识别不准确。

**缓解**:
- 通过 HITL 让用户编辑/确认
- 在 UI 中提示"识别结果仅供参考"

### 3. 隐私安全

**风险**: 图片可能包含敏感信息。

**缓解**:
- 图片仅在内存中处理，不保存到磁盘
- 提取的文本保存前需用户确认
- 遵循现有的本地优先原则

## Open Questions

1. **是否支持拖拽图片**?
   - 建议：后续版本添加，本次先实现粘贴功能

2. **是否支持从剪贴板历史选择图片**?
   - 建议：暂不支持，依赖系统剪贴板

3. **图片大小限制**?
   - 建议：4MB 上限，超过则自动压缩
