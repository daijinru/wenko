import { useState } from "react"
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
import { Badge } from "@/components/ui/badge"
import { api, ApiError } from "@/lib/api-client"
import { useToast } from "@/hooks/use-toast"
import { formatTime } from "@/lib/utils"
import type { ChatMessage, MemoryCategory, CreateMemoryRequest } from "@/types/api"

interface SaveMemoryDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  message: ChatMessage | null
}

const CATEGORIES: { value: MemoryCategory; label: string }[] = [
  { value: "preference", label: "偏好" },
  { value: "fact", label: "事实" },
  { value: "pattern", label: "模式" },
]

export function SaveMemoryDialog({
  open,
  onOpenChange,
  message,
}: SaveMemoryDialogProps) {
  const { toast } = useToast()
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    category: "fact" as MemoryCategory,
    key: "",
    value: "",
    confidence: 80,
  })

  // Reset form when message changes
  const resetForm = () => {
    if (message) {
      setForm({
        category: "fact",
        key: message.role === "user" ? "用户输入" : "AI回复",
        value: message.content,
        confidence: 80,
      })
    }
  }

  const handleSave = async () => {
    if (!form.key.trim()) {
      toast.error("请输入记忆键名")
      return
    }

    setSaving(true)
    try {
      const request: CreateMemoryRequest = {
        category: form.category,
        key: form.key,
        value: form.value,
        confidence: form.confidence / 100,
        source: "user_stated",
      }
      await api.post("/memory/long-term", request)
      toast.success("消息已保存到长期记忆")
      onOpenChange(false)
    } catch (error) {
      const msg = error instanceof ApiError ? error.message : "保存失败"
      toast.error(msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(newOpen) => {
        if (newOpen) resetForm()
        onOpenChange(newOpen)
      }}
    >
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>保存消息到长期记忆</DialogTitle>
        </DialogHeader>

        <div className="p-4 space-y-4">
          {message && (
            <div className="p-2 bg-muted rounded text-xs">
              <Badge variant={message.role === "user" ? "blue" : "green"}>
                {message.role === "user" ? "用户消息" : "AI回复"}
              </Badge>
              <span className="text-[10px] text-muted-foreground ml-2">
                {formatTime(message.created_at)}
              </span>
            </div>
          )}

          <div className="space-y-2">
            <label className="text-xs font-bold">类别</label>
            <div className="flex gap-1">
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
              placeholder="例如: 用户偏好, 重要事实"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold">值 (Value)</label>
            <Textarea
              value={form.value}
              onChange={(e) => setForm((f) => ({ ...f, value: e.target.value }))}
              rows={4}
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold">
              置信度: {form.confidence}%
            </label>
            <Slider
              value={[form.confidence]}
              onValueChange={([value]) =>
                setForm((f) => ({ ...f, confidence: value }))
              }
              min={0}
              max={100}
              step={1}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "保存中..." : "保存"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
