/**
 * @file Execution stage overlay — shows current execution status in the Live2D chat interface.
 * @module execution-stage
 */

/** Human-readable execution state from SSE event. */
interface HumanState {
  行动: string;
  原状态: string;
  新状态: string;
  是否已结束: boolean;
  是否需要关注: boolean;
  是否不可逆: boolean;
}

const OVERLAY_ID = 'wenko-execution-stage';
const FADE_OUT_DELAY = 3000;

let fadeTimer: ReturnType<typeof setTimeout> | null = null;

function getShadowRoot(): ShadowRoot | null {
  return document.getElementById('WENKO__CONTAINER-ROOT')?.shadowRoot ?? null;
}

function getOrCreateOverlay(): HTMLElement | null {
  const shadowRoot = getShadowRoot();
  if (!shadowRoot) return null;

  let overlay = shadowRoot.getElementById(OVERLAY_ID);
  if (overlay) return overlay;

  const waifu = shadowRoot.getElementById('waifu');
  if (!waifu) return null;

  overlay = document.createElement('div');
  overlay.id = OVERLAY_ID;
  overlay.style.cssText = [
    'position: absolute',
    'bottom: 80px',
    'left: 8px',
    // 'transform: translateX(-50%)',
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

function statusColor(state: HumanState): string {
  if (state.是否需要关注) return '#f59e0b'; // amber
  if (state.是否已结束) {
    if (state.新状态 === '已完成') return '#22c55e'; // green
    return '#ef4444'; // red (出了问题/已拒绝/已停止)
  }
  return '#60a5fa'; // blue (进行中/准备中)
}

function formatText(state: HumanState): string {
  if (!state.是否已结束) {
    if (state.新状态 === '准备中') return state.行动 + '——准备中';
    return '正在' + state.行动 + '……';
  }
  return state.行动 + '——' + state.新状态;
}

/**
 * Update the execution stage overlay with a new human-readable state.
 */
export function updateExecutionStage(state: HumanState): void {
  const overlay = getOrCreateOverlay();
  if (!overlay) return;

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
  } else {
    overlay.style.background = 'rgba(0, 0, 0, 0.65)';
  }

  if (state.是否已结束) {
    fadeTimer = setTimeout(() => {
      overlay.style.opacity = '0';
      fadeTimer = null;
    }, FADE_OUT_DELAY);
  }
}
