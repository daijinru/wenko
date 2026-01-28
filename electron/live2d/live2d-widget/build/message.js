let messageTimer = null;
function showMessage(text, timeout, priority, override = true) {
}
function showSSEMessage(text, id, timeout = 60000) {
    var _a;
    console.log(`[showSSEMessage] id=${id}, textLen=${text.length}`);
    const shadowRoot = (_a = document.getElementById('WENKO__CONTAINER-ROOT')) === null || _a === void 0 ? void 0 : _a.shadowRoot;
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
    setTimeout(() => {
        tips.scrollTop = tips.scrollHeight;
    }, 0);
    const currentSSEId = tips.getAttribute('data-sse-id');
    const isLoadingMessage = id.includes('loading');
    if (currentSSEId === id && !isLoadingMessage) {
        tips.innerHTML += text;
    }
    else {
        tips.classList.remove('waifu-tips-active');
        tips.removeAttribute('data-sse-id');
        tips.innerHTML = text;
        tips.setAttribute('data-sse-id', id);
        setTimeout(() => {
            tips.classList.add('waifu-tips-active');
        }, 10);
    }
}
function welcomeMessage(time, welcomeTemplate, referrerTemplate) {
    if (location.pathname === '/') {
        for (const { hour, text } of time) {
            const now = new Date(), after = hour.split('-')[0], before = hour.split('-')[1] || after;
            if (Number(after) <= now.getHours() &&
                now.getHours() <= Number(before)) {
                return text;
            }
        }
    }
    const text = i18n(welcomeTemplate, document.title);
    if (document.referrer !== '') {
        const referrer = new URL(document.referrer);
        if (location.hostname === referrer.hostname)
            return text;
        return `${i18n(referrerTemplate, referrer.hostname)}<br>${text}`;
    }
    return text;
}
function i18n(template, ...args) {
    return template.replace(/\$(\d+)/g, (_, idx) => {
        var _a;
        const i = parseInt(idx, 10) - 1;
        return (_a = args[i]) !== null && _a !== void 0 ? _a : '';
    });
}
function showMemoryNotification(count, entries) {
    var _a;
    const shadowRoot = (_a = document.getElementById('WENKO__CONTAINER-ROOT')) === null || _a === void 0 ? void 0 : _a.shadowRoot;
    if (!shadowRoot)
        return;
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
    const entryLabels = entries.slice(0, 3).map(e => e.key).join('、');
    const suffix = entries.length > 3 ? '...' : '';
    notificationContainer.innerHTML = `
    <div style="font-weight: bold; margin-bottom: 4px;">已自动保存 ${count} 条记忆</div>
    <div style="font-size: 12px; opacity: 0.9;">${entryLabels}${suffix}</div>
  `;
    setTimeout(() => {
        notificationContainer.style.opacity = '1';
        notificationContainer.style.transform = 'translateY(0)';
    }, 10);
    setTimeout(() => {
        notificationContainer.style.opacity = '0';
        notificationContainer.style.transform = 'translateY(20px)';
    }, 3000);
}
export { showMessage, showSSEMessage, welcomeMessage, i18n, showMemoryNotification };
