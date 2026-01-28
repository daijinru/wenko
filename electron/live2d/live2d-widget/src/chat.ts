/**
 * @file Chat module for Live2D AI conversation.
 * @module chat
 *
 * Uses localStorage to persist session_id across page reloads.
 * Messages are saved to backend SQLite database when session_id is provided.
 */

// @ts-ignore
import { fetchEventSource } from "https://esm.sh/@microsoft/fetch-event-source";
import { showSSEMessage, showMemoryNotification } from './message.js';

const CHAT_API_URL = 'http://localhost:8002/chat';
const IMAGE_CHAT_API_URL = 'http://localhost:8002/chat/image';
const HITL_API_URL = 'http://localhost:8002/hitl/respond';
const HITL_CONTINUE_API_URL = 'http://localhost:8002/hitl/continue';
const MAX_HISTORY_LENGTH = 10;
const MAX_IMAGE_SIZE = 4 * 1024 * 1024; // 4MB
const SESSION_ID_KEY = 'wenko-chat-session-id';
const HISTORY_KEY = 'wenko-chat-history';

// HITL Debug Logger
const HITL_DEBUG = true;
function hitlLog(stage: string, data?: any): void {
  if (HITL_DEBUG) {
    console.log(`[HITL] ${stage}:`, data);
  }
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface EmotionInfo {
  primary: string;
  category: string;
  confidence: number;
}

export interface MemorySavedInfo {
  count: number;
  entries: Array<{
    id: string;
    category: string;
    key: string;
  }>;
}

// HITL Types
export interface HITLOption {
  value: string;
  label: string;
}

export interface HITLField {
  name: string;
  type: string;
  label: string;
  required?: boolean;
  placeholder?: string;
  default?: any;
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
}

export interface HITLResult {
  action: 'approve' | 'edit' | 'reject';
  data?: Record<string, any>;
  result?: any;
}

export interface HITLContinuationData {
  request_title: string;
  action: string;
  form_data?: Record<string, any>;
  field_labels: Record<string, string>;
}

// Emotion display configuration
const EMOTION_DISPLAY: Record<string, { label: string; color: string }> = {
  neutral: { label: 'Neutral', color: '#9ca3af' },
  happy: { label: 'Happy', color: '#22c55e' },
  excited: { label: 'Excited', color: '#f59e0b' },
  grateful: { label: 'Grateful', color: '#ec4899' },
  curious: { label: 'Curious', color: '#8b5cf6' },
  sad: { label: 'Sad', color: '#3b82f6' },
  anxious: { label: 'Anxious', color: '#ef4444' },
  frustrated: { label: 'Frustrated', color: '#f97316' },
  confused: { label: 'Confused', color: '#6366f1' },
  help_seeking: { label: 'Help', color: '#14b8a6' },
  info_seeking: { label: 'Info', color: '#0ea5e9' },
  validation_seeking: { label: 'Validation', color: '#a855f7' },
};

let currentEmotion: EmotionInfo | null = null;
let currentHITLRequest: HITLRequest | null = null;

/**
 * 生成 UUID v4
 */
function generateUUID(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * SessionManager - 管理会话 ID
 */
class SessionManager {
  getSessionId(): string {
    let sessionId = localStorage.getItem(SESSION_ID_KEY);
    if (!sessionId) {
      sessionId = generateUUID();
      localStorage.setItem(SESSION_ID_KEY, sessionId);
    }
    return sessionId;
  }

  createNewSession(): string {
    const sessionId = generateUUID();
    localStorage.setItem(SESSION_ID_KEY, sessionId);
    // 清除本地历史记录
    localStorage.removeItem(HISTORY_KEY);
    return sessionId;
  }

  clearSession(): void {
    localStorage.removeItem(SESSION_ID_KEY);
    localStorage.removeItem(HISTORY_KEY);
  }
}

/**
 * ChatHistoryManager - 管理本地对话历史（用于发送给 LLM 的上下文）
 *
 * 注意：消息同时会保存到后端数据库（通过 session_id）
 * 本地历史仅用于构建 LLM 请求的 history 参数
 */
class ChatHistoryManager {
  getHistory(): ChatMessage[] {
    try {
      const data = localStorage.getItem(HISTORY_KEY);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  }

  addMessage(message: ChatMessage): void {
    const history = this.getHistory();
    history.push(message);

    // 限制历史长度（保留最近 MAX_HISTORY_LENGTH 轮对话）
    const maxMessages = MAX_HISTORY_LENGTH * 2;
    if (history.length > maxMessages) {
      history.splice(0, history.length - maxMessages);
    }

    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  }

  clearHistory(): void {
    localStorage.removeItem(HISTORY_KEY);
  }
}

const sessionManager = new SessionManager();
const historyManager = new ChatHistoryManager();

let isLoading = false;

// ============ HITL IPC Result Listener ============

/**
 * Setup listener for HITL results from main process
 */
function setupHITLResultListener(): void {
  if (!window.electronAPI?.on) {
    hitlLog('SETUP_LISTENER', 'electronAPI.on not available, skipping HITL listener setup');
    return;
  }

  window.electronAPI.on('hitl:result', (result: any) => {
    hitlLog('HITL_RESULT_RECEIVED', result);

    if (result.action === 'approve' && result.message) {
      showSSEMessage(`<div class="wenko-chat-system">${result.message}</div>`, 'wenko-chat-system-msg');
    } else if (result.action === 'reject') {
      showSSEMessage(`<div class="wenko-chat-system">已跳过</div>`, 'wenko-chat-system-msg');
    } else if (result.action === 'cancel') {
      showSSEMessage(`<div class="wenko-chat-system">已取消</div>`, 'wenko-chat-system-msg');
    } else if (result.action === 'timeout') {
      showSSEMessage(`<div class="wenko-chat-error">请求已超时</div>`, 'wenko-chat-error-msg');
    }

    // Handle continuation if present
    if (result.success && result.continuationData) {
      hitlLog('HITL_CONTINUATION_TRIGGERED', result.continuationData);
      handleHITLContinuation(result.continuationData);
    }
  });

  hitlLog('SETUP_LISTENER', 'HITL result listener setup complete');
}

/**
 * Setup listener for Image Preview results from main process
 */
function setupImagePreviewResultListener(): void {
  if (!window.electronAPI?.on) {
    console.log('[ImagePreview] electronAPI.on not available, skipping listener setup');
    return;
  }

  window.electronAPI.on('image-preview:result', (result: {
    success: boolean;
    action: string;
    hitlRequest?: HITLRequest;
  }) => {
    console.log('[ImagePreview] Result received:', result);

    if (result.action === 'cancel') {
      // User cancelled, no action needed
      console.log('[ImagePreview] User cancelled');
    } else if (result.action === 'hitl' && result.hitlRequest) {
      // HITL request from image analysis - open HITL window
      console.log('[ImagePreview] Opening HITL window for memory confirmation');

      const sessionId = sessionManager.getSessionId();

      if (window.electronAPI?.invoke) {
        window.electronAPI.invoke('hitl:open-window', {
          request: result.hitlRequest,
          sessionId: sessionId,
        }).then(() => {
          console.log('[ImagePreview] HITL window opened');
        }).catch((error: Error) => {
          console.error('[ImagePreview] Failed to open HITL window:', error);
          showSSEMessage('<div class="wenko-chat-error">无法打开记忆确认窗口</div>', 'wenko-chat-error-msg');
        });
      }
    }
  });

  console.log('[ImagePreview] Result listener setup complete');
}

// Initialize Image Preview listener when module loads
setupImagePreviewResultListener();

/**
 * Handle HITL continuation - trigger AI to continue conversation
 */
function handleHITLContinuation(continuationData: HITLContinuationData): void {
  const sessionId = sessionManager.getSessionId();

  triggerHITLContinuation(
    sessionId,
    continuationData,
    (chunk) => {
      showSSEMessage(chunk, 'wenko-chat-response');
    },
    () => {
      hitlLog('HITL_CONTINUATION_DONE');
    },
    (error) => {
      showSSEMessage(`<div class="wenko-chat-error">错误: ${error}</div>`, 'wenko-chat-error-msg');
    },
    (newHitlRequest) => {
      // Handle chained HITL request - open new window
      hitlLog('HITL_CHAINED_REQUEST', { id: newHitlRequest.id, title: newHitlRequest.title });
      if (window.electronAPI?.invoke) {
        window.electronAPI.invoke('hitl:open-window', {
          request: newHitlRequest,
          sessionId: sessionId,
        });
      }
    }
  );
}

// Initialize HITL listener when module loads
setupHITLResultListener();

/**
 * 获取当前会话 ID
 */
export function getSessionId(): string {
  return sessionManager.getSessionId();
}

/**
 * 创建新会话
 */
export function createNewSession(): string {
  return sessionManager.createNewSession();
}

/**
 * 发送对话消息并处理 SSE 流式响应
 */
export function sendChatMessage(
  message: string,
  onChunk: (text: string) => void,
  onDone?: () => void,
  onError?: (error: string) => void,
  onEmotion?: (emotion: EmotionInfo) => void,
  onHITL?: (hitlRequest: HITLRequest) => void,
  onMemorySaved?: (info: MemorySavedInfo) => void
): void {
  if (isLoading) return;
  if (!message.trim()) return;

  isLoading = true;

  // 获取当前会话 ID
  const sessionId = sessionManager.getSessionId();
  hitlLog('SEND_MESSAGE', { message, sessionId });

  // 添加用户消息到本地历史
  historyManager.addMessage({ role: 'user', content: message });

  let assistantResponse = '';

  fetchEventSource(CHAT_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message: message,
      session_id: sessionId,
      history: historyManager.getHistory().slice(0, -1), // 不包含刚添加的用户消息
    }),
    onopen: (res: Response) => {
      hitlLog('SSE_OPEN', { status: res.status });
      if (res.ok) return Promise.resolve();
      throw new Error(`HTTP ${res.status}`);
    },
    onmessage: (event: { event: string; data: string }) => {
      hitlLog('SSE_EVENT', { event: event.event, data: event.data?.substring(0, 200) });
      try {
        if (event.event === 'text') {
          const data = JSON.parse(event.data);
          if (data.type === 'text' && data.payload?.content) {
            assistantResponse += data.payload.content;
            onChunk(data.payload.content);
          }
        } else if (event.event === 'emotion') {
          // Handle emotion event
          const data = JSON.parse(event.data);
          if (data.type === 'emotion' && data.payload) {
            currentEmotion = {
              primary: data.payload.primary,
              category: data.payload.category,
              confidence: data.payload.confidence,
            };
            onEmotion?.(currentEmotion);
          }
        } else if (event.event === 'memory_saved') {
          // Handle memory saved event
          const data = JSON.parse(event.data);
          if (data.type === 'memory_saved' && data.payload) {
            const memorySavedInfo: MemorySavedInfo = {
              count: data.payload.count,
              entries: data.payload.entries,
            };
            console.log(`[Memory] 自动保存了 ${memorySavedInfo.count} 条记忆:`, memorySavedInfo.entries);
            onMemorySaved?.(memorySavedInfo);
          }
        } else if (event.event === 'hitl') {
          // Handle HITL event
          hitlLog('HITL_EVENT_RECEIVED', event.data);
          const data = JSON.parse(event.data);
          if (data.type === 'hitl' && data.payload) {
            currentHITLRequest = data.payload as HITLRequest;
            hitlLog('HITL_REQUEST_PARSED', {
              id: currentHITLRequest.id,
              title: currentHITLRequest.title,
              fields: currentHITLRequest.fields?.length
            });
            onHITL?.(currentHITLRequest);
          }
        } else if (event.event === 'done') {
          // 添加助手响应到本地历史
          if (assistantResponse) {
            historyManager.addMessage({ role: 'assistant', content: assistantResponse });
          }
          isLoading = false;
          onDone?.();
        } else if (event.event === 'error') {
          const data = JSON.parse(event.data);
          const errorMsg = data.payload?.message || '未知错误';
          isLoading = false;
          onError?.(errorMsg);
        }
      } catch (e) {
        console.error('解析 SSE 消息失败:', e);
      }
    },
    onclose: () => {
      if (isLoading) {
        // 添加助手响应到本地历史
        if (assistantResponse) {
          historyManager.addMessage({ role: 'assistant', content: assistantResponse });
        }
        isLoading = false;
        onDone?.();
      }
    },
    onerror: (err: Error) => {
      console.error('Chat SSE error:', err);
      isLoading = false;
      onError?.(err.message || '连接错误');
    },
  });
}

/**
 * 获取当前加载状态
 */
export function isChatLoading(): boolean {
  return isLoading;
}

/**
 * 清除对话历史并创建新会话
 */
export function clearChatHistory(): void {
  historyManager.clearHistory();
  sessionManager.createNewSession();
}

/**
 * 创建 ChatInput UI 组件
 */
export function createChatInput(shadowRoot: ShadowRoot): HTMLElement {
  const container = document.createElement('div');
  container.id = 'wenko-chat-input';
  container.innerHTML = `
    <input type="text" id="wenko-chat-text" placeholder="输入消息..." />
    <button id="wenko-chat-send" title="发送">
      <svg viewBox="0 0 24 24" width="18" height="18">
        <path fill="currentColor" d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
      </svg>
    </button>
  `;

  const input = container.querySelector('#wenko-chat-text') as HTMLInputElement;
  const sendBtn = container.querySelector('#wenko-chat-send') as HTMLButtonElement;

  // 输入法组合状态标记
  let isComposing = false;

  const handleSend = () => {
    const text = input.value.trim();
    if (!text || isLoading) return;

    input.value = '';
    input.disabled = true;
    sendBtn.disabled = true;

    // 显示用户消息
    showSSEMessage(`<div class="wenko-chat-user">${escapeHtml(text)}</div>`, 'wenko-chat-user-msg');

    // 发送请求
    sendChatMessage(
      text,
      (chunk) => {
        showSSEMessage(chunk, 'wenko-chat-response');
      },
      () => {
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
      },
      (error) => {
        showSSEMessage(`<div class="wenko-chat-error">错误: ${escapeHtml(error)}</div>`, 'wenko-chat-error-msg');
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
      },
      undefined, // onEmotion
      (hitlRequest) => {
        // Handle HITL request - open HITL window via IPC
        hitlLog('HITL_CALLBACK_TRIGGERED', { id: hitlRequest.id, title: hitlRequest.title });

        const sessionId = sessionManager.getSessionId();

        // Open HITL window via Electron IPC
        if (window.electronAPI?.invoke) {
          window.electronAPI.invoke('hitl:open-window', {
            request: hitlRequest,
            sessionId: sessionId,
          }).then((result: any) => {
            hitlLog('HITL_WINDOW_OPENED', result);
          }).catch((error: any) => {
            hitlLog('HITL_WINDOW_ERROR', error);
            showSSEMessage(`<div class="wenko-chat-error">无法打开 HITL 窗口</div>`, 'wenko-chat-error-msg');
          });
        } else {
          // Fallback for non-Electron environment
          hitlLog('HITL_NO_ELECTRON_API', 'electronAPI not available');
          showSSEMessage(`<div class="wenko-chat-system">HITL 请求: ${hitlRequest.title}</div>`, 'wenko-chat-system-msg');
        }
      },
      (memorySavedInfo) => {
        // Handle memory saved notification
        showMemoryNotification(memorySavedInfo.count, memorySavedInfo.entries);
      }
    );
  };

  sendBtn.addEventListener('click', handleSend);

  // 监听输入法组合事件
  input.addEventListener('compositionstart', () => {
    isComposing = true;
  });
  input.addEventListener('compositionend', () => {
    isComposing = false;
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault();
      handleSend();
    }
  });

  // 添加图片粘贴事件监听
  input.addEventListener('paste', async (e: ClipboardEvent) => {
    const handled = await handleImagePaste(e, shadowRoot, container);
    if (handled) {
      console.log('[Chat] Image paste handled');
    }
  });

  return container;
}

function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * 获取当前检测到的情绪
 */
export function getCurrentEmotion(): EmotionInfo | null {
  return currentEmotion;
}

/**
 * 获取情绪显示配置
 */
export function getEmotionDisplay(emotion: string): { label: string; color: string } {
  return EMOTION_DISPLAY[emotion] || { label: emotion, color: '#9ca3af' };
}

/**
 * 创建情绪指示器 UI 组件
 */
export function createEmotionIndicator(shadowRoot: ShadowRoot): HTMLElement {
  const container = document.createElement('div');
  container.id = 'wenko-emotion-indicator';
  container.className = 'wenko-emotion-indicator';
  container.style.cssText = `
    display: none;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 12px;
    background: rgba(255, 255, 255, 0.9);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    position: absolute;
    top: 10px;
    right: 10px;
    z-index: 100;
    transition: all 0.3s ease;
  `;

  container.innerHTML = `
    <span class="emotion-dot" style="width: 8px; height: 8px; border-radius: 50%; background: #9ca3af;"></span>
    <span class="emotion-label">Neutral</span>
    <span class="emotion-confidence" style="opacity: 0.6; font-size: 10px;"></span>
  `;

  return container;
}

/**
 * 更新情绪指示器显示
 */
export function updateEmotionIndicator(container: HTMLElement, emotion: EmotionInfo): void {
  const display = getEmotionDisplay(emotion.primary);
  const dot = container.querySelector('.emotion-dot') as HTMLElement;
  const label = container.querySelector('.emotion-label') as HTMLElement;
  const confidence = container.querySelector('.emotion-confidence') as HTMLElement;

  if (dot) {
    dot.style.background = display.color;
  }
  if (label) {
    label.textContent = display.label;
  }
  if (confidence) {
    confidence.textContent = `${Math.round(emotion.confidence * 100)}%`;
  }

  container.style.display = 'flex';
}

/**
 * 隐藏情绪指示器
 */
export function hideEmotionIndicator(container: HTMLElement): void {
  container.style.display = 'none';
}

// ============ HITL Functions ============

/**
 * 获取当前 HITL 请求
 */
export function getCurrentHITLRequest(): HITLRequest | null {
  return currentHITLRequest;
}

/**
 * 清除当前 HITL 请求
 */
export function clearHITLRequest(): void {
  currentHITLRequest = null;
}

/**
 * 提交 HITL 响应到后端
 */
export async function submitHITLResponse(
  requestId: string,
  sessionId: string,
  action: string,
  data: Record<string, any> | null
): Promise<any> {
  hitlLog('SUBMIT_START', { requestId, sessionId, action, data });
  try {
    const response = await fetch(HITL_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        request_id: requestId,
        session_id: sessionId,
        action: action,
        data: data,
      }),
    });

    hitlLog('SUBMIT_RESPONSE', { status: response.status });

    if (!response.ok) {
      const errorData = await response.json();
      hitlLog('SUBMIT_ERROR', errorData);
      throw new Error(errorData.detail || 'HITL 提交失败');
    }

    const result = await response.json();
    hitlLog('SUBMIT_SUCCESS', result);
    currentHITLRequest = null;
    return result;
  } catch (error: any) {
    hitlLog('SUBMIT_EXCEPTION', { message: error.message });
    throw error;
  }
}

/**
 * 创建 HITL 表单 UI
 */
export function createHITLForm(
  hitlRequest: HITLRequest,
  onComplete?: (result: HITLResult) => void
): HTMLElement {
  hitlLog('CREATE_FORM_START', { id: hitlRequest.id, fields: hitlRequest.fields?.length });

  const container = document.createElement('div');
  container.id = 'wenko-hitl-form';
  container.className = 'wenko-hitl-form';
  container.style.cssText = `
    position: fixed;
    bottom: 120px;
    right: 20px;
    width: 320px;
    max-height: 400px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    z-index: 10000;
    overflow: hidden;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  `;

  // Header
  const header = document.createElement('div');
  header.style.cssText = `
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 12px 16px;
    font-weight: bold;
    font-size: 14px;
  `;
  header.textContent = hitlRequest.title || '请选择';
  container.appendChild(header);

  // Description
  if (hitlRequest.description) {
    const desc = document.createElement('p');
    desc.style.cssText = `
      margin: 12px 16px 8px;
      color: #666;
      font-size: 12px;
    `;
    desc.textContent = hitlRequest.description;
    container.appendChild(desc);
  }

  // Form content
  const formContent = document.createElement('div');
  formContent.style.cssText = `
    padding: 8px 16px;
    max-height: 250px;
    overflow-y: auto;
  `;

  const formData: Record<string, any> = {};

  hitlRequest.fields?.forEach(field => {
    hitlLog('CREATE_FIELD', { name: field.name, type: field.type });

    const fieldDiv = document.createElement('div');
    fieldDiv.style.cssText = 'margin-bottom: 12px;';

    const label = document.createElement('label');
    label.style.cssText = `
      display: block;
      font-size: 12px;
      font-weight: 500;
      margin-bottom: 4px;
      color: #333;
    `;
    label.innerHTML = field.label + (field.required ? '<span style="color: #ef4444; margin-left: 2px;">*</span>' : '');
    fieldDiv.appendChild(label);

    if (field.type === 'select' && field.options) {
      const select = document.createElement('select');
      select.style.cssText = `
        width: 100%;
        padding: 8px;
        border: 1px solid #ddd;
        border-radius: 6px;
        font-size: 13px;
        background: white;
      `;

      const defaultOpt = document.createElement('option');
      defaultOpt.value = '';
      defaultOpt.textContent = '请选择...';
      select.appendChild(defaultOpt);

      field.options.forEach(opt => {
        const option = document.createElement('option');
        option.value = opt.value;
        option.textContent = opt.label;
        select.appendChild(option);
      });

      select.onchange = () => {
        formData[field.name] = select.value;
        hitlLog('FIELD_CHANGE', { field: field.name, value: select.value });
      };
      fieldDiv.appendChild(select);
    } else if (field.type === 'radio' && field.options) {
      const radioGroup = document.createElement('div');
      radioGroup.style.cssText = 'display: flex; flex-wrap: wrap; gap: 8px;';

      field.options.forEach(opt => {
        const radioLabel = document.createElement('label');
        radioLabel.style.cssText = `
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 12px;
          cursor: pointer;
        `;

        const radio = document.createElement('input');
        radio.type = 'radio';
        radio.name = field.name;
        radio.value = opt.value;
        radio.onchange = () => {
          formData[field.name] = opt.value;
          hitlLog('FIELD_CHANGE', { field: field.name, value: opt.value });
        };

        radioLabel.appendChild(radio);
        radioLabel.appendChild(document.createTextNode(opt.label));
        radioGroup.appendChild(radioLabel);
      });

      fieldDiv.appendChild(radioGroup);
    } else if (field.type === 'checkbox' && field.options) {
      formData[field.name] = [];
      const checkGroup = document.createElement('div');
      checkGroup.style.cssText = 'display: flex; flex-wrap: wrap; gap: 8px;';

      field.options.forEach(opt => {
        const checkLabel = document.createElement('label');
        checkLabel.style.cssText = `
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 12px;
          cursor: pointer;
        `;

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = opt.value;
        checkbox.onchange = () => {
          if (checkbox.checked) {
            formData[field.name].push(opt.value);
          } else {
            formData[field.name] = formData[field.name].filter((v: string) => v !== opt.value);
          }
          hitlLog('FIELD_CHANGE', { field: field.name, value: formData[field.name] });
        };

        checkLabel.appendChild(checkbox);
        checkLabel.appendChild(document.createTextNode(opt.label));
        checkGroup.appendChild(checkLabel);
      });

      fieldDiv.appendChild(checkGroup);
    } else if (field.type === 'textarea') {
      const textarea = document.createElement('textarea');
      textarea.style.cssText = `
        width: 100%;
        padding: 8px;
        border: 1px solid #ddd;
        border-radius: 6px;
        font-size: 13px;
        resize: vertical;
        min-height: 60px;
      `;
      textarea.placeholder = field.placeholder || '';
      textarea.oninput = () => { formData[field.name] = textarea.value; };
      fieldDiv.appendChild(textarea);
    } else {
      const input = document.createElement('input');
      input.type = field.type === 'number' ? 'number' : 'text';
      input.style.cssText = `
        width: 100%;
        padding: 8px;
        border: 1px solid #ddd;
        border-radius: 6px;
        font-size: 13px;
      `;
      input.placeholder = field.placeholder || '';
      input.oninput = () => { formData[field.name] = input.value; };
      fieldDiv.appendChild(input);
    }

    formContent.appendChild(fieldDiv);
  });

  container.appendChild(formContent);

  // Action buttons
  const actions = document.createElement('div');
  actions.style.cssText = `
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 12px 16px;
    border-top: 1px solid #eee;
    background: #fafafa;
  `;

  const createButton = (text: string, style: string, onClick: () => void): HTMLButtonElement => {
    const btn = document.createElement('button');
    btn.textContent = text;
    btn.style.cssText = `
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 13px;
      cursor: pointer;
      border: none;
      transition: all 0.2s;
      ${style}
    `;
    btn.onclick = onClick;
    return btn;
  };

  const rejectBtn = createButton(
    hitlRequest.actions?.reject?.label || '跳过',
    'background: #f3f4f6; color: #374151;',
    async () => {
      hitlLog('ACTION_REJECT', { requestId: hitlRequest.id });
      try {
        await submitHITLResponse(hitlRequest.id, hitlRequest.session_id, 'reject', null);
        container.remove();
        onComplete?.({ action: 'reject' });
      } catch (e) {
        console.error('Reject failed:', e);
      }
    }
  );

  const approveBtn = createButton(
    hitlRequest.actions?.approve?.label || '确认',
    'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;',
    async () => {
      hitlLog('ACTION_APPROVE', { requestId: hitlRequest.id, formData });
      try {
        const result = await submitHITLResponse(hitlRequest.id, hitlRequest.session_id, 'approve', formData);
        container.remove();
        onComplete?.({ action: 'approve', data: formData, result });
      } catch (e) {
        console.error('Approve failed:', e);
      }
    }
  );

  actions.appendChild(rejectBtn);
  actions.appendChild(approveBtn);
  container.appendChild(actions);

  hitlLog('CREATE_FORM_DONE', { id: hitlRequest.id });
  return container;
}

/**
 * 创建内联 HITL 表单 HTML（用于渲染到气泡内）
 */
export function createHITLFormHtml(hitlRequest: HITLRequest): string {
  hitlLog('CREATE_INLINE_FORM', { id: hitlRequest.id, fields: hitlRequest.fields?.length });

  let fieldsHtml = '';

  hitlRequest.fields?.forEach(field => {
    hitlLog('RENDER_FIELD', { name: field.name, type: field.type, label: field.label, hasOptions: !!field.options });
    let fieldHtml = '';

    if (field.type === 'select' && field.options) {
      const optionsHtml = field.options.map(opt =>
        `<option value="${escapeHtml(opt.value)}">${escapeHtml(opt.label)}</option>`
      ).join('');
      fieldHtml = `
        <select class="hitl-field" data-field="${escapeHtml(field.name)}" style="width:100%;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:12px;background:transparent;">
          <option value="">请选择...</option>
          ${optionsHtml}
        </select>
      `;
    } else if (field.type === 'radio' && field.options) {
      const optionsHtml = field.options.map(opt =>
        `<label style="display:inline-flex;align-items:center;gap:3px;margin-right:8px;font-size:11px;cursor:pointer;">
          <input type="radio" name="hitl_${escapeHtml(field.name)}" value="${escapeHtml(opt.value)}" class="hitl-field" data-field="${escapeHtml(field.name)}" style="margin:0;">
          ${escapeHtml(opt.label)}
        </label>`
      ).join('');
      fieldHtml = `<div style="display:flex;flex-wrap:wrap;gap:4px;">${optionsHtml}</div>`;
    } else if (field.type === 'checkbox' && field.options) {
      const optionsHtml = field.options.map(opt =>
        `<label style="display:inline-flex;align-items:center;gap:3px;margin-right:8px;font-size:11px;cursor:pointer;">
          <input type="checkbox" value="${escapeHtml(opt.value)}" class="hitl-field hitl-checkbox" data-field="${escapeHtml(field.name)}" style="margin:0;">
          ${escapeHtml(opt.label)}
        </label>`
      ).join('');
      fieldHtml = `<div style="display:flex;flex-wrap:wrap;gap:4px;">${optionsHtml}</div>`;
    } else if (field.type === 'textarea') {
      fieldHtml = `
        <textarea class="hitl-field" data-field="${escapeHtml(field.name)}" placeholder="${escapeHtml(field.placeholder || '')}"
          style="width:100%;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:12px;resize:vertical;min-height:40px;"></textarea>
      `;
    } else if (field.type === 'date') {
      fieldHtml = `
        <input type="date" class="hitl-field" data-field="${escapeHtml(field.name)}"
          style="width:100%;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:12px;">
      `;
    } else if (field.type === 'datetime') {
      fieldHtml = `
        <input type="datetime-local" class="hitl-field" data-field="${escapeHtml(field.name)}"
          ${field.default ? `value="${escapeHtml(String(field.default))}"` : ''}
          style="width:100%;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:12px;">
      `;
    } else if (field.type === 'slider' || (field.type === 'number' && field.min !== undefined && field.max !== undefined)) {
      const min = field.min ?? 0;
      const max = field.max ?? 100;
      const step = field.step ?? 1;
      const defaultVal = field.default ?? min;
      fieldHtml = `
        <div style="display:flex;align-items:center;gap:8px;">
          <input type="range" class="hitl-field hitl-slider" data-field="${escapeHtml(field.name)}"
            min="${min}" max="${max}" step="${step}" value="${defaultVal}"
            style="flex:1;">
          <span class="hitl-slider-value" style="min-width:30px;text-align:right;font-size:11px;">${defaultVal}</span>
        </div>
      `;
    } else if (field.type === 'boolean') {
      fieldHtml = `
        <label style="display:inline-flex;align-items:center;gap:6px;font-size:12px;cursor:pointer;">
          <input type="checkbox" class="hitl-field hitl-boolean" data-field="${escapeHtml(field.name)}" style="margin:0;">
          <span>${escapeHtml(field.placeholder || '是')}</span>
        </label>
      `;
    } else {
      // Default: text, number, or unknown types
      const inputType = field.type === 'number' ? 'number' : 'text';
      fieldHtml = `
        <input type="${inputType}" class="hitl-field" data-field="${escapeHtml(field.name)}" placeholder="${escapeHtml(field.placeholder || '')}"
          style="width:100%;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:12px;">
      `;
    }

    const requiredMark = field.required ? '<span style="color:#ef4444;margin-left:2px;">*</span>' : '';
    fieldsHtml += `
      <div style="margin-bottom:10px;">
        <label style="display:block;font-size:11px;font-weight:500;margin-bottom:3px;color:#333;">
          ${escapeHtml(field.label)}${requiredMark}
        </label>
        ${fieldHtml}
      </div>
    `;
  });

  const approveLabel = hitlRequest.actions?.approve?.label || '确认';
  const rejectLabel = hitlRequest.actions?.reject?.label || '跳过';

  return `
    <div class="wenko-hitl-inline" data-hitl-id="${escapeHtml(hitlRequest.id)}" data-session-id="${escapeHtml(hitlRequest.session_id)}"
      style="background:transparent;border:1px solid #e0e0e0;border-radius:8px;padding:10px;margin-top:8px;">
      <div style="font-weight:bold;font-size:12px;color:#333;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid #eee;">
        ${escapeHtml(hitlRequest.title || '请选择')}
      </div>
      ${hitlRequest.description ? `<div style="font-size:11px;color:#666;margin-bottom:8px;">${escapeHtml(hitlRequest.description)}</div>` : ''}
      <div class="hitl-fields">
        ${fieldsHtml}
      </div>
      <div style="display:flex;justify-content:flex-end;gap:6px;margin-top:10px;padding-top:8px;border-top:1px solid #eee;">
        <button class="hitl-btn-reject" style="padding:5px 12px;border-radius:4px;font-size:11px;cursor:pointer;border:1px solid #ccc;background:#f5f5f5;color:#666;">
          ${escapeHtml(rejectLabel)}
        </button>
        <button class="hitl-btn-approve" style="padding:5px 12px;border-radius:4px;font-size:11px;cursor:pointer;border:none;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;">
          ${escapeHtml(approveLabel)}
        </button>
      </div>
    </div>
  `;
}

/**
 * 显示 HITL 表单错误信息
 */
function showHITLError(formContainer: HTMLElement, errorMessage: string): void {
  // Remove any existing error message
  const existingError = formContainer.querySelector('.hitl-error-msg');
  if (existingError) {
    existingError.remove();
  }

  // Create error element
  const errorEl = document.createElement('div');
  errorEl.className = 'hitl-error-msg';
  errorEl.style.cssText = `
    color: #dc2626;
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 4px;
    padding: 8px 12px;
    margin: 8px 0;
    font-size: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
  `;
  errorEl.innerHTML = `
    <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor">
      <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
    </svg>
    <span>${escapeHtml(errorMessage)}</span>
  `;

  // Insert before the action buttons
  const actionsDiv = formContainer.querySelector('div:last-child');
  if (actionsDiv) {
    actionsDiv.parentNode?.insertBefore(errorEl, actionsDiv);
  } else {
    formContainer.appendChild(errorEl);
  }

  // Auto-remove after 5 seconds
  setTimeout(() => {
    errorEl.remove();
  }, 5000);
}

/**
 * 绑定内联 HITL 表单事件
 */
export function bindHITLFormEvents(
  hitlRequest: HITLRequest,
  onComplete?: (result: HITLResult) => void
): void {
  const shadowRoot = document.getElementById('WENKO__CONTAINER-ROOT')?.shadowRoot;
  if (!shadowRoot) {
    hitlLog('BIND_EVENTS_ERROR', 'shadowRoot not found');
    return;
  }

  const formContainer = shadowRoot.querySelector(`.wenko-hitl-inline[data-hitl-id="${hitlRequest.id}"]`) as HTMLElement;
  if (!formContainer) {
    hitlLog('BIND_EVENTS_ERROR', 'form container not found');
    return;
  }

  hitlLog('BIND_EVENTS_START', { id: hitlRequest.id });

  const formData: Record<string, any> = {};

  // Initialize checkbox arrays and boolean defaults
  hitlRequest.fields?.forEach(field => {
    if (field.type === 'checkbox') {
      formData[field.name] = [];
    } else if (field.type === 'boolean') {
      formData[field.name] = false;
    } else if (field.type === 'slider' || (field.type === 'number' && field.min !== undefined)) {
      // Initialize slider with default value
      formData[field.name] = field.default ?? field.min ?? 0;
    }
  });

  // Bind field change events
  const fields = formContainer.querySelectorAll('.hitl-field');
  fields.forEach(el => {
    const fieldName = el.getAttribute('data-field');
    if (!fieldName) return;

    if (el.tagName === 'SELECT') {
      (el as HTMLSelectElement).onchange = () => {
        formData[fieldName] = (el as HTMLSelectElement).value;
        hitlLog('FIELD_CHANGE', { field: fieldName, value: formData[fieldName] });
      };
    } else if (el.tagName === 'INPUT') {
      const input = el as HTMLInputElement;
      if (input.type === 'radio') {
        input.onchange = () => {
          if (input.checked) {
            formData[fieldName] = input.value;
            hitlLog('FIELD_CHANGE', { field: fieldName, value: formData[fieldName] });
          }
        };
      } else if (input.type === 'checkbox') {
        // Check if this is a boolean field or a multi-select checkbox
        if (el.classList.contains('hitl-boolean')) {
          input.onchange = () => {
            formData[fieldName] = input.checked;
            hitlLog('FIELD_CHANGE', { field: fieldName, value: formData[fieldName] });
          };
        } else {
          input.onchange = () => {
            if (!Array.isArray(formData[fieldName])) {
              formData[fieldName] = [];
            }
            if (input.checked) {
              if (!formData[fieldName].includes(input.value)) {
                formData[fieldName].push(input.value);
              }
            } else {
              formData[fieldName] = formData[fieldName].filter((v: string) => v !== input.value);
            }
            hitlLog('FIELD_CHANGE', { field: fieldName, value: formData[fieldName] });
          };
        }
      } else if (input.type === 'range') {
        // Slider input
        input.oninput = () => {
          formData[fieldName] = parseFloat(input.value);
          // Update the value display
          const valueDisplay = el.parentElement?.querySelector('.hitl-slider-value');
          if (valueDisplay) {
            valueDisplay.textContent = input.value;
          }
          hitlLog('FIELD_CHANGE', { field: fieldName, value: formData[fieldName] });
        };
      } else {
        input.oninput = () => {
          formData[fieldName] = input.type === 'number' ? parseFloat(input.value) || input.value : input.value;
        };
      }
    } else if (el.tagName === 'TEXTAREA') {
      (el as HTMLTextAreaElement).oninput = () => {
        formData[fieldName] = (el as HTMLTextAreaElement).value;
      };
    }
  });

  // Bind button events
  const approveBtn = formContainer.querySelector('.hitl-btn-approve') as HTMLButtonElement;
  const rejectBtn = formContainer.querySelector('.hitl-btn-reject') as HTMLButtonElement;

  // Helper function to handle continuation after HITL response
  const handleContinuation = (continuationData: HITLContinuationData) => {
    hitlLog('AUTO_CONTINUATION_TRIGGERED', continuationData);

    // Build field labels from hitlRequest
    const fieldLabels: Record<string, string> = {};
    hitlRequest.fields?.forEach(field => {
      fieldLabels[field.name] = field.label;
    });

    // Update continuation data with field labels
    continuationData.field_labels = fieldLabels;

    triggerHITLContinuation(
      hitlRequest.session_id,
      continuationData,
      (chunk) => {
        showSSEMessage(chunk, 'wenko-chat-response');
      },
      () => {
        hitlLog('AUTO_CONTINUATION_DONE');
      },
      (error) => {
        showSSEMessage(`<div class="wenko-chat-error">错误: ${escapeHtml(error)}</div>`, 'wenko-chat-error-msg');
      },
      (newHitlRequest) => {
        // Handle chained HITL request
        hitlLog('CHAINED_HITL_REQUEST', { id: newHitlRequest.id, title: newHitlRequest.title });
        const formHtml = createHITLFormHtml(newHitlRequest);
        showSSEMessage(formHtml, 'wenko-hitl-form');

        // Recursively bind events for chained HITL
        setTimeout(() => {
          bindHITLFormEvents(newHitlRequest, onComplete);
        }, 50);
      }
    );
  };

  if (approveBtn) {
    approveBtn.onclick = async () => {
      hitlLog('ACTION_APPROVE', { requestId: hitlRequest.id, formData });
      approveBtn.disabled = true;
      rejectBtn.disabled = true;
      try {
        const result = await submitHITLResponse(hitlRequest.id, hitlRequest.session_id, 'approve', formData);

        // Check if response indicates an error (e.g., required field missing)
        if (!result.success && result.error) {
          hitlLog('VALIDATION_ERROR', { error: result.error });
          // Show error message in the form
          showHITLError(formContainer, result.error);
          approveBtn.disabled = false;
          rejectBtn.disabled = false;
          return;
        }

        formContainer.remove();
        onComplete?.({ action: 'approve', data: formData, result });

        // Auto-trigger continuation if continuation_data is present
        if (result.continuation_data) {
          handleContinuation(result.continuation_data as HITLContinuationData);
        }
      } catch (e) {
        console.error('Approve failed:', e);
        approveBtn.disabled = false;
        rejectBtn.disabled = false;
      }
    };
  }

  if (rejectBtn) {
    rejectBtn.onclick = async () => {
      hitlLog('ACTION_REJECT', { requestId: hitlRequest.id });
      approveBtn.disabled = true;
      rejectBtn.disabled = true;
      try {
        const result = await submitHITLResponse(hitlRequest.id, hitlRequest.session_id, 'reject', null);
        formContainer.remove();
        onComplete?.({ action: 'reject', result });

        // Auto-trigger continuation for reject as well
        if (result.continuation_data) {
          handleContinuation(result.continuation_data as HITLContinuationData);
        }
      } catch (e) {
        console.error('Reject failed:', e);
        approveBtn.disabled = false;
        rejectBtn.disabled = false;
      }
    };
  }

  hitlLog('BIND_EVENTS_DONE', { id: hitlRequest.id });
}

/**
 * 触发 HITL 继续对话
 * 在用户响应 HITL 表单后自动调用，让 AI 基于用户响应继续对话
 */
export function triggerHITLContinuation(
  sessionId: string,
  continuationData: HITLContinuationData,
  onChunk: (text: string) => void,
  onDone?: () => void,
  onError?: (error: string) => void,
  onHITL?: (hitlRequest: HITLRequest) => void
): void {
  hitlLog('CONTINUATION_START', { sessionId, continuationData });

  // Prevent multiple concurrent requests
  if (isLoading) {
    hitlLog('CONTINUATION_BLOCKED', 'Already loading');
    return;
  }
  isLoading = true;

  // Show loading indicator - specialized message for HITL form submission
  hitlLog('CONTINUATION_SHOW_LOADING', 'Calling showSSEMessage for loading indicator');
  showSSEMessage('<div class="wenko-chat-loading">AI 正在分析您的信息...</div>', 'wenko-chat-loading-msg');
  hitlLog('CONTINUATION_SHOW_LOADING_DONE', 'showSSEMessage called');

  let assistantResponse = '';

  // Helper to remove loading indicator
  const removeLoadingIndicator = () => {
    const shadowRoot = document.getElementById('WENKO__CONTAINER-ROOT')?.shadowRoot;
    const loadingEl = shadowRoot?.querySelector('.wenko-chat-loading');
    if (loadingEl) {
      // Only remove the loading element itself, not its parent (which is #waifu-tips)
      loadingEl.remove();
    }
  };

  fetchEventSource(HITL_CONTINUE_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId,
      continuation_data: continuationData,
    }),
    openWhenHidden: true, // Keep connection even when page is hidden
    onopen: async (res: Response) => {
      hitlLog('CONTINUATION_SSE_OPEN', { status: res.status, ok: res.ok });
      // Don't remove loading here - wait for first text chunk
      if (res.ok) return;
      const text = await res.text();
      hitlLog('CONTINUATION_SSE_OPEN_ERROR', { status: res.status, text });
      removeLoadingIndicator();
      throw new Error(`HTTP ${res.status}: ${text}`);
    },
    onmessage: (event: { event: string; data: string }) => {
      hitlLog('CONTINUATION_SSE_EVENT', { event: event.event, dataLen: event.data?.length });
      try {
        if (event.event === 'text') {
          // Remove loading indicator on first text chunk
          removeLoadingIndicator();
          const data = JSON.parse(event.data);
          if (data.type === 'text' && data.payload?.content) {
            assistantResponse += data.payload.content;
            hitlLog('CONTINUATION_TEXT_CHUNK', { contentLen: data.payload.content.length, totalLen: assistantResponse.length });
            onChunk(data.payload.content);
          }
        } else if (event.event === 'hitl') {
          // Handle chained HITL request
          hitlLog('CONTINUATION_HITL_EVENT', event.data);
          const data = JSON.parse(event.data);
          if (data.type === 'hitl' && data.payload) {
            currentHITLRequest = data.payload as HITLRequest;
            hitlLog('CONTINUATION_HITL_PARSED', {
              id: currentHITLRequest.id,
              title: currentHITLRequest.title,
              fields: currentHITLRequest.fields?.length
            });
            onHITL?.(currentHITLRequest);
          }
        } else if (event.event === 'done') {
          // Add assistant response to local history
          if (assistantResponse) {
            historyManager.addMessage({ role: 'assistant', content: assistantResponse });
          }
          hitlLog('CONTINUATION_DONE', { responseLength: assistantResponse.length });
          isLoading = false;
          onDone?.();
        } else if (event.event === 'error') {
          const data = JSON.parse(event.data);
          const errorMsg = data.payload?.message || '未知错误';
          hitlLog('CONTINUATION_ERROR', { error: errorMsg });
          isLoading = false;
          onError?.(errorMsg);
        }
      } catch (e) {
        console.error('解析 continuation SSE 消息失败:', e);
        hitlLog('CONTINUATION_PARSE_ERROR', { error: String(e), data: event.data?.substring(0, 100) });
      }
    },
    onclose: () => {
      hitlLog('CONTINUATION_SSE_CLOSE', { isLoading, assistantResponseLength: assistantResponse.length });
      removeLoadingIndicator();
      if (isLoading) {
        if (assistantResponse) {
          historyManager.addMessage({ role: 'assistant', content: assistantResponse });
        }
        isLoading = false;
        onDone?.();
      }
    },
    onerror: (err: Error) => {
      console.error('Continuation SSE error:', err);
      hitlLog('CONTINUATION_SSE_ERROR', { message: err.message, name: err.name });
      removeLoadingIndicator();
      isLoading = false;
      onError?.(err.message || '连接错误');
      // Throw error to prevent automatic retry
      throw err;
    },
  });
}

// ============ Image Analysis Functions ============


/**
 * 压缩图片到指定大小
 */
async function compressImage(dataUrl: string, maxSize: number = MAX_IMAGE_SIZE): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      let { width, height } = img;

      // 计算压缩比例
      const originalSize = dataUrl.length * 0.75; // Base64 约为原始大小的 4/3
      if (originalSize <= maxSize) {
        resolve(dataUrl);
        return;
      }

      const ratio = Math.sqrt(maxSize / originalSize);
      width = Math.floor(width * ratio);
      height = Math.floor(height * ratio);

      canvas.width = width;
      canvas.height = height;

      const ctx = canvas.getContext('2d');
      if (!ctx) {
        reject(new Error('无法创建 canvas context'));
        return;
      }

      ctx.drawImage(img, 0, 0, width, height);

      // 使用 JPEG 格式压缩
      const compressed = canvas.toDataURL('image/jpeg', 0.8);
      resolve(compressed);
    };

    img.onerror = () => reject(new Error('图片加载失败'));
    img.src = dataUrl;
  });
}

/**
 * 将 File 对象转换为 Base64
 */
function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        resolve(reader.result);
      } else {
        reject(new Error('Failed to read file as base64'));
      }
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

/**
 * 发送图片分析请求
 */
export function sendImageMessage(
  imageData: string,
  action: 'analyze_only' | 'analyze_for_memory' = 'analyze_for_memory',
  onChunk: (text: string) => void,
  onDone?: () => void,
  onError?: (error: string) => void,
  onHITL?: (hitlRequest: HITLRequest) => void
): void {
  if (isLoading) return;

  isLoading = true;
  const sessionId = sessionManager.getSessionId();

  console.log('[Image] Sending image for analysis', { sessionId, action });

  fetchEventSource(IMAGE_CHAT_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      image: imageData,
      session_id: sessionId,
      action: action,
    }),
    onopen: (res: Response) => {
      console.log('[Image] SSE connection opened', { status: res.status });
      if (res.ok) return Promise.resolve();
      throw new Error(`HTTP ${res.status}`);
    },
    onmessage: (event: { event: string; data: string }) => {
      try {
        if (event.event === 'text') {
          const data = JSON.parse(event.data);
          if (data.type === 'text' && data.payload?.content) {
            onChunk(data.payload.content);
          }
        } else if (event.event === 'hitl') {
          const data = JSON.parse(event.data);
          if (data.type === 'hitl' && data.payload) {
            currentHITLRequest = data.payload as HITLRequest;
            onHITL?.(currentHITLRequest);
          }
        } else if (event.event === 'done') {
          isLoading = false;
          onDone?.();
        } else if (event.event === 'error') {
          const data = JSON.parse(event.data);
          const errorMsg = data.payload?.message || '未知错误';
          isLoading = false;
          onError?.(errorMsg);
        }
      } catch (e) {
        console.error('解析图片分析 SSE 消息失败:', e);
      }
    },
    onclose: () => {
      if (isLoading) {
        isLoading = false;
        onDone?.();
      }
    },
    onerror: (err: Error) => {
      console.error('Image analysis SSE error:', err);
      isLoading = false;
      onError?.(err.message || '连接错误');
    },
  });
}

/**
 * 处理图片粘贴事件 - 使用 Electron 新窗口
 */
export async function handleImagePaste(
  event: ClipboardEvent,
  shadowRoot: ShadowRoot,
  chatInputContainer: HTMLElement
): Promise<boolean> {
  const items = event.clipboardData?.items;
  if (!items) return false;

  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    if (item.type.startsWith('image/')) {
      event.preventDefault();

      const file = item.getAsFile();
      if (!file) continue;

      try {
        // 转换为 Base64
        let base64Data = await fileToBase64(file);

        // 检查并压缩大图片
        const originalSize = base64Data.length * 0.75;
        if (originalSize > MAX_IMAGE_SIZE) {
          console.log('[Image] Compressing large image', { originalSize });
          base64Data = await compressImage(base64Data);
        }

        const sessionId = sessionManager.getSessionId();

        // 使用 Electron IPC 打开图片预览窗口
        if (window.electronAPI?.invoke) {
          console.log('[Image] Opening preview window via IPC');

          window.electronAPI.invoke('image-preview:open', {
            imageData: base64Data,
            sessionId: sessionId,
          }).then((result: { success: boolean }) => {
            if (result.success) {
              console.log('[Image] Preview window opened');
            }
          }).catch((error: Error) => {
            console.error('[Image] Failed to open preview window:', error);
            showSSEMessage('<div class="wenko-chat-error">无法打开图片预览窗口</div>', 'wenko-chat-error-msg');
          });
        } else {
          // 非 Electron 环境的回退处理
          console.log('[Image] electronAPI not available, using inline preview');
          showSSEMessage('<div class="wenko-chat-system">请在 Electron 环境中使用图片粘贴功能</div>', 'wenko-chat-system-msg');
        }

        return true;
      } catch (error) {
        console.error('[Image] Failed to process pasted image:', error);
        showSSEMessage('<div class="wenko-chat-error">图片处理失败</div>', 'wenko-chat-error-msg');
      }
    }
  }

  return false;
}
