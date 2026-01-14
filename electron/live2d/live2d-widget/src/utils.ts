/**
 * @file Contains utility functions.
 * @module utils
 */

/**
 * Randomly select an element from an array, or return the original value if not an array.
 * @param {string[] | string} obj - The object or array to select from.
 * @returns {string} The randomly selected element or the original value.
 */
function randomSelection(obj: string[] | string): string {
  return Array.isArray(obj) ? obj[Math.floor(Math.random() * obj.length)] : obj;
}

function randomOtherOption(total: number, excludeIndex: number): number {
  const idx = Math.floor(Math.random() * (total - 1));
  return idx >= excludeIndex ? idx + 1 : idx;
}

/**
 * Asynchronously load external resources.
 * @param {string} url - Resource path.
 * @param {string} type - Resource type.
 */
function loadExternalResource(url: string, type: string): Promise<string> {
  return new Promise((resolve: any, reject: any) => {
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
}

const LocalStoreage_Key = 'live2d-widget';
/**
 * 通过 localStorage 存储对象，并设置过期时间，如果过期则返回 null
 * @param {string} key - 存储的键名
 * @param {any} value - 存储的值
 * @param {number} expire - 过期时间，单位为秒
 * @returns {any} 存储的值
 */
export const setLocalStorage = (key: string, value: any, expire: number) => {
  const data = {
    value,
    expire: Date.now() + expire * 1000,
  };
  localStorage.setItem(`${LocalStoreage_Key}-${key}`, JSON.stringify(data));
}

/**
 * 通过 localStorage 获取对象，如果过期则返回 null
 * @param {string} key - 存储的键名
 * @returns {any} 存储的值
 */
export const getLocalStorage = (key: string) => {
  const data = localStorage.getItem(`${LocalStoreage_Key}-${key}`);
  if (data) {
    const { value, expire } = JSON.parse(data);
    if (Date.now() < expire) {
      return value;
    }
  }
  return null;
}

/**
 * 一个用于读写 live2d-widget-options 的方法
 */
export const writeOptions = (options: any) => {
  // 写入前检查是否已存在，如果存在则覆写
  const oldOptions = getLocalStorage('options');
  if (oldOptions) {
    options = { ...oldOptions, ...options };
  }
  console.info('<wenko> 写入选项:', options);
  setLocalStorage('options', options, 3600 * 24 * 30);
}
export const readOptions = () => {
  return getLocalStorage('options');
}


export {
  randomSelection,
  loadExternalResource,
  randomOtherOption,
};
