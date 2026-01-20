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
export type MemoryCategory = 'preference' | 'fact' | 'pattern';
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
