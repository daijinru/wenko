import type { HITLDisplayField as HITLDisplayFieldType, HITLTableData, HITLAsciiData } from '../types/hitl';
import { HITLTable } from './hitl-table';
import { HITLAscii } from './hitl-ascii';

interface HITLDisplayFieldProps {
  field: HITLDisplayFieldType;
}

export function HITLDisplayField({ field }: HITLDisplayFieldProps) {
  switch (field.type) {
    case 'table':
      return <HITLTable data={field.data as HITLTableData} />;
    case 'ascii':
      return <HITLAscii data={field.data as HITLAsciiData} />;
    default:
      return null;
  }
}
