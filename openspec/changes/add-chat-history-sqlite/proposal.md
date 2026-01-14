# Change: 为 Live2D AI 对话添加 SQLite 持久化存储

## Why

当前 Live2D AI 对话的历史记录仅存储在浏览器的 `sessionStorage` 中，关闭窗口后即丢失。用户希望：
1. 持久化保存对话记录，跨会话查看历史
2. 在 Workflow 界面中查看和管理聊天记录
3. SQLite 数据库文件可独立备份，在不同机器上迁移使用

## What Changes

- **Python 后端 (`workflow/`):**
  - 新增 SQLite 数据库模块，使用相对路径存储 `data/chat_history.db`
  - 扩展 `/chat` API，在对话完成时自动保存消息到数据库
  - 新增聊天记录 CRUD API 接口：
    - `GET /chat/history` - 获取聊天会话列表
    - `GET /chat/history/{session_id}` - 获取特定会话的消息
    - `DELETE /chat/history/{session_id}` - 删除特定会话
  - 数据库使用相对路径，确保便携性

- **前端 Live2D Widget (`electron/live2d/live2d-widget/src/`):**
  - 修改 `chat.ts`，移除 `sessionStorage` 依赖
  - 每次对话生成唯一 `session_id`，传递给后端
  - 支持从后端加载历史记录恢复对话上下文

- **Workflow UI (`electron/src/renderer/workflow/`):**
  - 新增"聊天记录"标签页
  - 展示会话列表（按时间排序）
  - 查看会话详情（消息时间线）
  - 支持删除会话

## Impact

- Affected specs: `electron-app`（新增聊天记录查看能力）
- Affected code:
  - `workflow/main.py` - Chat API 扩展
  - `workflow/chat_db.py` - 新增 SQLite 数据库模块
  - `workflow/data/` - SQLite 数据库存储目录（需创建）
  - `electron/live2d/live2d-widget/src/chat.ts` - 前端对话模块改造
  - `electron/src/renderer/workflow/App.jsx` - 新增聊天记录 Tab
- Database: `workflow/data/chat_history.db`（相对路径，便于备份迁移）
