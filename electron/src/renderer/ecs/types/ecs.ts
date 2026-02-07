// ECS Types for Electron IPC communication

export interface ECSOption {
  value: string;
  label: string;
}

export interface ECSField {
  name: string;
  type: 'text' | 'textarea' | 'select' | 'multiselect' | 'radio' | 'checkbox' | 'number' | 'slider' | 'date' | 'datetime' | 'boolean';
  label: string;
  required?: boolean;
  placeholder?: string;
  default?: unknown;
  options?: ECSOption[];
  min?: number;
  max?: number;
  step?: number;
}

export interface ECSActions {
  approve?: { label: string; style: string };
  edit?: { label: string; style: string };
  reject?: { label: string; style: string };
}

export interface ECSRequest {
  id: string;
  type: string;
  title: string;
  description?: string;
  fields: ECSField[];
  actions?: ECSActions;
  session_id: string;
  ttl_seconds?: number;
  readonly?: boolean;  // Readonly mode for context variable replay
}

// Visual Display Types
export type ECSDisplayType = 'table' | 'ascii';

export interface ECSTableData {
  headers: string[];
  rows: string[][];
  alignment?: ('left' | 'center' | 'right')[];
  caption?: string;
}

export interface ECSAsciiData {
  content: string;
  title?: string;
}

export interface ECSDisplayField {
  type: ECSDisplayType;
  data: ECSTableData | ECSAsciiData;
}

export interface ECSDisplayRequest {
  id: string;
  type: 'visual_display';
  title: string;
  description?: string;
  displays: ECSDisplayField[];
  dismiss_label?: string;
  session_id: string;
  ttl_seconds?: number;
  readonly?: boolean;
}

// Type guard for display request
export function isDisplayRequest(request: ECSRequest | ECSDisplayRequest): request is ECSDisplayRequest {
  return request.type === 'visual_display';
}

// Union type for any ECS request
export type AnyECSRequest = ECSRequest | ECSDisplayRequest;

export interface ECSContinuationData {
  request_title: string;
  action: string;
  form_data?: Record<string, unknown>;
  field_labels: Record<string, string>;
}

// IPC Message Types
export interface ECSOpenRequest {
  request: AnyECSRequest;
  sessionId: string;
}

export interface ECSSubmitRequest {
  requestId: string;
  sessionId: string;
  action: 'approve' | 'reject';
  formData: Record<string, unknown> | null;
}

export interface ECSResultResponse {
  success: boolean;
  action: string;
  message?: string;
  error?: string;
  continuationData?: ECSContinuationData;
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
