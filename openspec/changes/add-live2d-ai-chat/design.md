# Live2D AI 对话功能设计

## Context

Wenko 是一个工作流编排系统，已集成 Live2D 虚拟形象用于增强用户体验。当前 Live2D 仅作为装饰性元素，需要添加 AI 对话功能使其成为交互式助手。

**约束条件**:
- 使用远程 LLM API（支持 OpenAI 兼容接口）
- 配置文件需 git 忽略，保护 API Key 安全
- 低延迟：使用 SSE 流式输出，提供即时响应体验
- 轻量级：最小化对现有代码的改动

## Goals / Non-Goals

**Goals**:
- 用户可以通过输入框与 Live2D 角色对话
- 对话响应以流式方式在消息气泡中展示
- 支持多轮对话上下文
- 通过配置文件灵活切换不同 LLM 服务商

**Non-Goals**:
- 不实现语音输入/输出功能（后续可扩展）
- 不实现复杂的对话管理系统（如对话分支、意图识别）

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Live2D Window (Electron)                  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Live2D Canvas                                          ││
│  │  ┌───────────────────────────────────────────────────┐ ││
│  │  │  Message Bubble (SSE Stream Display)              │ ││
│  │  └───────────────────────────────────────────────────┘ ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Chat Input Bar                                         ││
│  │  ┌─────────────────────────────────────┐  ┌──────────┐ ││
│  │  │  Text Input                          │  │  Send    │ ││
│  │  └─────────────────────────────────────┘  └──────────┘ ││
│  └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│                    HTTP SSE                                  │
│                       ↓                                      │
├─────────────────────────────────────────────────────────────┤
│              Python Backend (FastAPI)                        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  POST /chat                                              ││
│  │  - Receives: { message, session_id, history? }          ││
│  │  - Returns: SSE stream of text chunks                   ││
│  └─────────────────────────────────────────────────────────┘│
│                       ↓                                      │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  LLM Client (OpenAI Compatible)                         ││
│  │  - Config: workflow/chat_config.json                    ││
│  │  - Supports: OpenAI, DeepSeek, Azure, etc.              ││
│  │  - Streaming: enabled                                   ││
│  └─────────────────────────────────────────────────────────┘│
│                       ↓                                      │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Remote LLM API                                         ││
│  │  - OpenAI API / DeepSeek / Azure OpenAI / etc.          ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Configuration

### 配置文件: `workflow/chat_config.json`

```json
{
  "api_base": "https://api.openai.com/v1",
  "api_key": "sk-your-api-key-here",
  "model": "gpt-4o-mini",
  "system_prompt": "你是一个友好的 AI 助手，名叫 Wenko。请用简洁、亲切的方式回答用户问题。",
  "max_tokens": 1024,
  "temperature": 0.7
}
```

### 配置文件模板: `workflow/chat_config.example.json`

提供示例配置文件，帮助用户快速配置：

```json
{
  "api_base": "https://api.openai.com/v1",
  "api_key": "your-api-key-here",
  "model": "gpt-4o-mini",
  "system_prompt": "你是一个友好的 AI 助手。",
  "max_tokens": 1024,
  "temperature": 0.7
}
```

### Git 忽略规则

在 `.gitignore` 中添加：
```
workflow/chat_config.json
```

## Decisions

### D1: 使用 SSE 而非 WebSocket

**决策**: 使用 Server-Sent Events (SSE) 实现流式响应

**理由**:
- 现有代码已使用 `@microsoft/fetch-event-source` 进行 SSE 通信
- SSE 更简单，无需维护双向连接
- 对话场景是单向流（用户发送 → AI 回复），SSE 足够满足需求

### D2: 使用远程 LLM API

**决策**: 集成远程 LLM API（OpenAI 兼容接口）

**理由**:
- 无需用户本地安装额外软件
- 响应速度更快，模型能力更强
- 支持多种服务商切换（OpenAI、DeepSeek、Azure 等）
- 通过配置文件灵活配置

**兼容的服务商**:
- OpenAI API (`https://api.openai.com/v1`)
- DeepSeek (`https://api.deepseek.com/v1`)
- Azure OpenAI
- 其他 OpenAI 兼容接口

### D3: 配置文件与 API Key 安全

**决策**: 使用独立配置文件 `workflow/chat_config.json`，并在 git 中忽略

**理由**:
- 保护 API Key 不被提交到版本控制
- 提供示例配置文件帮助用户快速上手
- 配置与代码分离，便于不同环境部署

### D4: 对话历史存储在前端

**决策**: 对话历史在前端 sessionStorage 中管理

**理由**:
- 减少后端复杂度
- 对话历史随会话结束清除，符合桌面应用习惯
- 后续可轻松扩展为持久化存储

## Data Flow

```
1. 用户在输入框输入消息
2. 前端发送 POST /chat 请求
   - body: { message: "用户输入", history: [...] }
3. 后端读取 chat_config.json 配置
4. 后端调用远程 LLM API（流式）
5. 后端通过 SSE 逐 token 返回响应
6. 前端实时追加到消息气泡
7. 流结束后，更新对话历史
```

## API Design

### POST /chat

```typescript
// Request
{
  message: string;          // 用户消息
  session_id?: string;      // 会话 ID（可选）
  history?: Array<{         // 对话历史（可选）
    role: 'user' | 'assistant';
    content: string;
  }>;
}

// SSE Response
event: text
data: {"type": "text", "payload": {"content": "响应片段"}}

event: done
data: {"type": "done"}

event: error
data: {"type": "error", "payload": {"message": "错误信息"}}
```

## UI Components

### ChatInput 组件

位于 Live2D 窗口底部，包含：
- 文本输入框（placeholder: "输入消息..."）
- 发送按钮（支持 Enter 键发送）
- 发送中状态显示

### 消息气泡增强

复用现有 `showSSEMessage` 函数：
- 支持 markdown 渲染（可选）
- 自动滚动到最新内容
- 加载中动画

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| API Key 泄露 | 配置文件 git 忽略，提供 example 文件 |
| 配置文件缺失 | 启动时检查，缺失则提示用户创建 |
| 网络连接失败 | 显示友好错误提示，支持重试 |
| API 费用 | 默认使用低成本模型（如 gpt-4o-mini） |
| 对话历史过长 | 限制历史长度（如最近 10 轮） |

## Open Questions

1. 是否需要支持 markdown 渲染？（影响 UI 复杂度）
2. 是否需要添加「清除对话」按钮？
3. 是否需要在 UI 中显示当前使用的模型名称？
