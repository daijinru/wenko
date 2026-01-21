import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import type { WorkingMemory } from "@/types/api"
import type { HITLField } from "@hitl/types/hitl"

interface ContextVariableDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  memory: WorkingMemory | null
}

// Context variable value structure (from backend hitl_handler.py)
interface HITLContextValue {
  fields: Record<string, unknown>  // labeled data (label -> value)
  fields_def?: HITLField[]  // original field definitions
  form_data?: Record<string, unknown>  // original form data (field_name -> value)
  timestamp: string
}

/**
 * Check if value is a HITL context value with fields_def
 */
function isHITLContextValue(value: unknown): value is HITLContextValue {
  return (
    typeof value === 'object' &&
    value !== null &&
    'fields' in value &&
    'timestamp' in value
  )
}

/**
 * Build HITL fields for replay with proper types and values
 */
function buildReplayFields(key: string, value: unknown): HITLField[] {
  // Check if this is a HITL context value with fields_def
  if (isHITLContextValue(value) && value.fields_def && value.form_data) {
    // Use original field definitions with form values
    return value.fields_def.map((fieldDef) => ({
      ...fieldDef,
      // Use form_data value as default for replay
      default: value.form_data?.[fieldDef.name] ?? fieldDef.default,
    }))
  }

  // Fallback: convert to simple fields (for legacy data or non-HITL context)
  if (isHITLContextValue(value)) {
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
  // Remove "hitl_" prefix if present for cleaner title
  if (key.startsWith('hitl_')) {
    return key.substring(5)
  }
  return key
}

/**
 * Open HITL window in readonly mode to display context variable details
 */
async function handleReplay(key: string, value: unknown, sessionId: string) {
  const fields = buildReplayFields(key, value)
  const title = getReplayTitle(key)

  await window.electronAPI.invoke('hitl:open-window', {
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
  if (isHITLContextValue(value)) {
    const fieldCount = value.fields_def?.length ?? Object.keys(value.fields).length
    return {
      type: 'hitl',
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
          <DialogTitle>上下文变量</DialogTitle>
        </DialogHeader>

        <div className="p-4">
          {entries.length === 0 ? (
            <div className="text-xs text-muted-foreground text-center py-4">
              无上下文变量
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
                    const displayKey = key.startsWith('hitl_') ? key.substring(5) : key

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
                            replay
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
