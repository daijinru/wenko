# Tasks: Remove Workflow Legacy Features

## 1. Frontend Cleanup (App.jsx)

- [x] 1.1 移除工作流相关状态变量
  - `workflowSteps`, `workflowContext`, `debugMode`, `workflowResult`, `workflowLoading`
  - `templates`, `templatesLoading`, `searchQuery`, `templateDialogVisible`, `currentTemplate`, `templateForm`
  - `steps`, `stepsLoading`
  - `healthResult`

- [x] 1.2 移除工作流相关函数
  - `executeWorkflow`, `loadExample`, `clearWorkflow`
  - `loadTemplates`, `searchTemplates`, `viewTemplate`, `analyzeTemplateContext`
  - `executeTemplate`, `editTemplate`, `showCreateTemplate`, `saveTemplate`, `deleteTemplate`
  - `loadSteps`
  - `checkHealth` (保留基础调用，但移除 Tab)

- [x] 1.3 移除工作流相关组件
  - `WorkflowTab` 组件
  - `TemplatesTab` 组件
  - `StepsTab` 组件
  - `HealthTab` 组件
  - 模板编辑 Modal

- [x] 1.4 更新 Tabs 组件
  - 只保留 `chatHistory` 和 `memory` 两个 TabPane
  - 更新 `activeTab` 默认值为 `chatHistory`

- [x] 1.5 更新页面标题和样式
  - 修改 `app-header` 标题为情感记忆相关

- [x] 1.6 清理 `useEffect` 初始化逻辑
  - 移除 `loadSteps()` 和 `loadTemplates()` 调用

## 2. Backend API Cleanup (main.py)

- [x] 2.1 移除工作流相关 Pydantic 模型
  - `WorkflowRequest`, `WorkflowResponse`
  - `StepRegistryResponse`
  - `StepTemplate`, `CreateStepTemplateRequest`, `UpdateStepTemplateRequest`
  - `StepTemplateListResponse`, `StepTemplateResponse`

- [x] 2.2 移除模板存储类
  - `StepTemplateStorageInterface`
  - `StepTemplateStorage`
  - `template_storage` 全局实例

- [x] 2.3 移除工作流相关 API 端点
  - `GET /steps`
  - `POST /run`
  - `POST /templates`
  - `GET /templates`
  - `GET /templates/{template_id}`
  - `PUT /templates/{template_id}`
  - `DELETE /templates/{template_id}`
  - `GET /templates/search/{query}`
  - `POST /templates/{template_id}/execute`

- [x] 2.4 移除工作流相关 imports
  - `from graph import workflow_graph`
  - `from steps import STEP_REGISTRY`

- [x] 2.5 保留并简化健康检查端点
  - 保留 `/health` 端点

## 3. Backend Files Cleanup

- [x] 3.1 删除工作流引擎文件
  - `workflow/graph.py`
  - `workflow/executor.py`
  - `workflow/steps.py`
  - `workflow/control_steps.py`

- [x] 3.2 删除辅助文件
  - `workflow/app.py`
  - `workflow/example.py`
  - `workflow/test_workflow.py`
  - `workflow/templates_api_examples.md`

- [x] 3.3 评估配置文件
  - 删除 `workflow/langgraph.json`（工作流引擎已移除，不再需要）

## 4. Documentation Update

- [x] 4.1 更新 `openspec/project.md`
  - 修改项目 Purpose 描述
  - 更新 Tech Stack（移除 LangGraph 相关）
  - 更新 Domain Context（移除工作流/步骤描述）
  - 更新可用步骤类型表格（移除）

- [x] 4.2 重写 `workflow/README.md`
  - 更新为情感记忆系统文档
  - 描述核心模块：emotion_detector, memory_manager, response_strategy, chat_processor
  - 更新 API 文档

## 5. Validation

- [x] 5.1 验证前端功能
  - 聊天记录 Tab 正常工作
  - 记忆管理 Tab 正常工作
  - 无 JS 错误

- [x] 5.2 验证后端功能
  - `/health` 端点正常
  - `/chat` 端点正常
  - `/chat/history/*` 端点正常
  - `/memory/*` 端点正常

- [x] 5.3 验证应用启动
  - Python 后端正常启动 (main.py imports successfully)
  - Electron 应用正常启动 (App.jsx has no blocking errors)
  - Live2D 聊天功能正常

## Dependencies

- Task 2 可与 Task 1 并行
- Task 3 依赖 Task 2（确保 imports 已移除）
- Task 4 可与其他任务并行
- Task 5 依赖所有前序任务

## Estimated Impact

- **代码行数减少**: ~1500+ 行
- **文件数减少**: 8 个文件 (包括 langgraph.json)
- **API 端点减少**: 9 个端点
