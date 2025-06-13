import { useState, useEffect, useRef } from 'react'
import { Card, Button, notification, Space, Tooltip, Flex, Result } from 'antd'
import { Sender, Bubble } from '@ant-design/x'
import { BulbTwoTone, DeleteTwoTone, UserOutlined, NotificationOutlined } from '@ant-design/icons'
import { fetchEventSource } from '@microsoft/fetch-event-source'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { isObject, last } from 'lodash-es'
import Editor from './editor'
import Prompts from './Prompts'
import './NewTab.css'

// 一个使用 uuid 生成 msg_id 的函数
const generateMsgId = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

export const NewTab = () => {
  const [editor, setEditor] = useState(false)
  const [documents, setDocuments] = useState([])
  const [userValue, setUserValue] = useState('')
  const [messages, setMessages] = useState([] as any[])
  const inputRef = useRef<any>(null)
  const [isFocus, setIsFocus] = useState(false)
  const [isTaskMode, setIsTaskMode] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    reload()

    window['_NewTab'] = {
      messages,
    }
  }, [])

  const reload = () => {
    // fetch http://localhost:8080/documents
    fetch("http://localhost:8080/documents", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        limit: 100,
        offset: 0,
      }),
    })
      .then((res) => res.json())
      .then((docs) => {
        // console.log(docs)
        if (Array.isArray(docs)) {
          docs.forEach(doc => {
            if (!doc.metadata || !doc.metadata.content) return
            doc.metadata.content = decodeURIComponent(doc.metadata?.content)
          })
        }
        docs = docs.sort(() => Math.random() - 0.5)
        setDocuments(docs)
      })
  }
  const getRelations = (text) => {
    fetch("http://localhost:8080/search", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text,
      }),
    })
      .then(res => res.json())
      .then(docs => {
        if (!Array.isArray(docs)) {
          notification.warning({ message: '没有找到匹配的线索' })
          return
        }
        docs.forEach(doc => {
          doc.content = decodeURIComponent(doc.content)
          if (!doc.metadata) doc.metadata = {}
          doc.metadata.content = doc.content
        })
        // 随机处理 docs
        docs = docs.sort(() => Math.random() - 0.5)
        console.info('>< 线索:', docs)
        setDocuments(docs)
      })
  }
  const deleteRecord = async (id: string) => {
    const r = window.confirm('确认删除吗？')
    if (!r) return
    fetch("http://localhost:8080/delete?id=" + id, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    })
      .then(res => res.json())
      .then(id => {
        if (id) {
          reload()
        } else {
          console.warn('删除失败', id)
          alert('删除失败')
        }
      })
  }

  const fooAvatar: React.CSSProperties = {
    color: '#f56a00',
    backgroundColor: '#fde3cf',
  };
  const barAvatar: React.CSSProperties = {
    color: '#fff',
    backgroundColor: '#87d068',
  };
  const hideAvatar: React.CSSProperties = {
    visibility: 'hidden',
  };
  const isUser = message => message.role === 'user'
  const isAssistant = message => message.role === 'assistant'
  const isAnswer = () => {
    const lastMessage = last(messages)
    return lastMessage?.type === 'ask'
  }
  const onUserSubmit = content => {
    const newMessage = {
      type: 'text',
      role: 'user',
      content,
      id: generateMsgId(),
    }
    setMessages(prev => [...prev, newMessage])
    setUserValue('')

    console.info('>< isTaskMode:', isTaskMode, isAnswer())
    if (isTaskMode) {
      if (isAnswer()) {
        fetch("http://localhost:8080/planning/task/answer", {
          method: 'POST',
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            text: content,
            actionID: last(messages)?.id,
          }),
        })
      } else {
        onNewTask(content)
      }
      return
    }
    // 普通对话
    newChat(content)
  }

  let currentMsgId = ''
  const newChat = async text => {
    setIsLoading(true)
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
            content: `${text}`
          }
        ]
      }),
      onopen(res) {
        if (!currentMsgId) currentMsgId = generateMsgId()
        if (res.ok) return Promise.resolve()
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
            // setLoadingText(parsed?.content)
          }
          if (parsed?.content && parsed?.type === 'text') {
            // setInterpretation(prev => prev + parsed.content)
            // setLoadingText('')
            const newMessage = {
              id: currentMsgId,
              type: 'text',
              role: 'assistant',
              content: parsed.content,
            }
            setMessages(prev => {
              const lastMessage = prev[prev.length - 1]
              if (lastMessage?.id === currentMsgId) {
                const updatedMessage = { ...lastMessage, content: lastMessage.content + parsed.content }
                return [...prev.slice(0, -1), updatedMessage]
              } else {
                return [...prev, newMessage]
              }
            })
            if (parsed?.done) {
              currentMsgId = ''
            }
          }
        } catch (error) {
          currentMsgId = ''
        }
      },
      onclose() {
        setIsLoading(false)
      },
      onerror(err) {
        console.error(err)
        currentMsgId = ''
      },
    })
  }

  type PayloadMessageType = {
    type: string
    payload: {
      content: string
      meta: {
        id: string
        [key: string]: any
      }
    }
  }
  type DataMessageType = {
    type: string
    payload: string
    actionID: string
  }
  // const onNewMessage = (payload: PayloadMessage) => {
  //   if (payload.Type === 'text') {
  //     const newMessage = {
  //       id: payload.Meta.id,
  //       type: 'text',
  //       role: 'assistant',
  //       content: payload.Content,
  //     }
  //     setMessages(prev => [...prev, newMessage])
  //   }
  // }
  const onNewTask = async text => {
    const userTaskMessage = {
      id: generateMsgId(),
      type: 'text',
      role: 'user',
      content: text,
    }
    setMessages(prev => [...prev, userTaskMessage])
    
    setIsTaskMode(true)
    setIsLoading(true)
    await fetchEventSource('http://localhost:8080/task', {
      method: 'POST',
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        text,
      }),
      onopen(res) {
        if (res.ok) return Promise.resolve()
      },
      onmessage(line) {
        try {
          const parsed: DataMessageType = JSON.parse(line.data)

          // 状态文本处理
          if (parsed?.type === 'statusText') {
            const newMessage = {
              id: generateMsgId(),
              type: 'statusText',
              role: 'assistant',
              content: parsed?.payload,
            }
            setMessages(prev => [...prev, newMessage])
          }
          // console.info('>< parsed:', parsed)

          // 正文处理
          const payload: PayloadMessageType = JSON.parse(parsed?.payload)
          if (parsed?.type === 'text' && isObject(payload)) {
            if (payload?.type === 'text') {
              const newMessage = {
                id: payload.payload.meta.id,
                type: 'text',
                role: 'assistant',
                content: payload.payload.content || '',
              }
              setMessages(prev => {
                const lastMessage = prev.findLast(msg => msg.id === payload.payload.meta.id)
                if (!lastMessage) return [...prev, newMessage]
                const updatedMessage = { ...lastMessage, content: lastMessage.content + newMessage.content }
                return [...prev.slice(0, -1), updatedMessage]
              })

            } else if (payload?.type === 'ask') {
              const newMessage = {
                id: parsed.actionID,
                type: 'ask',
                role: 'assistant',
                content: payload.payload.content || '',
              }
              setMessages(prev => {
                const lastMessage = prev.findLast(msg => msg.id === payload.payload.meta.id)
                if (!lastMessage) return [...prev, newMessage]
                const updatedMessage = { ...lastMessage, content: lastMessage.content + newMessage.content }
                return [...prev.slice(0, -1), updatedMessage]
              })
            }
          }
        } catch (error) {
          console.error(error)
        }
      },
      onclose() {
        setIsLoading(false)
      },
      onerror(err) {
        console.error(err)
      },
    })
  }

  const onCancelTask = () => {
    fetch("http://localhost:8080/planning/task/interrupt", {
      method: 'POST',
      headers: {
        "Content-Type": "application/json",
      },
    })
      .then(res => res.json())
      .then(res => {
        setIsLoading(false)
        setIsTaskMode(false)
      })
  }
  function renderAssistantMessage(message) {
    if (message.type === 'statusText') {
      return (
        <Bubble
          key={message.id}
          placement='start'
          avatar={{ icon: <UserOutlined />, style: hideAvatar }}
          content={
            <Result
              icon={<NotificationOutlined />}
              title={message.content}
            />
          }
        />
      )
    }
    if (message.type === 'text') {
      return (
        <Bubble
          key={message.id}
          placement='start'
          avatar={{ icon: <UserOutlined />, style: fooAvatar }}
          content={
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeRaw]}
            >
              {message.content}
            </ReactMarkdown>
          }
        />
      )
    } else if (message.type === 'ask') {
      return (
        <Bubble
          key={message.id}
          placement='start'
          avatar={{ icon: <UserOutlined />, style: fooAvatar }}
          content={<>
            <Card title={message.content} variant='borderless' size='small'>
              <Space>
                <Button type='text' disabled size='small'>请直接回复，或者取消</Button>
                <Button type='text' color='danger' size='small' onClick={onCancelTask}>取消</Button>
              </Space>
            </Card>
          </>}
        />
      )
    }
    return <></>
  }

  return (
    <>
      <section>
        {
          editor
            ? <Editor />
            : <section>
              <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4 md:p-6 lg:p-8">
                <div className="columns-1 sm:columns-2 lg:columns-3 xl:columns-4 gap-4 md:gap-6 space-y-4 md:space-y-6">
                  {
                    documents.map(doc => {
                      return (
                        <Card
                          size='small'
                          key={doc.id}
                          className="break-inside-avoid mb-4 md:mb-6 shadow-sm hover:shadow-md transition-shadow duration-300 bg-white/80 backdrop-blur-sm border-slate-200/50"
                          extra={
                            <Space size="small">
                              <Tooltip title="删除">
                                <Button onClick={() => deleteRecord(doc.id)} icon={<DeleteTwoTone twoToneColor={"#eb2f96"} />} type="text"></Button>
                              </Tooltip>
                              <Tooltip title="线索">
                                <Button onClick={() => getRelations(doc.metadata?.content)} icon={<BulbTwoTone />} type="text"></Button>
                              </Tooltip>
                            </Space>
                          }
                        >
                          <div className="p-4 md:p-6">
                            <p className="text-12 overflow-hidden text-slate-700 leading-relaxed">{doc.metadata?.content}</p>
                          </div>
                        </Card>
                      )
                    })
                  }
                </div>
              </div>
            </section>
        }
      </section>
      <section>
        <div className='w-480px fixed bottom-32px right-32px'>
          {
            messages.length > 0 ?
              <div
                className='mb-16px bg-[rgba(255,255,255,0.9)] rounded-12px overflow-y-scroll scrollbar-hide px-16px py-16px'
                style={{
                  maxHeight: 'calc(100vh - 200px)',
                  boxShadow: 'rgba(14, 63, 126, 0.06) 0px 0px 0px 1px, rgba(42, 51, 70, 0.03) 0px 1px 1px -0.5px, rgba(42, 51, 70, 0.04) 0px 2px 2px -1px, rgba(42, 51, 70, 0.04) 0px 3px 3px -1.5px, rgba(42, 51, 70, 0.03) 0px 5px 5px -2.5px, rgba(42, 51, 70, 0.03) 0px 10px 10px -5px, rgba(42, 51, 70, 0.03) 0px 24px 24px -8px'
                }}
              >
                <Flex gap="middle" vertical>
                  {
                    messages.map(message => {
                      return (
                        <>
                          {
                            isAssistant(message) && renderAssistantMessage(message)
                          }
                          {
                            isUser(message) &&
                            <Bubble
                              key={message.id}
                              placement='end'
                              avatar={{ icon: <UserOutlined />, style: barAvatar }}
                              content={message.content}
                            />
                          }
                        </>
                      )
                    })
                  }
                </Flex>
              </div>
              : isFocus ?
                <div
                  className='mb-16px bg-[rgba(255,255,255,0.9)] rounded-12px p-16px'
                  style={{
                    boxShadow: 'rgba(14, 63, 126, 0.06) 0px 0px 0px 1px, rgba(42, 51, 70, 0.03) 0px 1px 1px -0.5px, rgba(42, 51, 70, 0.04) 0px 2px 2px -1px, rgba(42, 51, 70, 0.04) 0px 3px 3px -1.5px, rgba(42, 51, 70, 0.03) 0px 5px 5px -2.5px, rgba(42, 51, 70, 0.03) 0px 10px 10px -5px, rgba(42, 51, 70, 0.03) 0px 24px 24px -8px'
                  }}
                >
                  <Prompts onSend={onNewTask} />
                </div>
                : null
          }
          <div
            className='bg-white rounded-12px'
            style={{
              boxShadow: 'rgba(14, 63, 126, 0.06) 0px 0px 0px 1px, rgba(42, 51, 70, 0.03) 0px 1px 1px -0.5px, rgba(42, 51, 70, 0.04) 0px 2px 2px -1px, rgba(42, 51, 70, 0.04) 0px 3px 3px -1.5px, rgba(42, 51, 70, 0.03) 0px 5px 5px -2.5px, rgba(42, 51, 70, 0.03) 0px 10px 10px -5px, rgba(42, 51, 70, 0.03) 0px 24px 24px -8px'
            }}
          >
            <Sender
              ref={inputRef}
              value={userValue}
              onChange={setUserValue}
              loading={isLoading}
              submitType="shiftEnter"
              placeholder="Press Shift + Enter to send message"
              onSubmit={text => {
                onUserSubmit(text)
                // message.success('Send message successfully!');
              }}
              onCancel={onCancelTask}
              onFocus={() => setIsFocus(true)}
              onBlur={() => {
                setTimeout(() => {
                  setIsFocus(false)
                }, 100)
              }}
            />
          </div>
        </div>
      </section>
    </>
  )
}

export default NewTab
