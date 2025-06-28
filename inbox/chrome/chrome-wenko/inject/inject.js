const rootId = 'react-content-root'

// 插入挂载点
function injectRootDiv() {
  if (!document.getElementById(rootId)) {
    const div = document.createElement('div')
    div.id = rootId
    document.body.appendChild(div)
  }
}

// 动态注入 React bundle
function injectReactScript() {
  const script = document.createElement('script')
  script.src = chrome.runtime.getURL('inject/build/contentScriptReact.iife.js?t=' + Date.now())
  script.type = 'module'
  document.documentElement.appendChild(script)
  script.onload = () => {
    script.remove()
  }
}

injectRootDiv()
injectReactScript()
