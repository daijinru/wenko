/**
 * @file Contains functions for displaying waifu messages.
 * @module message
 */

import { randomSelection } from './utils.js';

type Time = {
  /**
   * Time period, format is "HH-HH", e.g. "00-06" means from 0 to 6 o'clock.
   * @type {string}
   */
  hour: string;
  /**
   * Message to display during this time period.
   * @type {string}
   */
  text: string;
}[];

let messageTimer: NodeJS.Timeout | null = null;

/**
 * Display waifu message.
 * @param {string | string[]} text - Message text or array of texts.
 * @param {number} timeout - Timeout for message display (ms).
 * @param {number} priority - Priority of the message.
 * @param {boolean} [override=true] - Whether to override existing message.
 */
function showMessage(
  text: string | string[],
  timeout: number,
  priority: number,
  override: boolean = true
) {
  // let currentPriority = parseInt(sessionStorage.getItem('waifu-message-priority'), 10);
  // if (isNaN(currentPriority)) {
  //   currentPriority = 0;
  // }
  // if (
  //   !text ||
  //   (override && currentPriority > priority) ||
  //   (!override && currentPriority >= priority)
  // )
  //   return;
  // if (messageTimer) {
  //   clearTimeout(messageTimer);
  //   messageTimer = null;
  // }
  // text = randomSelection(text) as string;
  // sessionStorage.setItem('waifu-message-priority', String(priority));
  // // 从 shadow dom 中获取 tips 元素
  // const shadowRoot = document.getElementById('WENKO__CONTAINER-ROOT')?.shadowRoot;
  // if (!shadowRoot) return;
  // const tips = shadowRoot.getElementById('waifu-tips');
  // tips.innerHTML = text;
  // tips.classList.add('waifu-tips-active');
  // messageTimer = setTimeout(() => {
  //   sessionStorage.removeItem('waifu-message-priority');
  //   tips.classList.remove('waifu-tips-active');
  // }, timeout);
}

/**
 * Display or append SSE message in waifu message bubble.
 * @param {string} text - Text fragment to display or append.
 * @param {string} id - Unique identifier for this SSE message session.
 */
function showSSEMessage(text: string, id: string, timeout: number = 60000) {
  // Debug logging
  console.log(`[showSSEMessage] id=${id}, textLen=${text.length}`);

  // 从 shadow dom 中获取 tips 元素
  const shadowRoot = document.getElementById('WENKO__CONTAINER-ROOT')?.shadowRoot;
  if (!shadowRoot) {
    console.warn('[showSSEMessage] shadowRoot not found');
    return;
  }
  const tips = shadowRoot.getElementById('waifu-tips');
  if (!tips) {
    console.warn('[showSSEMessage] waifu-tips element not found');
    return;
  }

  console.log(`[showSSEMessage] tips found, currentSSEId=${tips.getAttribute('data-sse-id')}`);

  // 滚动 tips 到最底部，使用异步确保内容更新后滚动
  setTimeout(() => {
    tips.scrollTop = tips.scrollHeight;
  }, 0);

  // 检查当前的 sse id
  const currentSSEId = tips.getAttribute('data-sse-id');

  // Loading 消息每次都应该重置，而不是追加
  const isLoadingMessage = id.includes('loading');

  if (currentSSEId === id && !isLoadingMessage) {
    // 同一个 id 且不是 loading 消息，追加文本
    tips.innerHTML += text;
  } else {
    // 新的 id 或 loading 消息，重置内容
    tips.classList.remove('waifu-tips-active');
    tips.removeAttribute('data-sse-id');
    // 重置内容
    tips.innerHTML = text;
    tips.setAttribute('data-sse-id', id);
    // 激活新消息
    setTimeout(() => {
      tips.classList.add('waifu-tips-active');
    }, 10);
  }
  // tips.classList.add('waifu-tips-active');
}

/**
 * Show welcome message based on time.
 * @param {Time} time - Time message configuration.
 * @returns {string} Welcome message.
 */
function welcomeMessage(time: Time, welcomeTemplate: string, referrerTemplate: string): string {
  if (location.pathname === '/') {
    // If on the homepage
    for (const { hour, text } of time) {
      const now = new Date(),
        after = hour.split('-')[0],
        before = hour.split('-')[1] || after;
      if (
        Number(after) <= now.getHours() &&
        now.getHours() <= Number(before)
      ) {
        return text;
      }
    }
  }
  const text = i18n(welcomeTemplate, document.title);
  if (document.referrer !== '') {
    const referrer = new URL(document.referrer);
    if (location.hostname === referrer.hostname) return text;
    return `${i18n(referrerTemplate, referrer.hostname)}<br>${text}`;
  }
  return text;
}

function i18n(template: string, ...args: string[]) {
  return template.replace(/\$(\d+)/g, (_, idx) => {
    const i = parseInt(idx, 10) - 1;
    return args[i] ?? '';
  });
}

/**
 * Show memory saved notification as a toast-like message.
 * @param {number} count - Number of memories saved.
 * @param {Array} entries - Saved memory entries.
 */
function showMemoryNotification(count: number, entries: Array<{ key: string; category: string }>) {
  const shadowRoot = document.getElementById('WENKO__CONTAINER-ROOT')?.shadowRoot;
  if (!shadowRoot) return;

  // Create or get notification container
  let notificationContainer = shadowRoot.getElementById('memory-notification');
  if (!notificationContainer) {
    notificationContainer = document.createElement('div');
    notificationContainer.id = 'memory-notification';
    notificationContainer.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 12px 16px;
      border-radius: 8px;
      font-size: 13px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      z-index: 10000;
      opacity: 0;
      transform: translateY(20px);
      transition: all 0.3s ease;
      max-width: 280px;
    `;
    shadowRoot.appendChild(notificationContainer);
  }

  // Format entries for display
  const entryLabels = entries.slice(0, 3).map(e => e.key).join('、');
  const suffix = entries.length > 3 ? '...' : '';
  notificationContainer.innerHTML = `
    <div style="font-weight: bold; margin-bottom: 4px;">已自动保存 ${count} 条记忆</div>
    <div style="font-size: 12px; opacity: 0.9;">${entryLabels}${suffix}</div>
  `;

  // Show notification
  setTimeout(() => {
    notificationContainer!.style.opacity = '1';
    notificationContainer!.style.transform = 'translateY(0)';
  }, 10);

  // Hide after 3 seconds
  setTimeout(() => {
    notificationContainer!.style.opacity = '0';
    notificationContainer!.style.transform = 'translateY(20px)';
  }, 3000);
}

export { showMessage, showSSEMessage, welcomeMessage, i18n, showMemoryNotification, Time };
