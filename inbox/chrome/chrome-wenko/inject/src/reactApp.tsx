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

function FloatButton() {
  const [visible, setVisible] = useState(false)
  const [text, setText] = useState('')
  const root = document.getElementById(rootId)

  useEffect(() => {
    setTimeout(() => {
      // 从数据属性取出文本
      const selectedText = root?.getAttribute('data-selected-text') || ''
      setText(selectedText)
      setVisible(true)
    }, 1000)
  }, [])

  return (
    <>
      <div
        className={[
          'fixed bottom-20px right-20px z-9999',
          'h-32px px-10px py-2px rounded-8px text-16px text-black',
          'flex items-center',
          'cursor-pointer',
        ].join(' ')}
        style={{
          boxShadow: 'rgb(85, 91, 255) 0px 0px 0px 3px, rgb(31, 193, 27) 0px 0px 0px 6px, rgb(255, 217, 19) 0px 0px 0px 9px, rgb(255, 156, 85) 0px 0px 0px 12px, rgb(255, 85, 85) 0px 0px 0px 15px',
        }}
        onClick={() => {
          root?.remove()
        }}
      >
        <CloseOutlined /> <span className='ml-4px'>WENKO</span>
      </div>
      {visible && (
        <div
          style={{
            position: 'fixed',
            right: '20px',
            bottom: '100px',
            width: '480px',
            maxHeight: '70%',
            backgroundColor: 'white',
            borderRadius: '8px',
            boxShadow: 'rgba(240, 46, 170, 0.4) 5px 5px, rgba(240, 46, 170, 0.3) 10px 10px, rgba(240, 46, 170, 0.2) 15px 15px, rgba(240, 46, 170, 0.1) 20px 20px, rgba(240, 46, 170, 0.05) 25px 25px',
            zIndex: 10000,
            overflow: 'auto',
            boxSizing: 'border-box',
            scrollbarWidth: 'none',
          }}
        >
          <Sidepanel
            text={text}
            title={document.title}
            url={window.location.href}
            body={document.body?.innerText?.slice(0, 200) || ''}
          />
        </div>
      )}
    </>
  )
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