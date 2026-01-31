## 1. 扩展 MCP 服务配置

- [x] 1.1 在 `mcp_manager.py` 的 `MCPServerConfig` 中添加 `description: Optional[str]` 字段
- [x] 1.2 在 `mcp_manager.py` 的 `MCPServerConfig` 中添加 `trigger_keywords: List[str]` 字段
- [x] 1.3 更新 `MCPServerInfo` 模型以包含新字段
- [x] 1.4 更新 `main.py` 中的 MCP API 模型以支持新字段

## 2. 扩展意图识别系统

- [x] 2.1 在 `intent_types.py` 中添加 `MCPIntent` 枚举类
- [x] 2.2 在 `intent_types.py` 的 `IntentCategory` 中添加 `MCP` 类别
- [x] 2.3 在 `IntentResult` 中添加 `mcp_service_name: Optional[str]` 字段
- [x] 2.4 在 `intent_rules.py` 中添加 MCP 通用规则（显式调用模式）
- [x] 2.5 实现从 MCP 配置动态加载 trigger_keywords 到规则的逻辑
- [x] 2.6 更新 `intent_recognizer.py` 的 `RuleBasedMatcher` 支持动态 MCP 规则

## 3. 实现 MCP 工具执行模块

- [x] 3.1 创建 `mcp_tool_executor.py` 模块
- [x] 3.2 实现 `MCPToolExecutor` 类
  - [x] 3.2.1 实现 `get_available_tools()` - 获取运行中服务的工具列表
  - [x] 3.2.2 实现 `get_tool_description(tool_name)` - 获取工具描述（Level 1/2/3）
  - [x] 3.2.3 实现 `execute_tool(tool_name, arguments)` - 执行工具调用
  - [x] 3.2.4 实现 stdio 通信逻辑（JSON-RPC 格式）
  - [x] 3.2.5 实现超时控制和错误处理

## 4. 集成到对话处理器

- [x] 4.1 在 `chat_processor.py` 中添加 `MCP_INTENT_SNIPPET_TEMPLATE`
- [x] 4.2 更新 `get_intent_snippet()` 函数支持 MCP 意图
- [x] 4.3 实现 `get_mcp_intent_snippet()` - 构建工具描述 prompt
- [x] 4.4 更新 `CHAT_PROMPT_TEMPLATE` 支持 tool_call 输出格式
- [x] 4.5 实现 `extract_tool_call()` - 提取工具调用请求

## 5. 扩展聊天 API

- [x] 5.1 在 `main.py` 中实现 tool_call 响应解析
- [x] 5.2 实现工具调用执行和结果处理流程
- [x] 5.3 实现工具调用结果 SSE 事件（`event: tool_result`）
- [x] 5.4 支持工具调用后继续对话（在 stream_chat_response 和 stream_hitl_continuation 中）

## 6. 测试

- [x] 6.1 添加 MCP 意图识别单元测试
- [x] 6.2 添加 MCP 工具执行单元测试
- [x] 6.3 添加 tool_call 提取测试
- [x] 6.4 确保现有测试通过（43 个测试全部通过）

## 7. 文档更新

- [ ] 7.1 更新 MCP 服务注册 UI 以支持 description 和 trigger_keywords 输入
- [ ] 7.2 更新 openspec/project.md 中的 MCP 相关说明
