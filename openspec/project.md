# Project Context

## Purpose

Wenko 是一个情感记忆 AI 系统，专注于提供智能对话、情感检测和记忆管理功能。项目目标：

1. 提供具有情感感知能力的 AI 对话
2. 支持长期记忆管理，让 AI 记住用户偏好和事实
3. 通过 Electron 桌面应用提供用户友好的界面
4. 集成 Live2D 虚拟形象增强用户体验

## Tech Stack

### Electron 客户端 (`/electron/`)
- **运行时**: Electron 38
- **前端框架**: React 19
- **构建工具**: Vite 7
- **UI 组件库**: Ant Design 4
- **HTTP 服务**: Express (静态服务器)
- **虚拟形象**: Live2D Cubism SDK

### Python 后端 (`/workflow/`)
- **运行时**: Python 3.10+
- **Web 框架**: FastAPI + Uvicorn
- **数据库**: SQLite (聊天记录和记忆存储)
- **数据验证**: Pydantic
- **HTTP 客户端**: httpx
- **包管理**: uv / hatch

## Project Conventions

### Code Style

#### JavaScript/React
- 使用 ES6+ 语法
- React 函数组件优先
- 使用 JSX 扩展名 (`.jsx`)
- Ant Design 组件用于 UI 构建

#### Python
- 遵循 PEP 8
- 使用类型注解 (Type Hints)
- Pydantic 模型用于数据验证
- 异步函数优先 (`async/await`)

### Architecture Patterns

#### 前后端分离
- Electron 前端通过 HTTP 与 Python 后端通信
- REST API 风格接口
- SSE (Server-Sent Events) 用于流式对话响应

#### 核心模块
- `chat_processor.py` - 聊天处理与 LLM 集成
- `emotion_detector.py` - 情绪检测解析
- `response_strategy.py` - 响应策略选择
- `memory_manager.py` - 记忆管理系统
- `chat_db.py` - SQLite 数据库管理

### Testing Strategy
- Python 后端：待完善测试覆盖
- Electron 前端：通过 API 测试工具手动验证

### Git Workflow
- 主分支: `main`
- 功能分支: `feature/*`
- 提交信息格式: `type(scope): description`
  - type: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
  - scope: `electron`, `workflow`, `docs` 等

## Domain Context

### 情感检测 (Emotion Detection)
系统能够检测用户消息中的情感，并据此调整响应策略。

### 记忆系统 (Memory System)
- **长期记忆**: 存储用户偏好、事实和行为模式
- **工作记忆**: 会话级别的上下文信息

### 记忆类别
| 类别 | 描述 |
|------|------|
| `preference` | 用户偏好（如喜欢的语言、话题） |
| `fact` | 用户相关事实（如姓名、职业） |
| `pattern` | 行为模式（如对话风格） |

## Important Constraints

1. **跨平台兼容**: Electron 应用需支持 macOS、Windows
2. **本地优先**: 数据存储在本地，保护用户隐私
3. **LLM 无关性**: 支持多种 OpenAI 兼容的 LLM 服务

## External Dependencies

### 必需服务
- Python 后端服务 (默认端口: 8002)

### 远程 LLM API（AI 对话功能）
- 支持 OpenAI 兼容接口（OpenAI、DeepSeek、Azure OpenAI 等）
- 配置存储在 SQLite 数据库 `workflow/data/chat_history.db` 的 `app_settings` 表中
- 可通过 Workflow 面板的"设置"选项卡进行图形化配置
- 可通过 Settings API (`/api/settings`) 进行程序化配置

### Live2D
- Live2D Cubism SDK Web
- 模型文件存放在 `/electron/public/live2d/`
- 支持 AI 对话功能（通过 Chat API）
