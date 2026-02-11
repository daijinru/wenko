# Change: 定义 Wenko 执行感知 UI 哲学

## 为什么

Wenko 的 ExecutionObserver 是一套完整、稳定的机器侧执行感知系统，被以下模块全量消费：
- **ReasoningNode**（`workflow/core/nodes/reasoning.py:299`）— 通过 `consequence_views()` 感知执行后果
- **MemoryNode**（`workflow/core/nodes/memory.py:110`）— 通过 `consequence_view()` 记录执行事实
- **GraphRunner**（`workflow/graph_runner.py:322-333`）— 通过 `snapshot()` 做 resume 对齐
- **HTTP API**（`workflow/main.py:2199-2251`）— 通过 `timeline()/snapshot()/topology()` 暴露给前端
- **SSE Events**（`workflow/graph_runner.py:514-535`）— 通过 `_build_execution_state_event()` 推送状态变更

Observer 是完成态，无死代码。**但它对人类用户而言仍是"不可见的神经系统"**。

当前缺失的是：一套**稳定的人类执行感知模型**——把 Observer 输出翻译为人类能理解、信任、操作的执行体验。

没有这套哲学，未来任何 UI 工作都会面临两个风险：
- 直接暴露工程概念（snapshot / topology / contract），让非技术用户困惑
- 拼凑临时视图，无法随系统演进

## 变更内容

- 定义 Wenko **执行 UI 哲学**：系统如何将执行呈现为叙事（而非日志）
- 建立**人类执行感知对象模型**：用户感知到的命名概念（执行 / 行动 / 后果 / 状态 / 记忆影响）——不含工程词汇
- 规定**执行认知视图结构**：五个稳定的认知视图（执行舞台 / 行动解释 / 执行历史 / 执行结构 / 记忆影响）
- 提供 **Observer → UI 语义映射表**：确保每个 Observer 输出都有明确的人类含义
- 声明**边界规则**：防止 UI 绕过 Observer 或展示未验证数据

## 影响

- 影响的 spec：新增 `execution-ui-philosophy` 能力（不修改现有 `execution-observation` 或 `execution-state-machine`）
- 影响的代码：**不改代码** — 这是纯设计 proposal，为所有未来执行 UI 工作建立概念基础
- 依赖关系：依赖 `add-execution-observation-layer`（本哲学映射的 Observer 体系）

## 代码参考

| 文件 | 关键内容 |
|-----|---------|
| `workflow/observation.py:50-275` | ExecutionObserver 完整实现 |
| `workflow/core/state.py:210-349` | 所有 Observation 数据模型定义 |
| `workflow/core/state.py:220-228` | `STATUS_TO_CONSEQUENCE` — 当前唯一的"人类标签"映射 |
| `workflow/observation.py:33-47` | `_generate_action_summary()` — 行动摘要生成 |
| `workflow/core/nodes/reasoning.py:299-332` | ReasoningNode 消费 consequence_views |
| `workflow/core/nodes/memory.py:110-145` | MemoryNode 记录 execution_fact |
| `workflow/graph_runner.py:322-370` | Resume 对齐 + SSE 事件发射 |
| `workflow/graph_runner.py:514-535` | `_build_execution_state_event()` SSE 事件构造 |
| `workflow/main.py:2199-2251` | HTTP API 端点（timeline / snapshot / topology） |
