# Change: Integrate GraphRunner into Production Chat Flow

## Why

当前系统存在两套并行的聊天处理架构：

1. **现有生产架构** (`main.py:stream_chat_response` + `stream_image_analysis`)：直接调用 LLM API，手动处理记忆、情感、意图识别、HITL、MCP 工具调用等功能，代码复杂度高（~500 行核心逻辑）。

2. **新 LangGraph 架构** (`graph_runner.py` + `core/`)：基于 LangGraph 的认知图谱实现，已完成核心节点（EmotionNode、MemoryNode、ReasoningNode、ToolNode、HITLNode），但尚未接入生产环境。

`refactor-langgraph-cognitive-system` 提案已完成第 1-3 阶段（State 定义、核心节点实现），现需完成第 4 阶段：**将 GraphRunner 完整接入生产聊天流程**，完整替换现有的手动编排逻辑。

## What Changes

### **BREAKING**
- `/chat` 端点将完整切换为 GraphRunner 驱动的认知图谱执行
- `/chat/image` 端点将通过 GraphRunner 处理图片分析流程
- 删除旧的 `stream_chat_response` 和 `stream_image_analysis` 函数
- SSE 事件格式保持兼容，但事件产生机制从手动触发变为基于图节点状态更新

### 核心变更
1. **GraphRunner 增强**
   - 集成真实 LLM 客户端（httpx AsyncClient）到 ReasoningNode
   - 支持流式响应输出（当前仅支持批量响应）
   - 集成现有的 `chat_processor` 中的 prompt 构建逻辑
   - 支持 HITL 请求的完整生命周期（暂停、恢复）

2. **ReasoningNode 重构**
   - 使用 `chat_processor.build_system_prompt()` 构建 prompt
   - 支持意图识别结果注入
   - 实现真实 LLM 调用替换 mock 逻辑
   - 支持流式输出令牌

3. **新增 ImageNode（图片处理节点）**
   - 封装 Vision API 调用逻辑
   - 支持 OCR 文本提取
   - 支持记忆提取和 HITL 表单生成
   - 集成到认知图谱作为可选入口节点

4. **状态持久化**
   - 将 GraphState 与现有 SQLite 数据库集成
   - 支持会话恢复（HITL 暂停后恢复）
   - 维护 `dialogue_history` 与现有 `chat_db` 同步

5. **端点替换**
   - `/chat` 端点直接使用 GraphRunner
   - `/chat/image` 端点使用 GraphRunner（带 ImageNode）
   - 删除旧的 `stream_chat_response` 和 `stream_image_analysis` 函数

6. **代码清理**
   - 移除 `main.py` 中约 500 行的手动编排逻辑
   - 将可复用逻辑迁移到 `chat_processor.py` 或 `core/` 模块

## Impact

### Affected specs
- `cognitive-graph`（新建）

### Affected code
- `workflow/graph_runner.py` - 主要修改，成为聊天入口
- `workflow/core/nodes/reasoning.py` - 重构，集成真实 LLM
- `workflow/core/nodes/image.py` - 新增，图片处理节点
- `workflow/core/graph.py` - 调整路由逻辑，支持图片入口
- `workflow/core/state.py` - 扩展字段，支持图片输入
- `workflow/main.py` - 删除旧逻辑，使用 GraphRunner
- `workflow/chat_processor.py` - 提取可复用逻辑
- `workflow/image_analyzer.py` - 被 ImageNode 调用

### Dependencies
- `langgraph>=0.2.6`（已安装）
- 现有系统功能完整性依赖（记忆、情感、HITL、MCP）

### Migration Notes
- 一次性完整替换，无过渡期
- 前端 SSE 事件格式保持兼容，无需修改
- 数据库结构兼容，无需迁移
