import React, { useState } from 'react'
import { createRoot } from 'react-dom/client'

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
            bottom: 70,
            right: 20,
            padding: 15,
            backgroundColor: 'white',
            border: '1px solid #ccc',
            borderRadius: 6,
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            zIndex: 10000,
          }}
        >
          这里是弹窗内容，可以使用 React 自定义 UI
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