## ADDED Requirements

### Requirement: Visual Display Request Type

系统 SHALL 支持新的 HITL 请求类型 `visual_display`，用于 AI 向用户展示结构化的视觉内容。

Visual Display 请求 MUST 包含以下字段：
- `id`: 唯一标识符
- `type`: 固定值 `"visual_display"`
- `title`: 弹窗标题
- `displays`: 展示组件数组

Visual Display 请求 MAY 包含以下可选字段：
- `description`: 描述文本
- `dismiss_label`: 关闭按钮文案，默认 "关闭"

#### Scenario: AI 发起 Visual Display 请求

- **WHEN** AI 返回的 JSON 响应包含 `hitl_request` 且 `type` 为 `"visual_display"`
- **THEN** 系统解析该请求并打开 Visual Display 弹窗
- **AND** 弹窗显示 title、description 和 displays 内容
- **AND** 弹窗底部显示关闭按钮

#### Scenario: Visual Display 弹窗关闭

- **WHEN** 用户点击关闭按钮或按 ESC 键
- **THEN** 弹窗关闭
- **AND** 对话可正常继续（无需触发 AI continuation）

---

### Requirement: Table Display Component

系统 SHALL 支持 `table` 类型的展示组件，用于渲染二维表格数据。

Table 组件数据 MUST 包含：
- `headers`: 字符串数组，表示列标题
- `rows`: 二维字符串数组，每行数据与 headers 对应

Table 组件数据 MAY 包含：
- `alignment`: 字符串数组，每列的对齐方式（`"left"` | `"center"` | `"right"`）
- `caption`: 表格标题/说明

#### Scenario: 渲染简单表格

- **GIVEN** 一个 table display field，headers 为 `["名称", "价格", "评分"]`，rows 为 `[["iPhone 15", "5999", "4.5"], ["Pixel 8", "4499", "4.7"]]`
- **WHEN** 弹窗渲染该组件
- **THEN** 显示一个 3 列 2 行的表格
- **AND** 表头显示 "名称"、"价格"、"评分"
- **AND** 数据行显示对应的手机信息

#### Scenario: 渲染带对齐方式的表格

- **GIVEN** 一个 table display field，alignment 为 `["left", "right", "center"]`
- **WHEN** 弹窗渲染该组件
- **THEN** 第一列左对齐
- **AND** 第二列右对齐
- **AND** 第三列居中对齐

#### Scenario: 渲染带标题的表格

- **GIVEN** 一个 table display field，caption 为 "2024 年手机推荐"
- **WHEN** 弹窗渲染该组件
- **THEN** 表格上方或下方显示标题 "2024 年手机推荐"

---

### Requirement: ASCII Display Component

系统 SHALL 支持 `ascii` 类型的展示组件，用于渲染预格式化的 ASCII 艺术或文本图形。

ASCII 组件数据 MUST 包含：
- `content`: 字符串，包含预格式化的 ASCII 内容

ASCII 组件数据 MAY 包含：
- `title`: ASCII 内容的标题

#### Scenario: 渲染 ASCII 流程图

- **GIVEN** 一个 ascii display field，content 为包含方框和箭头的 ASCII 流程图
- **WHEN** 弹窗渲染该组件
- **THEN** 使用等宽字体渲染内容
- **AND** 保留所有空格和换行
- **AND** 内容正确对齐显示

#### Scenario: 渲染带标题的 ASCII 内容

- **GIVEN** 一个 ascii display field，title 为 "系统架构图"，content 为 ASCII 架构图
- **WHEN** 弹窗渲染该组件
- **THEN** ASCII 内容上方显示标题 "系统架构图"

---

### Requirement: Multiple Display Fields

系统 SHALL 支持在一个 Visual Display 请求中包含多个 display fields。

#### Scenario: 渲染多个组件

- **GIVEN** 一个 Visual Display 请求，displays 数组包含 2 个 table 和 1 个 ascii 组件
- **WHEN** 弹窗渲染该请求
- **THEN** 按数组顺序依次渲染所有组件
- **AND** 各组件之间有适当的间距

---

### Requirement: Display Request Schema

后端 SHALL 提供 `HITLDisplayRequest` Pydantic 模型用于验证 Visual Display 请求。

#### Scenario: 解析有效的 Visual Display 请求

- **GIVEN** LLM 返回的 JSON 包含有效的 visual_display 类型 hitl_request
- **WHEN** 调用 `parse_hitl_request_from_dict` 函数
- **THEN** 返回解析后的 `HITLDisplayRequest` 对象
- **AND** 对象包含正确的 title、displays 等字段

#### Scenario: 解析无效的 Visual Display 请求

- **GIVEN** JSON 中 displays 字段缺失或格式错误
- **WHEN** 调用解析函数
- **THEN** 返回 `None`
- **AND** 不抛出异常

---

### Requirement: Frontend Type Definitions

前端 SHALL 提供 TypeScript 类型定义以支持 Visual Display 请求的类型安全。

#### Scenario: 类型安全的请求处理

- **GIVEN** 前端收到 HITL 请求
- **WHEN** 使用 `isDisplayRequest(request)` type guard
- **THEN** 能正确识别 visual_display 类型
- **AND** TypeScript 编译器能推断出正确的请求类型

---

### Requirement: Working Memory Persistence

系统 SHALL 将 Visual Display 请求数据持久化到工作记忆的上下文变量中，以便后续会话上下文引用和 replay。

上下文变量存储格式 MUST 包含：
- `type`: 固定值 `"visual_display"`，用于区分 form 类型
- `displays`: 原始 display fields 数据数组
- `displays_def`: display fields 定义，用于 replay
- `timestamp`: ISO 格式时间戳

#### Scenario: Visual Display 数据持久化

- **GIVEN** AI 发起了一个 Visual Display 请求
- **WHEN** 用户关闭弹窗
- **THEN** display 数据被存储到工作记忆的 `context_variables` 中
- **AND** 存储键名为 `hitl_{title}` 格式

#### Scenario: 上下文变量大小限制

- **GIVEN** 上下文变量总大小接近限制
- **WHEN** 存储新的 Visual Display 数据导致超限
- **THEN** 系统按 LRU 策略移除最旧的条目
- **AND** 新数据被成功存储

---

### Requirement: Context Variable Replay Support

上下文变量对话框 SHALL 支持 replay Visual Display 类型的数据，允许用户回顾 AI 之前展示的信息。

#### Scenario: 识别 Visual Display 类型上下文变量

- **GIVEN** 上下文变量列表中包含 Visual Display 类型的条目
- **WHEN** 对话框渲染该条目
- **THEN** 类型列显示 `visual_display`
- **AND** 预览列显示组件数量和时间戳

#### Scenario: Replay Visual Display 内容

- **GIVEN** 用户点击 Visual Display 类型条目的 "replay" 按钮
- **WHEN** 系统打开 HITL 弹窗
- **THEN** 弹窗以 `type: 'visual_display'` 模式打开
- **AND** 弹窗显示存储的 displays 内容
- **AND** 弹窗为只读模式（`readonly: true`）

#### Scenario: Replay 显示原始表格数据

- **GIVEN** 存储的 Visual Display 包含 table 组件
- **WHEN** 用户 replay 该条目
- **THEN** 弹窗渲染与原始展示相同的表格
- **AND** 包含相同的 headers、rows、alignment 和 caption
