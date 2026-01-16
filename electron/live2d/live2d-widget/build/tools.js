import { fa_paper_plane, fa_plus } from './icons.js';
import { showSSEMessage } from './message.js';
import { createNewSession } from './chat.js';
class ToolsManager {
    constructor(model, config, tips) {
        this.config = config;
        this.tools = {
            plane: {
                icon: fa_paper_plane,
                callback: () => {
                    window.electronAPI.send('wenko_shortcut', { action: 'open' });
                }
            },
            newChat: {
                icon: fa_plus,
                callback: () => {
                    createNewSession();
                    showSSEMessage('<div class="wenko-chat-system">已创建新会话</div>', 'wenko-chat-system-msg');
                }
            },
        };
    }
    registerTools() {
        var _a, _b;
        const tools = Object.entries(this.tools);
        for (const [name, value] of tools) {
            const { icon, callback } = value;
            const element = document.createElement('span');
            element.id = `waifu-tool-${name}`;
            element.innerHTML = icon;
            const shadowRoot = (_a = document.getElementById('WENKO__CONTAINER-ROOT')) === null || _a === void 0 ? void 0 : _a.shadowRoot;
            (_b = shadowRoot
                .getElementById('waifu-tool')) === null || _b === void 0 ? void 0 : _b.insertAdjacentElement('beforeend', element);
            element.addEventListener('click', callback);
        }
    }
}
export { ToolsManager };
