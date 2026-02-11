# implement-execution-ui — Design

## 1. 架构概览

前端执行感知 UI 需要解决两个核心挑战：

1. **两个 UI 层的统一**：Live2D Widget（对话界面，Shadow DOM + 原生 TS）和 React Workflow Panel（管理面板）是完全独立的渲染上下文
2. **实时数据流**：SSE `execution_state` 事件需要从对话流推送到两个独立的 UI 层

### 数据流架构

```
Backend (Python)
  │
  ├── SSE Stream (/chat)
  │   └── execution_state event (human=true 自动附带)
  │       ├──→ Live2D Widget (chat.ts) ──→ 执行舞台 overlay
  │       └──→ Electron Main Process ──→ IPC ──→ React Workflow Panel
  │
  └── HTTP API
      ├── GET /api/execution/{session_id}/timeline?human=true
      │   └──→ React Workflow Panel ──→ 执行历史 Tab
      └── GET /api/execution/{execution_id}/snapshot?human=true
          └──→ React Workflow Panel ──→ 执行舞台（补充查询）
```

## 2. 关键决策

### 决策 1：SSE 人类化时机——后端自动附带（方案 B）

**选择**：在后端 SSE 发射 `execution_state` 事件时，自动调用 `_humanize_execution_state_event()` 并将人类化数据作为 `human` 字段附带在原始 payload 中。

**理由**：
- 前端无需维护状态标签映射表的副本
- 单一翻译来源，避免前后端不一致
- 不影响原始 payload（机器消费者仍可读原始字段）

**格式**：
```json
{
  "execution_id": "abc-123",
  "action_summary": "email.send",
  "from_status": "running",
  "to_status": "completed",
  "is_terminal": true,
  "has_side_effects": true,
  "human": {
    "行动": "发送email",
    "原状态": "进行中",
    "新状态": "已完成",
    "是否已结束": true,
    "是否需要关注": false,
    "是否不可逆": true
  }
}
```

### 决策 2：Live2D 与 React 的执行状态桥接——IPC 转发

**选择**：Live2D Widget 在收到 `execution_state` SSE 事件后，通过 `window.electronAPI.send('execution-state-update', humanData)` 将人类化数据发送到 Electron Main Process，Main Process 再通过 IPC 转发到 Workflow 窗口。

**理由**：
- Live2D Widget 已有 `window.electronAPI` 调用先例（ECS 表单通过 IPC 打开独立窗口）
- 避免 React Workflow Panel 建立独立 SSE 连接（对话 SSE 流只在 Live2D 窗口中建立）
- 符合 Electron 的架构模式（Main Process 作为窗口间通信的中心）

**备选（不采用）**：React Panel 独立订阅 SSE——增加连接数，且需要知道当前 session_id，而 session 管理在 Live2D 侧。

### 决策 3：执行状态 UI 位置——Live2D 对话 overlay + React Tab

**选择**：

| 视图 | 位置 | 形态 |
|------|------|------|
| 执行舞台 | Live2D 对话窗口底部 | 叙事状态条，如"正在发送邮件……" |
| 执行历史 | React Workflow Panel 新 Tab | 时间线列表（类似日志但是叙事形式） |
| 行动解释 | 执行历史条目展开 | 展开卡片显示后果、不可逆标记 |

**理由**：
- 执行舞台需要在用户对话时实时可见（Live2D 窗口是主界面）
- 执行历史是事后查看需求（Workflow Panel 是管理界面）
- 与现有 Tab 结构一致（聊天历史、工作记忆、长期记忆、MCP、日志、设置）

### 决策 4：前端状态管理——轻量 React Context

**选择**：新建 `ExecutionContext`，通过 IPC `on('execution-state-update')` 接收数据，提供给执行历史 Tab 和执行舞台组件。

**理由**：
- 项目已有 `ToastContext` 作为先例
- 执行状态是跨组件共享数据（执行历史 Tab 和未来可能的其他消费者）
- 无需引入新依赖（Redux/Zustand）

### 决策 5：SSE 事件防抖策略——最新状态覆盖

**选择**：对于同一个 execution_id 的连续状态更新，只展示最新状态。执行舞台只显示最近一条非终态的行动。

**理由**：
- 状态转换可能很快（PENDING→RUNNING 在毫秒内发生）
- 用户不需要看到中间态闪烁
- 终态（COMPLETED/FAILED/CANCELLED/REJECTED）保留在历史中

## 3. 文件规划

### 新增文件

| 文件 | 职责 |
|------|------|
| `electron/src/renderer/workflow/hooks/use-execution.ts` | 执行状态 hook：IPC 监听 + HTTP API 调用 |
| `electron/src/renderer/workflow/components/features/execution/execution-tab.tsx` | 执行历史 Tab 主组件 |
| `electron/src/renderer/workflow/components/features/execution/execution-timeline.tsx` | 时间线列表组件 |
| `electron/src/renderer/workflow/components/features/execution/execution-detail.tsx` | 行动解释展开卡片 |
| `electron/src/renderer/workflow/components/features/execution/execution-stage.tsx` | 执行舞台状态条（可选独立组件，或嵌入 Live2D） |
| `electron/src/renderer/workflow/types/execution.ts` | 执行相关 TypeScript 类型定义 |
| `electron/live2d/live2d-widget/src/execution-stage.ts` | Live2D 侧执行舞台 overlay 渲染 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `electron/live2d/live2d-widget/src/chat.ts` | 新增 `execution_state` SSE 事件处理分支 |
| `electron/src/renderer/workflow/App.tsx` | 新增"执行状态" Tab |
| `electron/main.cjs` | 新增 IPC 转发 `execution-state-update` |
| `electron/preload.cjs` | 新增 IPC channel 白名单（如需） |
| `workflow/graph_runner.py` | SSE 发射时自动附带 `human` 字段 |

## 4. UI 设计原则

遵循 `execution-ui-philosophy` 五条边界规则：

1. **叙事优先**：展示"正在发送邮件……已完成"，不展示"RUNNING→COMPLETED"
2. **禁止工程词汇**：用户可见文本不含 snapshot/contract/topology/observer/execution_id
3. **只展示已验证事实**：pending 状态的行动标记为"准备中"，不暗示已开始
4. **Observer 不可见**：UI 表现为"系统正在做事"，不是"监控面板"
5. **唯一来源**：所有执行数据来自 `?human=true` API 或人类化 SSE，不从 LLM 回复中提取

### 视觉风格

遵循现有 classic-stylesheets Mac OS 9 主题 + Tailwind CSS + Radix UI 组合：
- 执行舞台状态条：简洁文字 + 状态色点（进行中=蓝、需要关注=橙、已完成=绿、出了问题=红）
- 执行历史时间线：卡片列表，与日志 Tab 风格一致但内容叙事化
- 不可逆操作标记：使用 Badge 组件 + 醒目色彩
