# Design: Add Plan Reminder Feature

## Context

Wenko 是一个情感记忆 AI 系统，当前支持三种长期记忆类型：preference、fact、pattern。用户希望能够在对话中设置时间相关的提醒，系统在指定时间通过 Live2D 主动通知用户。

**约束条件：**
- 必须复用现有的 HITL 机制收集计划详情
- 必须使用 Electron 进程进行轮询（前端 SSE 不适合长期轮询）
- 需要支持本地时区，数据存储在本地 SQLite

## Goals / Non-Goals

**Goals:**
- 用户能通过自然对话创建时间提醒
- 用户能通过 Workflow 面板主动创建、查看、编辑和删除计划
- LLM 能识别时间意图并触发 HITL 表单
- 系统在计划到期时通过 Live2D 主动提醒
- 用户能够完成/推迟/取消提醒

**Non-Goals:**
- 不实现日历集成（Google Calendar, iCal 等）
- 不实现复杂的重复规则（仅支持简单重复：每天/每周/每月/无）
- 不实现多设备同步

## Decisions

### Decision 1: Plan 作为独立记忆类型

**选择:** 在 `MemoryCategory` 枚举中新增 `PLAN` 类型

**理由:**
- 计划有明确的时间属性和状态（pending/completed/dismissed），与现有类型语义不同
- 需要独立的查询逻辑（按时间查询到期计划）
- 便于未来扩展（如日历视图）

**替代方案（不采用）:**
- 使用 `fact` 类型存储计划：语义混乱，查询困难
- 独立的 Plans 表：增加复杂度，与记忆系统割裂

### Decision 2: 计划数据结构

```python
@dataclass
class PlanEntry:
    id: str                          # UUID
    session_id: Optional[str]        # 创建时的会话
    title: str                       # 计划标题 (e.g., "开会")
    description: Optional[str]       # 详细描述
    target_time: datetime            # 目标时间 (UTC)
    reminder_offset_minutes: int     # 提前提醒时间 (默认 10 分钟)
    repeat_type: str                 # none | daily | weekly | monthly
    status: str                      # pending | completed | dismissed | snoozed
    snooze_until: Optional[datetime] # 推迟到的时间
    created_at: datetime
    updated_at: datetime
```

### Decision 3: Electron 轮询策略

**选择:** Electron main process 定时轮询后端 API

**轮询间隔:** 60 秒（平衡实时性和资源消耗）

**流程:**
```
[Electron main.cjs]
    ↓ setInterval(60000)
    ↓ fetch('http://localhost:8002/plans/due')
    ↓
[Backend returns due plans]
    ↓
[IPC: plan:reminder] → [Live2D renderer]
    ↓
[Live2D displays reminder]
```

**理由:**
- Electron main process 可在后台持续运行
- 不依赖窗口 focus 状态
- 与现有 HITL IPC 模式一致

### Decision 4: HITL 计划表单设计

**触发条件:** LLM 识别到时间意图时生成 HITL 请求

**表单字段:**
| 字段 | 类型 | 描述 |
|------|------|------|
| title | text | 计划标题 |
| description | textarea | 详细描述（可选） |
| target_datetime | datetime | 目标日期时间 |
| reminder_offset | select | 提前提醒：立即/5分钟/10分钟/30分钟/1小时 |
| repeat_type | select | 重复：不重复/每天/每周/每月 |

**HITL Context:**
```json
{
  "intent": "collect_plan",
  "memory_category": "plan"
}
```

### Decision 5: 时区处理

**选择:** 存储 UTC，显示时转换为本地时区

**理由:**
- 一致的数据存储格式
- 避免夏令时问题
- Python `datetime` 和 JavaScript `Date` 都能轻松处理 UTC

### Decision 6: Workflow 面板计划管理 UI

**选择:** 在 Workflow 面板新增 Plans 页面，提供完整的 CRUD 功能

**UI 组件:**
| 组件 | 描述 |
|------|------|
| PlanList | 计划列表，按时间分组（今天/明天/本周/更晚），显示状态标签 |
| PlanForm | 添加/编辑表单，复用 HITL 表单字段设计 |
| PlanFilters | 状态过滤器：全部/待执行/已完成/已取消 |
| PlanCard | 单个计划卡片，显示标题、时间、状态，支持快捷操作 |

**页面布局:**
```
┌─────────────────────────────────────┐
│ Plans                    [+ 添加]   │
├─────────────────────────────────────┤
│ 过滤: [全部] [待执行] [已完成] [已取消] │
├─────────────────────────────────────┤
│ 今天                                │
│ ┌─────────────────────────────────┐ │
│ │ ○ 开会 · 15:00 · 提前10分钟     │ │
│ └─────────────────────────────────┘ │
│ 明天                                │
│ ┌─────────────────────────────────┐ │
│ │ ○ 提交报告 · 10:00 · 每周重复   │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

**理由:**
- 复用现有 Workflow 面板结构，保持 UI 一致性
- 提供比 HITL 表单更完整的管理能力（列表、过滤、批量操作）
- 表单字段与 HITL 保持一致，减少代码重复

**API 调用:**
- 列表: `GET /plans?status=pending&page=1&limit=20`
- 创建: `POST /plans`
- 更新: `PUT /plans/{id}`
- 删除: `DELETE /plans/{id}`

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM 时间解析不准确 | 创建错误时间的计划 | HITL 表单让用户确认/修正时间 |
| 轮询间隔过长 | 提醒延迟最多 60 秒 | 可接受；重要场景可减少间隔 |
| Electron 应用未运行 | 错过提醒 | 不在 Non-Goals 中处理；未来可考虑系统通知 |
| 大量过期计划 | 启动时提醒轰炸 | 查询时限制返回数量，分批处理 |

## Migration Plan

1. 添加 MemoryCategory.PLAN（向后兼容）
2. 创建 plans 表（新表，无迁移）
3. 更新 LLM 提示词（无破坏性）
4. 添加 API 端点（新增）
5. 更新 Electron 和 Live2D（客户端更新）

**回滚方案:** 移除 PLAN 类别和相关代码，plans 表可保留不影响系统

## Open Questions

1. **推迟提醒的默认时间?** 建议选项：5分钟/15分钟/1小时/明天同一时间
2. **是否需要声音提醒?** 当前设计仅使用 Live2D 视觉提醒
3. **应用未运行时的处理?** 当前设计不处理，启动后会显示过期提醒
