import { useState, useEffect, useRef } from 'react'

import './SidePanel.css'

export const SidePanel = () => {
  const [selectedText, setSelectedText] = useState('')
  const hightlightId = useRef('')
  useEffect(() => {

    // 接收后台传递的文本 
    chrome.runtime.onMessage.addListener((request)  => {
      console.info('接收到后台传递的文本:', request);
      if (request.action  === "updateSidePanel") {
        const text = request.text.split('_')[0]; // 仅获取文本部分
        setSelectedText(text);

        const id = request.text.split('_')[1]
        hightlightId.current = id; // 更新高亮ID
      }
    });
  }, [])

  return (
    <main>
      <h3>欢迎使用 Wenko 侧边栏</h3>
      <article>
        <h2>正在选中文本</h2>
        <p>{selectedText}</p>
      </article>
    </main>
  )
}

export default SidePanel
