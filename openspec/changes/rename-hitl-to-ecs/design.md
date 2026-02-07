## Context

HITL (Human-in-the-Loop) 是 Wenko 系统中一个核心子系统，负责在 AI 推理过程中将特定认知步骤外包给用户完成。该子系统经过 6 个迭代演进（从基础中间件到多轮交互、架构迁移、触发率优化、响应质量提升、可视化展示），已成为系统中最复杂的跨层模块之一。

重命名涉及：
- **后端层**: Python 模块（FastAPI、LangGraph、Pydantic 模型）
- **前端层**: React 组件（Electron 渲染进程）
- **桥接层**: Electron 主进程 IPC 通信
- **集成层**: Live2D Widget 内嵌 HITL 表单
- **配置层**: 数据库配置项、构建工具配置
- **协议层**: API 路由、SSE 事件、IPC 通道

## Goals / Non-Goals

### Goals
- 将所有 HITL 命名统一替换为 ECS，确保零遗留
- 保持所有功能行为完全不变
- 保持代码可编译、可运行
- 保持 openspec 历史变更记录的可追溯性

### Non-Goals
- 不重构任何业务逻辑
- 不改变 API 行为（仅变路由路径）
- 不变更数据库 schema（仅变配置值）
- 不修改 openspec 历史提案文件名/目录名
- 不处理已有用户数据库中的旧配置值迁移（如果有用户已配置 `system.hitl_enabled`，需要手动或通过数据库迁移脚本处理，但本提案不覆盖自动迁移）

## Decisions

### Decision 1: 全量一次性重命名 vs 渐进式重命名

**选择: 全量一次性重命名**

理由:
- 系统尚处于开发阶段，无外部消费者依赖旧 API
- 保留双重命名（兼容层）会增加长期维护负担
- 一次性完成可避免中间状态的混淆

### Decision 2: 文件名重命名策略

**选择: 先创建新文件，再删除旧文件（而非 git mv）**

理由:
- `git mv` 等效于 delete + add，git 会通过相似度自动检测重命名
- 对于同时修改内容和路径的情况，直接创建新文件更清晰
- 但对于纯目录移动（如 `renderer/hitl/` → `renderer/ecs/`），使用 `git mv` 保留历史追踪

### Decision 3: 已有数据库配置兼容

**选择: 修改默认配置键名 + 添加迁移逻辑**

理由:
- `chat_db.py` 中的默认配置会在初始化时插入
- 对于已存在 `system.hitl_enabled` 配置的数据库，需要一个简单的迁移：读取旧值 → 写入新键 → 删除旧键
- 在 `chat_db.py` 的初始化逻辑中添加一次性迁移

### Decision 4: Prompt 模板中的 HITL 一词

**选择: 全部替换为 ECS 及其全称描述**

理由:
- Prompt 模板中的 HITL 一词面向 LLM，LLM 需要理解 ECS 的含义
- 在 prompt 中首次使用时提供全称 "Externalized Cognitive Step (ECS)"，后续使用缩写
- LLM 本身不依赖特定缩写，只需理解语义即可

### Decision 5: openspec 历史变更目录

**选择: 不重命名历史变更目录**

理由:
- `openspec/changes/add-hitl-middleware/` 等目录名是历史记录的一部分
- 重命名这些目录会破坏 `openspec list` 的历史追溯能力
- 内容中的 HITL 引用保留为历史快照

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 遗漏某处 HITL 引用导致运行时错误 | 实施后执行全局 grep 验证 + 编译检查 + 运行时测试 |
| Live2D chat.ts 高度耦合，改动量大 | 分步骤处理：先改类型/接口定义，再改函数，最后改 HTML/CSS |
| SSE 事件名变更导致前后端不匹配 | 前后端在同一个 task 中同步修改 |
| 已有数据库配置不兼容 | 添加一次性迁移逻辑 |

## Migration Plan

### 执行顺序

```
Phase 1: 后端核心（无外部依赖）
  ├── 1.1 重命名 hitl_schema.py → ecs_schema.py（修改所有类名）
  ├── 1.2 重命名 hitl_handler.py → ecs_handler.py（修改所有函数名/变量名）
  ├── 1.3 更新 core/state.py（状态字段名）
  ├── 1.4 更新 core/nodes/hitl.py → core/nodes/ecs.py
  └── 1.5 更新所有后端导入和引用

Phase 2: 后端 API 层
  ├── 2.1 更新 main.py API 路由和模型
  ├── 2.2 更新 SSE 事件类型
  └── 2.3 更新数据库配置项和迁移逻辑

Phase 3: Electron 主进程
  └── 3.1 更新 main.cjs 中所有 IPC 通道和变量名

Phase 4: 前端渲染器
  ├── 4.1 重命名 renderer/hitl/ → renderer/ecs/ 目录
  ├── 4.2 更新所有组件和类型文件中的命名
  ├── 4.3 更新 Vite 和 TypeScript 配置
  └── 4.4 更新 Workflow 渲染器中的引用

Phase 5: Live2D Widget
  └── 5.1 更新 chat.ts 中所有引用

Phase 6: Prompt 模板和意图系统
  ├── 6.1 更新 chat_processor.py 中的常量和模板
  ├── 6.2 更新 intent_types.py 和 intent_rules.py
  └── 6.3 更新 core/prompts.py 模板变量

Phase 7: 文档和验证
  ├── 7.1 更新 README.md 和 README_CN.md
  ├── 7.2 更新 work_state_summary.md
  ├── 7.3 全局 grep 验证无遗漏
  └── 7.4 编译和运行验证
```

### Rollback

由于这是纯重命名操作，回滚策略为 `git revert`。

## Open Questions

- 无（需求明确，范围已界定）
