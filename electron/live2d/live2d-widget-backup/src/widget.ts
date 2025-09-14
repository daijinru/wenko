/**
 * @file Contains functions for initializing the waifu widget.
 * @module widget
 */

import { ModelManager, Config, ModelList } from './model.js';
import { showMessage, showSSEMessage, welcomeMessage, Time } from './message.js';
import { randomSelection, writeOptions, readOptions, } from './utils.js';
import { ToolsManager } from './tools.js';
import logger from './logger.js';
import registerDrag from './drag.js';
import {
  getKanbanDaily,
  getDaily,
  getSearch,
  saveHightlightText as saveText,
  saveDaily,
} from './conversation.js';
interface Tips {
  /**
   * Default message configuration.
   */
  message: {
    /**
     * Default message array.
     * @type {string[]}
     */
    default: string[];
    /**
     * Console message.
     * @type {string}
     */
    console: string;
    /**
     * Copy message.
     * @type {string}
     */
    copy: string;
    /**
     * Visibility change message.
     * @type {string}
     */
    visibilitychange: string;
    changeSuccess: string;
    changeFail: string;
    photo: string;
    goodbye: string;
    hitokoto: string;
    welcome: string;
    referrer: string;
    hoverBody: string;
    tapBody: string;
  };
  /**
   * Time configuration.
   * @type {Time}
   */
  time: Time;
  /**
   * Mouseover message configuration.
   * @type {Array<{selector: string, text: string | string[]}>}
   */
  mouseover: {
    selector: string;
    text: string | string[];
  }[];
  /**
   * Click message configuration.
   * @type {Array<{selector: string, text: string | string[]}>}
   */
  click: {
    selector: string;
    text: string | string[];
  }[];
  /**
   * Season message configuration.
   * @type {Array<{date: string, text: string | string[]}>}
   */
  seasons: {
    date: string;
    text: string | string[];
  }[];
  models: ModelList[];
}

/**
 * Register event listeners.
 * @param {Tips} tips - Result configuration.
 */
function registerEventListener(tips: Tips) {
  // Detect user activity and display messages when idle
  let userAction = false;
  let userActionTimer: any;
  const messageArray = tips.message.default;
  tips.seasons.forEach(({ date, text }) => {
    const now = new Date(),
      after = date.split('-')[0],
      before = date.split('-')[1] || after;
    if (
      Number(after.split('/')[0]) <= now.getMonth() + 1 &&
      now.getMonth() + 1 <= Number(before.split('/')[0]) &&
      Number(after.split('/')[1]) <= now.getDate() &&
      now.getDate() <= Number(before.split('/')[1])
    ) {
      text = randomSelection(text);
      text = (text as string).replace('{year}', String(now.getFullYear()));
      messageArray.push(text);
    }
  });
  let lastHoverElement: any;
  window.addEventListener('mousemove', () => (userAction = true));
  window.addEventListener('keydown', () => (userAction = true));
  setInterval(() => {
    if (userAction) {
      userAction = false;
      clearInterval(userActionTimer);
      userActionTimer = null;
    } else if (!userActionTimer) {
      userActionTimer = setInterval(() => {
        showMessage(messageArray, 6000, 9);
      }, 20000);
    }
  }, 1000);

  window.addEventListener('mouseover', (event) => {
    // eslint-disable-next-line prefer-const
    for (let { selector, text } of tips.mouseover) {
      if (!(event.target as HTMLElement)?.closest(selector)) continue;
      if (lastHoverElement === selector) return;
      lastHoverElement = selector;
      text = randomSelection(text);
      text = (text as string).replace(
        '{text}',
        (event.target as HTMLElement).innerText,
      );
      showMessage(text, 4000, 8);
      return;
    }
  });

  // let dblclickLoading = false;
  // 双击事件
  // window.addEventListener('dblclick', (event) => {
  //   // 只有在 div#WENKO__CONTAINER-ROOT 的 shadow dom 中的元素才触发
  //   const target = event.target as HTMLElement;
  //   if (!target) return;
    
  //   // 检查元素是否在指定容器内，兼容没有 closest 方法的情况
  //   let isInContainer = false;
  //   if (target.closest) {
  //     // 使用 closest 方法（现代浏览器）
  //     isInContainer = !!target.closest('#WENKO__CONTAINER-ROOT');
  //   } else {
  //     // 降级方案：手动遍历父元素
  //     let current: HTMLElement | null = target;
  //     while (current) {
  //       if (current.id === 'WENKO__CONTAINER-ROOT') {
  //         isInContainer = true;
  //         break;
  //       }
  //       current = current.parentElement;
  //     }
  //   }
  //   if (!isInContainer) return;

  //   if (dblclickLoading) return;
  //   dblclickLoading = true;
  //   getDaily(str => {
  //     showSSEMessage(str, 'wenko-daily');
  //   }, str => {
  //     showSSEMessage(str, 'wenko-daily-loading');
  //   }, () => {
  //     dblclickLoading = false;
  //     // showSSEMessage 添加关闭按钮
  //     const closeStr = '<div class="wenko-tips-close" onclick="this.parentElement.classList.remove(\'waifu-tips-active\')">好的</div>';
  //     showSSEMessage(closeStr, 'wenko-daily');
  //   })
  // });

  window.addEventListener('live2d:hoverbody', () => {
    console.info('>>> live2d:hoverbody');
    const text = randomSelection(tips.message.hoverBody);
    showMessage(text, 4000, 8, false);
  });
  window.addEventListener('live2d:tapbody', () => {
    console.info('>>> live2d:tapbody');
    const text = randomSelection(tips.message.tapBody);
    showMessage(text, 4000, 9);
  });

  const devtools = () => {};
  devtools.toString = () => {
    showMessage(tips.message.console, 6000, 9);
  };
  window.addEventListener('copy', () => {
    showMessage(tips.message.copy, 6000, 9);
  });
  window.addEventListener('visibilitychange', () => {
    if (!document.hidden)
      showMessage(tips.message.visibilitychange, 6000, 9);
  });

  // 监听自定义事件 wenko-highlight
  window.addEventListener('wenko_highlight', (event: any) => {
    let text = event.detail
    getKanbanDaily(text, str => {
      showSSEMessage(str, 'wenko_highlight');
    }, str => {
      showSSEMessage(str, 'wenko_highlight_loading');
    })

    // TODO 这里应作为 task_flow 指定的工具被执行，例如 tool_get_relations
    // getSearch(text, (str) => {
    //   let merged = `这是指定解析文本：${text}`
    //   if (str && Array.isArray(str)) {
    //     merged += `，这是关联上下文：${str[0].content}。`
    //   }
    //   merged += '在解析给定文本时，如果存在关联上下文，应将其纳入处理范围，并根据上下文进行语义补全与判断。如果不存在，则仅对给定文本进行处理。'
    //   getKanbanDaily(merged, str => {
    //     showSSEMessage(str, 'wenko_highlight');
    //   }, str => {
    //     showSSEMessage(str, 'wenko_highlight_loading');
    //   })
    // })
  });

  window.addEventListener('wenko_saveText', (event: any) => {
    let text = event.detail
    saveText(text, (str) => {
      showSSEMessage(str, 'wenko_saveText');
    }, str => {
      showSSEMessage(str, 'wenko_saveText_loading');
    })
  });
}

/** 获取 shadow dom 容器中的挂载点 */
function getShadowRootMounted() {
  const shadowRoot = document.getElementById('WENKO__CONTAINER-ROOT')?.shadowRoot;
  if (shadowRoot) {
    const mounted = shadowRoot.getElementById('wenko_wifu');
    if (mounted) {
      return mounted;
    }
  }
  return null;
}

/**
 * Load the waifu widget.
 * @param {Config} config - Waifu configuration.
 */
async function loadWidget(config: Config) {
  localStorage.removeItem('waifu-display');
  sessionStorage.removeItem('waifu-message-priority');
  // 挂载到 shadow dom 容器
  // const shadowRoot = document.getElementById(config.mounted)?.shadowRoot;
  const mounted = getShadowRootMounted();
  mounted.insertAdjacentHTML(
    'beforeend',
    `<div id="waifu">
      <div id="waifu-tips"></div>
      <div id="waifu-canvas">
        <canvas id="live2d" width="800" height="800"></canvas>
      </div>
      <div id="waifu-tool"></div>
    </div>`,
  );
  let models: ModelList[] = [];
  let tips: Tips | null;
  if (config.waifuPath) {
    const response = await fetch(config.waifuPath);
    tips = await response.json();
    models = tips.models;
    registerEventListener(tips);
  }
  const model = await ModelManager.initCheck(config, models);
  await model.loadModel('');
  new ToolsManager(model, config, tips).registerTools();
  // if (config.drag) registerDrag();
  document.getElementById('waifu')?.classList.add('waifu-active');
}

/**
 * Initialize the waifu widget.
 * @param {string | Config} config - Waifu configuration or configuration path.
 */
function initWidget(config: string | Config) {
  console.info('<wenko> initWidget', config);
  if (typeof config === 'string') {
    logger.error('Your config for Live2D initWidget is outdated. Please refer to https://github.com/stevenjoezhang/live2d-widget/blob/master/dist/autoload.js');
    return;
  }
  logger.setLevel(config.logLevel);
  loadWidget(config as Config);

  // const mounted = getShadowRootMounted();
  // console.info('>>> mounted', mounted);
  // mounted.insertAdjacentHTML(
  //   'beforeend',
  //   `<div id="waifu-toggle">
  //      ${fa_child}
  //    </div>`,
  // );

  // const toggle = document.getElementById('waifu-toggle');
  // toggle?.addEventListener('click', () => {
  //   toggle?.classList.remove('waifu-toggle-active');
  //   if (toggle?.getAttribute('first-time')) {
  //     loadWidget(config as Config);
  //     toggle?.removeAttribute('first-time');
  //   } else {
  //     localStorage.removeItem('waifu-display');
  //     document.getElementById('waifu')?.classList.remove('waifu-hidden');
  //     setTimeout(() => {
  //       document.getElementById('waifu')?.classList.add('waifu-active');
  //     }, 0);
  //   }
  // });
  // if (
  //   localStorage.getItem('waifu-display') &&
  //   Date.now() - Number(localStorage.getItem('waifu-display')) <= 86400000
  // ) {
  //   toggle?.setAttribute('first-time', 'true');
  //   setTimeout(() => {
  //     toggle?.classList.add('waifu-toggle-active');
  //   }, 0);
  // } else {
  //   loadWidget(config as Config);
  // }
}

export { initWidget, Tips };
