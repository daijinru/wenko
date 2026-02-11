import type { ExecutionTimelineItem } from '@/types/execution';

interface ExecutionDetailProps {
  item: ExecutionTimelineItem;
}

export function ExecutionDetail({ item }: ExecutionDetailProps) {
  return (
    <div className="pl-4 pr-2 py-2 bg-slate-50 border-t border-slate-100 text-sm space-y-1.5">
      {item.结果 && (
        <div>
          <span className="text-slate-500">结果：</span>
          <span>{item.结果}</span>
        </div>
      )}
      {item.错误 && (
        <div className="text-red-600">
          <span className="text-red-500">问题：</span>
          <span>{item.错误}</span>
        </div>
      )}
      {item.是否不可逆 && (
        <div className="text-amber-700 text-xs">
          此操作已生效，无法撤销。
        </div>
      )}
      {!item.结果 && !item.错误 && !item.是否不可逆 && (
        <div className="text-slate-400 text-xs">暂无详细信息</div>
      )}
    </div>
  );
}
