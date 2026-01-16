# 情感记忆 AI 系统

一个基于 FastAPI 的情感感知 AI 对话系统，支持情感检测、长期记忆管理和智能响应策略。

## 功能特性

- **AI 对话**: 流式对话接口 (SSE)，支持多种 LLM 服务
- **情感检测**: 自动识别用户消息中的情感
- **记忆管理**: 长期记忆存储和检索
- **会话管理**: 聊天记录持久化

## 快速开始

### 启动 FastAPI 服务

**方式一：使用启动脚本（推荐）**
```bash
./start.sh
```
启动脚本会自动检查并清理端口占用，然后启动服务。

**方式二：直接启动**
```bash
uv run python main.py
```

**注意**：如果遇到 `Address already in use` 错误，说明端口 8002 已被占用。可以：
- 使用启动脚本自动处理
- 手动清理：`lsof -ti :8002 | xargs kill -9`
- 或修改 `main.py` 中的端口号

## 核心模块

| 模块 | 描述 |
|------|------|
| `main.py` | FastAPI 主应用入口 |
| `chat_processor.py` | 聊天处理与 LLM 集成 |
| `emotion_detector.py` | 情绪检测解析 |
| `response_strategy.py` | 响应策略选择 |
| `memory_manager.py` | 长期记忆管理 |
| `chat_db.py` | SQLite 数据库管理 |

## API 接口

### 系统接口
- `GET /health` - 健康检查

### AI 对话接口
- `POST /chat` - AI 对话（SSE 流式响应）

### 聊天记录接口
- `GET /chat/history` - 获取会话列表
- `GET /chat/history/{session_id}` - 获取会话详情
- `DELETE /chat/history/{session_id}` - 删除会话
- `DELETE /chat/history` - 清空所有会话

### 记忆管理接口
- `GET /memory/long-term` - 获取记忆列表
- `GET /memory/long-term/{id}` - 获取记忆详情
- `POST /memory/long-term` - 创建记忆
- `PUT /memory/long-term/{id}` - 更新记忆
- `DELETE /memory/long-term/{id}` - 删除记忆
- `DELETE /memory/long-term` - 清空所有记忆
- `POST /memory/long-term/batch-delete` - 批量删除
- `GET /memory/long-term/export` - 导出记忆
- `POST /memory/long-term/import` - 导入记忆
- `GET /memory/working/{session_id}` - 获取工作记忆

## AI 对话功能配置

### 配置文件

1. 复制示例配置文件:
```bash
cp chat_config.example.json chat_config.json
```

2. 编辑 `chat_config.json`，填写您的 API 配置:
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

### 支持的 LLM 服务商

| 服务商 | API Base URL |
|--------|-------------|
| OpenAI | `https://api.openai.com/v1` |
| DeepSeek | `https://api.deepseek.com/v1` |
| Azure OpenAI | `https://{your-resource}.openai.azure.com/openai/deployments/{deployment-id}` |

### 请求格式

```json
{
  "message": "你好",
  "session_id": "optional-session-id",
  "history": [
    {"role": "user", "content": "之前的问题"},
    {"role": "assistant", "content": "之前的回答"}
  ]
}
```

### 响应格式（SSE）

```
event: text
data: {"type": "text", "payload": {"content": "响应片段"}}

event: emotion
data: {"type": "emotion", "payload": {"primary": "happy", "category": "positive", "confidence": 0.85}}

event: done
data: {"type": "done"}
```

## 记忆系统

### 记忆类别

| 类别 | 描述 | 示例 |
|------|------|------|
| `preference` | 用户偏好 | 喜欢的编程语言、话题 |
| `fact` | 用户事实 | 姓名、职业、所在城市 |
| `pattern` | 行为模式 | 对话风格、常用表达 |

### 环境变量

- `USE_MEMORY_EMOTION_SYSTEM=true` - 启用记忆和情绪系统（默认禁用）

服务默认运行在 `http://localhost:8002`
