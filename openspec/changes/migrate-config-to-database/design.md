## Context

Wenko 是一个情感记忆 AI 系统，使用 Electron + Python FastAPI 架构。当前配置通过 `chat_config.json` 文件管理，用户需要手动编辑 JSON 文件来配置 API 端点、密钥等信息。

现有数据库架构：
- 使用 SQLite 存储聊天记录和记忆数据
- 数据库文件位于 `workflow/data/chat_history.db`
- 已有完善的版本迁移机制 (`_DB_VERSION`)

现有 Workflow 面板架构：
- React 19 + Vite 7
- 使用 shadcn/ui 组件库
- 已有三个选项卡：聊天历史、工作记忆、长期记忆

## Goals / Non-Goals

### Goals
- 将 `chat_config.json` 中的所有配置项迁移到 SQLite 数据库
- 提供 RESTful API 管理配置的读写操作
- 在 Workflow 面板新增"设置"选项卡，提供图形化配置界面
- 配置修改后立即生效，无需重启服务

### Non-Goals
- 不支持多用户/多配置文件切换
- 不加密存储敏感信息（SQLite 本地文件与 JSON 安全级别相同）
- 不支持配置导入/导出功能（可后续扩展）
- 不支持环境变量覆盖配置（完全依赖数据库）

## Decisions

### 1. 数据库 Schema 设计

采用 Key-Value 结构存储配置，便于扩展：

```sql
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    value_type TEXT DEFAULT 'string',  -- string, number, boolean, json
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Alternatives considered:**
- 单行 JSON 存储所有配置：不便于单项更新和查询
- 强类型列存储：需要 ALTER TABLE 添加新配置项，不够灵活

### 2. 配置项定义

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `llm.api_base` | string | `https://api.openai.com/v1` | LLM API 端点 |
| `llm.api_key` | string | `""` | API 密钥 |
| `llm.model` | string | `gpt-4o-mini` | 对话模型 |
| `llm.system_prompt` | string | `你是一个友好的 AI 助手。` | 系统提示词 |
| `llm.max_tokens` | number | `1024` | 最大 token 数 |
| `llm.temperature` | number | `0.7` | 采样温度 |
| `llm.vision_model` | string | `volcengine/doubao-embedding-vision` | 视觉模型 |

### 3. API 设计

```
GET    /api/settings              # 获取所有配置
GET    /api/settings/{key}        # 获取单项配置
PUT    /api/settings/{key}        # 更新单项配置
PUT    /api/settings              # 批量更新配置
POST   /api/settings/reset        # 重置为默认值
```

### 4. 前端组件结构

```
components/features/settings/
├── settings-tab.tsx           # 设置选项卡主组件
├── llm-config-section.tsx     # LLM 配置区域
└── api-key-input.tsx          # API Key 输入组件（带显示/隐藏切换）
```

### 5. 配置加载策略

```python
def load_chat_config() -> ChatConfig:
    """从数据库加载配置，如不存在则使用默认值"""
    settings = get_all_settings()

    return ChatConfig(
        api_base=settings.get("llm.api_base", "https://api.openai.com/v1"),
        api_key=settings.get("llm.api_key", ""),
        model=settings.get("llm.model", "gpt-4o-mini"),
        # ...
    )
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 首次启动无配置 | 提供默认值，引导用户在设置页面填写 API Key |
| API Key 明文存储 | 与原 JSON 文件安全级别相同；可在后续版本集成系统密钥链 |
| 数据库迁移失败 | 使用 try/except 处理 ALTER TABLE，兼容旧版本数据库 |

## Migration Plan

1. 添加 `app_settings` 表（DB Version 5）
2. 如果存在 `chat_config.json`，自动导入到数据库
3. 修改所有配置加载函数使用数据库
4. 删除 `chat_config.json` 和 `chat_config.example.json` 文件
5. 更新 README 文档

## Open Questions

无
