// Chat session types
export interface ChatSession {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface ChatHistoryResponse {
  sessions: ChatSession[];
}

export interface SessionMessagesResponse {
  messages: ChatMessage[];
}

// Working memory types
export interface WorkingMemory {
  session_id: string;
  current_topic: string | null;
  last_emotion: string | null;
  turn_count: number;
  context_variables: Record<string, unknown>;
  updated_at: string;
}

export interface WorkingMemoriesResponse {
  memories: WorkingMemory[];
}

// Long-term memory types
export type MemoryCategory = 'preference' | 'fact' | 'pattern' | 'plan';
export type MemorySource = 'user_stated' | 'inferred' | 'system';

export interface LongTermMemory {
  id: string;
  category: MemoryCategory;
  key: string;
  value: string | Record<string, unknown>;
  confidence: number;
  source: MemorySource;
  access_count: number;
  created_at: string;
  last_accessed: string;
  // Plan-specific fields (only when category === 'plan')
  target_time?: string;
  reminder_offset_minutes?: number;
  repeat_type?: RepeatType;
  plan_status?: PlanStatus;
  snooze_until?: string | null;
}

export interface LongTermMemoriesResponse {
  memories: LongTermMemory[];
  total: number;
}

export interface CreateMemoryRequest {
  category: MemoryCategory;
  key: string;
  value: string;
  confidence: number;
  source?: MemorySource;
}

export interface UpdateMemoryRequest {
  category?: MemoryCategory;
  key?: string;
  value?: string;
  confidence?: number;
}

export interface DeleteResponse {
  deleted_count: number;
}

export interface BatchDeleteRequest {
  ids: string[];
}

// Health check
export interface HealthResponse {
  status: string;
}

// Memory form state (for UI)
export interface MemoryFormData {
  category: MemoryCategory;
  key: string;
  value: string;
  confidence: number;
  // Plan-specific fields (only when category === 'plan')
  target_time?: string;
  reminder_offset_minutes?: number;
  repeat_type?: RepeatType;
}

// Memory extraction types
export interface MemoryExtractRequest {
  content: string;
  role?: 'user' | 'assistant';
}

export interface MemoryExtractResponse {
  key: string;
  value: string;
  category: MemoryCategory;
  confidence: number;
}

// Plan types (used by LongTermMemory for category='plan')
export type PlanStatus = 'pending' | 'completed' | 'dismissed' | 'snoozed';
export type RepeatType = 'none' | 'daily' | 'weekly' | 'monthly';

// MCP Service types
export type MCPServerStatus = 'stopped' | 'running' | 'error';

export interface MCPServer {
  id: string;
  name: string;
  command: string;
  args: string[];
  env: Record<string, string>;
  enabled: boolean;
  created_at: string;
  status: MCPServerStatus;
  error_message: string | null;
  pid: number | null;
  description: string | null;
  trigger_keywords: string[];
}

export interface MCPServerListResponse {
  servers: MCPServer[];
  total: number;
}

export interface MCPServerCreateRequest {
  name: string;
  command: string;
  args?: string[];
  env?: Record<string, string>;
  enabled?: boolean;
  description?: string;
  trigger_keywords?: string[];
}

export interface MCPServerUpdateRequest {
  name?: string;
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  enabled?: boolean;
  description?: string;
  trigger_keywords?: string[];
}

export interface MCPServerActionResponse {
  success: boolean;
  message: string | null;
  server: MCPServer | null;
}
