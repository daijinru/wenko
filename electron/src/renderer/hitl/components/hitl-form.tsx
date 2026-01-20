import type { HITLRequest } from '../types/hitl';
import { HITLField } from './hitl-field';

interface HITLFormProps {
  request: HITLRequest;
  formData: Record<string, unknown>;
  onFieldChange: (fieldName: string, value: unknown) => void;
  error: string | null;
}

export function HITLForm({ request, formData, onFieldChange, error }: HITLFormProps) {
  return (
    <div className="flex-1 overflow-auto p-4">
      {request.description && (
        <p className="text-xs text-muted-foreground mb-4">
          {request.description}
        </p>
      )}

      <div className="space-y-1">
        {request.fields.map((field) => (
          <HITLField
            key={field.name}
            field={field}
            value={formData[field.name]}
            onChange={(value) => onFieldChange(field.name, value)}
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
