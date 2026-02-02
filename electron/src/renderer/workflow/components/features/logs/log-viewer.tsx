import { useMemo, useState, useCallback } from 'react';

interface LogViewerProps {
  lines: string[];
  keyword: string;
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

export function LogViewer({ lines, keyword }: LogViewerProps) {
  const [selectedLines, setSelectedLines] = useState<Set<number>>(new Set());
  const [hoveredLine, setHoveredLine] = useState<number | null>(null);

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

  const processedLines = useMemo(() => {
    return lines.map((line, index) => {
      const level = getLogLevel(line);
      const colors = getLevelColors(level);
      return { line, level, colors, index };
    });
  }, [lines]);

  return (
    <div className="font-mono text-xs leading-relaxed p-2" style={{ backgroundColor: '#f8fafc' }}>
      {processedLines.map(({ line, colors, index }) => {
        const isSelected = selectedLines.has(index);
        const isHovered = hoveredLine === index;

        // 计算背景色
        let backgroundColor = colors.bg;
        if (isSelected) {
          backgroundColor = '#bfdbfe'; // blue-200
        } else if (isHovered) {
          backgroundColor = colors.hoverBg;
        }

        return (
          <div
            key={index}
            onClick={() => toggleLineSelection(index)}
            onMouseEnter={() => setHoveredLine(index)}
            onMouseLeave={() => setHoveredLine(null)}
            style={{
              whiteSpace: 'pre',
              padding: '4px 12px',
              cursor: 'pointer',
              borderLeft: `4px solid ${colors.border}`,
              backgroundColor,
              color: isSelected ? '#1e3a8a' : colors.text,
              boxShadow: isSelected ? 'inset 0 0 0 2px rgba(59, 130, 246, 0.4)' : 'none',
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
}
