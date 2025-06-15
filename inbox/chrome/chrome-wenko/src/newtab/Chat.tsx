import { useRef } from "react"
import { observer } from "mobx-react-lite"
import { Flex, Result, Card, Space, Button } from "antd"
import { Sender, Bubble } from "@ant-design/x"
import { UserOutlined, NotificationOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { last } from "lodash-es"

import taskStore from "./store/newtab.task"
import Prompts from "./Prompts"

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
        key={message.content}
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
    if (!message.action) {
      return (
        <Bubble
          key={message.content}
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
    } else if (message.action === 'ask') {
      return (
        <Bubble
          key={message.content}
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
  }
  return <>
    <Bubble key={'xx-xx'} placement="start" content="nothing else" />
  </>
}

const Chat = () => {
  const inputRef = useRef<any>(null)
  return (
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
          : taskStore.messages.length < 1 ?
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
          onChange={value => taskStore.setUserValue(value)}
          loading={taskStore.isLoading}
          submitType="shiftEnter"
          placeholder="Press Shift + Enter to send message"
          onSubmit={text => {
            taskStore.onNewTask(text)
          }}
          onCancel={taskStore.onCancelTask}
        />
      </div>
    </div>
  );
}

export default observer(Chat);
