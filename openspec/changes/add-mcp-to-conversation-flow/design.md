## Context

Wenko 系统已实现 MCP 服务的注册和生命周期管理，但 MCP 工具尚未集成到对话流程中。本设计描述如何将 MCP 工具调用能力无缝集成到现有的对话处理架构中，同时复用意图识别系统实现 token 优化。

### 现有架构

```
用户消息 → 意图识别(Layer1/Layer2) → 构建 Prompt → LLM → 解析响应 → 返回
              ↓                          ↓
         Memory/HITL snippet      Memory/HITL 处理
```

### 目标架构

```
用户消息 → 意图识别(Layer1/Layer2) → 构建 Prompt → LLM → 解析响应
              ↓                          ↓              ↓
    Memory/HITL/MCP snippet      工具描述注入      工具调用检测
                                                       ↓
                                              MCP 工具执行 → 结果注入 → LLM 继续
```

## Goals / Non-Goals

### Goals
- 支持 AI 在对话中调用已注册且运行中的 MCP 工具
- 通过意图识别优化，仅在需要时注入工具描述，节省 token
- 支持混合触发模式：用户显式调用 + AI 主动判断
- 支持多轮工具调用（工具调用结果作为上下文继续对话）

### Non-Goals
- 不实现 MCP 服务的自动启动（用户需先手动启动服务）
- 不实现复杂的工具调用链（本期仅支持单工具单次调用）
- 不实现 MCP 服务发现（需先注册才能使用）

## Decisions

### Decision 1: 意图识别策略 - 两层结合

采用通用规则 + 动态关键词的组合策略：

**Layer 1 通用规则**（预设在 `intent_rules.py`）：
```python
MCP_RULES = [
    IntentRule(
        name="mcp_explicit_call",
        pattern=_compile_patterns([
            r"用.+工具",
            r"调用.+",
            r"使用.+服务",
            r"帮我.+一下",  # 配合工具名
        ]),
        intent_type="mcp_tool_call",
        priority=15,
    ),
]
```

**动态关键词**（从 MCP 配置加载）：
- 每个 MCP 服务可配置 `trigger_keywords`
- 运行时将这些关键词编译为额外的匹配规则
- 示例：weather 服务配置 `["天气", "气温", "下雨"]`

**Alternatives considered**:
- 仅使用通用规则：无法覆盖特定工具场景
- 仅使用 Layer 2 LLM：增加 API 调用，不符合 token 优化目标

### Decision 2: 工具描述注入策略 - 分层描述

采用三级工具描述策略：

**Level 1: 极简描述（~50 chars/工具）**
- 用于 Layer 1 意图匹配时的 snippet
- 仅包含工具名和一句话描述
- 示例：`[工具] weather: 查询指定城市的天气信息`

**Level 2: 简要 Schema（~200 chars/工具）**
- 用于 AI 判断是否需要调用
- 包含工具名、描述、主要参数
- 示例：
```json
{"name": "weather", "description": "查询天气", "params": ["city: 城市名"]}
```

**Level 3: 完整 Schema**
- 仅在确定要调用工具时发送
- 包含完整的 JSON Schema 和所有参数细节

**工作流程**：
1. Layer 1 匹配 MCP 意图 → 注入 Level 1 描述
2. LLM 决定调用工具 → 请求 Level 3 Schema
3. 执行工具调用

### Decision 3: 工具调用协议

采用 OpenAI Function Calling 兼容格式，便于复用现有 LLM 集成：

**LLM 输出格式**：
```json
{
  "response": "让我帮你查询天气",
  "tool_call": {
    "name": "weather",
    "arguments": {"city": "北京"}
  }
}
```

**工具调用结果注入**：
```json
{
  "role": "tool",
  "name": "weather",
  "content": "北京今天晴，温度 25°C"
}
```

### Decision 4: MCP 通信机制

使用 stdio 与 MCP 服务进程通信：

1. MCP 服务已由 `mcp_manager` 启动，持有 `subprocess.Popen` 引用
2. 通过 stdin/stdout 发送 JSON-RPC 请求
3. 支持异步调用和超时控制

**为什么不用 HTTP**：
- MCP 协议原生使用 stdio
- 避免额外的端口占用和网络开销
- 与 Claude Desktop 等工具的 MCP 实现保持一致

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| MCP 服务未运行时调用失败 | 调用前检查服务状态，返回友好提示 |
| 工具调用超时 | 设置合理超时（默认 30s），支持配置 |
| Layer 1 关键词误匹配 | 结合工具名验证，必要时回退到 Layer 2 |
| 多工具同名冲突 | 服务名作为命名空间：`service_name.tool_name` |

## Migration Plan

本变更为新增功能，无需迁移：
1. MCP 服务配置新增 `description` 和 `trigger_keywords` 字段（可选）
2. 现有 MCP 服务配置保持兼容，新字段有默认值
3. 用户可逐步为已注册服务添加触发关键词

## Open Questions

1. **工具调用频率限制**: 是否需要限制单次对话的工具调用次数？
   - 建议：默认限制 3 次，可配置

2. **工具调用审计**: 是否需要记录工具调用历史？
   - 建议：首期在日志中记录，后续考虑持久化

3. **敏感工具确认**: 某些工具是否需要用户确认后才能执行？
   - 建议：通过 HITL 机制实现，首期不做强制要求
