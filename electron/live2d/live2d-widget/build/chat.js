import { fetchEventSource } from "https://esm.sh/@microsoft/fetch-event-source";
import { showSSEMessage } from './message.js';
const CHAT_API_URL = 'http://localhost:8002/chat';
const HITL_API_URL = 'http://localhost:8002/hitl/respond';
const MAX_HISTORY_LENGTH = 10;
const SESSION_ID_KEY = 'wenko-chat-session-id';
const HISTORY_KEY = 'wenko-chat-history';
const HITL_DEBUG = true;
function hitlLog(stage, data) {
    if (HITL_DEBUG) {
        console.log(`[HITL] ${stage}:`, data);
    }
}
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
let currentHITLRequest = null;
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
export function sendChatMessage(message, onChunk, onDone, onError, onEmotion, onHITL) {
    if (isLoading)
        return;
    if (!message.trim())
        return;
    isLoading = true;
    const sessionId = sessionManager.getSessionId();
    hitlLog('SEND_MESSAGE', { message, sessionId });
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
            hitlLog('SSE_OPEN', { status: res.status });
            if (res.ok)
                return Promise.resolve();
            throw new Error(`HTTP ${res.status}`);
        },
        onmessage: (event) => {
            var _a, _b, _c, _d;
            hitlLog('SSE_EVENT', { event: event.event, data: (_a = event.data) === null || _a === void 0 ? void 0 : _a.substring(0, 200) });
            try {
                if (event.event === 'text') {
                    const data = JSON.parse(event.data);
                    if (data.type === 'text' && ((_b = data.payload) === null || _b === void 0 ? void 0 : _b.content)) {
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
                else if (event.event === 'hitl') {
                    hitlLog('HITL_EVENT_RECEIVED', event.data);
                    const data = JSON.parse(event.data);
                    if (data.type === 'hitl' && data.payload) {
                        currentHITLRequest = data.payload;
                        hitlLog('HITL_REQUEST_PARSED', {
                            id: currentHITLRequest.id,
                            title: currentHITLRequest.title,
                            fields: (_c = currentHITLRequest.fields) === null || _c === void 0 ? void 0 : _c.length
                        });
                        onHITL === null || onHITL === void 0 ? void 0 : onHITL(currentHITLRequest);
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
                    const errorMsg = ((_d = data.payload) === null || _d === void 0 ? void 0 : _d.message) || '未知错误';
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
        }, undefined, (hitlRequest) => {
            hitlLog('HITL_CALLBACK_TRIGGERED', { id: hitlRequest.id, title: hitlRequest.title });
            const formHtml = createHITLFormHtml(hitlRequest);
            showSSEMessage(formHtml, 'wenko-hitl-form');
            setTimeout(() => {
                bindHITLFormEvents(hitlRequest, (result) => {
                    var _a;
                    hitlLog('HITL_FORM_COMPLETED', result);
                    if (result.action === 'approve' && ((_a = result.result) === null || _a === void 0 ? void 0 : _a.message)) {
                        showSSEMessage(`<div class="wenko-chat-system">${escapeHtml(result.result.message)}</div>`, 'wenko-chat-system-msg');
                    }
                    else if (result.action === 'reject') {
                        showSSEMessage(`<div class="wenko-chat-system">已跳过</div>`, 'wenko-chat-system-msg');
                    }
                });
            }, 50);
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
export function getCurrentHITLRequest() {
    return currentHITLRequest;
}
export function clearHITLRequest() {
    currentHITLRequest = null;
}
export async function submitHITLResponse(requestId, sessionId, action, data) {
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
    }
    catch (error) {
        hitlLog('SUBMIT_EXCEPTION', { message: error.message });
        throw error;
    }
}
export function createHITLForm(hitlRequest, onComplete) {
    var _a, _b, _c, _d, _e, _f;
    hitlLog('CREATE_FORM_START', { id: hitlRequest.id, fields: (_a = hitlRequest.fields) === null || _a === void 0 ? void 0 : _a.length });
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
    const formContent = document.createElement('div');
    formContent.style.cssText = `
    padding: 8px 16px;
    max-height: 250px;
    overflow-y: auto;
  `;
    const formData = {};
    (_b = hitlRequest.fields) === null || _b === void 0 ? void 0 : _b.forEach(field => {
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
        }
        else if (field.type === 'radio' && field.options) {
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
        }
        else if (field.type === 'checkbox' && field.options) {
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
                    }
                    else {
                        formData[field.name] = formData[field.name].filter((v) => v !== opt.value);
                    }
                    hitlLog('FIELD_CHANGE', { field: field.name, value: formData[field.name] });
                };
                checkLabel.appendChild(checkbox);
                checkLabel.appendChild(document.createTextNode(opt.label));
                checkGroup.appendChild(checkLabel);
            });
            fieldDiv.appendChild(checkGroup);
        }
        else if (field.type === 'textarea') {
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
        }
        else {
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
    const actions = document.createElement('div');
    actions.style.cssText = `
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 12px 16px;
    border-top: 1px solid #eee;
    background: #fafafa;
  `;
    const createButton = (text, style, onClick) => {
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
    const rejectBtn = createButton(((_d = (_c = hitlRequest.actions) === null || _c === void 0 ? void 0 : _c.reject) === null || _d === void 0 ? void 0 : _d.label) || '跳过', 'background: #f3f4f6; color: #374151;', async () => {
        hitlLog('ACTION_REJECT', { requestId: hitlRequest.id });
        try {
            await submitHITLResponse(hitlRequest.id, hitlRequest.session_id, 'reject', null);
            container.remove();
            onComplete === null || onComplete === void 0 ? void 0 : onComplete({ action: 'reject' });
        }
        catch (e) {
            console.error('Reject failed:', e);
        }
    });
    const approveBtn = createButton(((_f = (_e = hitlRequest.actions) === null || _e === void 0 ? void 0 : _e.approve) === null || _f === void 0 ? void 0 : _f.label) || '确认', 'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;', async () => {
        hitlLog('ACTION_APPROVE', { requestId: hitlRequest.id, formData });
        try {
            const result = await submitHITLResponse(hitlRequest.id, hitlRequest.session_id, 'approve', formData);
            container.remove();
            onComplete === null || onComplete === void 0 ? void 0 : onComplete({ action: 'approve', data: formData, result });
        }
        catch (e) {
            console.error('Approve failed:', e);
        }
    });
    actions.appendChild(rejectBtn);
    actions.appendChild(approveBtn);
    container.appendChild(actions);
    hitlLog('CREATE_FORM_DONE', { id: hitlRequest.id });
    return container;
}
export function createHITLFormHtml(hitlRequest) {
    var _a, _b, _c, _d, _e, _f;
    hitlLog('CREATE_INLINE_FORM', { id: hitlRequest.id, fields: (_a = hitlRequest.fields) === null || _a === void 0 ? void 0 : _a.length });
    let fieldsHtml = '';
    (_b = hitlRequest.fields) === null || _b === void 0 ? void 0 : _b.forEach(field => {
        let fieldHtml = '';
        if (field.type === 'select' && field.options) {
            const optionsHtml = field.options.map(opt => `<option value="${escapeHtml(opt.value)}">${escapeHtml(opt.label)}</option>`).join('');
            fieldHtml = `
        <select class="hitl-field" data-field="${escapeHtml(field.name)}" style="width:100%;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:12px;background:transparent;">
          <option value="">请选择...</option>
          ${optionsHtml}
        </select>
      `;
        }
        else if (field.type === 'radio' && field.options) {
            const optionsHtml = field.options.map(opt => `<label style="display:inline-flex;align-items:center;gap:3px;margin-right:8px;font-size:11px;cursor:pointer;">
          <input type="radio" name="hitl_${escapeHtml(field.name)}" value="${escapeHtml(opt.value)}" class="hitl-field" data-field="${escapeHtml(field.name)}" style="margin:0;">
          ${escapeHtml(opt.label)}
        </label>`).join('');
            fieldHtml = `<div style="display:flex;flex-wrap:wrap;gap:4px;">${optionsHtml}</div>`;
        }
        else if (field.type === 'checkbox' && field.options) {
            const optionsHtml = field.options.map(opt => `<label style="display:inline-flex;align-items:center;gap:3px;margin-right:8px;font-size:11px;cursor:pointer;">
          <input type="checkbox" value="${escapeHtml(opt.value)}" class="hitl-field hitl-checkbox" data-field="${escapeHtml(field.name)}" style="margin:0;">
          ${escapeHtml(opt.label)}
        </label>`).join('');
            fieldHtml = `<div style="display:flex;flex-wrap:wrap;gap:4px;">${optionsHtml}</div>`;
        }
        else if (field.type === 'textarea') {
            fieldHtml = `
        <textarea class="hitl-field" data-field="${escapeHtml(field.name)}" placeholder="${escapeHtml(field.placeholder || '')}"
          style="width:100%;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:12px;resize:vertical;min-height:40px;"></textarea>
      `;
        }
        else {
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
    const approveLabel = ((_d = (_c = hitlRequest.actions) === null || _c === void 0 ? void 0 : _c.approve) === null || _d === void 0 ? void 0 : _d.label) || '确认';
    const rejectLabel = ((_f = (_e = hitlRequest.actions) === null || _e === void 0 ? void 0 : _e.reject) === null || _f === void 0 ? void 0 : _f.label) || '跳过';
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
export function bindHITLFormEvents(hitlRequest, onComplete) {
    var _a, _b;
    const shadowRoot = (_a = document.getElementById('WENKO__CONTAINER-ROOT')) === null || _a === void 0 ? void 0 : _a.shadowRoot;
    if (!shadowRoot) {
        hitlLog('BIND_EVENTS_ERROR', 'shadowRoot not found');
        return;
    }
    const formContainer = shadowRoot.querySelector(`.wenko-hitl-inline[data-hitl-id="${hitlRequest.id}"]`);
    if (!formContainer) {
        hitlLog('BIND_EVENTS_ERROR', 'form container not found');
        return;
    }
    hitlLog('BIND_EVENTS_START', { id: hitlRequest.id });
    const formData = {};
    (_b = hitlRequest.fields) === null || _b === void 0 ? void 0 : _b.forEach(field => {
        if (field.type === 'checkbox') {
            formData[field.name] = [];
        }
    });
    const fields = formContainer.querySelectorAll('.hitl-field');
    fields.forEach(el => {
        const fieldName = el.getAttribute('data-field');
        if (!fieldName)
            return;
        if (el.tagName === 'SELECT') {
            el.onchange = () => {
                formData[fieldName] = el.value;
                hitlLog('FIELD_CHANGE', { field: fieldName, value: formData[fieldName] });
            };
        }
        else if (el.tagName === 'INPUT') {
            const input = el;
            if (input.type === 'radio') {
                input.onchange = () => {
                    if (input.checked) {
                        formData[fieldName] = input.value;
                        hitlLog('FIELD_CHANGE', { field: fieldName, value: formData[fieldName] });
                    }
                };
            }
            else if (input.type === 'checkbox') {
                input.onchange = () => {
                    if (input.checked) {
                        if (!formData[fieldName].includes(input.value)) {
                            formData[fieldName].push(input.value);
                        }
                    }
                    else {
                        formData[fieldName] = formData[fieldName].filter((v) => v !== input.value);
                    }
                    hitlLog('FIELD_CHANGE', { field: fieldName, value: formData[fieldName] });
                };
            }
            else {
                input.oninput = () => {
                    formData[fieldName] = input.value;
                };
            }
        }
        else if (el.tagName === 'TEXTAREA') {
            el.oninput = () => {
                formData[fieldName] = el.value;
            };
        }
    });
    const approveBtn = formContainer.querySelector('.hitl-btn-approve');
    const rejectBtn = formContainer.querySelector('.hitl-btn-reject');
    if (approveBtn) {
        approveBtn.onclick = async () => {
            hitlLog('ACTION_APPROVE', { requestId: hitlRequest.id, formData });
            approveBtn.disabled = true;
            rejectBtn.disabled = true;
            try {
                const result = await submitHITLResponse(hitlRequest.id, hitlRequest.session_id, 'approve', formData);
                formContainer.remove();
                onComplete === null || onComplete === void 0 ? void 0 : onComplete({ action: 'approve', data: formData, result });
            }
            catch (e) {
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
                await submitHITLResponse(hitlRequest.id, hitlRequest.session_id, 'reject', null);
                formContainer.remove();
                onComplete === null || onComplete === void 0 ? void 0 : onComplete({ action: 'reject' });
            }
            catch (e) {
                console.error('Reject failed:', e);
                approveBtn.disabled = false;
                rejectBtn.disabled = false;
            }
        };
    }
    hitlLog('BIND_EVENTS_DONE', { id: hitlRequest.id });
}
