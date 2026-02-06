# 情感 UI 增强 Spec Delta

## ADDED Requirements

### Requirement: Live2D Emotion Indicator Connection

Live2D 聊天界面 SHALL 连接情感指示器，实时显示 AI 感知到的用户情感状态。

系统 SHALL 将 SSE `emotion` 事件传递到情感指示器 UI 组件，更新以下显示内容：
- 情感类型标签（如 "Happy"、"Sad"）
- 对应颜色的状态圆点
- 置信度百分比

#### Scenario: Emotion indicator updates on SSE event

- **GIVEN** Live2D 聊天界面已初始化
- **AND** 后端通过 SSE 发送 `emotion` 事件（primary: "happy", confidence: 0.85）
- **WHEN** 前端接收到该事件
- **THEN** 情感指示器 SHALL 显示：
  - 绿色状态圆点（happy 对应色 #22c55e）
  - 标签文本 "Happy"
  - 置信度 "85%"

#### Scenario: Emotion indicator shows neutral by default

- **GIVEN** Live2D 聊天界面刚初始化，尚未收到 emotion 事件
- **WHEN** 用户查看情感指示器
- **THEN** 情感指示器 SHALL 显示 neutral 状态（灰色圆点，"Neutral" 标签）

### Requirement: Emotion History Display in Workflow Panel

Workflow 管理面板 SHALL 在 Working Memory 区域提供情感历史视图，展示当前会话最近的情感变化。

情感历史视图 SHALL 展示以下信息：
- 每轮的情感类型（带对应颜色标记）
- 每轮的置信度
- 对话轮次序号

#### Scenario: Display emotion history list

- **GIVEN** 当前会话已进行 5 轮对话
- **AND** 工作记忆中 `emotion_history` 包含 5 条记录
- **WHEN** 用户查看 Workflow 面板的 Working Memory 区域
- **THEN** 系统 SHALL 展示 5 条情感历史记录
- **AND** 每条记录显示情感类型、颜色标记和置信度

#### Scenario: Empty emotion history

- **GIVEN** 当前会话刚开始，无情感历史记录
- **WHEN** 用户查看情感历史视图
- **THEN** 系统 SHALL 显示"暂无情感记录"的空状态提示

### Requirement: Emotion History API Extension

工作记忆 API SHALL 在响应中包含 `emotion_history` 字段，供前端情感历史视图使用。

#### Scenario: Working memory API returns emotion history

- **GIVEN** 当前会话工作记忆中包含 3 条情感历史记录
- **WHEN** 前端请求 `/api/memory/working` 接口
- **THEN** 响应 SHALL 包含 `emotion_history` 字段
- **AND** 字段为包含 3 个对象的数组，每个对象包含 `emotion`、`confidence`、`turn`
