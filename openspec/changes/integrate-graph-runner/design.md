# Design: Integrate GraphRunner into Production Chat Flow

## Context

Wenko 桌面 AI 助手已构建了基于 LangGraph 的认知图谱原型（`workflow/core/`），但生产环境仍使用传统的手动编排逻辑（`main.py:stream_chat_response` 和 `stream_image_analysis`）。本设计解决如何将 GraphRunner 无缝接入生产环境，同时保持向后兼容性。

### Stakeholders
- 终端用户：需要无感知的平滑迁移
- 开发者：需要可调试、可审计的执行轨迹
- 运维：需要灰度发布和快速回滚能力

### Constraints
- 必须保持 SSE 事件格式兼容
- 不能破坏现有的记忆/情感/HITL/MCP 功能
- 需要支持流式输出（用户体验关键）
- LangGraph 版本固定为 `>=0.2.6`

## Goals / Non-Goals

### Goals
1. 将 GraphRunner 接入 `/chat` 和 `/chat/image` 端点，实现认知图谱驱动的对话和图片分析
2. 复用现有 `chat_processor` 的 prompt 构建逻辑
3. 支持流式 LLM 响应输出
4. 实现 HITL 暂停/恢复的完整生命周期
5. 新增 ImageNode 处理图片分析流程

### Non-Goals
1. 重构前端 SSE 处理逻辑（保持兼容）
2. 修改 LangGraph 库本身
3. 实现分布式状态存储（本地 SQLite 足够）
4. 优化 LLM 响应延迟（不在本提案范围）

## Decisions

### Decision 1: 流式输出架构

**选择：节点级流式 + 增量状态更新**

当前 LangGraph 的 `astream()` 返回节点执行后的状态更新，不支持节点内部的流式输出。为解决此问题：

```
┌─────────────────────────────────────────────────────────────┐
│                     GraphRunner.run()                        │
├─────────────────────────────────────────────────────────────┤
│  for node_update in app.astream(state):                     │
│      if node_name == "reasoning":                           │
│          # ReasoningNode 内部使用 callback 发送流式 tokens  │
│          # 或返回 AsyncGenerator                            │
│          for token in reasoning_stream:                     │
│              yield SSE_event("text", token)                 │
│      else:                                                   │
│          # 其他节点返回批量更新                              │
│          process_state_update(node_update)                  │
└─────────────────────────────────────────────────────────────┘
```

**实现方式：ReasoningNode 返回 AsyncGenerator**

ReasoningNode.compute() 将返回一个包含 `stream` 字段的更新，该字段是 AsyncGenerator：

```python
async def compute(self, state: GraphState) -> Dict[str, Any]:
    async def token_stream():
        async for token in self._stream_llm(prompt):
            yield token

    return {
        "response_stream": token_stream(),  # AsyncGenerator
        "dialogue_history": updated_history,
    }
```

GraphRunner 检测到 `response_stream` 后迭代并发送 SSE 事件。

**替代方案考虑：**
- **Callback 注入**：更复杂，需要修改节点签名
- **自定义 Channel**：需要深度修改 LangGraph 配置
- **批量响应**：用户体验差，首字延迟高

### Decision 2: 状态持久化策略

**选择：基于 SQLite 的轻量级 Checkpoint**

不使用 LangGraph 的 Checkpoint 机制（需要额外存储后端），而是：

1. **会话开始时**：从 `chat_db` 加载 `dialogue_history`
2. **HITL 暂停时**：将 `GraphState` 序列化为 JSON 存入新表 `graph_checkpoints`
3. **HITL 恢复时**：从 `graph_checkpoints` 加载并反序列化

```sql
CREATE TABLE graph_checkpoints (
    session_id TEXT PRIMARY KEY,
    state_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**替代方案考虑：**
- **LangGraph Checkpoint**：需要 Redis/PostgreSQL 等外部存储
- **内存缓存**：进程重启后状态丢失
- **文件系统**：不如 SQLite 查询方便

### Decision 3: Prompt 构建复用

**选择：提取 chat_processor 为独立模块**

`chat_processor.py` 中的以下逻辑将被 ReasoningNode 复用：

```
chat_processor.py
├── build_chat_context()      → 复用（构建 ChatContext）
├── build_system_prompt()     → 复用（构建完整 prompt）
├── format_working_memory_summary() → 复用
├── format_relevant_memories()      → 复用
├── get_intent_snippet()            → 复用
└── process_llm_response()          → 复用（解析 JSON 输出）
```

ReasoningNode 将导入这些函数，避免代码重复。

### Decision 4: HITL 生命周期

**选择：显式暂停/恢复端点**

```
[User Input] → [GraphRunner.run()] → [EmotionNode] → [MemoryNode]
    → [ReasoningNode] → (检测到 HITL 请求) → [HITLNode]
    → 返回 status="suspended" + hitl_request
    → SSE: event=hitl

[User 提交 HITL 表单] → POST /hitl/respond → 存储响应

[继续执行] → POST /hitl/continue
    → 加载 checkpoint → 注入 hitl_response → GraphRunner.resume()
    → 从 [ReasoningNode] 继续（或重新执行）
```

**关键设计：**
- `HITLNode` 将 `status` 设为 `"suspended"`
- GraphRunner 检测到 `suspended` 后停止迭代并持久化状态
- `/hitl/continue` 端点加载状态并调用 `GraphRunner.resume()`

### Decision 5: 完整替换策略

**选择：一次性完整替换，无过渡期**

直接将 `/chat` 和 `/chat/image` 端点切换为 GraphRunner 实现，删除旧的 `stream_chat_response` 和 `stream_image_analysis` 函数。

**原因：**
- 减少代码复杂度，避免维护两套实现
- GraphRunner 已完成核心节点测试
- SSE 事件格式保持兼容，前端无需修改
- 简化部署和维护

**实施步骤：**
1. 完成 GraphRunner 所有增强
2. 实现 ImageNode 图片处理节点
3. 端到端测试验证功能完整性
4. 直接替换 `/chat` 和 `/chat/image` 端点实现
5. 删除旧代码

### Decision 6: 图片处理架构

**选择：新增 ImageNode 作为可选入口节点**

图片分析流程与文本对话流程共享认知图谱，但入口不同：

```
/chat/image 请求:
┌─────────────────────────────────────────────────────────────┐
│  [ImageNode] → [MemoryExtractionNode] → [HITLNode]         │
│       │                                                     │
│       └─→ 提取 OCR 文本 → 生成记忆 HITL 表单               │
└─────────────────────────────────────────────────────────────┘

/chat 请求:
┌─────────────────────────────────────────────────────────────┐
│  [EmotionNode] → [MemoryNode] → [ReasoningNode] → ...      │
└─────────────────────────────────────────────────────────────┘
```

**ImageNode 职责：**
1. 调用 Vision API（通过 `image_analyzer.analyze_image_text()`）
2. 提取 OCR 文本并填充 `SemanticInput.text`
3. 如果是 `analyze_for_memory` 模式，触发记忆提取
4. 生成 HITL 表单让用户确认保存

**GraphState 扩展：**
```python
class SemanticInput(BaseModel):
    text: str = ""
    images: List[str] = []  # 已存在，用于存储 base64 图片
    image_action: Optional[str] = None  # 新增: "analyze_only" | "analyze_for_memory"
```

**GraphRunner 入口选择：**
```python
async def run(self, request: ChatRequest | ImageChatRequest):
    if isinstance(request, ImageChatRequest):
        # 图片处理流程
        entry_point = "image"
    else:
        # 文本对话流程
        entry_point = "emotion"

    orchestrator = GraphOrchestrator(entry_point=entry_point)
    ...
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          FastAPI (main.py)                          │
├─────────────────────────────────────────────────────────────────────┤
│  POST /chat                                                         │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ runner = GraphRunner()                                        │ │
│  │ return StreamingResponse(runner.run(request))                 │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  POST /chat/image                                                   │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ runner = GraphRunner()                                        │ │
│  │ return StreamingResponse(runner.run_image(request))           │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      GraphRunner (graph_runner.py)                  │
├─────────────────────────────────────────────────────────────────────┤
│  async def run(request: ChatRequest) -> AsyncGenerator[str, None]: │
│      state = init_state(request)                                   │
│      app = GraphOrchestrator().build().compile()                   │
│                                                                     │
│      async for update in app.astream(state):                       │
│          yield format_sse_event(update)                            │
│                                                                     │
│          if state.status == "suspended":                           │
│              save_checkpoint(state)                                │
│              break                                                 │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   GraphOrchestrator (core/graph.py)                 │
├─────────────────────────────────────────────────────────────────────┤
│  Text Entry → [EmotionNode] → [MemoryNode] → [ReasoningNode]       │
│                                                   │                 │
│                                   ┌───────────────┼───────────────┐ │
│                                   ▼               ▼               ▼ │
│                               [ToolNode]    [HITLNode]          END │
│                                   │               │                 │
│                                   └───────────────┘                 │
│                                           │                         │
│                                           ▼                         │
│                                   [ReasoningNode] ← (loop back)     │
│                                                                     │
│  Image Entry → [ImageNode] → [MemoryExtractionNode] → [HITLNode]   │
│                     │                                    │          │
│                     └─→ OCR 提取文本                     └─→ END   │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Text Chat Flow
```
ChatRequest → GraphState Initialization
    │
    ├── session_id → load dialogue_history from chat_db
    ├── message → SemanticInput.text
    └── intent_result → SemanticInput.intent (via chat_processor)

GraphState → Node Execution
    │
    ├── EmotionNode: semantic_input.text → emotional_context
    ├── MemoryNode: semantic_input.text → working_memory.retrieved_memories
    ├── ReasoningNode: all context → response_stream + tool_calls/hitl_request
    ├── ToolNode: pending_tool_calls → observation
    └── HITLNode: hitl_request → status="suspended"

Node Updates → SSE Events
    │
    ├── emotional_context → event: emotion
    ├── response_stream → event: text (streaming tokens)
    ├── hitl_request → event: hitl
    ├── tool_result → event: tool_result
    └── status == END → event: done
```

### Image Chat Flow
```
ImageChatRequest → GraphState Initialization
    │
    ├── session_id → load/create session
    ├── image → SemanticInput.images[0]
    └── action → SemanticInput.image_action

GraphState → Node Execution
    │
    ├── ImageNode: semantic_input.images[0] → OCR text extraction
    │              → semantic_input.text (extracted text)
    │              → SSE: event=text (OCR result)
    │
    ├── MemoryExtractionNode: semantic_input.text → memory extraction
    │                         → generate HITL form if confidence >= 0.3
    │
    └── HITLNode: hitl_request → status="suspended"
                 → SSE: event=hitl (memory confirm form)

Node Updates → SSE Events
    │
    ├── ocr_result → event: text (图片文本识别结果)
    ├── hitl_request → event: hitl (记忆保存确认表单)
    └── status == END → event: done
```

## Risks / Trade-offs

### Risk 1: 流式输出延迟
- **问题**：ReasoningNode 需要等待前置节点完成
- **缓解**：EmotionNode 和 MemoryNode 应快速执行（<100ms）
- **监控**：添加节点执行时间日志

### Risk 2: 状态序列化体积
- **问题**：GraphState 包含大量数据（dialogue_history）
- **缓解**：仅在 HITL 暂停时序列化；限制 history 长度
- **监控**：记录 checkpoint 大小

### Risk 3: LangGraph 版本兼容性
- **问题**：`astream()` API 可能在未来版本变化
- **缓解**：锁定版本 `>=0.2.6,<0.3.0`
- **监控**：CI 中测试 LangGraph 版本

### Trade-off: 代码复杂度 vs 解耦
- **选择**：复用 `chat_processor` 而非重写
- **原因**：减少重复代码，但增加模块间依赖
- **未来**：可考虑将公共逻辑提取到 `core/utils.py`

## Migration Plan

### Phase 1: GraphRunner Enhancement (Week 1)
1. 实现 ReasoningNode 真实 LLM 调用
2. 实现流式输出机制
3. 添加单元测试

### Phase 2: Integration (Week 2)
1. 添加 `graph_checkpoints` 表
2. 实现 ImageNode 图片处理节点
3. 替换 `/chat` 和 `/chat/image` 端点

### Phase 3: Testing & Deployment (Week 3)
1. 端到端测试验证
2. 修复发现的问题
3. 完整替换旧实现
4. 删除旧代码

### Rollback Strategy
- 使用 Git 回滚到替换前的版本
- 数据库结构兼容，无需迁移

## Open Questions

1. **是否需要支持并行节点执行？**
   - 当前设计是线性的 (Emotion → Memory → Reasoning)
   - Emotion 和 Memory 可并行执行以减少延迟
   - 需要评估 LangGraph 的并行节点支持

2. **HITL 恢复后是否重新执行 Reasoning？**
   - 选项 A：从暂停点继续（需要保存中间状态）
   - 选项 B：重新执行 Reasoning（简单，但可能重复 LLM 调用）
   - 当前倾向选项 B，简化实现

3. **如何处理长对话的 dialogue_history？**
   - 当前无截断策略
   - 可能需要实现滑动窗口或摘要机制
   - 不在本提案范围，但需考虑扩展点
