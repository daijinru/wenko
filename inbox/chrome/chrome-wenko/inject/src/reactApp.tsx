import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import Sidepanel from './Sidepanel'
import { CloseOutlined } from '@ant-design/icons'

import 'virtual:windi.css'

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

/**  */
function loadScript(src: string) {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = src
    script.onload = resolve
    script.onerror = reject
    document.head.appendChild(script)
  })
}

function FloatButton() {
  // 根节点，可用于获取数据属性 或者 整体移除
  const root = document.getElementById(rootId)
  const wifuMount = document.getElementById('wenko_wifu')

  loadScript('http://localhost:8080/live2d/live2d-widget/dist/autoload.js')


  useEffect(() => {
    setTimeout(() => {
      // 从数据属性取出文本
      const selectedText = root?.getAttribute('data-selected-text') || ''
    }, 1000)
  }, [])

  return <>
    <div
      id="wenko_wifu"
      className="fixed bottom-66px right-0 z-10000"
    ></div>
  </>
}

const rootEl = document.getElementById(rootId)
let reactRootContainer: HTMLElement | null = null
if (rootEl?.shadowRoot) {
  reactRootContainer = rootEl.shadowRoot.getElementById('wenko-react-root')
} else {
  reactRootContainer = rootEl
}
if (reactRootContainer) {
  const root = createRoot(reactRootContainer)
  root.render(<FloatButton />)
} else {
  CONSOLE.error('<Wenko-React-Root> not found')
}