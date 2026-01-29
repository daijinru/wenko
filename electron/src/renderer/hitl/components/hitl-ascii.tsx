import type { HITLAsciiData } from '../types/hitl';

interface HITLAsciiProps {
  data: HITLAsciiData;
}

export function HITLAscii({ data }: HITLAsciiProps) {
  const { content, title } = data;

  return (
    <div className="mb-4">
      {title && (
        <div className="text-xs font-medium text-muted-foreground mb-2">
          {title}
        </div>
      )}
      <div className="border-classic-inset bg-card p-3 overflow-x-auto">
        <pre className="font-mono text-xs whitespace-pre leading-tight">
          {content}
        </pre>
      </div>
    </div>
  );
}
