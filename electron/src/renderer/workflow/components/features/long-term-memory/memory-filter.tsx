import { cn } from "@/lib/utils"
import type { MemoryCategory } from "@/types/api"

interface MemoryFilterProps {
  currentFilter: MemoryCategory | ""
  total: number
  onFilterChange: (category: MemoryCategory | "") => void
}

const FILTERS: { key: MemoryCategory | ""; label: string }[] = [
  { key: "", label: "全部" },
  { key: "preference", label: "偏好" },
  { key: "fact", label: "事实" },
  { key: "pattern", label: "模式" },
]

export function MemoryFilter({
  currentFilter,
  total,
  onFilterChange,
}: MemoryFilterProps) {
  return (
    <div className="flex items-center gap-2 p-2 bg-secondary border-classic-inset !p-1">
      <span className="text-[11px] font-bold">类别:</span>
      <div className="flex gap-0.5">
        {FILTERS.map((item) => (
          <button
            key={item.key}
            className={cn(
              "px-2 py-0.5 text-[11px] border border-border cursor-pointer transition-colors",
              currentFilter === item.key
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-secondary hover:bg-accent"
            )}
            onClick={() => onFilterChange(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <span className="ml-auto text-[11px] text-muted-foreground">
        共 {total} 条记忆
      </span>
    </div>
  )
}
