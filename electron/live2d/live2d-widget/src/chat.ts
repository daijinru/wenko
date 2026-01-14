/**
 * @file Chat module for Live2D AI conversation.
 * @module chat
 */

// @ts-ignore
import { fetchEventSource } from "https://esm.sh/@microsoft/fetch-event-source";
import { showSSEMessage } from './message.js';

const CHAT_API_URL = 'http://localhost:8002/chat';
const MAX_HISTORY_LENGTH = 10;

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

/**
 * ChatHistoryManager - 管理对话历史
 */
class ChatHistoryManager {
  private storageKey = 'wenko-chat-history';

  getHistory(): ChatMessage[] {
    try {
      const data = sessionStorage.getItem(this.storageKey);
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

    sessionStorage.setItem(this.storageKey, JSON.stringify(history));
  }

  clearHistory(): void {
    sessionStorage.removeItem(this.storageKey);
  }
}

const historyManager = new ChatHistoryManager();

let isLoading = false;

/**
 * 发送对话消息并处理 SSE 流式响应
 */
export function sendChatMessage(
  message: string,
  onChunk: (text: string) => void,
  onDone?: () => void,
  onError?: (error: string) => void
): void {
  if (isLoading) return;
  if (!message.trim()) return;

  isLoading = true;

  // 添加用户消息到历史
  historyManager.addMessage({ role: 'user', content: message });

  let assistantResponse = '';

  fetchEventSource(CHAT_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message: message,
      history: historyManager.getHistory().slice(0, -1), // 不包含刚添加的用户消息
    }),
    onopen: (res: Response) => {
      if (res.ok) return Promise.resolve();
      throw new Error(`HTTP ${res.status}`);
    },
    onmessage: (event: { event: string; data: string }) => {
      try {
        if (event.event === 'text') {
          const data = JSON.parse(event.data);
          if (data.type === 'text' && data.payload?.content) {
            assistantResponse += data.payload.content;
            onChunk(data.payload.content);
          }
        } else if (event.event === 'done') {
          // 添加助手响应到历史
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
        // 添加助手响应到历史
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
 * 清除对话历史
 */
export function clearChatHistory(): void {
  historyManager.clearHistory();
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
      }
    );
  };

  sendBtn.addEventListener('click', handleSend);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  return container;
}

function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
