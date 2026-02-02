import { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useLogs } from '@/hooks/use-logs';
import { LogViewer } from './log-viewer';

interface ConfirmDialogState {
  open: boolean;
  title: string;
  content: string;
  onConfirm: () => void;
}

interface LogsTabProps {
  onConfirmDialog: (state: ConfirmDialogState) => void;
}

export function LogsTab({ onConfirmDialog: _onConfirmDialog }: LogsTabProps) {
  const {
    files,
    selectedDate,
    lines,
    total,
    hasMore,
    order,
    loading,
    loadingContent,
    error,
    selectDate,
    toggleOrder,
    loadMore,
    refresh,
    loadFiles,
  } = useLogs();

  const [keyword, setKeyword] = useState('');

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const filteredLines = useMemo(() => {
    return lines;
  }, [lines]);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-muted-foreground">加载日志文件列表...</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Controls - 工具栏 */}
      <div className="flex gap-2 flex-wrap items-center !p-1 bg-slate-50 border border-slate-200 rounded-lg shadow-sm">
        {/* 操作按钮组 */}
        <div className="flex gap-1.5 items-center border-r border-slate-300 pr-3 mr-1">
          <Button size="sm" onClick={loadFiles} disabled={loading} className="!h-3">
            刷新列表
          </Button>
          <Button size="sm" onClick={refresh} disabled={loadingContent || !selectedDate} className="!h-3">
            刷新内容
          </Button>
        </div>

        {/* 排序控制 */}
        <Button
          size="sm"
          variant="outline"
          onClick={toggleOrder}
          disabled={loadingContent || !selectedDate}
          className="!h-3 min-w-[80px]"
        >
          {order === 'desc' ? '倒序 ↓' : '正序 ↑'}
        </Button>

        {/* Date Selector - 日期选择 */}
        <select
          className="!h-3 px-3 border border-slate-300 rounded-md text-sm bg-white hover:border-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors min-w-[180px]"
          value={selectedDate || ''}
          onChange={(e) => selectDate(e.target.value)}
          disabled={files.length === 0}
        >
          {files.length === 0 ? (
            <option value="">无可用日志</option>
          ) : (
            files.map((file) => (
              <option key={file.date} value={file.date}>
                {file.date} ({formatFileSize(file.size)})
              </option>
            ))
          )}
        </select>

        {/* Keyword Input - 关键字搜索 */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-slate-500">高亮:</span>
          <Input
            type="text"
            placeholder="输入关键字..."
            className="!h-3 w-44 border-slate-300 focus:ring-2 focus:ring-blue-500"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
          />
          {keyword && (
            <button
              onClick={() => setKeyword('')}
              className="!h-3 w-6 flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-200 rounded transition-colors"
              title="清除"
            >
              ×
            </button>
          )}
        </div>

        {/* Stats - 统计信息 */}
        {selectedDate && (
          <div className="ml-auto flex items-center gap-2 text-sm">
            <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded-md font-medium">
              {total} 行
            </span>
            {hasMore && (
              <span className="px-2 py-1 bg-amber-100 text-amber-700 rounded-md">
                已加载 {lines.length}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Error - 错误提示 */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm flex items-center gap-2">
          <span className="text-red-500">⚠</span>
          {error}
        </div>
      )}

      {/* Log Content - 日志内容区域 */}
      <div className="flex-1 min-h-0 border border-slate-200 rounded-lg shadow-sm overflow-hidden bg-white">
        {!selectedDate ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-2">
            <span className="text-4xl">📄</span>
            <span>暂无日志文件</span>
          </div>
        ) : loadingContent ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-2">
            <span className="animate-spin text-2xl">⏳</span>
            <span>加载日志内容...</span>
          </div>
        ) : filteredLines.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-2">
            <span className="text-4xl">📭</span>
            <span>日志为空</span>
          </div>
        ) : (
          <div className="h-full flex flex-col">
            <div className="flex-1 overflow-auto !p-1">
              <LogViewer lines={filteredLines} keyword={keyword} />
            </div>
            {hasMore && (
              <div className="p-3 border-t border-slate-200 bg-slate-50 text-center">
                <Button size="sm" variant="outline" onClick={loadMore} className="min-w-[120px]">
                  加载更多 ↓
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
