import type { HITLDisplayRequest } from '../types/hitl';
import { HITLDisplayField } from './hitl-display-field';

interface HITLDisplayProps {
  request: HITLDisplayRequest;
}

export function HITLDisplay({ request }: HITLDisplayProps) {
  return (
    <div className="flex-1 overflow-auto p-4">
      {request.description && (
        <p className="text-xs text-muted-foreground mb-4">
          {request.description}
        </p>
      )}

      <div className="space-y-2">
        {request.displays.map((display, index) => (
          <HITLDisplayField key={index} field={display} />
        ))}
      </div>
    </div>
  );
}
