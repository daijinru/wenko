## Context

Live2D AI 对话功能已实现，但对话记录仅存于内存（sessionStorage），无法持久化。用户需要：
- 跨会话保留对话历史
- 在桌面端 Workflow UI 中查看历史记录
- 数据库文件可独立备份，在不同机器间迁移

技术约束：
- Electron 应用需跨 macOS/Windows 平台
- Python 后端使用 FastAPI
- 需保证 SQLite 文件的便携性（相对路径，无硬编码绝对路径）

## Goals / Non-Goals

**Goals:**
- SQLite 数据库存储对话记录
- 使用相对路径 `workflow/data/chat_history.db`，确保便携性
- 提供 REST API 查询、删除历史记录
- 在 Workflow UI 添加聊天记录查看界面
- 对话记录可在不同机器间迁移（复制 `data/` 目录即可）

**Non-Goals:**
- 不实现云同步
- 不实现实时推送（WebSocket）
- 不实现全文搜索（可后续增强）
- 不加密数据库（用户可自行加密备份文件）

## Decisions

### 数据库选择：SQLite
- **理由:** 零配置，单文件存储，Python 标准库支持，适合桌面应用
- **替代方案:**
  - PostgreSQL/MySQL - 需额外安装服务，过于复杂
  - JSON 文件 - 无法高效查询，数据量大时性能差

### 数据库路径：相对路径 `workflow/data/chat_history.db`
- **理由:**
  - 与应用代码同目录，便于整体备份
  - 使用相对路径，复制到新机器时无需修改配置
  - 自动创建 `data/` 目录（如不存在）
- **替代方案:**
  - 用户 Home 目录 `~/.wenko/chat_history.db` - 需处理跨平台路径差异
  - 绝对路径配置 - 不便携

### 数据库 Schema

```sql
-- 会话表
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,           -- UUID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    title TEXT                     -- 可选：会话标题（取首条消息摘要）
);

-- 消息表
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,            -- 'user' | 'assistant'
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX idx_messages_session ON messages(session_id);
CREATE INDEX idx_sessions_updated ON sessions(updated_at DESC);
```

### Session ID 管理
- 前端生成 UUID 作为 `session_id`
- 存储在 `localStorage`（相比 sessionStorage 可持久）
- 用户可点击"新建会话"清除当前 session_id
- 后端根据 session_id 关联消息

### API 设计

```
# 现有 API 扩展
POST /chat
  Request: { message, session_id?, history? }
  - 如果提供 session_id，消息自动保存到对应会话
  - 如果不提供 session_id，按原有逻辑仅返回响应不保存

# 新增 API
GET /chat/history
  Response: { sessions: [{ id, title, created_at, updated_at, message_count }], count }
  - 返回所有会话列表，按 updated_at 降序

GET /chat/history/{session_id}
  Response: { session: { id, title, ... }, messages: [{ role, content, created_at }] }
  - 返回特定会话的所有消息

DELETE /chat/history/{session_id}
  Response: { success: true }
  - 删除会话及其所有消息

DELETE /chat/history
  Response: { success: true, deleted_count }
  - 清空所有聊天记录
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| SQLite 并发写入冲突 | 单用户桌面应用，冲突概率极低；使用 WAL 模式提高并发性能 |
| 数据库文件损坏 | 用户自行备份 `data/` 目录；应用启动时检查数据库完整性 |
| 数据量过大影响性能 | 分页查询；可后续添加自动清理老旧记录功能 |

## Migration Plan

1. 新建 `workflow/chat_db.py` 数据库模块
2. 应用启动时自动创建 `data/` 目录和数据库表
3. 扩展 `/chat` API，支持 session_id 参数
4. 添加历史记录 API
5. 修改前端 `chat.ts`，使用 localStorage 存储 session_id
6. 在 Workflow UI 添加聊天记录 Tab

回滚方案：
- 删除 API 扩展和数据库模块
- 前端恢复使用 sessionStorage
- 数据库文件可保留或删除

## Open Questions

1. 是否需要限制历史记录保留数量？（如仅保留最近 100 条会话）
   - 当前决定：不限制，由用户手动管理
2. 是否需要导出功能（如导出为 JSON/Markdown）？
   - 当前决定：不在本次变更范围，可后续增强
