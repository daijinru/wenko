import { useState, useEffect, useRef } from 'react'
import { fetchEventSource } from '@microsoft/fetch-event-source';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';

import { Welcome } from '@ant-design/x';
import { CoffeeOutlined, SmileOutlined } from '@ant-design/icons';
import { Button, Space, Typography, Spin, Card, notification } from 'antd'
import { pick } from 'lodash-es';

const { Text, Link } = Typography

import './Sidepanel.css'

/**
 * 带权重的文本结构体
 * ```javascript
 * { Text: selectedText, Weight: 0.6 },                       // 高亮文本为核心，权重最高
 * { Text: document.title, Weight: 0.15 },                   // 网页标题，体现页面主题
 * { Text: location.href, Weight: 0.15 },                    // URL，提供上下文来源
 * { Text: document.body.innerText.slice(0, 500), Weight: 0.1 }, // 网页正文首500字符，提供部分上下文
 * ```
 */
type WeightedText = {
	Text: string
	Weight: number
}

const Sidepanel = (props) => {
  const [selectedText, setSelectedText] = useState('')
  const refTexts = useRef<Record<string, string>>([] as any)
  const [matchResults, setMatchResults] = useState([])
  const [interpretation, setInterpretation] = useState<string>('')
  const [loadingText, setLoadingText] = useState<string>('')
  const hightlightId = useRef('')
  const [isLoading, setIsLoading] = useState(true)
  useEffect(() => {

    // 接收后台传递的文本 
    const text = props.text.split('_')[0]; // 仅获取文本部分
    setSelectedText(text);
    refTexts.current = {...pick(props, ['url', 'title', 'body']), ...{text}};
    const id = props.text.split('_')[1]
    hightlightId.current = id; // 更新高亮ID
  }, [])

  useEffect(() => {
    if (selectedText) {
      setMatchResults([])
      setInterpretation('')
      setIsLoading(true)

      // 请求 http://localhost:8080/search 接口，请求体 text
      // 设置带权重的文本结构体
      const weightedTexts: WeightedText[] = [
        { Text: refTexts.current.text, Weight: 0.6 },
        { Text: refTexts.current.title, Weight: 0.15 },
        { Text: refTexts.current.url, Weight: 0.15 },
        { Text: refTexts.current.body, Weight: 0.1 },
      ]
      console.info('获得权重文本：', weightedTexts)
      fetch("http://localhost:8080/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          texts: weightedTexts,
        }),
      })
        .then((res) => res.json())
        .then(async data => {
          setMatchResults(data)
          setIsLoading(false)

          const promises = data.map(async item => {
            const res = await fetch('http://localhost:8080/compare', {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                texts: weightedTexts,
                id: item.id
              }),
            })
            const parsed = await res.json()
            return parsed.result
          })
          const finalRes = await Promise.all(promises)
          console.info('✅ 比对结果: ', finalRes)
          const matched = finalRes.some(fr => fr)
          if (matched) return
          // const matchResult = data.find(item => item.content === selectedText)
          // if (matchResult && matchResult.content) return
          notification.info({
            message: '温馨提示',
            description: '没有找到完全匹配的搜索结果，正在生成向量',
          })
          // 请求 http://localhost:8080/generate 接口，请求体 text，返回的 id
          fetch("http://localhost:8080/generate", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              texts: weightedTexts,
            }),
          })
            .then((res) => res.json())
            .then((res) => {
              if (res.id) {
                notification.success({
                  message: '温馨提示',
                  description: `已生成并存储，${res.id}`,
                })
              }
            })
            .catch(err => {
              notification.error({
                message: '温馨提示',
                description: `生成向量失败，${err}`,
              })
            })
        })
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
${matchResults.map((item,index)  => 
  `线索${index+1}: ${item.content}`
).join('\n\n')}`;
  }
  const handleInterpretation = async () => {
    notification.info({
      message: '温馨提示',
      description: '正在生成AI解读...',
    })

    
    setInterpretation('');

    await fetchEventSource('http://localhost:8080/chat', {
      method: 'POST',
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model: "qwen/qwen3-32b:free", // 已废弃
        messages: [
          {
            role: "user",
            content: `${getPrompts()}`
          }
        ]
      }),
      onopen(res) {
        if (res.ok) return Promise.resolve()
      },
      onmessage(line) {
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
          notification.error({
            message: '温馨提示',
            description: 'JSON.parse 解析数据失败',
          })
        }
      },
      onerror(err) {
        notification.error({
          message: '温馨提示',
          description: '连接异常',
        })
      },
    })
  }

  return (
    <main>
      <Welcome
        style={{
          backgroundColor: 'rgb(255, 255, 255)',
        }}
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
          // padding: '0 16px',
        }}>
          <Typography style={{marginBottom: '16px'}}>
            <Typography.Title level={2} mark>
              <SmileOutlined /> AI 解读
            </Typography.Title>
            { loadingText &&
              <Typography.Paragraph>
                {loadingText} <Spin />
              </Typography.Paragraph>
            }
            {
              interpretation &&
              <Typography.Paragraph style={{
                backgroundColor: 'rgba(255, 255, 255, 1)',
                border: '1px solid rgba(100, 100, 100, 0.2)',
                borderRadius: '6px',
                padding: '0.4em 0.6em',
                marginTop: '16px',
                marginBottom: '16px',
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
          marginTop: '32px',
        }}
      >
        <Typography>
          <Typography.Title level={2} mark>
            <CoffeeOutlined /> 相关线索
          </Typography.Title>
        </Typography>
        {
          matchResults.map((item, key) => {
            return (
              <Card
                style={{
                  marginBottom: '12px',
                }}
                size='small'
              >
                <p>
                  <strong>线索{key + 1}</strong>: 
                  {/* {item.content} */}
                  <Space direction="vertical" size="small">
                  {
                    // 将 doc.metadata?.content 按 $-$ 分割，换行显示
                    item.content.split('$-$').map((item, index) => {
                      if (index == 0) return <Text>{item}</Text>
                      if (index == 1) return <Text keyboard>{item}</Text>
                      if (index == 2) return <Link href={item} target="_blank">{item}</Link>
                      if (index === 3) return <Text italic type="secondary">{item}</Text>
                    })
                  }
                  </Space>
                </p>
              </Card>
            )
          })
        }
      </div>
      }
    </main>
  )
}

export default Sidepanel
