# HITL Middleware Design

## Context

Wenko 是一个情感记忆 AI 系统。在某些场景下，AI 需要在执行操作前获取用户确认或收集额外信息。当前系统缺乏这种人机交互中间层，HITL 中间件填补这一空白。

### 典型使用场景

1. **偏好收集**: AI 询问 "您喜欢哪种运动？" → 前端渲染下拉选择框
2. **信息确认**: AI 要保存用户信息到长期记忆 → 请求用户确认
3. **多选决策**: AI 需要了解用户多个偏好 → 渲染复选框组
4. **自由输入**: AI 需要具体信息 → 渲染文本输入框

## Goals / Non-Goals

### Goals
- 提供灵活的表单 Schema 系统，支持多种输入类型
- 允许 AI 根据对话上下文动态生成表单
- 前端能够根据 Schema 自动渲染复合表单
- 用户可以 approve、edit 或 reject AI 的请求

### Non-Goals
- 不实现复杂的表单验证规则引擎
- 不支持表单之间的级联依赖
- 不实现表单模板持久化

## Decisions

### Decision 1: Form Schema 设计

采用 JSON Schema 风格的表单描述格式，由 AI 在响应中生成。

```json
{
  "hitl_request": {
    "id": "uuid",
    "type": "form",
    "title": "选择您的运动偏好",
    "description": "这将帮助我更好地了解您",
    "fields": [
      {
        "name": "sport",
        "type": "select",
        "label": "您最喜欢的运动",
        "required": true,
        "options": [
          {"value": "basketball", "label": "篮球"},
          {"value": "football", "label": "足球"},
          {"value": "swimming", "label": "游泳"},
          {"value": "running", "label": "跑步"}
        ]
      },
      {
        "name": "frequency",
        "type": "select",
        "label": "运动频率",
        "required": false,
        "options": [
          {"value": "daily", "label": "每天"},
          {"value": "weekly", "label": "每周"},
          {"value": "monthly", "label": "每月"}
        ]
      },
      {
        "name": "notes",
        "type": "textarea",
        "label": "补充说明",
        "placeholder": "可选填写",
        "required": false
      }
    ],
    "actions": {
      "approve": {"label": "确认", "style": "primary"},
      "edit": {"label": "修改后提交", "style": "default"},
      "reject": {"label": "跳过", "style": "secondary"}
    },
    "context": {
      "intent": "collect_preference",
      "memory_category": "preference"
    }
  }
}
```

**Rationale**: JSON Schema 风格易于解析、扩展性好，前端可直接映射到 Ant Design 组件。

### Decision 2: 支持的字段类型

| Type | Description | Ant Design Component |
|------|-------------|---------------------|
| `text` | 单行文本输入 | `Input` |
| `textarea` | 多行文本输入 | `Input.TextArea` |
| `select` | 单选下拉框 | `Select` |
| `multiselect` | 多选下拉框 | `Select mode="multiple"` |
| `radio` | 单选按钮组 | `Radio.Group` |
| `checkbox` | 复选框组 | `Checkbox.Group` |
| `number` | 数字输入 | `InputNumber` |
| `slider` | 滑块选择 | `Slider` |
| `date` | 日期选择 | `DatePicker` |
| `boolean` | 开关/确认 | `Switch` |

**Rationale**: 覆盖常见输入场景，与 Ant Design 组件一一对应，实现简单。

### Decision 3: HITL 交互流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        HITL 交互流程                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────┐     ┌─────────┐     ┌─────────────┐     ┌─────────────┐
│  User   │────▶│   AI    │────▶│ HITL Check  │────▶│  Response   │
│ Message │     │ Process │     │             │     │             │
└─────────┘     └─────────┘     └─────────────┘     └─────────────┘
                                      │
                                      │ needs_hitl = true
                                      ▼
                               ┌─────────────┐
                               │ Generate    │
                               │ Form Schema │
                               └─────────────┘
                                      │
                                      ▼
                               ┌─────────────┐
                               │  SSE Event  │
                               │ type: hitl  │
                               └─────────────┘
                                      │
                                      ▼
                               ┌─────────────┐
                               │  Frontend   │
                               │ Render Form │
                               └─────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
             ┌──────────┐      ┌──────────┐      ┌──────────┐
             │ Approve  │      │   Edit   │      │  Reject  │
             │          │      │          │      │          │
             └──────────┘      └──────────┘      └──────────┘
                    │                 │                 │
                    ▼                 ▼                 ▼
             ┌─────────────────────────────────────────────┐
             │              POST /hitl/respond             │
             │  {request_id, action, data}                 │
             └─────────────────────────────────────────────┘
                                      │
                                      ▼
                               ┌─────────────┐
                               │ Continue    │
                               │ AI Process  │
                               └─────────────┘
```

### Decision 4: API 设计

#### SSE 事件类型扩展

在现有 SSE 事件基础上增加 `hitl` 类型：

```javascript
event: hitl
data: {"type": "hitl", "payload": {"request": <FormSchema>}}
```

#### HITL 响应端点

```
POST /hitl/respond
Content-Type: application/json

{
  "request_id": "uuid",
  "session_id": "uuid",
  "action": "approve" | "edit" | "reject",
  "data": {
    "sport": "basketball",
    "frequency": "weekly",
    "notes": "周末打球"
  }
}

Response:
{
  "success": true,
  "next_action": "continue" | "complete",
  "message": "偏好已保存"
}
```

### Decision 5: AI Prompt 扩展

在 `chat_processor.py` 的 prompt 模板中增加 HITL 请求能力：

```python
HITL_INSTRUCTION = """
当你需要向用户收集信息或确认操作时，可以在 JSON 响应中包含 hitl_request 字段。

示例：询问用户喜欢的运动
{
  "response": "让我了解一下您的运动偏好",
  "hitl_request": {
    "type": "form",
    "title": "运动偏好",
    "fields": [
      {"name": "sport", "type": "select", "label": "喜欢的运动", "options": [...]}
    ]
  }
}

仅在以下情况使用 hitl_request:
1. 需要收集用户偏好或个人信息
2. 执行重要操作前需要确认
3. 存在多个选项需要用户选择
"""
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| AI 生成无效 Schema | 前端进行 Schema 验证，无效时降级为文本显示 |
| 用户体验中断感 | 表单设计简洁，提供快速操作按钮 |
| 请求超时处理 | 设置 HITL 请求 TTL，超时自动取消 |
| 表单复杂度失控 | 限制单个表单最多 5 个字段 |

## Migration Plan

1. 后端增加 HITL 处理模块，不影响现有 `/chat` 端点
2. 前端增加 HITL 表单组件，集成到聊天界面
3. 渐进式启用：通过环境变量控制 HITL 功能开关
4. 回滚：禁用 HITL 功能即可恢复原有行为

## Open Questions

1. ~~是否需要支持表单字段的条件显示逻辑？~~ → 初版不支持，保持简单
2. HITL 请求的超时时间设置为多少合适？建议 5 分钟
