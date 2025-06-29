import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import Sidepanel from './Sidepanel'
import { Button } from 'antd'
import { CloseOutlined } from '@ant-design/icons'

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
      <button
        style={{
          position: 'fixed',
          bottom: 20,
          right: 20,
          zIndex: 9999,
          cursor: 'pointer',
        }}
        onClick={() => {
          root?.remove()
        }}
      >
        <Button color="primary" variant="outlined">
          <CloseOutlined /> WENKO
        </Button>
      </button>
      {visible && (
        <div
          style={{
            position: 'fixed',
            right: '20px',
            bottom: '75px',
            padding: '16px',
            width: '50%',
            height: '80%',
            backgroundColor: 'white',
            borderRadius: '16px',
            boxShadow: 'rgba(6, 24, 44, 0.4) 0px 0px 0px 2px, rgba(6, 24, 44, 0.65) 0px 4px 6px -1px, rgba(255, 255, 255, 0.08) 0px 1px 0px inset',
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
if (rootEl) {
  const root = createRoot(rootEl)
  root.render(<FloatButton />)
}