# Project Context

## Purpose

Wenko 是一个工作流编排系统，用于定义和执行自动化工作流。项目目标：

1. 提供可视化的工作流编排能力
2. 支持灵活的步骤定义和条件控制
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
- **工作流引擎**: LangGraph
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

#### 工作流引擎
- 步骤 (Step) 是基本执行单元
- 使用 `step_registry` 注册可用步骤
- 支持条件分支 (if/then/else)
- 上下文 (Context) 在步骤间共享状态

#### 模板系统
- 模板存储在 JSON 文件中 (`templates.json`)
- 支持模板的 CRUD 操作
- 模板可直接执行

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

### 工作流 (Workflow)
一个工作流由多个步骤 (Steps) 组成，按顺序或条件执行。

### 步骤 (Step)
基本执行单元，每个步骤有：
- `step`: 步骤类型 (如 `EchoInput`, `FetchURL`)
- `id`: 唯一标识符
- `input`: 输入参数 (可选)
- `output_var`: 输出变量名 (可选)

### 可用步骤类型
| 步骤 | 描述 |
|------|------|
| `EchoInput` | 回显输入内容 |
| `SetVar` | 设置变量 |
| `GetVar` | 获取变量 |
| `FetchURL` | HTTP 请求 |
| `ParseJSON` | 解析 JSON |
| `JSONLookup` | JSON 路径查询 |
| `JSONExtractValues` | 提取 JSON 值 |
| `TemplateReplace` | 模板字符串替换 |
| `MultilineToSingleLine` | 多行转单行 |
| `OutputResult` | 输出结果 |
| `CopyVar` | 复制变量 |

### 条件控制
```json
{
  "if": { "var": "condition", "equals": true },
  "then": [/* steps */],
  "else": [/* steps */]
}
```

## Important Constraints

1. **跨平台兼容**: Electron 应用需支持 macOS、Windows
2. **本地优先**: 工作流执行在本地进行，不依赖云服务
3. **可扩展性**: 新步骤类型可以轻松添加到注册表

## External Dependencies

### 必需服务
- Python 后端服务 (默认端口: 8080)

### 可选服务
- Ollama (本地 LLM 推理)
- Docker (容器化部署)

### Live2D
- Live2D Cubism SDK Web
- 模型文件存放在 `/electron/public/live2d/`
