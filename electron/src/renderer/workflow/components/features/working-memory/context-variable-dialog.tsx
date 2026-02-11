import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import type { WorkingMemory } from "@/types/api"
import type { ECSField, ECSDisplayField } from "@ecs/types/ecs"

interface ContextVariableDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  memory: WorkingMemory | null
}

// Context variable value structure (from backend ecs_handler.py)
interface ECSContextValue {
  fields: Record<string, unknown>  // labeled data (label -> value)
  fields_def?: ECSField[]  // original field definitions
  form_data?: Record<string, unknown>  // original form data (field_name -> value)
  timestamp: string
}

// Visual Display context value structure
interface VisualDisplayContextValue {
  type: 'visual_display'
  displays: ECSDisplayField[]
  displays_def: ECSDisplayField[]
  timestamp: string
}

/**
 * Check if value is a Visual Display context value
 */
function isVisualDisplayContextValue(value: unknown): value is VisualDisplayContextValue {
  return (
    typeof value === 'object' &&
    value !== null &&
    'type' in value &&
    (value as Record<string, unknown>).type === 'visual_display' &&
    'displays_def' in value &&
    'timestamp' in value
  )
}

/**
 * Check if value is an ECS context value with fields_def
 */
function isECSContextValue(value: unknown): value is ECSContextValue {
  return (
    typeof value === 'object' &&
    value !== null &&
    'fields' in value &&
    'timestamp' in value &&
    !isVisualDisplayContextValue(value)
  )
}

/**
 * Build ECS fields for replay with proper types and values
 */
function buildReplayFields(key: string, value: unknown): ECSField[] {
  // Check if this is an ECS context value with fields_def
  if (isECSContextValue(value) && value.fields_def && value.form_data) {
    // Use original field definitions with form values
    return value.fields_def.map((fieldDef) => ({
      ...fieldDef,
      // Use form_data value as default for replay
      default: value.form_data?.[fieldDef.name] ?? fieldDef.default,
    }))
  }

  // Fallback: convert to simple fields (for legacy data or non-ECS context)
  if (isECSContextValue(value)) {
    // Has fields but no fields_def - use labeled data
    return Object.entries(value.fields).map(([label, val]) => ({
      name: label,
      type: (typeof val === 'string' && val.length > 50) ? 'textarea' as const : 'text' as const,
      label: label,
      default: typeof val === 'object' ? JSON.stringify(val, null, 2) : String(val ?? ''),
    }))
  }

  // Generic object - convert each property to a field
  if (typeof value === 'object' && value !== null) {
    return Object.entries(value as Record<string, unknown>).map(([k, v]) => ({
      name: k,
      type: (typeof v === 'string' && v.length > 50) ? 'textarea' as const : 'text' as const,
      label: k,
      default: typeof v === 'object' ? JSON.stringify(v, null, 2) : String(v ?? ''),
    }))
  }

  // Primitive value
  return [{
    name: key,
    type: 'textarea' as const,
    label: key,
    default: typeof value === 'string' ? value : JSON.stringify(value, null, 2),
  }]
}

/**
 * Get title for replay window
 */
function getReplayTitle(key: string): string {
  // Remove "ecs_" prefix if present for cleaner title
  if (key.startsWith('ecs_')) {
    return key.substring(4)
  }
  return key
}

/**
 * Open ECS window in readonly mode to display context variable details
 */
async function handleReplay(key: string, value: unknown, sessionId: string) {
  const title = getReplayTitle(key)

  // Check if this is a visual display type
  if (isVisualDisplayContextValue(value)) {
    await window.electronAPI.invoke('ecs:open-window', {
      request: {
        id: `context-replay-${Date.now()}`,
        type: 'visual_display',
        title: title,
        displays: value.displays_def,
        readonly: true,
        session_id: sessionId,
      },
      sessionId: sessionId,
    })
    return
  }

  // Form type replay
  const fields = buildReplayFields(key, value)

  await window.electronAPI.invoke('ecs:open-window', {
    request: {
      id: `context-replay-${Date.now()}`,
      type: 'context-replay',
      title: title,
      fields: fields,
      readonly: true,
      session_id: sessionId,
    },
    sessionId: sessionId,
  })
}

/**
 * Get display info for a context variable entry
 */
function getEntryDisplayInfo(_: string, value: unknown): { type: string; preview: string } {
  // Check for visual display type
  if (isVisualDisplayContextValue(value)) {
    const displayCount = value.displays_def?.length ?? 0
    return {
      type: 'visual_display',
      preview: `${displayCount} 个组件 (${value.timestamp.split('T')[0]})`,
    }
  }

  if (isECSContextValue(value)) {
    const fieldCount = value.fields_def?.length ?? Object.keys(value.fields).length
    return {
      type: 'ecs',
      preview: `${fieldCount} 个字段 (${value.timestamp.split('T')[0]})`,
    }
  }

  const preview = JSON.stringify(value)
  return {
    type: typeof value,
    preview: preview.length > 50 ? preview.substring(0, 50) + '...' : preview,
  }
}

export function ContextVariableDialog({
  open,
  onOpenChange,
  memory,
}: ContextVariableDialogProps) {
  const contextVars = memory?.context_variables || {}
  const entries = Object.entries(contextVars)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>采集数据</DialogTitle>
        </DialogHeader>

        <div className="p-4">
          {entries.length === 0 ? (
            <div className="text-xs text-muted-foreground text-center py-4">
              无采集数据
            </div>
          ) : (
            <div className="border-classic-inset bg-card overflow-y-auto max-h-[400px]">
              <table className="w-full text-xs border-collapse detailed">
                <thead className="bg-muted sticky top-0 z-10 font-bold text-muted-foreground">
                  <tr>
                    <th className="p-2 text-left border-b border-r border-border">键名</th>
                    <th className="p-2 text-left border-b border-r border-border w-20">类型</th>
                    <th className="p-2 text-left border-b border-r border-border">预览</th>
                    <th className="p-2 text-center border-b border-border w-20">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map(([key, value]) => {
                    const { type, preview } = getEntryDisplayInfo(key, value)
                    const displayKey = key.startsWith('ecs_') ? key.substring(4) : key

                    return (
                      <tr
                        key={key}
                        className="hover:bg-muted/50 transition-colors p-2"
                      >
                        <td className="p-2 border-b border-r border-border font-mono">
                          {displayKey}
                        </td>
                        <td className="p-2 border-b border-r border-border text-muted-foreground">
                          {type}
                        </td>
                        <td className="p-2 border-b border-r border-border truncate max-w-[200px]" title={preview}>
                          {preview}
                        </td>
                        <td className="p-2 border-b border-border text-center">
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-3 text-[10px] px-2"
                            onClick={() => handleReplay(key, value, memory?.session_id || '')}
                          >
                            回放
                          </Button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <DialogFooter className="!mt-2 !mb-1 !mr-1">
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            关闭
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
