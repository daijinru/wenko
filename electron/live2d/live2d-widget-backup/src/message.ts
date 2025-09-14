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
  // 从 shadow dom 中获取 tips 元素
  const shadowRoot = document.getElementById('WENKO__CONTAINER-ROOT')?.shadowRoot;
  if (!shadowRoot) return;
  const tips = shadowRoot.getElementById('waifu-tips');
  if (!tips) return;

  // 滚动 tips 到最底部，使用异步确保内容更新后滚动
  setTimeout(() => {
    tips.scrollTop = tips.scrollHeight;
  }, 0);

  // 检查当前的 sse id
  const currentSSEId = tips.getAttribute('data-sse-id');
  if (currentSSEId === id) {
    // 同一个 id，追加文本
    tips.innerHTML += text;
  } else {
    // 新的 id，销毁前一个消息
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

export { showMessage, showSSEMessage, welcomeMessage, i18n, Time };
