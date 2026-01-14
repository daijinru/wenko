## 1. 数据库模块实现

- [x] 1.1 创建 `workflow/chat_db.py` SQLite 数据库模块
- [x] 1.2 实现数据库初始化函数（自动创建 `data/` 目录和表结构）
- [x] 1.3 实现 Session CRUD 操作（create_session, get_session, list_sessions, delete_session）
- [x] 1.4 实现 Message CRUD 操作（add_message, get_messages_by_session）
- [x] 1.5 使用 WAL 模式优化并发性能

## 2. 后端 API 扩展

- [x] 2.1 在 `workflow/main.py` 导入 chat_db 模块，应用启动时初始化数据库
- [x] 2.2 扩展 `POST /chat` API，支持 session_id 参数，自动保存消息
- [x] 2.3 实现 `GET /chat/history` API（获取会话列表）
- [x] 2.4 实现 `GET /chat/history/{session_id}` API（获取会话消息）
- [x] 2.5 实现 `DELETE /chat/history/{session_id}` API（删除单个会话）
- [x] 2.6 实现 `DELETE /chat/history` API（清空所有记录）

## 3. 前端 Live2D Chat 模块改造

- [x] 3.1 修改 `electron/live2d/live2d-widget/src/chat.ts`
- [x] 3.2 使用 `localStorage` 替代 `sessionStorage` 存储 session_id
- [x] 3.3 发送消息时携带 session_id 参数
- [x] 3.4 添加"新建会话"功能（生成新 session_id）
- [x] 3.5 重新构建 live2d-widget（运行 build）

## 4. Workflow UI 聊天记录界面

- [x] 4.1 在 `electron/src/renderer/workflow/App.jsx` 添加"聊天记录"Tab
- [x] 4.2 实现会话列表组件（显示会话标题、时间、消息数）
- [x] 4.3 实现会话详情组件（消息时间线展示）
- [x] 4.4 实现删除会话功能（带确认弹窗）
- [x] 4.5 实现清空所有记录功能

## 5. 测试与验证

- [ ] 5.1 验证数据库文件创建在正确位置 (`workflow/data/chat_history.db`)
- [ ] 5.2 验证对话记录正确保存和读取
- [ ] 5.3 验证 Workflow UI 正确显示聊天记录
- [ ] 5.4 验证删除功能正常工作
- [ ] 5.5 验证复制 `data/` 目录到新位置后数据库可正常使用（便携性测试）
