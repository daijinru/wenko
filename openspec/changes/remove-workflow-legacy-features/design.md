# Design: Remove Workflow Legacy Features

## Overview

本变更将项目从「工作流编排系统」转型为「情感记忆 AI 系统」，移除所有工作流相关功能，只保留聊天、情感检测和记忆管理核心模块。

## Architecture After Change

```
┌─────────────────────────────────────────────────────────────┐
│                    Electron App                              │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Live2D Chat │  │ Chat History│  │   Memory Manager    │  │
│  │   Widget    │  │     Tab     │  │       Tab           │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
└─────────┼────────────────┼────────────────────┼─────────────┘
          │                │                    │
          ▼                ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  /chat   │  │/chat/history │  │      /memory/*         │ │
│  └────┬─────┘  └──────┬───────┘  └───────────┬────────────┘ │
│       │               │                      │              │
│  ┌────▼────────────────▼──────────────────────▼───────────┐ │
│  │                  Core Modules                          │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌───────────────────┐ │ │
│  │  │   chat_     │ │  emotion_   │ │  response_        │ │ │
│  │  │  processor  │ │  detector   │ │   strategy        │ │ │
│  │  └──────┬──────┘ └──────┬──────┘ └────────┬──────────┘ │ │
│  │         │               │                 │            │ │
│  │  ┌──────▼───────────────▼─────────────────▼──────────┐ │ │
│  │  │              memory_manager                       │ │ │
│  │  └───────────────────────┬───────────────────────────┘ │ │
│  └──────────────────────────┼─────────────────────────────┘ │
│                             │                               │
│  ┌──────────────────────────▼─────────────────────────────┐ │
│  │                     chat_db                            │ │
│  │        (SQLite: sessions, messages, memory)            │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Files to Remove

### workflow/ 目录

| 文件 | 原用途 | 移除原因 |
|-----|-------|---------|
| `graph.py` | LangGraph 工作流图定义 | 不再需要工作流引擎 |
| `executor.py` | 工作流执行器 | 不再需要工作流执行 |
| `steps.py` | 步骤类型定义 (EchoInput, SetVar, etc.) | 不再需要步骤系统 |
| `control_steps.py` | 条件控制步骤 | 不再需要条件分支 |
| `app.py` | LangGraph API 入口 | 被 main.py 替代 |
| `example.py` | 工作流示例代码 | 不再相关 |
| `test_workflow.py` | 工作流测试 | 测试目标已移除 |
| `templates_api_examples.md` | 模板 API 文档 | API 将被移除 |

## Files to Keep

### workflow/ 目录

| 文件 | 用途 |
|-----|------|
| `main.py` | FastAPI 主应用（精简后） |
| `chat_db.py` | SQLite 数据库管理 |
| `chat_processor.py` | 聊天处理与 LLM 集成 |
| `emotion_detector.py` | 情绪检测解析 |
| `response_strategy.py` | 响应策略选择 |
| `memory_manager.py` | 记忆管理系统 |
| `chat_config.json` | LLM API 配置 |
| `chat_config.example.json` | 配置示例 |

## API Endpoints After Change

### 保留的端点

```
GET  /health                         # 健康检查
POST /chat                           # 聊天 (SSE)
GET  /chat/history                   # 会话列表
GET  /chat/history/{session_id}      # 会话详情
DELETE /chat/history/{session_id}    # 删除会话
DELETE /chat/history                 # 清空所有会话

GET  /memory/long-term               # 记忆列表
GET  /memory/long-term/{id}          # 记忆详情
POST /memory/long-term               # 创建记忆
PUT  /memory/long-term/{id}          # 更新记忆
DELETE /memory/long-term/{id}        # 删除记忆
DELETE /memory/long-term             # 清空记忆
POST /memory/long-term/batch-delete  # 批量删除
GET  /memory/long-term/export        # 导出记忆
POST /memory/long-term/import        # 导入记忆
GET  /memory/working/{session_id}    # 工作记忆
```

### 移除的端点

```
GET  /steps                          # 步骤注册表
POST /run                            # 执行工作流
POST /templates                      # 创建模板
GET  /templates                      # 模板列表
GET  /templates/{id}                 # 模板详情
PUT  /templates/{id}                 # 更新模板
DELETE /templates/{id}               # 删除模板
GET  /templates/search/{query}       # 搜索模板
POST /templates/{id}/execute         # 执行模板
```

## Frontend Changes

### App.jsx 变更

**移除:**
- 工作流执行 Tab 及相关状态/函数
- 模板管理 Tab 及相关状态/函数
- 步骤注册表 Tab 及相关状态/函数
- 健康检查 Tab（保留 API 调用，移除 UI）
- 模板编辑 Modal

**保留:**
- 聊天记录 Tab
- 记忆管理 Tab
- 记忆编辑 Modal
- 服务状态指示器（简化）

### 默认 Tab 变更

```javascript
// Before
const [activeTab, setActiveTab] = useState('workflow');

// After
const [activeTab, setActiveTab] = useState('chatHistory');
```

## Database Compatibility

数据库 schema 保持不变，确保：
- 现有聊天记录数据可继续使用
- 现有记忆数据可继续使用
- 无需数据迁移

## Dependencies Cleanup

### pyproject.toml

评估是否移除:
- `langgraph` 依赖（如果不再需要）

### package.json

无需变更，Electron/React 依赖保持不变。

## Migration Path

1. **Phase 1**: 移除前端 UI 组件
2. **Phase 2**: 移除后端 API 端点和模型
3. **Phase 3**: 删除不再需要的文件
4. **Phase 4**: 更新文档
5. **Phase 5**: 验证功能完整性
