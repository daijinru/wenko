import React, { useState } from 'react'
import { createRoot } from 'react-dom/client'
import Sidepanel from './Sidepanel'

function FloatButton() {
  const [visible, setVisible] = useState(false)

  return (
    <>
      <button
        style={{
          position: 'fixed',
          bottom: 20,
          right: 20,
          zIndex: 9999,
          padding: '10px 15px',
          borderRadius: '5px',
          backgroundColor: '#007bff',
          color: '#fff',
          border: 'none',
          cursor: 'pointer',
        }}
        onClick={() => setVisible(!visible)}
      >
        浮动按钮
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
            border: '1px solid #ccc',
            borderRadius: '12px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            zIndex: 10000,
            overflow: 'auto',
          }}
        >
          <Sidepanel
            text='我的订阅列表越来越长，从开始的 ChatGPT 不断增加，最多有一个月我记得订阅费有 5k，那个时候甚至还会省钱去订阅，因为探索得入迷了，各种功能各种牛逼的使用结果，让我爱不释手。ChatGPT、Midjourney、ElevenLabs、Runway、Perplexity……一排五颜六色的图标仿佛儿童乐园的跷跷板，弹跳着你的注意力；而「annual plan」等字样却在账单角落悄悄累积。'
            title={document.title}
            url={window.location.href}
            body={document.body?.innerText?.slice(0, 200) || ''}
          />
        </div>
      )}
    </>
  )
}

console.info('<wenko> reactApp is running')
const rootEl = document.getElementById('react-content-root')
if (rootEl) {
  const root = createRoot(rootEl)
  root.render(<FloatButton />)
}