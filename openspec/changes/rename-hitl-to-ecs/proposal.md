# Change: Rename HITL to ECS (Externalized Cognitive Step)

## Why

当前系统使用 "HITL" (Human-in-the-Loop) 命名一整套人机交互机制。但 HITL 是一个泛化的工业术语，不能精确描述我们的系统行为——我们的机制并非简单的"人类参与回路"，而是：**在智能体执行图中，将一个无法在系统内部完成的认知步骤，显式外包给外部实体完成，并将其结果重新注入推理流程**。

"Externalized Cognitive Step (ECS)" 更准确地传达了这一语义：
- **Externalized**：认知步骤被显式地外部化
- **Cognitive**：这是一个认知步骤，而非简单的数据采集
- **Step**：它是执行图中的一个离散步骤，有明确的输入和输出

这个重命名将提升代码可读性、领域建模精确性，以及与项目架构设计理念的一致性。

## What Changes

### 命名映射规则

| 旧名称 | 新名称 | 说明 |
|--------|--------|------|
| `HITL` / `hitl` | `ECS` / `ecs` | 核心缩写 |
| `HITLRequest` | `ECSRequest` | 所有类名/接口名中的 HITL 前缀 |
| `hitl_request` | `ecs_request` | 所有变量名/字段名中的 hitl 前缀 |
| `hitl:open-window` | `ecs:open-window` | IPC 通道名 |
| `/hitl/respond` | `/ecs/respond` | API 路由 |
| `system.hitl_enabled` | `system.ecs_enabled` | 配置键 |
| `event: hitl` | `event: ecs` | SSE 事件名 |
| `@hitl/` | `@ecs/` | Vite 路径别名 |
| `hitl-` CSS 类 | `ecs-` CSS 类 | CSS class 前缀 |
| `data-hitl-id` | `data-ecs-id` | HTML data 属性 |
| `hitl_` 内存前缀 | `ecs_` 内存前缀 | 工作记忆 key 前缀 |
| `HITL_INSTRUCTION` | `ECS_INSTRUCTION` | Prompt 模板常量名 |
| `HITLNode` | `ECSNode` | LangGraph 节点名 |
| `HITLIntent` | `ECSIntent` | 意图分类枚举 |
| `hitl_handler.py` | `ecs_handler.py` | 文件名 |
| `hitl_schema.py` | `ecs_schema.py` | 文件名 |
| `renderer/hitl/` | `renderer/ecs/` | 目录名 |

### **BREAKING** 变更

- API 路由从 `/hitl/*` 变更为 `/ecs/*`
- IPC 通道名全部从 `hitl:*` 变更为 `ecs:*`
- SSE 事件类型从 `hitl` 变更为 `ecs`
- 配置键 `system.hitl_enabled` 变更为 `system.ecs_enabled`
- LangGraph 状态字段 `hitl_request` / `hitl_full_request` 变更为 `ecs_request` / `ecs_full_request`
- 工作记忆中 `hitl_` 前缀的 context variable 变更为 `ecs_` 前缀

### 不变更的内容

- openspec/changes/ 下已有的 HITL 提案文件名和目录名（保留历史记录）
- 构建产物（dist/、build/、__pycache__/）——重新构建即可
- git 历史中的提交消息

## Impact

- Affected specs: 无现有 spec 文件涉及 HITL（均未归档到 specs/ 目录）
- Affected code:
  - **Python 后端**: 11 个源文件，2 个核心模块文件重命名
  - **Electron 前端**: 16 个 TypeScript/TSX 源文件，1 个目录重命名
  - **Electron 主进程**: `main.cjs` 大量 IPC 相关代码
  - **Live2D 组件**: `chat.ts` 约 50+ 处引用
  - **配置文件**: `vite.config.js`、`tsconfig.json`
  - **文档**: `README.md`、`README_CN.md`、`work_state_summary.md`
  - **数据库**: `chat_db.py` 默认配置项
