import { useState, useEffect, useRef } from 'react'

import './SidePanel.css'

export const SidePanel = () => {
  const [selectedText, setSelectedText] = useState('')
  const [matchResults, setMatchResults] = useState([])
  const hightlightId = useRef('')
  const [isLoading, setIsLoading] = useState(true)
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
  }, [])

  useEffect(() => {
    if (selectedText) {
      setIsLoading(true)
      chrome.runtime.sendMessage({
        target: "content-script",
        type: "TOAST",
        text: `已选中，正在搜索关联文本，请稍等...`,
        duration: 2000,
      });
      // 请求 http://localhost:8080/search 接口，请求体 text
      fetch("http://localhost:8080/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text: selectedText,
        }),
      })
        .then((res) => res.json())
        .then((data) => {
          chrome.runtime.sendMessage({
            target: "content-script",
            type: "LOG",
            text: JSON.stringify(data),
          })
          setMatchResults(data)
          setIsLoading(false)
          // data 是一个数组 [{id, content}]，有可能空，遍历，如果content与selectedText一致，则调用生成向量接口
          const matchResult = data.find(item => item.content === selectedText)
          if (matchResult && matchResult.content) return
          chrome.runtime.sendMessage({
            target: "content-script",
            type: "TOAST",
            text: `没有找到完全匹配的搜索结果，正在生成向量`,
            duration: 2000,
          });
          // 请求 http://localhost:8080/generate 接口，请求体 text，返回的 id
          fetch("http://localhost:8080/generate", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              text: selectedText,
            }),
          })
            .then((res) => res.json())
            .then((res) => {
              if (res.id) {
                chrome.runtime.sendMessage({
                  target: "content-script",
                  type: "TOAST",
                  text: `已生成并存储，${res.id}`,
                  duration: 2000,
                });
              }
            })
        })
      setTimeout(() => {
        chrome.runtime.sendMessage({ 
          target: "content-script",
          type: "HideSidePanel",
          text: `移除高亮`,
        });
      }, 2000)
    }
  }, [selectedText])

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
      <h3>欢迎使用 Wenko</h3>
      <article>
        <h2>当前选中文本</h2>
        <p style={{
          backgroundColor: 'yellow',
          padding: '1rem',
        }}>{selectedText}</p>
        {/* <button onClick={handleGenerateVector}>生成向量</button> */}
      </article>
      <div style={{
        paddingTop: '16px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '1rem',
      }}>
      {
        isLoading
          ? <div className='loading'></div>
          : <article>
              <h2>可能存在关联</h2>

              {
                matchResults.length < 1
                  ? <p>没有匹配结果</p>
                  : matchResults.map(item => {
                      return <p>{item.content}</p>
                    })
              }
            </article>
      }
      </div>
    </main>
  )
}

export default SidePanel
