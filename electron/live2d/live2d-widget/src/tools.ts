/**
 * @file Contains the configuration and functions for waifu tools.
 * @module tools
 */

import {
  fa_comment,
  fa_paper_plane,
  fa_street_view,
  fa_shirt,
  fa_camera_retro,
  fa_info_circle,
  fa_xmark
} from './icons.js';
import { showMessage, i18n } from './message.js';
import type { Config, ModelManager } from './model.js';
import type { Tips } from './widget.js';

interface Tools {
  /**
   * Key-value pairs of tools, where the key is the tool name.
   * @type {string}
   */
  [key: string]: {
    /**
     * Icon of the tool, usually an SVG string.
     * @type {string}
     */
    icon: string;
    /**
     * Callback function for the tool.
     * @type {() => void}
     */
    callback: (message: any) => void;
  };
}

/**
 * Waifu tools manager.
 */
class ToolsManager {
  tools: Tools;
  config: Config;

  constructor(model: ModelManager, config: Config, tips: Tips) {
    this.config = config;
    this.tools = {
      comment: {
        icon: fa_comment,
        callback: async () => {
          // Add hitokoto.cn API
        }
      },
      plane: {
        icon: fa_paper_plane,
        callback: () => {
          window.electronAPI.send('wenko_shortcut', {action: 'open'});
        }
      },
    };
  }

  registerTools() {
    // if (!Array.isArray(this.config.tools)) {
    //   this.config.tools = Object.keys(this.tools);
    // }
    const tools = Object.entries(this.tools);
    for (const [name, value] of tools) {
      const { icon, callback } = value;
      const element = document.createElement('span');
      element.id = `waifu-tool-${name}`;
      element.innerHTML = icon;
      const shadowRoot = document.getElementById('WENKO__CONTAINER-ROOT')?.shadowRoot;
      shadowRoot
        .getElementById('waifu-tool')
        ?.insertAdjacentElement(
          'beforeend',
          element,
        );
      element.addEventListener('click', callback);
    }
  }
}

export { ToolsManager, Tools };
