import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';

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

  const [interpretation, setInterpretation] = useState<string>('')

const getPrompts = () => {
  return `
【智能解析任务】
基于用户选中的文本片段「${selectedText}」，结合下列${Math.min(matchResults.length,5)} 条上下文线索，进行多维度语义解析。注意：
1. 若上下文存在矛盾信息，需标注差异点并解释成因 
2. 涉及专业术语时，须构建领域知识图谱关联 
3. 区分文本的字面逻辑与潜在表达张力 
 
【上下文线索】
${matchResults.slice(0,5).map((item,index)  => 
  `线索${index+1}: ${item.content}`
).join('\n\n')}`;
}
  const handleInterpretation = async () => {
    chrome.runtime.sendMessage({
      target: "content-script",
      type: "TOAST",
      text: "正在生成AI解读..."
    });

    setInterpretation('');

    try {
      const response = await fetch("http://localhost:8080/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          model: "qwen/qwen3-4b:free",
          messages: [
            {
              role: "user",
              content: `${getPrompts()}`
            }
          ]
        })
      });

      if (!response.ok) {
        setInterpretation("解释过程中出错，请重试。");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let accumulatedContent = "";

      while (!done) {
        const { value, done: streamDone } = await reader.read();
        done = streamDone;
        const chunk = decoder.decode(value, { stream: !done });
        accumulatedContent += chunk;

        // Update interpretation state incrementally as data streams in
        setInterpretation(accumulatedContent);
      }
    } catch (error) {
      setInterpretation("解释过程中出错，请重试。");
    }
  }

  return (
    <main>
      <h3>温故而知新</h3>
      <article>
        <h2>当前选中文本</h2>
        <p style={{
          backgroundColor: 'yellow',
          padding: '1rem',
        }}>{selectedText}</p>
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
      {
        !isLoading &&
        <div style={{
          paddingTop: '16px',
        }}>
          <button onClick={handleInterpretation}>解读以上内容</button>
          <article style={{
            marginTop: '16px',
            textAlign: 'left',
            color: '#000',
            padding: '16px',
            backgroundColor: 'yellow',
          }}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeRaw]}
            >
              {interpretation}
            </ReactMarkdown>
          </article>
        </div>
      }
    </main>
  )
}

export default SidePanel
