import { useState, useEffect } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Slider } from "@/components/ui/slider"
import type { LongTermMemory, MemoryCategory, MemoryFormData } from "@/types/api"

interface MemoryFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  memory: LongTermMemory | null
  onSave: (data: MemoryFormData) => Promise<boolean>
}

const CATEGORIES: { value: MemoryCategory; label: string }[] = [
  { value: "preference", label: "偏好" },
  { value: "fact", label: "事实" },
  { value: "pattern", label: "模式" },
]

export function MemoryFormDialog({
  open,
  onOpenChange,
  memory,
  onSave,
}: MemoryFormDialogProps) {
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState<MemoryFormData>({
    category: "fact",
    key: "",
    value: "",
    confidence: 0.9,
  })

  useEffect(() => {
    if (open) {
      if (memory) {
        setForm({
          category: memory.category,
          key: memory.key,
          value:
            typeof memory.value === "object"
              ? JSON.stringify(memory.value)
              : memory.value,
          confidence: memory.confidence,
        })
      } else {
        setForm({
          category: "fact",
          key: "",
          value: "",
          confidence: 0.9,
        })
      }
    }
  }, [open, memory])

  const handleSave = async () => {
    if (!form.key.trim()) {
      return
    }

    setSaving(true)
    const success = await onSave(form)
    setSaving(false)

    if (success) {
      onOpenChange(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{memory ? "编辑记忆" : "添加记忆"}</DialogTitle>
        </DialogHeader>

        <div className="p-4 space-y-4">
          <div className="space-y-2">
            <label className="text-xs font-bold">类别</label>
            <div className="flex gap-1 !mt-1 !mb-1">
              {CATEGORIES.map((cat) => (
                <Button
                  key={cat.value}
                  variant={form.category === cat.value ? "default" : "secondary"}
                  size="sm"
                  onClick={() => setForm((f) => ({ ...f, category: cat.value }))}
                >
                  {cat.label}
                </Button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold">键名 (Key)</label>
            <Input
              value={form.key}
              onChange={(e) => setForm((f) => ({ ...f, key: e.target.value }))}
              placeholder="例如: preferred_language, name"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold">值 (Value)</label>
            <Textarea
              value={form.value}
              onChange={(e) => setForm((f) => ({ ...f, value: e.target.value }))}
              placeholder="输入记忆内容"
              rows={8}
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold">
              置信度: {Math.round(form.confidence * 100)}%
            </label>
            <Slider
              value={[form.confidence * 100]}
              onValueChange={([value]) =>
                setForm((f) => ({ ...f, confidence: value / 100 }))
              }
              min={0}
              max={100}
              step={1}
            />
          </div>
        </div>

        <DialogFooter className="!mt-4 !mb-1 !mr-1 flex gap-1">
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={handleSave} disabled={saving || !form.key.trim()}>
            {saving ? "保存中..." : "保存"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
