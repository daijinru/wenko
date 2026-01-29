// HITL Types for Electron IPC communication

export interface HITLOption {
  value: string;
  label: string;
}

export interface HITLField {
  name: string;
  type: 'text' | 'textarea' | 'select' | 'multiselect' | 'radio' | 'checkbox' | 'number' | 'slider' | 'date' | 'datetime' | 'boolean';
  label: string;
  required?: boolean;
  placeholder?: string;
  default?: unknown;
  options?: HITLOption[];
  min?: number;
  max?: number;
  step?: number;
}

export interface HITLActions {
  approve?: { label: string; style: string };
  edit?: { label: string; style: string };
  reject?: { label: string; style: string };
}

export interface HITLRequest {
  id: string;
  type: string;
  title: string;
  description?: string;
  fields: HITLField[];
  actions?: HITLActions;
  session_id: string;
  ttl_seconds?: number;
  readonly?: boolean;  // Readonly mode for context variable replay
}

// Visual Display Types
export type HITLDisplayType = 'table' | 'ascii';

export interface HITLTableData {
  headers: string[];
  rows: string[][];
  alignment?: ('left' | 'center' | 'right')[];
  caption?: string;
}

export interface HITLAsciiData {
  content: string;
  title?: string;
}

export interface HITLDisplayField {
  type: HITLDisplayType;
  data: HITLTableData | HITLAsciiData;
}

export interface HITLDisplayRequest {
  id: string;
  type: 'visual_display';
  title: string;
  description?: string;
  displays: HITLDisplayField[];
  dismiss_label?: string;
  session_id: string;
  ttl_seconds?: number;
  readonly?: boolean;
}

// Type guard for display request
export function isDisplayRequest(request: HITLRequest | HITLDisplayRequest): request is HITLDisplayRequest {
  return request.type === 'visual_display';
}

// Union type for any HITL request
export type AnyHITLRequest = HITLRequest | HITLDisplayRequest;

export interface HITLContinuationData {
  request_title: string;
  action: string;
  form_data?: Record<string, unknown>;
  field_labels: Record<string, string>;
}

// IPC Message Types
export interface HITLOpenRequest {
  request: AnyHITLRequest;
  sessionId: string;
}

export interface HITLSubmitRequest {
  requestId: string;
  sessionId: string;
  action: 'approve' | 'reject';
  formData: Record<string, unknown> | null;
}

export interface HITLResultResponse {
  success: boolean;
  action: string;
  message?: string;
  error?: string;
  continuationData?: HITLContinuationData;
}

// ElectronAPI type declaration
declare global {
  interface Window {
    electronAPI: {
      send: (channel: string, ...args: unknown[]) => void;
      invoke: <T = unknown>(channel: string, ...args: unknown[]) => Promise<T>;
      on: (channel: string, callback: (...args: unknown[]) => void) => () => void;
      once: (channel: string, callback: (...args: unknown[]) => void) => void;
    };
  }
}
