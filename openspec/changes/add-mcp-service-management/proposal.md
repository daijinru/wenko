# Change: 添加 MCP 服务管理模块

## Why

当前系统需要扩展功能以支持 MCP (Model Context Protocol) 服务的集成。MCP 是一个开放协议，允许 AI 应用与外部工具和数据源进行交互。添加 MCP 服务管理功能将：

1. 允许用户注册和配置多个 MCP 服务器
2. 提供统一的服务生命周期管理（启动/停止/删除）
3. 在 Workflow 控制面板中提供可视化的服务管理界面
4. 为未来的工具调用和数据集成提供基础设施

## What Changes

### 后端 (workflow/)
- **新增** `mcp_manager.py` - MCP 服务管理核心模块
  - 服务注册、配置存储
  - 服务进程生命周期管理（启动/停止）
  - 服务健康检查和状态监控
- **新增** `/api/mcp/*` API 路由组 - 提供 RESTful 接口
- **修改** `chat_db.py` - 添加 MCP 服务配置的数据库存储

### 前端 (electron/src/renderer/workflow/)
- **新增** `hooks/use-mcp-services.ts` - MCP 服务状态管理 Hook
- **新增** `components/features/mcp/` - MCP 管理 UI 组件
  - `mcp-tab.tsx` - MCP 服务列表和管理主界面
  - `mcp-service-card.tsx` - 单个服务状态卡片
  - `mcp-register-dialog.tsx` - 服务注册对话框
- **修改** `App.tsx` - 添加 MCP 标签页

## Impact

- **Affected specs**:
  - `workflow-engine` (新增 MCP 集成能力)
  - 新增 `mcp-service-management` capability
- **Affected code**:
  - `workflow/main.py` - 添加 API 路由
  - `workflow/chat_db.py` - 数据库 schema 扩展
  - `electron/src/renderer/workflow/App.tsx` - UI 入口
- **Breaking changes**: 无
- **Dependencies**:
  - Python: `mcp` SDK (官方 Python SDK)
  - 可选: `subprocess` 用于进程管理
