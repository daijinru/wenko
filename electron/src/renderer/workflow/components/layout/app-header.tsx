import { cn } from "@/lib/utils"

interface AppHeaderProps {
  title: string
  online: boolean
  checking: boolean
}

export function AppHeader({ title, online, checking }: AppHeaderProps) {
  return (
    <header className="window-draggable border-b border-border !p-[6px] !mb-[6px] flex justify-between items-center">
      <h1 className="flex-1 text-center text-xs font-bold">{title}</h1>
      <div className="flex items-center gap-1.5 window-not-draggable">
        <span
          className={cn(
            "w-2 h-2 rounded-full border",
            online
              ? "bg-green-500 border-green-600"
              : "bg-red-500 border-red-600"
          )}
        />
        <span className="text-[10px]">
          {checking ? "检查中..." : online ? "在线" : "离线"}
        </span>
      </div>
    </header>
  )
}
