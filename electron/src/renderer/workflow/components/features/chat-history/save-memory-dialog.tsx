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
import { Badge } from "@/components/ui/badge"
import { Spinner } from "@/components/ui/spinner"
import { api, ApiError } from "@/lib/api-client"
import { useToast } from "@/hooks/use-toast"
import { formatTime } from "@/lib/utils"
import type {
  ChatMessage,
  MemoryCategory,
  CreateMemoryRequest,
  MemoryExtractRequest,
  MemoryExtractResponse,
} from "@/types/api"

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
  const [extracting, setExtracting] = useState(false)
  const [form, setForm] = useState({
    category: "fact" as MemoryCategory,
    key: "",
    value: "",
    confidence: 80,
  })

  // Auto-extract when dialog opens
  useEffect(() => {
    if (open && message) {
      extractMemory()
    }
  }, [open, message])

  const extractMemory = async () => {
    if (!message) return

    setExtracting(true)
    try {
      const request: MemoryExtractRequest = {
        content: message.content,
        role: message.role,
      }
      const result = await api.post<MemoryExtractResponse>(
        "/memory/extract",
        request
      )

      // Update form with extracted data
      setForm({
        category: result.category,
        key: result.key,
        value: result.value,
        confidence: Math.round(result.confidence * 100),
      })
    } catch (error) {
      // On extraction failure, use default values
      setForm({
        category: "fact",
        key: message.role === "user" ? "用户输入" : "AI回复",
        value: message.content,
        confidence: 80,
      })
    } finally {
      setExtracting(false)
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
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>保存消息到长期记忆</DialogTitle>
        </DialogHeader>

        {extracting ? (
          <div className="p-8 flex flex-col items-center justify-center gap-3">
            <Spinner />
            <span className="text-sm text-muted-foreground">
              智能提取中...
            </span>
          </div>
        ) : (
          <div className="p-4 space-y-4">
            {message && (
              <div className="flex flex-row justify-between items-center p-2 bg-muted rounded text-[12px]">
                <Badge
                  variant={message.role === "user" ? "blue" : "green"}
                  className="text-[12px] !mr-1"
                >
                  {message.role === "user" ? "用户消息" : "AI回复"}
                </Badge>
                <span className="text-[12px] text-muted-foreground ml-2">
                  {formatTime(message.created_at)}
                </span>
              </div>
            )}

            <div className="space-y-2 !mt-1">
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
                placeholder="例如: 用户偏好, 重要事实"
              />
            </div>

            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <label className="text-xs font-bold">值 (Value)</label>
                {message && form.value !== message.content && (
                  <Button
                    variant="link"
                    size="sm"
                    className="text-[10px] p-0 h-auto"
                    onClick={() =>
                      setForm((f) => ({ ...f, value: message.content }))
                    }
                  >
                    使用原文
                  </Button>
                )}
              </div>
              <Textarea
                value={form.value}
                onChange={(e) =>
                  setForm((f) => ({ ...f, value: e.target.value }))
                }
                rows={8}
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
        )}

        <DialogFooter className="!mt-4 !mb-1 !mr-1 flex gap-1">
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={handleSave} disabled={saving || extracting}>
            {saving ? "保存中..." : "保存"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
