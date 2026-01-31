## 1. 后端基础设施

- [x] 1.1 创建 `workflow/mcp_manager.py` 模块
  - [x] 1.1.1 定义 `MCPServerConfig` Pydantic 模型
  - [x] 1.1.2 实现 `MCPServerRegistry` 类 (服务配置管理)
  - [x] 1.1.3 实现 `MCPProcessManager` 类 (进程生命周期管理)

- [x] 1.2 扩展数据库支持
  - [x] 1.2.1 在 `chat_db.py` 的 `_DEFAULT_SETTINGS` 添加 `mcp.servers` 默认值
  - [x] 1.2.2 添加 MCP 服务配置的读写辅助函数

## 2. 后端 API 实现

- [x] 2.1 在 `main.py` 添加 MCP API 路由
  - [x] 2.1.1 `GET /api/mcp/servers` - 获取服务列表及状态
  - [x] 2.1.2 `POST /api/mcp/servers` - 注册新服务
  - [x] 2.1.3 `GET /api/mcp/servers/{id}` - 获取单个服务详情
  - [x] 2.1.4 `PUT /api/mcp/servers/{id}` - 更新服务配置
  - [x] 2.1.5 `DELETE /api/mcp/servers/{id}` - 删除服务

- [x] 2.2 服务控制 API
  - [x] 2.2.1 `POST /api/mcp/servers/{id}/start` - 启动服务
  - [x] 2.2.2 `POST /api/mcp/servers/{id}/stop` - 停止服务
  - [x] 2.2.3 `POST /api/mcp/servers/{id}/restart` - 重启服务

- [x] 2.3 应用生命周期管理
  - [x] 2.3.1 在 FastAPI `on_startup` 事件初始化 MCP Manager
  - [x] 2.3.2 在 FastAPI `on_shutdown` 事件清理所有运行中的服务进程

## 3. 前端状态管理

- [x] 3.1 创建 `hooks/use-mcp-services.ts`
  - [x] 3.1.1 定义 MCP 服务类型接口
  - [x] 3.1.2 实现服务列表加载函数
  - [x] 3.1.3 实现服务操作函数 (注册/更新/删除/启动/停止)
  - [x] 3.1.4 实现状态轮询逻辑 (5秒间隔)

- [x] 3.2 更新 API 类型定义
  - [x] 3.2.1 在 `types/api.ts` 添加 MCP 相关类型

## 4. 前端 UI 组件

- [x] 4.1 创建 MCP 组件目录 `components/features/mcp/`

- [x] 4.2 实现服务列表组件
  - [x] 4.2.1 `mcp-tab.tsx` - MCP 管理主界面
  - [x] 4.2.2 `mcp-service-card.tsx` - 单个服务卡片组件

- [x] 4.3 实现服务操作组件
  - [x] 4.3.1 `mcp-register-dialog.tsx` - 服务注册对话框
  - [x] 4.3.2 `mcp-edit-dialog.tsx` - 服务编辑对话框 (合并到 mcp-register-dialog.tsx)
  - [x] 4.3.3 `mcp-delete-confirm.tsx` - 删除确认对话框 (使用通用 ConfirmDialog)

- [x] 4.4 集成到主应用
  - [x] 4.4.1 修改 `App.tsx` 添加 MCP 标签页

## 5. 测试与验证

- [x] 5.1 后端 API 测试
  - [x] 5.1.1 验证 Python 语法正确
  - [ ] 5.1.2 验证服务启动/停止 API (需手动测试)
  - [ ] 5.1.3 验证服务删除 API (需手动测试)
  - [ ] 5.1.4 验证应用关闭时进程清理 (需手动测试)

- [x] 5.2 前端功能测试
  - [x] 5.2.1 验证 TypeScript 编译通过
  - [ ] 5.2.2 验证服务注册流程 (需手动测试)
  - [ ] 5.2.3 验证服务启动/停止操作 (需手动测试)
  - [ ] 5.2.4 验证状态实时更新 (需手动测试)

- [ ] 5.3 跨平台测试
  - [ ] 5.3.1 macOS 环境验证
  - [ ] 5.3.2 Windows 环境验证（如适用）

## 6. 文档更新

- [ ] 6.1 更新 `openspec/project.md` 添加 MCP 模块说明
- [ ] 6.2 更新 API 文档（如有）

## Dependencies

- 任务 2.* 依赖 1.* 完成 ✓
- 任务 4.* 依赖 3.* 完成 ✓
- 任务 5.* 依赖 2.* 和 4.* 完成 ✓
- 任务 6.* 可并行进行

## Parallelizable Work

以下任务可以并行执行：
- 1.1 (后端模块) 和 3.1 (前端 Hook) 可并行开发 ✓
- 4.2 和 4.3 的各个组件可并行开发 ✓
- 5.3.1 和 5.3.2 可并行测试

## Implementation Summary

### 已创建/修改的文件

**后端 (workflow/)**:
- `mcp_manager.py` - MCP 服务管理核心模块 (新建)
- `chat_db.py` - 添加 `mcp.servers` 默认设置
- `main.py` - 添加 MCP API 路由和生命周期管理

**前端 (electron/src/renderer/workflow/)**:
- `types/api.ts` - 添加 MCP 相关类型定义
- `hooks/use-mcp-services.ts` - MCP 服务状态管理 Hook (新建)
- `components/features/mcp/mcp-tab.tsx` - MCP 管理主界面 (新建)
- `components/features/mcp/mcp-service-card.tsx` - 服务卡片组件 (新建)
- `components/features/mcp/mcp-register-dialog.tsx` - 注册/编辑对话框 (新建)
- `components/features/mcp/index.ts` - 组件导出 (新建)
- `App.tsx` - 添加 MCP 服务标签页
