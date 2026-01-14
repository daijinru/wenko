import { fetchEventSource } from "https://esm.sh/@microsoft/fetch-event-source";
import { showSSEMessage } from './message.js';
const CHAT_API_URL = 'http://localhost:8002/chat';
const MAX_HISTORY_LENGTH = 10;
class ChatHistoryManager {
    constructor() {
        this.storageKey = 'wenko-chat-history';
    }
    getHistory() {
        try {
            const data = sessionStorage.getItem(this.storageKey);
            return data ? JSON.parse(data) : [];
        }
        catch (_a) {
            return [];
        }
    }
    addMessage(message) {
        const history = this.getHistory();
        history.push(message);
        const maxMessages = MAX_HISTORY_LENGTH * 2;
        if (history.length > maxMessages) {
            history.splice(0, history.length - maxMessages);
        }
        sessionStorage.setItem(this.storageKey, JSON.stringify(history));
    }
    clearHistory() {
        sessionStorage.removeItem(this.storageKey);
    }
}
const historyManager = new ChatHistoryManager();
let isLoading = false;
export function sendChatMessage(message, onChunk, onDone, onError) {
    if (isLoading)
        return;
    if (!message.trim())
        return;
    isLoading = true;
    historyManager.addMessage({ role: 'user', content: message });
    let assistantResponse = '';
    fetchEventSource(CHAT_API_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: message,
            history: historyManager.getHistory().slice(0, -1),
        }),
        onopen: (res) => {
            if (res.ok)
                return Promise.resolve();
            throw new Error(`HTTP ${res.status}`);
        },
        onmessage: (event) => {
            var _a, _b;
            try {
                if (event.event === 'text') {
                    const data = JSON.parse(event.data);
                    if (data.type === 'text' && ((_a = data.payload) === null || _a === void 0 ? void 0 : _a.content)) {
                        assistantResponse += data.payload.content;
                        onChunk(data.payload.content);
                    }
                }
                else if (event.event === 'done') {
                    if (assistantResponse) {
                        historyManager.addMessage({ role: 'assistant', content: assistantResponse });
                    }
                    isLoading = false;
                    onDone === null || onDone === void 0 ? void 0 : onDone();
                }
                else if (event.event === 'error') {
                    const data = JSON.parse(event.data);
                    const errorMsg = ((_b = data.payload) === null || _b === void 0 ? void 0 : _b.message) || '未知错误';
                    isLoading = false;
                    onError === null || onError === void 0 ? void 0 : onError(errorMsg);
                }
            }
            catch (e) {
                console.error('解析 SSE 消息失败:', e);
            }
        },
        onclose: () => {
            if (isLoading) {
                if (assistantResponse) {
                    historyManager.addMessage({ role: 'assistant', content: assistantResponse });
                }
                isLoading = false;
                onDone === null || onDone === void 0 ? void 0 : onDone();
            }
        },
        onerror: (err) => {
            console.error('Chat SSE error:', err);
            isLoading = false;
            onError === null || onError === void 0 ? void 0 : onError(err.message || '连接错误');
        },
    });
}
export function isChatLoading() {
    return isLoading;
}
export function clearChatHistory() {
    historyManager.clearHistory();
}
export function createChatInput(shadowRoot) {
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
    const input = container.querySelector('#wenko-chat-text');
    const sendBtn = container.querySelector('#wenko-chat-send');
    const handleSend = () => {
        const text = input.value.trim();
        if (!text || isLoading)
            return;
        input.value = '';
        input.disabled = true;
        sendBtn.disabled = true;
        showSSEMessage(`<div class="wenko-chat-user">${escapeHtml(text)}</div>`, 'wenko-chat-user-msg');
        sendChatMessage(text, (chunk) => {
            showSSEMessage(chunk, 'wenko-chat-response');
        }, () => {
            input.disabled = false;
            sendBtn.disabled = false;
            input.focus();
        }, (error) => {
            showSSEMessage(`<div class="wenko-chat-error">错误: ${escapeHtml(error)}</div>`, 'wenko-chat-error-msg');
            input.disabled = false;
            sendBtn.disabled = false;
            input.focus();
        });
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
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
