# Design: enhance-context-variable-display

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Workflow Window                               │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Memory List Table                                             │  │
│  │  ┌─────────┬──────────┬────────┬────────┬───────────────────┐ │  │
│  │  │ Expand  │ 会话/话题 │  状态  │  时间  │      操作         │ │  │
│  │  ├─────────┼──────────┼────────┼────────┼───────────────────┤ │  │
│  │  │   ▶     │ abc123   │ happy  │ 10:30  │ 保存 清除 [上下文]│ │  │
│  │  └─────────┴──────────┴────────┴────────┴───────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│                              ▼ Click "上下文"                        │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Context Variable Dialog                                       │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │  Key         │  Type    │  Preview            │ 操作    │  │  │
│  │  ├─────────────────────────────────────────────────────────┤  │  │
│  │  │  hitl_form   │  object  │  { "name": "test".. │ [replay]│  │  │
│  │  │  user_prefs  │  object  │  { "theme": "dark"} │ [replay]│  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  │  [关闭]                                                        │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ Click "replay"
┌─────────────────────────────────────────────────────────────────────┐
│              HITL Window (Readonly Mode)                             │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Title: hitl_form                                              │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │  name:   [test      ] (readonly)                         │  │  │
│  │  │  value:  [123       ] (readonly)                         │  │  │
│  │  │  ...                                                     │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  │                                              [关闭]            │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Design

### 1. Memory List Button Enhancement

**File**: `memory-list.tsx`

修改操作单元格，添加上下文变量按钮：

```tsx
<td className="p-2 border-b border-border text-center">
  <div className="flex justify-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
    <Button size="sm" variant="ghost" onClick={...}>保存</Button>
    <Button size="sm" variant="destructive" onClick={...}>清除</Button>
    {/* 新增：上下文变量按钮 */}
    {Object.keys(wm.context_variables || {}).length > 0 && (
      <Button size="sm" variant="outline" onClick={() => onShowContextDialog(wm)}>
        上下文
      </Button>
    )}
  </div>
</td>
```

### 2. Context Variable Dialog

**File**: `context-variable-dialog.tsx`

使用 shadcn/ui Dialog 组件，展示 Table 列表：

```tsx
interface ContextVariableDialogProps {
  open: boolean
  memory: WorkingMemory | null
  onOpenChange: (open: boolean) => void
  onReplay: (key: string, value: unknown) => void
}

export function ContextVariableDialog({
  open,
  memory,
  onOpenChange,
  onReplay
}: ContextVariableDialogProps) {
  const contextVars = memory?.context_variables || {}
  const entries = Object.entries(contextVars)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>上下文变量</DialogTitle>
        </DialogHeader>

        {entries.length === 0 ? (
          <div>无上下文变量</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>键名</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>预览</TableHead>
                <TableHead className="w-20">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entries.map(([key, value]) => (
                <TableRow key={key}>
                  <TableCell className="font-mono">{key}</TableCell>
                  <TableCell>{typeof value}</TableCell>
                  <TableCell className="truncate max-w-[200px]">
                    {JSON.stringify(value).substring(0, 50)}...
                  </TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => onReplay(key, value)}
                    >
                      replay
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            关闭
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

### 3. HITL Window Readonly Mode

**File**: `hitl.ts` - 添加只读模式支持

```typescript
export interface HITLRequest {
  id: string;
  type: string;
  title: string;
  description?: string;
  fields: HITLField[];
  actions?: HITLActions;
  session_id: string;
  ttl_seconds?: number;
  readonly?: boolean;  // 新增：只读模式标识
}
```

**File**: `App.tsx` - 处理只读模式

```tsx
// 只读模式下，所有字段禁用，仅显示关闭按钮
{request.readonly ? (
  <div className="flex justify-end">
    <Button onClick={() => window.electronAPI.invoke('hitl:cancel')}>
      关闭
    </Button>
  </div>
) : (
  <HITLActions ... />
)}
```

**File**: `hitl-field.tsx` - 只读字段渲染

```tsx
// 根据 readonly 属性禁用所有输入
<input
  disabled={readonly}
  className={cn(readonly && 'opacity-75 cursor-not-allowed')}
  ...
/>
```

### 4. Electron Main Process Changes

**File**: `main.cjs`

复用现有 HITL 窗口，支持只读模式：

```javascript
// 修改 hitl:open-window handler，支持 readonly 模式
ipcMain.handle('hitl:open-window', async (event, data) => {
  console.log('[HITL] Opening window:', data.request?.title, 'readonly:', data.request?.readonly);

  const { request, sessionId } = data;
  currentHITLRequest = { request, sessionId };

  createHITLWindow(request);

  // 只读模式不设置超时
  if (!request.readonly) {
    const ttlSeconds = request.ttl_seconds || 300;
    setupHITLTimeout(ttlSeconds);
  }

  return { success: true };
});
```

### 5. IPC Call from Workflow

**File**: `context-variable-dialog.tsx` 或 parent component

```typescript
async function handleReplay(key: string, value: unknown) {
  // 将 value 转换为 HITL fields
  const fields = convertToHITLFields(key, value);

  await window.electronAPI.invoke('hitl:open-window', {
    request: {
      id: `context-replay-${Date.now()}`,
      type: 'context-replay',
      title: key,
      fields: fields,
      readonly: true,  // 只读模式
      session_id: memory.session_id,
    },
    sessionId: memory.session_id,
  });
}

function convertToHITLFields(key: string, value: unknown): HITLField[] {
  if (typeof value !== 'object' || value === null) {
    return [{
      name: key,
      type: 'textarea',
      label: key,
      default: JSON.stringify(value, null, 2),
    }];
  }

  // 对象类型：每个属性转为一个字段
  return Object.entries(value).map(([k, v]) => ({
    name: k,
    type: typeof v === 'string' && v.length > 50 ? 'textarea' : 'text',
    label: k,
    default: typeof v === 'object' ? JSON.stringify(v, null, 2) : String(v),
  }));
}
```

## Data Flow

```
1. User clicks "上下文" button in memory-list
   ↓
2. ContextVariableDialog opens with memory data
   ↓
3. Dialog displays Table with all context variables
   ↓
4. User clicks "replay" button on a row
   ↓
5. IPC call: hitl:open-window with { request: { readonly: true, fields: [...] } }
   ↓
6. Main process creates/focuses HITL window
   ↓
7. HITL window renders in readonly mode with only "关闭" button
```

## UI/UX Considerations

1. **按钮可见性**：仅当 context_variables 非空时显示按钮
2. **对话框大小**：使用 `max-w-2xl` 以容纳 Table
3. **只读模式**：字段灰显，无法编辑，仅显示关闭按钮
4. **主题一致**：复用 HITL 窗口的 classic-stylesheets 主题
5. **表格预览**：长内容使用 truncate，完整内容通过 replay 查看

## Error Handling

1. **空数据**：显示"无上下文变量"提示
2. **IPC 失败**：显示错误提示
3. **字段转换**：安全处理各种数据类型
