function randomSelection(obj) {
    return Array.isArray(obj) ? obj[Math.floor(Math.random() * obj.length)] : obj;
}
function randomOtherOption(total, excludeIndex) {
    const idx = Math.floor(Math.random() * (total - 1));
    return idx >= excludeIndex ? idx + 1 : idx;
}
function loadExternalResource(url, type) {
    return new Promise((resolve, reject) => {
        let tag;
        if (type === 'css') {
            tag = document.createElement('link');
            tag.rel = 'stylesheet';
            tag.href = url;
        }
        else if (type === 'js') {
            tag = document.createElement('script');
            tag.src = url;
        }
        if (tag) {
            tag.onload = () => resolve(url);
            tag.onerror = () => reject(url);
            document.head.appendChild(tag);
        }
    });
}
export const generateMsgId = () => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
};
const LocalStoreage_Key = 'live2d-widget';
export const setLocalStorage = (key, value, expire) => {
    const data = {
        value,
        expire: Date.now() + expire * 1000,
    };
    localStorage.setItem(`${LocalStoreage_Key}-${key}`, JSON.stringify(data));
};
export const getLocalStorage = (key) => {
    const data = localStorage.getItem(`${LocalStoreage_Key}-${key}`);
    if (data) {
        const { value, expire } = JSON.parse(data);
        if (Date.now() < expire) {
            return value;
        }
    }
    return null;
};
export const writeOptions = (options) => {
    const oldOptions = getLocalStorage('options');
    if (oldOptions) {
        options = Object.assign(Object.assign({}, oldOptions), options);
    }
    console.info('<wenko> 写入选项:', options);
    setLocalStorage('options', options, 3600 * 24 * 30);
};
export const readOptions = () => {
    return getLocalStorage('options');
};
export { randomSelection, loadExternalResource, randomOtherOption, };
