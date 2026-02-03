# Cognitive Architecture Design

## 1. 系统级意图声明 (System Intent)
本系统的存在是为了提供一个**可信赖的、协作式的桌面认知伴侣**。它不仅是问答机器，而是具备长期记忆、能够感知用户情绪、并在不确定时主动寻求人类协助（HITL）的智能代理。它通过显式的认知轨迹（Cognitive Trace）建立用户信任。

## 2. 核心 State 设计 (State Schema)
Graph State 是系统唯一的真理来源（Source of Truth）。它必须是可序列化、类型安全的。

### 长期稳定字段 (Stable State)
这些字段在整个认知周期中保持一致或单调增长：
*   `conversation_id`: 会话唯一标识。
*   `user_profile`: 用户的长期画像引用（非全量数据，而是关键特征快照）。
*   `working_memory`: 当前任务的工作记忆（短期上下文、目标栈）。
*   `dialogue_history`: 标准化的对话历史（OpenAI 格式）。
*   `emotional_context`: 当前的情绪状态向量（用于调制，非决策）。
*   `semantic_input`: 归一化后的多模态输入语义（Text/Image -> Semantic Representation）。
*   `execution_trace`: 关键决策节点的执行快照列表（用于回放和审计）。

### 不应进入 State 的信息
*   `llm_raw_response`: 原始的、未解析的 LLM 输出流（除非用于调试）。
*   `ui_render_state`: 前端具体的 UI 状态（如弹窗是否打开）。
*   `large_blobs`: 大文件二进制数据（应存储引用/路径）。

## 3. 主要节点类型划分 (Node Types)

### 3.1. 输入规范化节点 (Input Normalization Node)
*   **职责**：接收文本、图片、文件拖拽等原始输入，转换为统一的语义表示。
*   **输出**：更新 State 中的 `semantic_input`。

### 3.2. 情绪推断节点 (Emotion Inference Node)
*   **职责**：基于输入和历史，更新情绪状态。
*   **约束**：**调制器（Modulator）**。它不改变控制流分支，只修改后续 Prompt 的语气参数或工具调用的置信度阈值。

### 3.3. 记忆节点 (Memory Node)
*   **职责**：长期记忆的检索（Recall）与写入（Consolidate）。
*   **交互**：与外部向量数据库或 SQLite 交互，将结果注入 `working_memory`。

### 3.4. 推理节点 (Reasoning/Planner Node)
*   **职责**：核心大脑。基于 State 生成下一步行动计划（Plan）。
*   **决策**：决定是直接回复、调用工具、还是请求 HITL。

### 3.5. 工具选择与 MCP 调用节点 (Tool Selector & Executor)
*   **Selector**：从 MCP Registry 筛选可用工具。
*   **Executor**：执行工具调用，捕获结果或异常。

### 3.6. HITL 中断节点 (Human-in-the-loop Node)
*   **职责**：挂起图执行，向用户呈现交互表单（确认、澄清、选择）。
*   **特性**：**合法中间态**。支持序列化挂起，等待用户异步输入后恢复（Resume）。用户输入被视为 State update。

### 3.7. 日志/观察节点 (Observer Node)
*   **职责**：记录认知轨迹。
*   **约束**：旁路节点，不影响决策。

## 4. 典型认知流示例 (Cognitive Flow)

### 场景：任务执行失败 -> HITL -> 恢复
1.  **Start**: 用户输入 "帮我分析这个报错日志"。
2.  **Normalize**: 解析文本，识别意图。
3.  **Reasoning**: 决定调用 `LogAnalyzer` 工具。
4.  **Tool Exec**: `LogAnalyzer` 执行失败，返回 "Permission Denied"。
5.  **Reasoning (Re-eval)**: 捕获错误，判断需要用户授权。
6.  **Transition to HITL**:
    *   State 更新：`status=suspended`, `hitl_request={type: "permission", msg: "需要授权..."}`。
    *   UI 弹出授权卡片。
    *   Graph 挂起。
7.  **Human Action**: 用户点击 "授权并重试"。
8.  **Resume**: Graph 恢复。
    *   State 更新：`last_human_input="authorized"`.
9.  **Reasoning**: 看到授权标记，重新生成计划。
10. **Tool Exec**: 重试 `LogAnalyzer`，成功。
11. **End**: 输出分析结果。

## 5. 关键设计约束 (Hard Constraints)
1.  **State Stability**: State 结构一旦定义，修改需兼容旧版。
2.  **Emotion as Modulator**: 严禁 `if emotion == 'angry': exit()` 这样的逻辑。情绪只能作为 Prompt 变量。
3.  **Normalized Input**: 节点间通信严禁处理原始 UI 事件，必须是语义数据。
4.  **Separation of Concerns**: MCP 服务管理（注册）与 MCP 调用（执行）分离。
