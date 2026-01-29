## Context

当前 HITL 系统设计为表单收集器（form collector），主要用于从用户处获取信息。本变更扩展 HITL 的用途，使其成为双向通信机制：

1. **Form Mode**（现有）：AI 向用户收集输入
2. **Visual Display Mode**（新增）：AI 向用户展示结构化视觉内容

这种设计复用现有的 HITL 弹窗基础设施（IPC 通信、窗口管理），同时通过 `request.type` 区分两种模式。

## Goals / Non-Goals

### Goals
- 为 AI 提供图形化表达能力
- 复用现有 HITL 弹窗架构，减少代码重复
- 第一期实现 table 和 ascii 两种基础组件
- 保持良好的扩展性，便于后续添加更多组件类型

### Non-Goals
- 不实现交互式组件（如可编辑表格）
- 不实现复杂的图表库集成
- 不实现 SVG/Canvas/HTML 渲染（留给后续迭代）
- 不改变现有 Form Mode 的行为

## Decisions

### 1. 通过 request.type 区分模式

**决策**: 使用 `request.type` 字段区分 `"form"` 和 `"visual_display"` 两种模式。

**理由**:
- 现有 HITLRequest 已有 type 字段，默认为 "form"
- 复用现有的 IPC 通道和窗口管理逻辑
- 前端可根据 type 决定渲染逻辑

**备选方案**:
- 创建完全独立的 Display 通道：增加代码复杂度，维护成本高

### 2. 新增 HITLDisplayRequest Schema

**决策**: 创建独立的 `HITLDisplayRequest` 模型，与 `HITLRequest` 区分。

**理由**:
- Display 请求不需要 fields（表单字段）定义
- Display 请求不需要 actions（approve/edit/reject）
- 类型清晰，避免字段混淆

**Schema 设计**:
```python
class HITLDisplayRequest(BaseModel):
    id: str
    type: Literal["visual_display"] = "visual_display"
    title: str
    description: Optional[str] = None
    displays: List[HITLDisplayField]  # table 或 ascii 组件
    dismiss_label: str = "关闭"  # 关闭按钮文案
```

### 3. Display Field 类型设计

**决策**: 使用联合类型表示不同的展示组件。

```python
class HITLDisplayType(str, Enum):
    TABLE = "table"
    ASCII = "ascii"

class HITLTableData(BaseModel):
    headers: List[str]
    rows: List[List[str]]
    alignment: Optional[List[str]] = None  # "left" | "center" | "right"
    caption: Optional[str] = None

class HITLAsciiData(BaseModel):
    content: str  # Pre-formatted ASCII art
    title: Optional[str] = None

class HITLDisplayField(BaseModel):
    type: HITLDisplayType
    data: Union[HITLTableData, HITLAsciiData]
```

### 4. 前端组件架构

```
hitl/
├── components/
│   ├── hitl-form.tsx           # 现有：表单容器
│   ├── hitl-field.tsx          # 现有：表单字段
│   ├── hitl-actions.tsx        # 现有：表单操作按钮
│   ├── hitl-display.tsx        # 新增：Visual Display 容器
│   ├── hitl-display-field.tsx  # 新增：Display 字段路由
│   ├── hitl-table.tsx          # 新增：Table 组件
│   ├── hitl-ascii.tsx          # 新增：ASCII 组件
│   └── hitl-display-actions.tsx # 新增：简化的关闭按钮
```

**App.tsx 路由逻辑**:
```tsx
if (request.type === 'visual_display') {
  return <HITLDisplay request={request} onDismiss={handleDismiss} />;
} else {
  return <HITLForm request={request} ... />;
}
```

### 5. 工作记忆持久化与 Replay 支持

**决策**: Visual Display 数据与 Form 数据一样，需要持久化到工作记忆的上下文变量中，并支持从"上下文变量"对话框中 replay。

**理由**:
- 保持用户体验一致性：用户可以回顾 AI 之前展示的信息
- 会话上下文连续性：后续对话可以引用之前展示的数据
- 调试和审计：便于查看 AI 的输出历史

**存储结构**:
```python
# 存储到 context_variables 的数据结构
ctx_key = f"hitl_{request.title}"
updated_ctx[ctx_key] = {
    "type": "visual_display",  # 区分于 form 类型
    "displays": [              # 原始 display fields 数据
        {"type": "table", "data": {...}},
        {"type": "ascii", "data": {...}},
    ],
    "displays_def": [...],     # display fields 定义，用于 replay
    "timestamp": "2024-01-29T12:00:00",
}
```

**Replay 逻辑**:
```typescript
// context-variable-dialog.tsx
function handleReplay(key: string, value: unknown, sessionId: string) {
  if (isVisualDisplayContextValue(value)) {
    // Visual Display 类型：使用 visual_display 模式打开
    await window.electronAPI.invoke('hitl:open-window', {
      request: {
        id: `context-replay-${Date.now()}`,
        type: 'visual_display',
        title: getReplayTitle(key),
        displays: value.displays_def,
        readonly: true,
        session_id: sessionId,
      },
      sessionId: sessionId,
    });
  } else {
    // Form 类型：使用现有逻辑
    // ...
  }
}
```

## Risks / Trade-offs

### Risk 1: 弹窗尺寸适配

**风险**: 表格或 ASCII 内容可能很长，导致弹窗无法完全显示。

**缓解措施**:
- 使用 `overflow-auto` 支持滚动
- 设置 `max-height` 限制最大高度
- 考虑添加全屏按钮（可选，非第一期）

### Risk 2: ASCII 渲染兼容性

**风险**: 不同系统的等宽字体可能导致 ASCII art 错位。

**缓解措施**:
- 使用明确的 `font-family: monospace` 样式
- 使用 `white-space: pre` 保留格式
- 推荐使用简单的 ASCII 艺术风格

### Risk 3: TypeScript 类型推断

**风险**: 联合类型 `HITLRequest | HITLDisplayRequest` 可能导致类型推断困难。

**缓解措施**:
- 使用 type guards 函数 `isDisplayRequest(request)`
- 在组件层面显式处理类型

## Open Questions

1. **是否需要 continuation**？Visual Display 弹窗关闭后，是否需要像 Form 一样触发 AI continuation？
   - 建议：简单的 dismiss 行为，不触发 continuation，因为这是单向信息展示

2. **是否支持多个 display fields**？一个弹窗是否可以同时显示多个 table 和 ascii？
   - 建议：支持，`displays` 为数组，可以顺序展示多个组件

3. **窗口尺寸如何确定**？
   - 建议：第一期使用固定尺寸 + 滚动，后续可以根据内容自适应
