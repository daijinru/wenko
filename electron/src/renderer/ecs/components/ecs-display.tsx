import type { ECSDisplayRequest } from '../types/ecs';
import { ECSDisplayField } from './ecs-display-field';

interface ECSDisplayProps {
  request: ECSDisplayRequest;
}

export function ECSDisplay({ request }: ECSDisplayProps) {
  return (
    <div className="flex-1 overflow-auto p-4">
      {request.description && (
        <p className="text-xs text-muted-foreground mb-4">
          {request.description}
        </p>
      )}

      <div className="space-y-2">
        {request.displays.map((display, index) => (
          <ECSDisplayField key={index} field={display} />
        ))}
      </div>
    </div>
  );
}
