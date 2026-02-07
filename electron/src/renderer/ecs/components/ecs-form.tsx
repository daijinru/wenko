import type { ECSRequest } from '../types/ecs';
import { ECSField } from './ecs-field';

interface ECSFormProps {
  request: ECSRequest;
  formData: Record<string, unknown>;
  onFieldChange: (fieldName: string, value: unknown) => void;
  error: string | null;
  readonly?: boolean;
}

export function ECSForm({ request, formData, onFieldChange, error, readonly }: ECSFormProps) {
  return (
    <div className="flex-1 overflow-auto p-4">
      {request.description && (
        <p className="text-xs text-muted-foreground mb-4">
          {request.description}
        </p>
      )}

      <div className="space-y-1">
        {request.fields.map((field) => (
          <ECSField
            key={field.name}
            field={field}
            value={formData[field.name]}
            onChange={(value) => onFieldChange(field.name, value)}
            readonly={readonly}
          />
        ))}
      </div>

      {error && (
        <div className="mt-4 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-600">
          {error}
        </div>
      )}
    </div>
  );
}
