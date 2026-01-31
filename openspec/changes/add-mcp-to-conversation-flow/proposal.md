# Change: 将 MCP 服务集成到对话流程

## Why

当前系统已实现 MCP 服务的注册和生命周期管理，但 MCP 服务尚未集成到对话流程中。AI 无法在对话过程中调用已注册的 MCP 工具，导致 MCP 功能的价值无法发挥。

同时，现有的意图识别系统（Layer 1 规则匹配 + Layer 2 LLM 分类）专注于 Memory 和 HITL 场景，没有考虑 MCP 工具调用的意图识别。如果每次对话都发送完整的 MCP 工具 schema，会消耗大量 token。

本次变更旨在：
1. 将 MCP 工具调用集成到对话流程中
2. 在意图识别中加入 MCP 相关逻辑，实现 token 优化
3. 支持混合触发模式（用户显式调用 + AI 主动判断）

## What Changes

### 后端 (workflow/)

- **新增** `mcp_tool_executor.py` - MCP 工具调用执行模块
  - 与已运行的 MCP 服务进程通信
  - 工具调用结果解析和格式化
  - 错误处理和超时控制

- **修改** `intent_types.py` - 添加 MCP 意图类型
  - 新增 `MCPIntent` 枚举
  - 新增 `IntentCategory.MCP` 类别

- **修改** `intent_rules.py` - 添加 MCP 意图识别规则
  - 通用 MCP 触发关键词（如"用 xxx 工具"、"调用"等）
  - 支持从 MCP 服务配置动态加载自定义关键词

- **修改** `mcp_manager.py` - 扩展服务配置
  - 添加 `description`（工具简短描述）字段
  - 添加 `trigger_keywords`（触发关键词）字段
  - 添加获取运行中服务工具描述的方法

- **修改** `chat_processor.py` - 集成 MCP 到对话流程
  - 添加 MCP 意图 snippet（简短描述模式）
  - 实现工具调用结果注入到上下文

- **修改** `main.py` - 扩展聊天 API
  - 处理 LLM 返回的工具调用请求
  - 调用 MCP 工具并返回结果
  - 支持多轮工具调用

### 数据结构

- **MCP 服务配置扩展**
  - `description: str` - 工具功能的简短描述（用于 prompt snippet）
  - `trigger_keywords: List[str]` - 触发关键词列表

- **意图识别扩展**
  - `MCPIntent` 枚举 - MCP 工具调用意图类型
  - `mcp_tool_name: Optional[str]` - 匹配到的工具名称

## Impact

- **Affected specs**:
  - 新增 `mcp-conversation-integration` capability
  - 关联 `workflow-engine` (扩展对话处理能力)

- **Affected code**:
  - `workflow/mcp_manager.py` - 配置扩展
  - `workflow/intent_types.py` - 意图类型扩展
  - `workflow/intent_rules.py` - 规则扩展
  - `workflow/chat_processor.py` - 对话流程扩展
  - `workflow/main.py` - API 扩展
  - 新增 `workflow/mcp_tool_executor.py`

- **Breaking changes**: 无（MCP 服务配置新增可选字段）

- **Dependencies**:
  - 依赖现有 `mcp_manager.py` 模块
  - 依赖现有意图识别系统
