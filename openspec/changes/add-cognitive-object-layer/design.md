# Design: Cognitive Object Layer (COL)

## Context

### 背景：Execution-driven 的局限性

Wenko 当前的认知架构围绕 **Execution（执行）** 组织：

```
用户输入
  → IntentNode → EmotionNode → MemoryNode → ReasoningNode
    → ToolNode / ECSNode（产出 ExecutionContract）
      → ExecutionObserver（只读投影）
        → 前端展示
```

`ExecutionContract`（`state.py:110-175`）是系统中唯一的"事情载体"——它描述了一次具体的执行尝试，拥有状态机（PENDING → RUNNING → COMPLETED/FAILED/...），支持挂起恢复。

但 ExecutionContract 的语义是 **"一次执行尝试"**，不是 **"一件事情"**。

| 概念 | ExecutionContract | 真实的"事情" |
|------|-------------------|-------------|
| 生命周期 | 单次执行（秒~分钟级） | 跨天、跨周、跨月 |
| 数量关系 | 1 个 Contract = 1 次执行 | 1 件事 = N 次执行 |
| 结束条件 | COMPLETED/FAILED/... | 目标达成或用户放弃 |
| 等待语义 | WAITING = 等待人类在此次执行中回复 | 等待 = 等待外部世界变化 |
| 持久化 | 会话级（Checkpoint 中） | 跨会话持久化 |

**核心问题：** Contract 结束 ≠ 事情结束。但当前系统中，Contract 结束后，事情没有地方继续存在。

### Stakeholders

- **用户**：需要看到"我的事情列表"，而非"执行历史"
- **ReasoningNode**：需要知道当前对话关联的长期事情上下文
- **MemoryNode**：需要将执行摘要归属到具体的事情
- **ECS Projection**：应该投影"事情"给用户操作，而非投影"执行"
- **GraphRunner**：需要在执行完成后更新 CO 状态

### Constraints

1. **Execution 降级为 COL 的执行子系统** — ExecutionContract 和 ExecutionObserver 保持不变，但不再是独立层，而是 COL 内部的执行机制
2. **不改变图拓扑** — IntentNode → EmotionNode → MemoryNode → ReasoningNode 的顺序不变
3. **不引入外部数据库** — 继续使用 SQLite
4. **渐进式启用** — COL 必须可以在不影响现有功能的前提下逐步启用
5. **LLM 不能直接改变 CO 状态** — 所有状态迁移基于 Execution 事实 + 用户操作，可追溯

## Goals / Non-Goals

### Goals

1. 定义 Cognitive Object (CO) 作为"事情"的实体化表示
2. 定义 CO 的生命周期状态机（六状态）
3. 建立 Execution 作为 CO 执行子系统的关系模型
4. CO 可以独立于 Execution 存在
5. CO 持久化到 SQLite，跨会话存活
6. 明确 CO 与 Memory、ECS 的边界
7. 支持语义增强字段（semantic_type, domain_tag 等）
8. 提供渐进迁移方案

### Non-Goals

- 不讨论 UI 视觉设计或样式
- 不将 CO 退化为 Execution 日志封装
- 不退回"弹窗系统"设计
- 不在此提案中实现 CO → CO 关系图谱（预留接口但不实现）
- 不修改现有 ExecutionContract 的核心状态机（Execution 内部机制不变，只改变其在系统中的定位）

---

## 一、Wenko Cognitive Stack 层级架构

### 新的层级定义

```
┌─────────────────────────────────────────────────┐
│  L4: ECS Projection Layer                       │
│  ─ CO 的人类交互投影接口                         │
│  ─ 可丢弃视图，关闭不销毁 CO                     │
│  ─ 用户操作作用于 CO，而非直接作用于 Execution    │
├─────────────────────────────────────────────────┤
│  L3: Cognitive Object Layer (NEW)               │
│  ─ 系统认知中心                                  │
│  ─ CO 的生命周期管理                             │
│  ─ 所有事情在这里存在                             │
│  ┌─────────────────────────────────────────┐    │
│  │  Execution Subsystem                    │    │
│  │  ─ CO 的执行子系统（非独立层）            │    │
│  │  ─ ExecutionContract 状态机              │    │
│  │  ─ ExecutionObserver 只读投影             │    │
│  │  ─ ToolNode / ECSNode 执行               │    │
│  └─────────────────────────────────────────┘    │
├─────────────────────────────────────────────────┤
│  L2: Memory Layer                               │
│  ─ Working Memory（会话级上下文）                 │
│  ─ Long-term Memory（跨会话事实记录）             │
│  ─ 存储事实，不存储事情                          │
├─────────────────────────────────────────────────┤
│  L1: Perception Layer                           │
│  ─ Input Normalization                          │
│  ─ Emotion Detection                            │
│  ─ Intent Recognition                           │
└─────────────────────────────────────────────────┘
```

### 层级边界规则

| 规则 | 说明 |
|------|------|
| Execution 是 COL 的子系统 | Execution 不再是独立层，而是 CO 调度执行的内部机制 |
| COL 不属于 UI 层 | CO 是领域实体，不是视觉组件 |
| COL 不属于 Memory 层 | Memory 存储事实，CO 是事情实体；CO 可以引用 Memory，但 Memory 不持有 CO |
| ECS 是 CO 的投影接口 | 用户通过 ECS 与 CO 交互，ECS 是可丢弃视图 |
| CO 拥有 Execution | CO 创建、调度、监听 Execution，Execution 为 CO 服务 |

### 数据流方向

```
用户 ──操作──> ECS (L4) ──作用于──> CO (L3)
                                     │
                          ┌──────────┴──────────┐
                          ↓                     ↓
                   Execution Subsystem    Memory (L2)
                   (CO 的内部执行机制)
                          │
                          ↓
                   CO (L3) ←── 状态更新（基于执行事实）
```

---

## 二、Cognitive Object 定义

### 2.1 CO 的本质

Cognitive Object (CO) 是 Wenko 中"事情"的实体化表示。它代表用户认知世界中的一个有边界的对象：

- 一个正在推进的项目
- 一个等待回复的邮件
- 一个需要每周检查的习惯
- 一个挂起的技术决策

**关键性质：** CO 可以在没有 Execution 的情况下存在。

### 2.2 数据模型

```python
class CognitiveObjectStatus(str, Enum):
    """CO 的六状态生命周期"""
    EMERGING = "emerging"    # 刚被识别，尚未完全定义
    ACTIVE = "active"        # 正在被积极推进
    WAITING = "waiting"      # 等待外部世界（不是等待 Execution）
    BLOCKED = "blocked"      # 被阻塞，需要解决依赖
    STABLE = "stable"        # 已达成目标，进入稳定态
    ARCHIVED = "archived"    # 不再活跃，归档保存

class CognitiveObject(BaseModel):
    """事情的实体化表示"""

    # === Identity ===
    co_id: str  # 稳定唯一 ID (UUID)
    title: str  # 人类可读的事情标题
    description: str = ""  # 事情描述

    # === Semantic Boundary ===
    semantic_type: Optional[str] = None   # 语义类型：task, project, goal, habit, decision, ...
    domain_tag: Optional[str] = None      # 领域标签：work, personal, health, finance, ...
    intent_category: Optional[str] = None # 意图分类：track, remind, analyze, create, ...

    # === Lifecycle ===
    status: CognitiveObjectStatus = CognitiveObjectStatus.EMERGING
    transitions: List[Dict[str, Any]] = []
    # Each: {"from": str, "to": str, "trigger": str, "timestamp": float,
    #         "actor": str, "reason": Optional[str]}

    # === Execution Links ===
    linked_execution_ids: List[str] = []  # ExecutionContract IDs

    # === Memory References ===
    linked_memory_ids: List[str] = []  # Long-term memory entry IDs

    # === External References ===
    external_references: List[Dict[str, str]] = []
    # Each: {"type": "url" | "email" | "file" | "person", "value": str, "label": str}

    # === CO → CO Relations (预留) ===
    related_co_ids: List[Dict[str, str]] = []
    # Each: {"co_id": str, "relation": "blocks" | "depends_on" | "part_of" | "related_to"}

    # === Metadata ===
    created_at: float
    updated_at: float
    created_by: str  # "user" | "system" | "reasoning_node"
    conversation_id: Optional[str] = None  # 创建时的会话 ID

    # === Context Snapshot ===
    creation_context: Optional[str] = None  # 创建时的上下文摘要
```

### 2.3 CO 与 Execution 的映射

```
CognitiveObject (CO)
    │
    ├── ExecutionContract #1 (COMPLETED)    ← "发了初步邮件"
    ├── ExecutionContract #2 (FAILED)       ← "尝试查询API失败"
    ├── ExecutionContract #3 (COMPLETED)    ← "重新查询成功"
    └── (等待更多 Execution...)

CO 存在，即使所有 Execution 都已结束。
CO.status = WAITING（等待对方回复邮件）
```

### 2.4 CO 独立性证明

| 场景 | CO 存在？ | Execution 存在？ |
|------|----------|-----------------|
| 用户说"我要跟踪这个项目进度" | EMERGING | 无 |
| 系统执行了一次查询 | ACTIVE | 1 个 COMPLETED |
| 查询完成，等待下周检查 | WAITING | 0 个活跃 |
| 用户说"这件事搞定了" | STABLE | 0 个活跃 |
| 一年后回顾 | ARCHIVED | 历史记录 |

---

## 三、Execution 作为 CO 的执行子系统

### 3.1 核心原则

```
┌──────────────────────────────────────────────────────┐
│  Execution 是 CO 的执行子系统                          │
│  CO 拥有 Execution，Execution 为 CO 服务               │
│  Execution 不能独立于 CO 定义"事情"的存在              │
│                                                      │
│  CO 调度 Execution                                   │
│  Execution 向 CO 汇报执行事实                         │
│  CO 根据执行事实决定自身状态迁移                       │
│                                                      │
│  CO.exists ≠ Execution.exists                        │
│  CO.end ≠ Execution.end                              │
│  CO.status ≠ Execution.status                        │
└──────────────────────────────────────────────────────┘
```

### 3.2 所有权结构

```
                    CognitiveObject (Owner)
                    ┌──────────────┐
                    │  co_id       │
                    │  status      │
                    │  title       │
                    │  ...         │
                    └──────┬───────┘
                           │ owns 1:N
            ┌──────────────┼──────────────┐
            │              │              │
   ExecutionContract  ExecutionContract  ExecutionContract
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │ execution_id │  │ execution_id │  │ execution_id │
   │ co_id (opt)  │  │ co_id (opt)  │  │ co_id (opt)  │
   │ status       │  │ status       │  │ status       │
   └──────────────┘  └──────────────┘  └──────────────┘
   (CO 的执行子单元)   (CO 的执行子单元)   (CO 的执行子单元)
```

### 3.3 所有权规则

| 规则 | 说明 |
|------|------|
| CO 拥有 Execution | Execution 是 CO 调度的执行子单元 |
| 1 CO → N Execution | 一个 CO 可以调度多个 ExecutionContract |
| Execution → 0..1 CO | 一个 Execution 可以不属于任何 CO（向后兼容，过渡期） |
| Execution 向 CO 汇报事实 | Execution 完成后，触发 CO 状态评估 |
| Execution 结束 ≠ CO 结束 | CO 的状态独立于 Execution 的终止状态 |
| CO 可以无 Execution | CO 可以在没有任何执行子单元的情况下存在 |

### 3.4 执行子系统 → CO 事实汇报

当 Execution 到达终止态时，作为 CO 的执行子系统，它向 CO 汇报执行事实，系统评估是否需要更新 CO 的状态：

```python
# 事件映射规则（伪代码）
def on_execution_terminal(contract: ExecutionContract, co: CognitiveObject):
    """Execution 终止后的 CO 状态评估"""

    if contract.status == ExecutionStatus.COMPLETED:
        # 执行成功 → CO 可能推进
        # 但不自动改变 CO 状态 —— 需要 ReasoningNode 评估
        emit_event("co.execution_completed", co_id=co.co_id, execution_id=contract.execution_id)

    elif contract.status == ExecutionStatus.FAILED:
        # 执行失败 → CO 可能被阻塞
        emit_event("co.execution_failed", co_id=co.co_id, execution_id=contract.execution_id)

    elif contract.status == ExecutionStatus.REJECTED:
        # 执行被拒 → CO 可能需要重新评估
        emit_event("co.execution_rejected", co_id=co.co_id, execution_id=contract.execution_id)
```

**关键：** 执行子系统汇报事实，但不直接改变 CO 状态。CO 状态迁移必须由明确的 trigger 驱动，记录 actor 和 reason。

---

## 四、CO 生命周期状态机

### 4.1 状态定义

```
 ┌───────────┐
 │ EMERGING  │ ← 初始态：事情刚被识别，边界尚未清晰
 └─────┬─────┘
       │ clarify
       ↓
 ┌───────────┐     wait      ┌───────────┐
 │  ACTIVE   │ ──────────── → │  WAITING  │
 └─────┬─────┘              └─────┬─────┘
       │              resume │     │ block
       │ ← ─────────────────┘     ↓
       │                    ┌───────────┐
       │    unblock         │  BLOCKED  │
       │ ← ────────────────┘└───────────┘
       │
       │ achieve
       ↓
 ┌───────────┐
 │  STABLE   │ ← 目标达成，进入稳定态
 └─────┬─────┘
       │ archive
       ↓
 ┌───────────┐
 │ ARCHIVED  │ ← 归档，不再活跃
 └───────────┘
```

### 4.2 合法状态迁移规则

```python
_CO_VALID_TRANSITIONS: Dict[str, Dict[str, str]] = {
    CognitiveObjectStatus.EMERGING: {
        "clarify": CognitiveObjectStatus.ACTIVE,
        "archive": CognitiveObjectStatus.ARCHIVED,  # 用户决定不追踪
    },
    CognitiveObjectStatus.ACTIVE: {
        "wait": CognitiveObjectStatus.WAITING,
        "block": CognitiveObjectStatus.BLOCKED,
        "achieve": CognitiveObjectStatus.STABLE,
        "archive": CognitiveObjectStatus.ARCHIVED,  # 用户放弃
    },
    CognitiveObjectStatus.WAITING: {
        "resume": CognitiveObjectStatus.ACTIVE,
        "block": CognitiveObjectStatus.BLOCKED,
        "achieve": CognitiveObjectStatus.STABLE,     # 在等待中自然达成
        "archive": CognitiveObjectStatus.ARCHIVED,
    },
    CognitiveObjectStatus.BLOCKED: {
        "unblock": CognitiveObjectStatus.ACTIVE,
        "archive": CognitiveObjectStatus.ARCHIVED,
    },
    CognitiveObjectStatus.STABLE: {
        "reactivate": CognitiveObjectStatus.ACTIVE,  # 重新打开
        "archive": CognitiveObjectStatus.ARCHIVED,
    },
    CognitiveObjectStatus.ARCHIVED: {
        "reactivate": CognitiveObjectStatus.ACTIVE,  # 从归档恢复
    },
}
```

### 4.3 状态迁移矩阵

| From \ To | EMERGING | ACTIVE | WAITING | BLOCKED | STABLE | ARCHIVED |
|-----------|----------|--------|---------|---------|--------|----------|
| EMERGING  | - | clarify | - | - | - | archive |
| ACTIVE    | - | - | wait | block | achieve | archive |
| WAITING   | - | resume | - | block | achieve | archive |
| BLOCKED   | - | unblock | - | - | - | archive |
| STABLE    | - | reactivate | - | - | - | archive |
| ARCHIVED  | - | reactivate | - | - | - | - |

### 4.4 状态迁移约束

1. **状态迁移基于 Execution 事实 + 用户操作** — 不允许无因状态变更
2. **LLM 不能直接改变 CO 状态** — LLM 可以建议（`suggest_transition`），但必须经过 CORegistry 验证并记录 actor
3. **所有迁移可追溯** — 每次迁移记录 `{from, to, trigger, timestamp, actor, reason}`
4. **actor 枚举** — `"user"` | `"system"` | `"execution_event"` | `"timeout"`
5. **ARCHIVED 可恢复** — 与 ExecutionContract 的终止态不同，CO 的 ARCHIVED 允许 reactivate

### 4.5 触发源分类

| trigger | 典型来源 | actor |
|---------|---------|-------|
| clarify | 用户在对话中提供了更多细节 | user |
| wait | 执行子系统完成后，系统判断需要等待外部 | execution_event |
| resume | 用户提供了外部信息，或时间条件满足 | user |
| block | 执行子系统失败且无法自动恢复 | execution_event |
| unblock | 用户解决了阻塞条件 | user |
| achieve | 用户确认目标达成 | user |
| archive | 用户主动归档 | user |
| reactivate | 用户重新打开 | user |

---

## 五、CO 与 Memory 的边界

### 5.1 本质区分

```
Memory = 事实记录（What happened）
CO     = 事情实体（What IS）
```

| 维度 | Memory | CO |
|------|--------|-----|
| 本质 | 被动记录 | 主动实体 |
| 时态 | 过去时：发生了什么 | 现在时：正在进行什么 |
| 生命周期 | 永久（除非被清理） | 有状态机驱动的生命周期 |
| 可操作性 | 只读查询 | 可变更状态 |
| 所有权 | 属于系统记忆库 | 属于用户认知空间 |

### 5.2 关系规则

| 规则 | 说明 |
|------|------|
| CO 持久化 | 是。存储在 SQLite `cognitive_objects` 表，跨会话存活 |
| CO 可以引用 Memory | 是。`linked_memory_ids` 字段存储关联的长期记忆 ID |
| Memory 可以脱离 CO 存在 | 是。大多数 Memory 不关联任何 CO（如用户偏好、事实） |
| Memory 不持有 CO | 是。Memory 层不感知 COL 的存在（单向依赖） |
| CO 创建时可生成 Memory | 是。"创建了一件新事情"本身可以作为事实记录 |

### 5.3 示例

```
CO: "准备下周的技术分享"
  ├── Memory #1: "用户偏好 Markdown 格式" (fact, 独立于 CO)
  ├── Memory #2: "技术分享主题确定为 LangGraph" (fact, 关联 CO)
  ├── Memory #3: "已发送邀请邮件给团队" (fact, 由 Execution 生成, 关联 CO)
  └── (CO 本身不是 Memory)
```

---

## 六、CO 与 ECS 的关系

### 6.1 ECS 的重新定位

| 旧定位 | 新定位 |
|--------|--------|
| Execution 的人类交互接口 | **CO 的投影接口** |
| 展示执行进度 | **投影事情状态** |
| 关闭 = 结束交互 | **关闭 ≠ 销毁 CO** |

### 6.2 ECS → CO 投影规则

```
用户操作 ──→ ECS (L4) ──→ CO (L3)
                              │
                              ↓ (如果需要执行)
                        Execution Subsystem
                        (CO 的内部执行机制)
```

| 规则 | 说明 |
|------|------|
| 用户操作作用于 CO | 用户在 ECS 中的操作（如"标记完成"）改变的是 CO 状态 |
| 关闭 ECS 不销毁 CO | ECS 是可丢弃的视图层 |
| ECS 是可丢弃视图 | 重新打开 ECS 应该能恢复 CO 的当前状态 |
| ECS 可以触发 Execution | 用户通过 ECS 决定执行某个操作 → 创建新的 ExecutionContract |

---

## 七、语义增强能力

### 7.1 语义字段

COL 在 CO 上支持以下语义增强字段，为未来认知图谱奠定基础：

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `semantic_type` | Optional[str] | CO 的语义类型 | `"task"`, `"project"`, `"goal"`, `"habit"`, `"decision"` |
| `domain_tag` | Optional[str] | 领域标签 | `"work"`, `"personal"`, `"health"`, `"finance"` |
| `intent_category` | Optional[str] | 意图分类 | `"track"`, `"remind"`, `"analyze"`, `"create"` |
| `external_references` | List[Dict] | 外部引用 | `[{"type": "url", "value": "...", "label": "..."}]` |
| `related_co_ids` | List[Dict] | CO → CO 关系（预留） | `[{"co_id": "...", "relation": "blocks"}]` |

### 7.2 CO → CO 关系（本期预留）

数据结构已定义但不实现查询/遍历逻辑：

```python
related_co_ids: List[Dict[str, str]] = []
# 支持的关系类型：
# - "blocks": 此 CO 阻塞目标 CO
# - "depends_on": 此 CO 依赖目标 CO
# - "part_of": 此 CO 是目标 CO 的子项
# - "related_to": 松散关联
```

未来认知图谱将基于这些关系实现：
- CO 依赖分析
- 阻塞链追踪
- 项目分解视图

---

## 八、持久化设计

### 8.1 SQLite 表结构

```sql
-- 主表：Cognitive Objects
CREATE TABLE IF NOT EXISTS cognitive_objects (
    co_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    semantic_type TEXT,
    domain_tag TEXT,
    intent_category TEXT,
    status TEXT NOT NULL DEFAULT 'emerging',
    transitions TEXT DEFAULT '[]',        -- JSON array
    external_references TEXT DEFAULT '[]', -- JSON array
    related_co_ids TEXT DEFAULT '[]',      -- JSON array
    linked_memory_ids TEXT DEFAULT '[]',   -- JSON array
    created_by TEXT NOT NULL,
    conversation_id TEXT,
    creation_context TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

-- 关联表：CO ↔ Execution 链接
CREATE TABLE IF NOT EXISTS co_execution_links (
    co_id TEXT NOT NULL,
    execution_id TEXT NOT NULL,
    linked_at REAL NOT NULL,
    PRIMARY KEY (co_id, execution_id),
    FOREIGN KEY (co_id) REFERENCES cognitive_objects(co_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_co_status ON cognitive_objects(status);
CREATE INDEX IF NOT EXISTS idx_co_domain ON cognitive_objects(domain_tag);
CREATE INDEX IF NOT EXISTS idx_co_type ON cognitive_objects(semantic_type);
CREATE INDEX IF NOT EXISTS idx_co_links_execution ON co_execution_links(execution_id);
```

### 8.2 查询模式

```python
class CORegistry:
    """CO 的 CRUD 和生命周期管理服务"""

    async def create(self, title: str, created_by: str, **kwargs) -> CognitiveObject
    async def get(self, co_id: str) -> Optional[CognitiveObject]
    async def list_active(self) -> List[CognitiveObject]  # 非 ARCHIVED 的 CO
    async def list_by_status(self, status: CognitiveObjectStatus) -> List[CognitiveObject]
    async def transition(self, co_id: str, trigger: str, actor: str, reason: str) -> CognitiveObject
    async def link_execution(self, co_id: str, execution_id: str) -> None
    async def link_memory(self, co_id: str, memory_id: str) -> None
    async def update_metadata(self, co_id: str, **kwargs) -> CognitiveObject
    async def search(self, query: str) -> List[CognitiveObject]  # 按 title/description 模糊查询
```

---

## 九、迁移策略

### 9.1 渐进式启用

COL 采用"影子层"策略渐进启用：

| 阶段 | 行为 | 风险 |
|------|------|------|
| Phase 0: 数据模型 | 只定义 CO 模型和表结构，不连接到认知图谱 | 零风险 |
| Phase 1: 独立 CRUD | CO 可以通过 API 创建/查询/修改，但不影响执行流程 | 极低 |
| Phase 2: Execution 归属 | ExecutionContract 新增可选 `cognitive_object_id`，建立 Execution 对 CO 的归属关系 | 低（可选字段） |
| Phase 3: ReasoningNode 集成 | ReasoningNode 在推理时读取关联的 CO 上下文 | 中（需要测试） |
| Phase 4: 全量启用 | ECS 投影 CO，Execution 完全作为 CO 的执行子系统运行 | 中高 |

### 9.2 现有 CPO 迁移

当前系统中没有显式的 CPO（Persistent Cognitive Object）实体。"事情"的概念散布在：

- `execution_trace`：执行历史
- `working_memory.current_goals`：当前目标栈
- `dialogue_history`：对话历史中隐含的事情

迁移方式：
- **无需数据迁移脚本** — 因为没有现有的 CPO 表
- **向后兼容** — COL 是纯新增，所有现有功能不受影响
- **渐进启用** — 通过配置开关 `system.col_enabled` 控制 Phase 2+ 的行为

### 9.3 ExecutionContract 修改

```python
class ExecutionContract(BaseModel):
    # ... 现有字段不变 ...

    # NEW: 可选的 CO 关联（Phase 2+）
    cognitive_object_id: Optional[str] = None
```

这是唯一对现有数据模型的修改，且为可选字段，向后完全兼容。

---

## 十、Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| CO 和 Execution 的状态可能不一致 | CO 状态基于 Execution 事实评估，不自动同步；不一致是合理的（事情没结束 ≠ 执行没结束） |
| CO 数量可能无限增长 | ARCHIVED 状态 + 未来清理策略；活跃 CO 预期数量 < 100 |
| LLM 可能错误创建 CO | CO 创建需要明确的 trigger（用户意图或系统规则），不允许 LLM 任意创建 |
| CO → CO 关系引入复杂度 | 本期只预留字段，不实现遍历逻辑 |
| 渐进迁移可能导致半启用状态 | 每个 Phase 都是可工作的完整状态，不存在"必须全部启用才能工作"的依赖 |
| ReasoningNode Prompt 膨胀 | CO 上下文注入采用摘要模式，不注入完整 CO 详情 |

## Open Questions

1. **CO 创建的 trigger 策略？**
   - 选项 A：ReasoningNode 检测到用户意图后自动创建
   - 选项 B：用户通过 UI 显式创建
   - 选项 C：两者结合 — 系统建议 + 用户确认
   - 当前倾向选项 C

2. **CO 的 title 由谁生成？**
   - 选项 A：LLM 从对话中提取
   - 选项 B：用户手动输入
   - 当前倾向 A（LLM 提取 + 用户可编辑）

3. **CO 状态自动评估的粒度？**
   - 每次 Execution 终止后？
   - 每次对话结束后？
   - 当前倾向：Execution 终止后触发评估事件，但评估逻辑在下一次 ReasoningNode 入口处执行
