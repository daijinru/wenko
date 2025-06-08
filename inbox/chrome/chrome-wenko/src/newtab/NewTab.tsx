import { useState, useEffect } from 'react'
import { Card, Button, notification, Space, Tooltip, Flex } from 'antd'
import { Sender, Bubble } from '@ant-design/x'
import { BulbTwoTone, DeleteTwoTone, UserOutlined } from '@ant-design/icons'
import { fetchEventSource } from '@microsoft/fetch-event-source'
import Editor from './editor'
import './NewTab.css'

// 一个使用 uuid 生成 msg_id 的函数
const generateMsgId = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

export const NewTab = () => {
  const [editor, setEditor] = useState(false)
  const [documents, setDocuments] = useState([])
  const [userValue, setUserValue] = useState('')
  const [messages, setMessages] = useState([] as any[])

  useEffect(() => {
    reload()
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
        notification.warning({message: '没有找到匹配的线索'})
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
  const onUserSubmit = content => {
    const newMessage = {
      type: 'text',
      role: 'user',
      content,
      id: generateMsgId(),
    }
    setMessages(prev => [...prev, newMessage])
    setUserValue('')
    newChat(content)
  }

  let currentMsgId = ''
  const newChat = async text => {
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
        if (res.ok) return Promise.resolve()
        if (!currentMsgId) currentMsgId = generateMsgId()
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
      onerror(err) {
        console.error(err)
        currentMsgId = ''
      },
    })
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
            messages.length > 0 &&
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
                          isAssistant(message) &&
                            <Bubble
                              key={message.id}
                              placement='start'
                              avatar={{ icon: <UserOutlined />, style: fooAvatar }}
                              content={message.content}
                            />
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
          }
          <div
            className='bg-white rounded-12px'
            style={{
              boxShadow: 'rgba(14, 63, 126, 0.06) 0px 0px 0px 1px, rgba(42, 51, 70, 0.03) 0px 1px 1px -0.5px, rgba(42, 51, 70, 0.04) 0px 2px 2px -1px, rgba(42, 51, 70, 0.04) 0px 3px 3px -1.5px, rgba(42, 51, 70, 0.03) 0px 5px 5px -2.5px, rgba(42, 51, 70, 0.03) 0px 10px 10px -5px, rgba(42, 51, 70, 0.03) 0px 24px 24px -8px'
            }}
          >
            <Sender
              value={userValue}
              onChange={setUserValue}
              submitType="shiftEnter"
              placeholder="Press Shift + Enter to send message"
              onSubmit={text => {
                onUserSubmit(text)
                // message.success('Send message successfully!');
              }}
            />
          </div>
        </div>
      </section>
    </>
  )
}

export default NewTab
