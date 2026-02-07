import type { ECSDisplayField as ECSDisplayFieldType, ECSTableData, ECSAsciiData } from '../types/ecs';
import { ECSTable } from './ecs-table';
import { ECSAscii } from './ecs-ascii';

interface ECSDisplayFieldProps {
  field: ECSDisplayFieldType;
}

export function ECSDisplayField({ field }: ECSDisplayFieldProps) {
  switch (field.type) {
    case 'table':
      return <ECSTable data={field.data as ECSTableData} />;
    case 'ascii':
      return <ECSAscii data={field.data as ECSAsciiData} />;
    default:
      return null;
  }
}
