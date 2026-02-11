import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { ExecutionDetail } from './execution-detail';
import type { ExecutionTimelineItem } from '@/types/execution';

interface ExecutionTimelineProps {
  items: ExecutionTimelineItem[];
}

function statusVariant(status: string): 'blue' | 'green' | 'orange' | 'destructive' | 'secondary' {
  switch (status) {
    case '进行中': return 'blue';
    case '已完成': return 'green';
    case '需要关注': return 'orange';
    case '出了问题': return 'destructive';
    case '已拒绝':
    case '已停止': return 'secondary';
    default: return 'secondary';
  }
}

export function ExecutionTimeline({ items }: ExecutionTimelineProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  const toggleExpand = (index: number) => {
    setExpandedIndex(prev => prev === index ? null : index);
  };

  return (
    <div className="space-y-1">
      {items.map((item, index) => (
        <div key={index} className="border border-slate-200 rounded-md bg-white overflow-hidden">
          <button
            type="button"
            className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-slate-50 transition-colors"
            onClick={() => toggleExpand(index)}
          >
            <span className="flex-1 text-sm truncate">{item.行动}</span>
            <Badge variant={statusVariant(item.状态)}>{item.状态}</Badge>
            {item.是否不可逆 && (
              <Badge variant="orange">不可撤销</Badge>
            )}
            <span className="text-xs text-slate-400">{expandedIndex === index ? '收起' : '详情'}</span>
          </button>
          {expandedIndex === index && <ExecutionDetail item={item} />}
        </div>
      ))}
    </div>
  );
}
