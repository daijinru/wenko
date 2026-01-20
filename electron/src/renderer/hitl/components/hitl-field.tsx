import type { HITLField as HITLFieldType } from '../types/hitl';
import { cn } from '../lib/utils';

interface HITLFieldProps {
  field: HITLFieldType;
  value: unknown;
  onChange: (value: unknown) => void;
}

export function HITLField({ field, value, onChange }: HITLFieldProps) {
  const renderField = () => {
    switch (field.type) {
      case 'text':
        return (
          <input
            type="text"
            value={(value as string) ?? ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            className="w-full px-2 py-1 text-xs bg-white border-classic-inset"
          />
        );

      case 'textarea':
        return (
          <textarea
            value={(value as string) ?? ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            className="w-full min-h-[60px] px-2 py-1 text-xs bg-white border-classic-inset resize-y"
          />
        );

      case 'number':
        return (
          <input
            type="number"
            value={(value as number) ?? ''}
            onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
            min={field.min}
            max={field.max}
            step={field.step}
            placeholder={field.placeholder}
            className="w-full px-2 py-1 text-xs bg-white border-classic-inset"
          />
        );

      case 'select':
        return (
          <select
            value={(value as string) ?? ''}
            onChange={(e) => onChange(e.target.value)}
            className="w-full px-2 py-1 text-xs bg-white border-classic-inset"
          >
            <option value="">请选择...</option>
            {field.options?.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        );

      case 'radio':
        return (
          <div className="flex flex-wrap gap-2">
            {field.options?.map((opt) => (
              <label
                key={opt.value}
                className="flex items-center gap-1 text-xs cursor-pointer"
              >
                <input
                  type="radio"
                  name={field.name}
                  value={opt.value}
                  checked={(value as string) === opt.value}
                  onChange={(e) => onChange(e.target.value)}
                  className="w-3 h-3"
                />
                {opt.label}
              </label>
            ))}
          </div>
        );

      case 'checkbox':
      case 'multiselect':
        const selectedValues = Array.isArray(value) ? value as string[] : [];
        return (
          <div className="flex flex-wrap gap-2">
            {field.options?.map((opt) => (
              <label
                key={opt.value}
                className="flex items-center gap-1 text-xs cursor-pointer"
              >
                <input
                  type="checkbox"
                  value={opt.value}
                  checked={selectedValues.includes(opt.value)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      onChange([...selectedValues, opt.value]);
                    } else {
                      onChange(selectedValues.filter((v) => v !== opt.value));
                    }
                  }}
                  className="w-3 h-3"
                />
                {opt.label}
              </label>
            ))}
          </div>
        );

      case 'boolean':
        return (
          <label className="flex items-center gap-2 text-xs cursor-pointer">
            <input
              type="checkbox"
              checked={(value as boolean) ?? false}
              onChange={(e) => onChange(e.target.checked)}
              className="w-4 h-4"
            />
            {field.placeholder || '是'}
          </label>
        );

      case 'slider':
        const min = field.min ?? 0;
        const max = field.max ?? 100;
        const step = field.step ?? 1;
        const sliderValue = (value as number) ?? min;
        return (
          <div className="flex items-center gap-2">
            <input
              type="range"
              min={min}
              max={max}
              step={step}
              value={sliderValue}
              onChange={(e) => onChange(parseFloat(e.target.value))}
              className="flex-1"
            />
            <span className="text-xs min-w-[30px] text-right">{sliderValue}</span>
          </div>
        );

      case 'date':
        return (
          <input
            type="date"
            value={(value as string) ?? ''}
            onChange={(e) => onChange(e.target.value)}
            className="w-full px-2 py-1 text-xs bg-white border-classic-inset"
          />
        );

      default:
        return (
          <input
            type="text"
            value={(value as string) ?? ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            className="w-full px-2 py-1 text-xs bg-white border-classic-inset"
          />
        );
    }
  };

  return (
    <div className="mb-3">
      <label className="block text-xs font-medium mb-1">
        {field.label}
        {field.required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {renderField()}
    </div>
  );
}
