import { useMemo, useState, useCallback, useEffect, useRef, useImperativeHandle, forwardRef } from 'react';

export interface LogViewerRef {
  selectedLines: Set<number>;
  selectedCount: number;
  clearAllSelections: () => void;
  goToNextSelection: () => number | null;
  goToPrevSelection: () => number | null;
  getCurrentSelectionIndex: () => number;
}

interface LogViewerProps {
  lines: string[];
  keyword: string;
  onSelectionChange?: (selectedLines: Set<number>) => void;
}

type LogLevel = 'INFO' | 'WARN' | 'WARNING' | 'ERROR' | 'DEBUG' | 'UNKNOWN';

function getLogLevel(line: string): LogLevel {
  if (line.includes(' - INFO - ')) return 'INFO';
  if (line.includes(' - WARNING - ') || line.includes(' - WARN - ')) return 'WARN';
  if (line.includes(' - ERROR - ')) return 'ERROR';
  if (line.includes(' - DEBUG - ')) return 'DEBUG';
  return 'UNKNOWN';
}

function getLevelColors(level: LogLevel): { text: string; bg: string; hoverBg: string; border: string } {
  switch (level) {
    case 'ERROR':
      return {
        text: '#b91c1c',      // red-700
        bg: '#fef2f2',        // red-50
        hoverBg: '#fecaca',   // red-200
        border: '#f87171',    // red-400
      };
    case 'WARN':
    case 'WARNING':
      return {
        text: '#b45309',      // amber-700
        bg: '#fffbeb',        // amber-50
        hoverBg: '#fde68a',   // amber-200
        border: '#fbbf24',    // amber-400
      };
    case 'DEBUG':
      return {
        text: '#2563eb',      // blue-600
        bg: 'transparent',
        hoverBg: '#dbeafe',   // blue-100
        border: '#93c5fd',    // blue-300
      };
    case 'INFO':
    default:
      return {
        text: '#475569',      // slate-600
        bg: 'transparent',
        hoverBg: '#e2e8f0',   // slate-200
        border: '#cbd5e1',    // slate-300
      };
  }
}

function highlightKeyword(text: string, keyword: string): React.ReactNode {
  if (!keyword.trim()) {
    return text;
  }

  const lowerText = text.toLowerCase();
  const lowerKeyword = keyword.toLowerCase();
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let index = lowerText.indexOf(lowerKeyword);
  let keyIndex = 0;

  while (index !== -1) {
    // Add text before match
    if (index > lastIndex) {
      parts.push(text.slice(lastIndex, index));
    }
    // Add highlighted match (preserve original case)
    parts.push(
      <mark key={keyIndex++} className="bg-yellow-300 text-black px-0.5 rounded">
        {text.slice(index, index + keyword.length)}
      </mark>
    );
    lastIndex = index + keyword.length;
    index = lowerText.indexOf(lowerKeyword, lastIndex);
  }

  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? <>{parts}</> : text;
}

export const LogViewer = forwardRef<LogViewerRef, LogViewerProps>(function LogViewer(
  { lines, keyword, onSelectionChange },
  ref
) {
  const [selectedLines, setSelectedLines] = useState<Set<number>>(new Set());
  const [hoveredLine, setHoveredLine] = useState<number | null>(null);
  const [currentSelectionIndex, setCurrentSelectionIndex] = useState<number>(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const lineRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  // 获取排序后的选中行索引
  const sortedSelectedLines = useMemo(() => {
    return Array.from(selectedLines).sort((a, b) => a - b);
  }, [selectedLines]);

  // 当选中行变化时通知父组件
  useEffect(() => {
    onSelectionChange?.(selectedLines);
  }, [selectedLines, onSelectionChange]);

  const toggleLineSelection = useCallback((index: number) => {
    setSelectedLines((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }, []);

  const clearAllSelections = useCallback(() => {
    setSelectedLines(new Set());
    setCurrentSelectionIndex(-1);
  }, []);

  const scrollToLine = useCallback((lineIndex: number) => {
    const lineElement = lineRefs.current.get(lineIndex);
    if (lineElement) {
      lineElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, []);

  const goToNextSelection = useCallback(() => {
    if (sortedSelectedLines.length === 0) return null;
    const nextIndex = currentSelectionIndex + 1 >= sortedSelectedLines.length ? 0 : currentSelectionIndex + 1;
    setCurrentSelectionIndex(nextIndex);
    const lineIndex = sortedSelectedLines[nextIndex];
    scrollToLine(lineIndex);
    return lineIndex;
  }, [sortedSelectedLines, currentSelectionIndex, scrollToLine]);

  const goToPrevSelection = useCallback(() => {
    if (sortedSelectedLines.length === 0) return null;
    const prevIndex = currentSelectionIndex - 1 < 0 ? sortedSelectedLines.length - 1 : currentSelectionIndex - 1;
    setCurrentSelectionIndex(prevIndex);
    const lineIndex = sortedSelectedLines[prevIndex];
    scrollToLine(lineIndex);
    return lineIndex;
  }, [sortedSelectedLines, currentSelectionIndex, scrollToLine]);

  // 暴露给父组件的方法
  useImperativeHandle(ref, () => ({
    selectedLines,
    selectedCount: selectedLines.size,
    clearAllSelections,
    goToNextSelection,
    goToPrevSelection,
    getCurrentSelectionIndex: () => currentSelectionIndex,
  }), [selectedLines, clearAllSelections, goToNextSelection, goToPrevSelection, currentSelectionIndex]);

  const processedLines = useMemo(() => {
    return lines.map((line, index) => {
      const level = getLogLevel(line);
      const colors = getLevelColors(level);
      return { line, level, colors, index };
    });
  }, [lines]);

  return (
    <div ref={containerRef} className="font-mono text-xs leading-relaxed p-2" style={{ backgroundColor: '#f8fafc' }}>
      {processedLines.map(({ line, colors, index }) => {
        const isSelected = selectedLines.has(index);
        const isHovered = hoveredLine === index;
        const isCurrentNav = sortedSelectedLines[currentSelectionIndex] === index;

        // 计算背景色
        let backgroundColor = colors.bg;
        if (isSelected) {
          backgroundColor = isCurrentNav ? '#93c5fd' : '#bfdbfe'; // blue-300 for current, blue-200 for others
        } else if (isHovered) {
          backgroundColor = colors.hoverBg;
        }

        return (
          <div
            key={index}
            ref={(el) => {
              if (el) {
                lineRefs.current.set(index, el);
              } else {
                lineRefs.current.delete(index);
              }
            }}
            onClick={() => toggleLineSelection(index)}
            onMouseEnter={() => setHoveredLine(index)}
            onMouseLeave={() => setHoveredLine(null)}
            style={{
              whiteSpace: 'pre',
              padding: '4px 12px',
              cursor: 'pointer',
              borderLeft: `4px solid ${isCurrentNav ? '#2563eb' : colors.border}`,
              backgroundColor,
              color: isSelected ? '#1e3a8a' : colors.text,
              boxShadow: isCurrentNav
                ? 'inset 0 0 0 2px rgba(37, 99, 235, 0.6)'
                : isSelected
                  ? 'inset 0 0 0 2px rgba(59, 130, 246, 0.4)'
                  : 'none',
              borderRadius: isSelected ? '2px' : '0',
              transition: 'background-color 0.1s ease, box-shadow 0.1s ease',
            }}
          >
            <span
              style={{
                marginRight: '12px',
                display: 'inline-block',
                width: '32px',
                textAlign: 'right',
                userSelect: 'none',
                color: isSelected ? '#2563eb' : '#94a3b8',
                fontWeight: isSelected ? 600 : 400,
              }}
            >
              {index + 1}
            </span>
            <span>{highlightKeyword(line, keyword)}</span>
          </div>
        );
      })}
    </div>
  );
});
