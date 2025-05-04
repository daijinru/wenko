import { useState, useEffect, useRef } from 'react'

import './SidePanel.css'

export const SidePanel = () => {
  const [selectedText, setSelectedText] = useState('')
  const hightlightId = useRef('')
  useEffect(() => {

    // 接收后台传递的文本 
    chrome.runtime.onMessage.addListener((request)  => {
      if (request.action  === "updateSidePanel") {
        const text = request.text.split('_')[0]; // 仅获取文本部分
        setSelectedText(text);

        const id = request.text.split('_')[1]
        hightlightId.current = id; // 更新高亮ID
      }
    })

    chrome.runtime.sendMessage({
      target: "content-script",
      type: "TOAST",
      text: `正在添加选中文本: ${selectedText}`,
      duration: 10000,
    });
    setTimeout(() => {
      chrome.runtime.sendMessage({ 
        target: "content-script",
        type: "HideSidePanel",
        text: `移除高亮`,
      });
    }, 2000)
  }, [])

  const handleGenerateVector = async () => {
    const tab = await chrome.tabs.getCurrent()

    chrome.runtime.sendMessage({ 
      target: "content-script",
      type: "LOG",
      text: "向量生成中..."
    });
  }

  return (
    <main>
      <h3>欢迎使用 Wenko 侧边栏</h3>
      <article>
        <h2>正在选中文本</h2>
        <p>{selectedText}</p>
        <button onClick={handleGenerateVector}>生成向量</button>
      </article>
    </main>
  )
}

export default SidePanel
