const OVERLAY_ID = 'wenko-execution-stage';
const FADE_OUT_DELAY = 3000;
let fadeTimer = null;
function getShadowRoot() {
    var _a, _b;
    return (_b = (_a = document.getElementById('WENKO__CONTAINER-ROOT')) === null || _a === void 0 ? void 0 : _a.shadowRoot) !== null && _b !== void 0 ? _b : null;
}
function getOrCreateOverlay() {
    const shadowRoot = getShadowRoot();
    if (!shadowRoot)
        return null;
    let overlay = shadowRoot.getElementById(OVERLAY_ID);
    if (overlay)
        return overlay;
    const waifu = shadowRoot.getElementById('waifu');
    if (!waifu)
        return null;
    overlay = document.createElement('div');
    overlay.id = OVERLAY_ID;
    overlay.style.cssText = [
        'position: absolute',
        'bottom: 80px',
        'left: 8px',
        'padding: 6px 14px',
        'border-radius: 16px',
        'font-size: 13px',
        'line-height: 1.4',
        'white-space: nowrap',
        'pointer-events: none',
        'z-index: 100',
        'transition: opacity 0.3s ease',
        'opacity: 0',
        'background: rgba(0, 0, 0, 0.65)',
        'color: #fff',
        'font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    ].join('; ');
    waifu.appendChild(overlay);
    return overlay;
}
function statusColor(state) {
    if (state.是否需要关注)
        return '#f59e0b';
    if (state.是否已结束) {
        if (state.新状态 === '已完成')
            return '#22c55e';
        return '#ef4444';
    }
    return '#60a5fa';
}
function formatText(state) {
    if (!state.是否已结束) {
        if (state.新状态 === '准备中')
            return state.行动 + '——准备中';
        return '正在' + state.行动 + '……';
    }
    return state.行动 + '——' + state.新状态;
}
export function updateExecutionStage(state) {
    const overlay = getOrCreateOverlay();
    if (!overlay)
        return;
    if (fadeTimer) {
        clearTimeout(fadeTimer);
        fadeTimer = null;
    }
    const color = statusColor(state);
    const dot = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color};margin-right:6px;vertical-align:middle;"></span>`;
    overlay.innerHTML = dot + formatText(state);
    overlay.style.opacity = '1';
    if (state.是否需要关注) {
        overlay.style.background = 'rgba(120, 53, 15, 0.85)';
    }
    else {
        overlay.style.background = 'rgba(0, 0, 0, 0.65)';
    }
    if (state.是否已结束) {
        fadeTimer = setTimeout(() => {
            overlay.style.opacity = '0';
            fadeTimer = null;
        }, FADE_OUT_DELAY);
    }
}
