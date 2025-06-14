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

import { observer } from 'mobx-react-lite'
import taskStore from './store/newtab.task'

import './NewTab.css'

// 一个使用 uuid 生成 msg_id 的函数
const generateMsgId = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

const NewTab = () => {
  const [editor, setEditor] = useState(false)
  const [documents, setDocuments] = useState([])
  const inputRef = useRef<any>(null)
  const [isFocus, setIsFocus] = useState(false)

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
                <Button type='text' color='danger' size='small' onClick={taskStore.onCancelTask}>取消</Button>
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
              <div className="!pb-400px min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4 md:p-6 lg:p-8">
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
        <div className='w-480px fixed bottom-32px left-32px'>
          {
            taskStore.messages.length > 0 ?
              <div
                className='mb-16px bg-[rgba(255,255,255,0.9)] rounded-12px overflow-y-scroll scrollbar-hide px-16px py-16px'
                style={{
                  maxHeight: 'calc(100vh - 200px)',
                  boxShadow: 'rgba(14, 63, 126, 0.06) 0px 0px 0px 1px, rgba(42, 51, 70, 0.03) 0px 1px 1px -0.5px, rgba(42, 51, 70, 0.04) 0px 2px 2px -1px, rgba(42, 51, 70, 0.04) 0px 3px 3px -1.5px, rgba(42, 51, 70, 0.03) 0px 5px 5px -2.5px, rgba(42, 51, 70, 0.03) 0px 10px 10px -5px, rgba(42, 51, 70, 0.03) 0px 24px 24px -8px'
                }}
              >
                <Flex gap="middle" vertical>
                  {
                    taskStore.messages.map(message => {
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
              : !taskStore.isWaitForAnswer && taskStore.messages.length < 1 ?
                <div
                  className='mb-16px bg-[rgba(255,255,255,0.9)] rounded-12px p-16px'
                  style={{
                    boxShadow: 'rgba(14, 63, 126, 0.06) 0px 0px 0px 1px, rgba(42, 51, 70, 0.03) 0px 1px 1px -0.5px, rgba(42, 51, 70, 0.04) 0px 2px 2px -1px, rgba(42, 51, 70, 0.04) 0px 3px 3px -1.5px, rgba(42, 51, 70, 0.03) 0px 5px 5px -2.5px, rgba(42, 51, 70, 0.03) 0px 10px 10px -5px, rgba(42, 51, 70, 0.03) 0px 24px 24px -8px'
                  }}
                >
                  <Prompts onSend={text => taskStore.onNewTask(text)} />
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
              disabled={!taskStore.isWaitForAnswer}
              value={taskStore.userValue}
              onChange={taskStore.setUserValue}
              loading={taskStore.isLoading}
              submitType="shiftEnter"
              placeholder="Press Shift + Enter to send message"
              onSubmit={text => {
                taskStore.onNewTask(text)
              }}
              onCancel={taskStore.onCancelTask}
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

export default observer(NewTab)
