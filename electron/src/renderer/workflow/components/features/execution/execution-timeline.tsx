import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
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

const TEXT_KEYS = ['text', 'content', 'message', 'result', 'output', 'data', 'body'];

/** Try to extract human-readable text segments from a parsed JSON value. */
function extractTexts(obj: unknown): string[] {
  if (typeof obj === 'string') return [obj];
  if (Array.isArray(obj)) return obj.flatMap(extractTexts);
  if (obj && typeof obj === 'object') {
    const texts: string[] = [];
    for (const key of TEXT_KEYS) {
      if (key in obj) {
        texts.push(...extractTexts((obj as Record<string, unknown>)[key]));
      }
    }
    return texts;
  }
  return [];
}

interface ParsedResult {
  texts: string[];
  json: object | null;
  raw: string;
}

function parseResult(raw: string): ParsedResult {
  try {
    const parsed = JSON.parse(raw);
    const texts = extractTexts(parsed);
    return { texts, json: parsed, raw };
  } catch {
    return { texts: [], json: null, raw };
  }
}

function ResultBlock({ value }: { value: string }) {
  const [showRaw, setShowRaw] = useState(false);
  const { texts, json } = parseResult(value);

  if (!json) {
    return (
      <div className="text-[11px] leading-relaxed whitespace-pre-wrap break-words border-classic-inset bg-card !p-1">
        {value}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {texts.length > 0 ? (
        <div className="text-[11px] leading-relaxed whitespace-pre-wrap break-words border-classic-inset bg-card !p-1">
          {texts.join('\n\n')}
        </div>
      ) : (
        <div className="text-[11px] text-muted-foreground">（无可读文本）</div>
      )}
      <button
        type="button"
        className="text-[10px] text-blue-600 hover:underline"
        onClick={() => setShowRaw(prev => !prev)}
      >
        {showRaw ? '收起 JSON' : '查看原始 JSON'}
      </button>
      {showRaw && (
        <pre className="text-[11px] leading-relaxed overflow-auto max-h-[40vh] !p-1 whitespace-pre-wrap break-words border-classic-inset bg-card font-mono">
          {JSON.stringify(json, null, 2)}
        </pre>
      )}
    </div>
  );
}

export function ExecutionTimeline({ items }: ExecutionTimelineProps) {
  const [detailItem, setDetailItem] = useState<ExecutionTimelineItem | null>(null);

  const openDetail = (e: React.MouseEvent, item: ExecutionTimelineItem) => {
    e.stopPropagation();
    setDetailItem(item);
  };

  return (
    <>
      <table className="detailed w-full text-sm border-collapse table-fixed">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50 text-slate-500 text-xs">
            <th className="text-left font-medium px-3 py-2 w-[40%]">行动</th>
            <th className="text-left font-medium px-3 py-2 w-[80px]">状态</th>
            <th className="text-left font-medium px-3 py-2 w-[80px]">标记</th>
            <th className="text-left font-medium px-3 py-2">结果</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => (
            <tr
              key={index}
              className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
            >
              <td className="px-3 py-2 align-middle">
                <span className="block break-words">{item.行动}</span>
              </td>
              <td className="px-3 py-2 align-middle">
                <Badge variant={statusVariant(item.状态)}>{item.状态}</Badge>
              </td>
              <td className="px-3 py-2 align-middle">
                <div className="flex gap-1 flex-wrap items-center">
                  {item.是否不可逆 && <Badge variant="orange">不可撤销</Badge>}
                  {item.是否已结束 && <Badge variant="green">已结束</Badge>}
                </div>
              </td>
              <td className="px-3 py-2 align-middle text-slate-600">
                {(item.结果 || item.错误) ? (
                  <button
                    type="button"
                    className="text-xs text-blue-600 hover:text-blue-800 hover:underline cursor-pointer"
                    onClick={(e) => openDetail(e, item)}
                  >
                    查看详情
                  </button>
                ) : (
                  <span className="text-slate-400 text-xs">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <Dialog open={!!detailItem} onOpenChange={(open) => !open && setDetailItem(null)}>
        <DialogContent className="sm:max-w-[600px] max-h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>{detailItem?.行动 ?? '详情'}</DialogTitle>
          </DialogHeader>

          <div className="flex-1 min-h-0 overflow-auto space-y-2 p-2">
            <div className="flex items-center gap-2 text-xs">
              <span className="text-muted-foreground">状态：</span>
              <Badge variant={statusVariant(detailItem?.状态 ?? '')}>{detailItem?.状态}</Badge>
              {detailItem?.是否不可逆 && <Badge variant="orange">不可撤销</Badge>}
              {detailItem?.是否已结束 && <Badge variant="green">已结束</Badge>}
            </div>

            {detailItem?.结果 && (
              <div>
                <div className="text-[11px] font-bold text-muted-foreground mb-1">结果</div>
                <ResultBlock value={detailItem.结果} />
              </div>
            )}

            {detailItem?.错误 && (
              <div>
                <div className="text-[11px] font-bold text-red-600 mb-1">错误</div>
                <pre className="text-[11px] leading-relaxed overflow-auto max-h-[30vh] p-2 whitespace-pre-wrap break-words border-classic-inset bg-red-50 text-red-700 font-mono">
                  {detailItem.错误}
                </pre>
              </div>
            )}

            {detailItem?.是否不可逆 && (
              <div className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 p-2">
                此操作已生效，无法撤销。
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
