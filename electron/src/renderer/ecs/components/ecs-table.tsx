import type { ECSTableData } from '../types/ecs';
import { cn } from '../lib/utils';

interface ECSTableProps {
  data: ECSTableData;
}

export function ECSTable({ data }: ECSTableProps) {
  const { headers, rows, alignment, caption } = data;

  const getAlignmentClass = (index: number) => {
    if (!alignment || !alignment[index]) return 'text-left';
    switch (alignment[index]) {
      case 'center':
        return 'text-center';
      case 'right':
        return 'text-right';
      default:
        return 'text-left';
    }
  };

  return (
    <div className="mb-4">
      {caption && (
        <div className="text-xs font-medium text-muted-foreground mb-2">
          {caption}
        </div>
      )}
      <div className="border-classic-inset bg-card overflow-x-auto">
        <table className="w-full text-xs border-collapse">
          <thead className="bg-muted font-bold text-muted-foreground">
            <tr>
              {headers.map((header, index) => (
                <th
                  key={index}
                  className={cn(
                    "p-2 border-b border-r border-border last:border-r-0",
                    getAlignmentClass(index)
                  )}
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={rowIndex} className="hover:bg-muted/50 transition-colors">
                {row.map((cell, cellIndex) => (
                  <td
                    key={cellIndex}
                    className={cn(
                      "p-2 border-b border-r border-border last:border-r-0",
                      getAlignmentClass(cellIndex)
                    )}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
