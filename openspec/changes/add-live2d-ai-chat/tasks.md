# Implementation Tasks

## 1. Configuration Setup

- [x] 1.1 创建 `workflow/chat_config.example.json` 示例配置文件
- [x] 1.2 在 `.gitignore` 中添加 `workflow/chat_config.json` 忽略规则
- [x] 1.3 实现配置文件加载和验证逻辑

## 2. Backend: Chat API

- [x] 2.1 在 `workflow/main.py` 添加 `/chat` SSE 端点
- [x] 2.2 实现 OpenAI 兼容客户端（使用 httpx 调用远程 API）
- [x] 2.3 实现流式响应处理，将 LLM 响应转换为 SSE 事件
- [x] 2.4 添加错误处理（配置缺失、API 连接失败、认证错误等）
- [x] 2.5 添加请求模型定义（ChatRequest, ChatMessage, ChatConfig）

## 3. Frontend: Chat Input Component

- [x] 3.1 在 `electron/live2d/live2d-widget/src/` 创建 `chat.ts` 模块
- [x] 3.2 实现 ChatInput 组件（输入框 + 发送按钮）
- [x] 3.3 添加 CSS 样式到 `waifu.css`
- [x] 3.4 在 `widget.ts` 中集成 ChatInput 组件
- [x] 3.5 实现 Enter 键发送和按钮点击发送

## 4. Frontend: Chat API Integration

- [x] 4.1 在 `chat.ts` 添加 `sendChatMessage` 函数
- [x] 4.2 使用 `fetchEventSource` 处理 SSE 流式响应
- [x] 4.3 实现加载状态管理（禁用输入、显示加载动画）
- [x] 4.4 实现错误处理和用户提示

## 5. Frontend: Conversation History

- [x] 5.1 实现 `ChatHistoryManager` 类管理对话历史
- [x] 5.2 使用 sessionStorage 存储历史
- [x] 5.3 实现历史长度限制（最多 10 轮）
- [x] 5.4 在发送请求时附带历史上下文

## 6. Build and Integration

- [x] 6.1 更新 `rollup.config.js` 包含新模块（无需修改，自动包含）
- [x] 6.2 运行构建验证无错误
- [ ] 6.3 在 Electron 应用中测试完整对话流程（待手动验证）

## 7. Documentation

- [x] 7.1 更新 `openspec/project.md` 的 External Dependencies 说明远程 API 配置
- [x] 7.2 在 `workflow/README.md` 添加 Chat API 使用说明和配置指南

## Dependencies

- Task 1 无依赖，可首先开始
- Task 2 依赖 Task 1（需要配置文件结构）
- Task 3 依赖 Task 2（需要后端 API 可用）
- Task 4 依赖 Task 2 和 Task 3
- Task 5 依赖 Task 4
- Task 6 依赖所有前置任务
