
// WENKO 注入脚本
window['WENKO_ROOT_ID'] = 'WENKO__CONTAINER-ROOT'
window['WENKO_ROOT'] = {
  console: {
    info: (...args) => {
      console.info('%c<wenko>%c', 'background: green; color: white; font-weight: bold; font-size: 16px; text-transform: uppercase;', 'color: inherit;', ...args)
    },
    error: (...args) => {
      console.info('%c<wenko>%c', 'background: red; color: white; font-weight: bold; font-size: 16px; text-transform: uppercase;', 'color: inherit;', ...args)
    },
  }
}
// WENKO 注入脚本

const rootId = window['WENKO_ROOT_ID']
const CONSOLE = window['WENKO_ROOT'].console

// 插入挂载点
function injectRootDiv(selectedText = '') {
  CONSOLE.info('挂载选中文本 ', selectedText)
  if (!document.getElementById(rootId)) {
    const div = document.createElement('div')
    div.id = rootId
    document.body.appendChild(div)
  }
  // 将选中文本挂载到 root 节点的数据属性上
  const root = document.getElementById(rootId) 
  root.setAttribute('data-selected-text', selectedText)
}

// 动态注入 React bundle
function injectReactScript() {
  const script = document.createElement('script')
  script.src = chrome.runtime.getURL('inject/build/contentScriptReact.iife.js?t=' + Date.now())
  // script.type = 'module'
  document.documentElement.appendChild(script)
  script.onload = () => {
    script.remove()
  }
}

CONSOLE.info('app is now running ^^')

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  CONSOLE.info('<wenko/inject> listener received ', request)
  if (request.action === "highlightAndOpenPanel") {
    // 高亮选中文本并生成唯一ID 
    const selection = window.getSelection()
    const range = selection?.getRangeAt(0)
    const highlightId = `highlight-${Date.now()}`
    // 该变量已在 background 声明
    if (!range) {
      CONSOLE.error("没有选中文本 ", range)
      return
    }
    const span = document.createElement("span")
    span.id = highlightId
    span.style.backgroundColor = "rgba(255, 255, 0, 0.5)"
    
    try {
      range.surroundContents(span)
    } catch (e) {
      CONSOLE.error("<surroundContents> 失败，尝试替代方案", e)

      span.textContent = selection.toString()

      // 用 span 替换选区中的内容
      range.deleteContents()
      range.insertNode(span)
    }

    if (request.selectedText) {
      injectRootDiv(request.selectedText)
      injectReactScript()
    }

    sendResponse({ highlightId }) // 返回ID供后台跟踪
  }
});
