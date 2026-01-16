# Proposal: Remove Workflow Legacy Features

## Summary

移除 workflow 面板中除聊天记录和记忆管理以外的所有功能，以及对应的后端服务逻辑。项目将专注于情感和记忆系统的开发。

## Motivation

当前项目包含大量工作流编排功能（工作流执行、模板管理、步骤注册表等），但项目方向已明确转向情感和记忆系统。保留这些冗余功能会：

1. 增加代码维护负担
2. 混淆项目核心定位
3. 占用不必要的 bundle 体积

## Scope

### 需要移除的前端功能 (App.jsx)

| Tab 名称 | 状态 |
|---------|------|
| 工作流执行 (workflow) | 移除 |
| 模板管理 (templates) | 移除 |
| 步骤注册表 (steps) | 移除 |
| 健康检查 (health) | 移除 |
| 聊天记录 (chatHistory) | **保留** |
| 记忆管理 (memory) | **保留** |

### 需要移除的后端 API (main.py)

| API 端点 | 状态 |
|---------|------|
| `/run` | 移除 |
| `/steps` | 移除 |
| `/templates/*` (全部) | 移除 |
| `/health` | **保留** (基础健康检查) |
| `/chat` | **保留** |
| `/chat/history/*` | **保留** |
| `/memory/*` | **保留** |

### 需要移除的后端文件

| 文件 | 状态 |
|-----|------|
| `workflow/graph.py` | 移除 |
| `workflow/executor.py` | 移除 |
| `workflow/steps.py` | 移除 |
| `workflow/control_steps.py` | 移除 |
| `workflow/app.py` | 移除 |
| `workflow/example.py` | 移除 |
| `workflow/test_workflow.py` | 移除 |
| `workflow/templates_api_examples.md` | 移除 |
| `workflow/chat_db.py` | **保留** |
| `workflow/chat_processor.py` | **保留** |
| `workflow/emotion_detector.py` | **保留** |
| `workflow/response_strategy.py` | **保留** |
| `workflow/memory_manager.py` | **保留** |
| `workflow/main.py` | **保留** (精简后) |

### 需要更新的文档

| 文件 | 变更 |
|-----|------|
| `openspec/project.md` | 更新项目定位和技术栈描述 |
| `workflow/README.md` | 重写为情感记忆系统文档 |

## Non-Goals

- 不修改 Live2D 聊天功能
- 不修改情感/记忆系统核心逻辑
- 不修改数据库 schema（保持向后兼容）

## Dependencies

- 无前置依赖

## Risks

1. **数据兼容性**: 现有数据库可能包含 workflow 相关表，需确保迁移兼容
2. **配置文件**: `langgraph.json` 等配置文件需要评估是否保留

## Success Criteria

1. 前端面板只保留聊天记录和记忆管理两个 Tab
2. 后端只保留 `/health`、`/chat/*`、`/memory/*` 相关 API
3. 项目文档更新为情感记忆系统定位
4. 应用正常启动，核心功能正常工作
