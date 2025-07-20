
import { Flex, Result, Card, Space, Button } from "antd"
import { Bubble, Sender } from '@ant-design/x'
import taskStore from '../store/newtab.task'
import { UserOutlined, NotificationOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'

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
}
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
            <Card variant='borderless' size='small'>
              <p>{message.content}</p>
              <Space direction='vertical'>
                <Sender
                  disabled={!taskStore.isWaitForAnswer}
                  value={taskStore.userValue}
                  onChange={value => taskStore.setUserValue(value)}
                  loading={taskStore.isLoading}
                  submitType="shiftEnter"
                  placeholder="Press Shift + Enter to send message"
                  onSubmit={text => {
                    taskStore.onAnswer(text)
                  }}
                  onCancel={taskStore.onCancelTask}
                />
                <Button type='text' color='danger' size='small' onClick={taskStore.onCancelTask}>Cancel</Button>
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

export const NAME = 'task.chat'
export const MENU = { name: NAME, display_name: 'Task', is_open: false }

const App = () => {
  return (
    <>
      {
        taskStore.messages.length > 0 ?
          <div
            className='mb-16px bg-[rgba(255,255,255,0.9)] rounded-12px overflow-y-scroll scrollbar-hide px-16px py-16px'
            style={{
              maxHeight: 'calc(100vh - 200px)',
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
          : <></>
      }
    </>
  )
}

export default App