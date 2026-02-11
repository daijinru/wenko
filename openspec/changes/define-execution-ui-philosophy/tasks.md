## 1. 人类状态标签层

在现有 `STATUS_TO_CONSEQUENCE`（`workflow/core/state.py:220-228`）基础上，新增 UI 层人类标签映射。

- [x] 1.1 在 `workflow/core/state.py` 中 `STATUS_TO_CONSEQUENCE` 之后（约 line 229），新增 `STATUS_TO_HUMAN_LABEL` 字典，定义 7 个状态 → 中文人类标签的映射（PENDING→"准备中", RUNNING→"进行中", WAITING→"需要关注", COMPLETED→"已完成", FAILED→"出了问题", REJECTED→"已拒绝", CANCELLED→"已停止"）
- [x] 1.2 在 `workflow/tests/test_execution_observation.py` 中新增 `TestHumanLabels` 测试类，验证：(a) 所有 7 个 `ExecutionStatus` 都有对应人类标签 (b) 标签值是中文字符串 (c) 与 `STATUS_TO_CONSEQUENCE` 的 key 完全一致
- [x] 1.3 确认 `STATUS_TO_HUMAN_LABEL` 不影响现有 `STATUS_TO_CONSEQUENCE` 的消费者（`observation.py:105` 的 `consequence_view()`、`reasoning.py:321`、`memory.py:133`）— 新映射是独立的 UI 层，不替换机器标签

## 2. 行动摘要翻译规则

当前 `_generate_action_summary()`（`workflow/observation.py:33-47`）输出技术格式（如 `"email.send"`, `"ecs:form"`）。定义 UI 层翻译规则。

- [x] 2.1 在 `workflow/observation.py` 中 `_generate_action_summary()` 之后（约 line 48），新增 `_humanize_action_summary(summary: str) -> str` 函数，将技术摘要转为自然语言（如 `"email.send"` → `"发送邮件"`, `"ecs:form"` → `"填写表单"`, 未识别的保持原样）
- [x] 2.2 在 `workflow/tests/test_execution_observation.py` 的 `TestActionSummaryGeneration`（约 line 568）中新增测试用例，覆盖：(a) `service.method` 格式翻译 (b) `ecs:type` 格式翻译 (c) 未识别格式的回退行为
- [x] 2.3 新增 `_humanize_consequence(consequence_label: str, has_side_effects: bool) -> str` 函数（放在 `_humanize_action_summary` 之后），将机器标签翻译为人类叙事（如 SUCCESS+side_effects → "已完成（不可撤销）", FAILED → "出了问题"）

## 3. UI 语义翻译层

建立从 Observer 投影到人类感知对象的翻译层。

- [x] 3.1 在 `workflow/` 下新建 `ui_translation.py`，定义 `ExecutionUITranslator` 类，包含以下方法：
  - `translate_snapshot(snapshot: ExecutionSnapshot) -> dict` — 将 snapshot 翻译为执行舞台视图数据（使用 `STATUS_TO_HUMAN_LABEL` 和 `_humanize_action_summary`）
  - `translate_consequence(view: ExecutionConsequenceView) -> dict` — 将 consequence_view 翻译为行动解释视图数据
  - `translate_timeline(timeline: ExecutionTimeline) -> dict` — 将 timeline 翻译为执行历史视图数据
- [x] 3.2 `ExecutionUITranslator` 的输出 dict 中，所有 key 使用人类语义命名（如 `"状态"`, `"行动"`, `"后果"`, `"是否不可逆"`），不含任何工程字段名
- [x] 3.3 在 `workflow/tests/` 下新建 `test_ui_translation.py`，测试翻译层：(a) snapshot → 执行舞台数据 (b) consequence_view → 行动解释数据 (c) timeline → 执行历史数据 (d) 输出中不包含工程词汇

## 4. SSE 事件人类化

当前 `_build_execution_state_event()`（`workflow/graph_runner.py:514-535`）构造的 SSE payload 包含工程字段（`execution_id`, `actor_category`, `from_status`, `to_status`）。

- [x] 4.1 在 `graph_runner.py:535` 之后，新增 `_humanize_execution_state_event(event: dict) -> dict` 方法，将 SSE 事件转为人类可读格式（使用 `STATUS_TO_HUMAN_LABEL` 和 `_humanize_action_summary`）
- [x] 4.2 保留原始 `_build_execution_state_event()` 不变（它服务于机器消费者如前端状态管理），`_humanize_execution_state_event` 作为可选的 UI 层包装
- [x] 4.3 在 `workflow/tests/test_execution_observation.py` 的 `TestSSEExecutionStatePayload`（约 line 812）中新增测试用例，验证人类化 SSE 事件：(a) 不包含 `actor_category` (b) `from_status` / `to_status` 被替换为人类标签 (c) `execution_id` 不直接暴露

## 5. API 端点人类化选项

当前 HTTP API（`workflow/main.py:2199-2251`）直接返回 Observer 投影的 `model_dump()`。

- [x] 5.1 在 `GET /api/execution/{session_id}/timeline`（`main.py:2199`）中增加可选 `?human=true` 查询参数，当启用时通过 `ExecutionUITranslator.translate_timeline()` 返回人类化数据
- [x] 5.2 在 `GET /api/execution/{execution_id}/snapshot`（`main.py:2223`）中增加可选 `?human=true` 参数，当启用时通过 `ExecutionUITranslator.translate_snapshot()` 返回
- [x] 5.3 默认行为（无 `?human` 参数）保持不变，确保不破坏现有 API 消费者

## 6. 边界规则验证

- [x] 6.1 审查 `electron/` 目录中所有消费 `/api/execution/` 的前端代码，确认是否有直接展示 `execution_id`、`actor_category`、`from_status` 等工程字段的情况 — **结果：零违规，Electron 前端未消费任何 Observer 数据**
- [x] 6.2 审查 SSE 事件消费（前端中处理 `execution_state` 事件的代码），确认是否有直接将原始 payload 展示给用户的情况 — **结果：零违规，前端未处理 execution_state 事件**
- [x] 6.3 如发现违规，记录到本 proposal 的补充说明中，作为后续 UI 修复的输入 — **无违规发现**

## 7. 验证

- [x] 7.1 运行 `openspec validate define-execution-ui-philosophy --strict` — **通过**
- [x] 7.2 运行现有测试 `pytest workflow/tests/test_execution_observation.py` 确认无回归 — **95 passed, 0 failed**
- [x] 7.3 运行新增测试 `pytest workflow/tests/test_ui_translation.py` — **12 passed, 0 failed**
