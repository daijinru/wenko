import { fetchEventSource } from "https://esm.sh/@microsoft/fetch-event-source";
import { showSSEMessage } from './message.js';
const CHAT_API_URL = 'http://localhost:8002/chat';
const MAX_HISTORY_LENGTH = 10;
const SESSION_ID_KEY = 'wenko-chat-session-id';
const HISTORY_KEY = 'wenko-chat-history';
const EMOTION_DISPLAY = {
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
let currentEmotion = null;
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}
class SessionManager {
    getSessionId() {
        let sessionId = localStorage.getItem(SESSION_ID_KEY);
        if (!sessionId) {
            sessionId = generateUUID();
            localStorage.setItem(SESSION_ID_KEY, sessionId);
        }
        return sessionId;
    }
    createNewSession() {
        const sessionId = generateUUID();
        localStorage.setItem(SESSION_ID_KEY, sessionId);
        localStorage.removeItem(HISTORY_KEY);
        return sessionId;
    }
    clearSession() {
        localStorage.removeItem(SESSION_ID_KEY);
        localStorage.removeItem(HISTORY_KEY);
    }
}
class ChatHistoryManager {
    getHistory() {
        try {
            const data = localStorage.getItem(HISTORY_KEY);
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
        localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    }
    clearHistory() {
        localStorage.removeItem(HISTORY_KEY);
    }
}
const sessionManager = new SessionManager();
const historyManager = new ChatHistoryManager();
let isLoading = false;
export function getSessionId() {
    return sessionManager.getSessionId();
}
export function createNewSession() {
    return sessionManager.createNewSession();
}
export function sendChatMessage(message, onChunk, onDone, onError, onEmotion) {
    if (isLoading)
        return;
    if (!message.trim())
        return;
    isLoading = true;
    const sessionId = sessionManager.getSessionId();
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
                else if (event.event === 'emotion') {
                    const data = JSON.parse(event.data);
                    if (data.type === 'emotion' && data.payload) {
                        currentEmotion = {
                            primary: data.payload.primary,
                            category: data.payload.category,
                            confidence: data.payload.confidence,
                        };
                        onEmotion === null || onEmotion === void 0 ? void 0 : onEmotion(currentEmotion);
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
    sessionManager.createNewSession();
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
export function getCurrentEmotion() {
    return currentEmotion;
}
export function getEmotionDisplay(emotion) {
    return EMOTION_DISPLAY[emotion] || { label: emotion, color: '#9ca3af' };
}
export function createEmotionIndicator(shadowRoot) {
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
export function updateEmotionIndicator(container, emotion) {
    const display = getEmotionDisplay(emotion.primary);
    const dot = container.querySelector('.emotion-dot');
    const label = container.querySelector('.emotion-label');
    const confidence = container.querySelector('.emotion-confidence');
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
export function hideEmotionIndicator(container) {
    container.style.display = 'none';
}
