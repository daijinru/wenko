import { useState, useEffect, useRef } from 'react'
import { fetchEventSource } from '@microsoft/fetch-event-source';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';

import { Welcome, Prompts } from '@ant-design/x';
import { FireOutlined, CoffeeOutlined, SmileOutlined, UserOutlined } from '@ant-design/icons';
import { Button, Space, Typography, Spin } from 'antd'

import './SidePanel.css'

// 随机抽一个 icon
const getRandomIcon = () => {
  const random = Math.floor(Math.random() * 3)
  const icons = {
    0: <FireOutlined style={{ color: '#F5222D' }} />,
    1: <SmileOutlined style={{ color: '#FAAD14' }} />,
    2: <CoffeeOutlined style={{ color: '#964B00' }} />,
  }
  return icons[random]
}

export const SidePanel = () => {
  const [selectedText, setSelectedText] = useState('')
  const [matchResults, setMatchResults] = useState([])
  const [interpretation, setInterpretation] = useState<string>('')
  const [loadingText, setLoadingText] = useState<string>('')
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
      setMatchResults([])
      setInterpretation('')
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
          text: encodeURIComponent(selectedText),
        }),
      })
        .then((res) => res.json())
        .then(data => {
          data.forEach(item => {
            item.content = decodeURIComponent(item.content)
          })
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
              text: encodeURIComponent(selectedText),
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

    await fetchEventSource('http://localhost:8080/chat', {
      method: 'POST',
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model: "qwen/qwen3-32b:free",
        messages: [
          {
            role: "user",
            content: `${getPrompts()}`
          }
        ]
      }),
      onopen(res) {
        if (res.ok) return Promise.resolve()
        chrome.runtime.sendMessage({
          target: "content-script",
          type: "TOAST",
          text: "建立会话连接失败",
        });
      },
      onmessage(line) {
        // chrome.runtime.sendMessage({
        //   target: "content-script",
        //   type: "LOG",
        //   text: line,
        // });
        try {
          const parsed = JSON.parse(line.data)
          if (parsed?.type === 'statusText') {
            setLoadingText(parsed?.content)
          }
          if (parsed?.content && parsed?.type === 'text') {
            setInterpretation(prev => prev + parsed.content)
            setLoadingText('')
          }
        } catch (error) {
          chrome.runtime.sendMessage({
            target: "content-script",
            type: "TOAST",
            text: "JSON.parse 解析数据失败",
          });
        }
      },
      onerror(err) {
        chrome.runtime.sendMessage({
          target: "content-script",
          type: "TOAST",
          text: "连接异常",
        });
      },
    })
  }

  return (
    <main>
      <Welcome
        icon="https://mdn.alipayobjects.com/huamei_iwk9zp/afts/img/A*s5sNRo5LjfQAAAAAAAAAAAAADgCCAQ/fmt.webp"
        title="Wenko，温故知新"
        description={selectedText}
        extra={
          <Space>
            <Button onClick={handleInterpretation}>AI解读</Button>
          </Space>
        }
      >
      </Welcome>
      {
        !isLoading && (interpretation || loadingText) &&
        <div style={{
          marginTop: '16px',
          padding: '0 16px',
        }}>
          <Typography style={{
          }}>
            <Typography.Title level={2} mark>
              AI 解读
            </Typography.Title>
            { loadingText &&
              <Typography.Paragraph>
                {loadingText} <Spin />
              </Typography.Paragraph>
            }
            {
              interpretation &&
              <Typography.Paragraph style={{
                backgroundColor: 'rgba(150, 150, 150, 0.1)',
                border: '1px solid rgba(100, 100, 100, 0.2)',
                borderRadius: '3px',
                padding: '0.4em 0.6em',
              }}>
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeRaw]}
                >
                  {interpretation}
                </ReactMarkdown>
              </Typography.Paragraph>
            }
          </Typography>
        </div>
      }
      { isLoading && <div
        style={{
          width: '100%',
          marginTop: '16px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <div className='loading'></div>
      </div>
      }
      {!isLoading && <div
        style={{
          maxWidth: '100%',
          marginTop: '16px',
          padding: '0 16px',
        }}
      >
        <Prompts
          title="🤔 你还记得这些线索吗？"
          items={matchResults.map((item, key) => {
            return {
              key: String(key),
              icon: getRandomIcon(),
              description: '线索' + (key + 1) + ': ' + item.content,
              disabled: false,
            }
          })}
          wrap
          styles={{
            item: {
              flex: 'none',
              width: 'calc(100% - 8px)',
            },
          }}
        >
        </Prompts>
      </div>
      }
    </main>
  )
}

export default SidePanel
