## RENAMED Requirements

- FROM: `### Requirement: HITL Middleware`
- TO: `### Requirement: ECS Middleware`

- FROM: `### Requirement: HITL Form Schema`
- TO: `### Requirement: ECS Form Schema`

- FROM: `### Requirement: HITL Continuation`
- TO: `### Requirement: ECS Continuation`

- FROM: `### Requirement: HITL Visual Display`
- TO: `### Requirement: ECS Visual Display`

- FROM: `### Requirement: HITL Trigger Strategy`
- TO: `### Requirement: ECS Trigger Strategy`

- FROM: `### Requirement: HITL Window`
- TO: `### Requirement: ECS Window`

## ADDED Requirements

### Requirement: ECS Naming Convention

所有代码、配置、API、IPC 通道和文档中的 "HITL" / "hitl" / "Human-in-the-Loop" 术语 SHALL 统一替换为 "ECS" / "ecs" / "Externalized Cognitive Step"。

命名映射规则：
- 类名/接口名前缀：`HITL` → `ECS`（如 `HITLRequest` → `ECSRequest`）
- 变量名/字段名前缀：`hitl_` → `ecs_`（如 `hitl_request` → `ecs_request`）
- 文件名前缀：`hitl_` → `ecs_`（如 `hitl_schema.py` → `ecs_schema.py`）
- 目录名：`hitl` → `ecs`（如 `renderer/hitl/` → `renderer/ecs/`）
- API 路由前缀：`/hitl/` → `/ecs/`
- IPC 通道前缀：`hitl:` → `ecs:`
- SSE 事件类型：`hitl` → `ecs`
- 配置键：`system.hitl_enabled` → `system.ecs_enabled`
- CSS 类前缀：`hitl-` → `ecs-`
- HTML data 属性：`data-hitl-` → `data-ecs-`
- 工作记忆 key 前缀：`hitl_` → `ecs_`
- Prompt 模板常量：`HITL_` → `ECS_`

#### Scenario: Python 后端重命名

- **WHEN** 开发者查看后端 Python 代码
- **THEN** 所有模块名、类名、函数名、变量名中不存在 "hitl"（不区分大小写）
- **AND** 所有功能行为保持不变

#### Scenario: Electron 前端重命名

- **WHEN** 开发者查看前端 TypeScript/TSX 代码
- **THEN** 所有组件名、接口名、类型名、函数名中不存在 "hitl"（不区分大小写）
- **AND** 所有 IPC 通道名使用 `ecs:` 前缀
- **AND** 所有功能行为保持不变

#### Scenario: API 路由重命名

- **WHEN** 客户端调用 ECS 相关 API
- **THEN** 所有端点路径使用 `/ecs/` 前缀（如 `/ecs/respond`、`/ecs/status/{id}`、`/ecs/continue`）
- **AND** 响应格式和行为与原 `/hitl/*` 端点完全一致

#### Scenario: 数据库配置迁移

- **WHEN** 系统启动且数据库中存在旧配置键 `system.hitl_enabled`
- **THEN** 系统自动将旧值迁移到 `system.ecs_enabled`
- **AND** 删除旧配置键
- **AND** 后续读取使用 `system.ecs_enabled`

#### Scenario: Prompt 模板更新

- **WHEN** AI 系统构建 prompt 时引用 ECS 指令
- **THEN** prompt 中使用 "Externalized Cognitive Step (ECS)" 全称描述功能语义
- **AND** LLM 生成的 ECS 请求格式和触发行为与原 HITL 一致

#### Scenario: 全局验证无遗漏

- **WHEN** 重命名完成后执行全局搜索 `grep -ri "hitl" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.cjs" --include="*.js"`
- **THEN** 除 openspec/changes/ 历史文件和构建产物外，无任何源文件包含 "hitl" 引用
