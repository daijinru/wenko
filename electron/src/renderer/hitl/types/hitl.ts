// HITL Types for Electron IPC communication

export interface HITLOption {
  value: string;
  label: string;
}

export interface HITLField {
  name: string;
  type: 'text' | 'textarea' | 'select' | 'multiselect' | 'radio' | 'checkbox' | 'number' | 'slider' | 'date' | 'boolean';
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

export interface HITLContinuationData {
  request_title: string;
  action: string;
  form_data?: Record<string, unknown>;
  field_labels: Record<string, string>;
}

// IPC Message Types
export interface HITLOpenRequest {
  request: HITLRequest;
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
