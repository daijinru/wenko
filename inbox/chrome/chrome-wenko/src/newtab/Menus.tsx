import { useEffect, useRef, useState } from "react"
import { observer } from "mobx-react-lite"
import { Flex, Result, Card, Space, Button } from "antd"
import { Sender, Bubble } from "@ant-design/x"
import { UserOutlined, NotificationOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'

import taskStore from "./store/newtab.task"
import menusStore from "./store/newtab.menus"
import Prompts, { NAME as PromptsName, MENU as PromptsMenu  } from "./common/Prompts"

import MenusHoc from "./common/menus.hoc"

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

const MenusHocPrompts = () => {
  return (
    <MenusHoc menu={PromptsMenu}>
      <Prompts onSend={text => taskStore.onNewTask(text)} />
    </MenusHoc>
  )
}

const Chat = () => {
  useEffect(() => {
    console.info('joinMenu', PromptsName, PromptsMenu)
    menusStore.joinMenu(PromptsMenu)
  }, [])
  return (
    <div className='w-480px fixed bottom-32px right-32px'>
      {
        taskStore.messages.length > 0 ?
          <div
            className='mb-16px bg-[rgba(255,255,255,0.9)] rounded-12px overflow-y-scroll scrollbar-hide px-16px py-16px'
            style={{
              maxHeight: 'calc(100vh - 200px)',
              // boxShadow: 'rgba(14, 63, 126, 0.06) 0px 0px 0px 1px, rgba(42, 51, 70, 0.03) 0px 1px 1px -0.5px, rgba(42, 51, 70, 0.04) 0px 2px 2px -1px, rgba(42, 51, 70, 0.04) 0px 3px 3px -1.5px, rgba(42, 51, 70, 0.03) 0px 5px 5px -2.5px, rgba(42, 51, 70, 0.03) 0px 10px 10px -5px, rgba(42, 51, 70, 0.03) 0px 24px 24px -8px'
              boxShadow: 'rgb(85, 91, 255) 0px 0px 0px 3px, rgb(31, 193, 27) 0px 0px 0px 6px, rgb(255, 217, 19) 0px 0px 0px 9px, rgb(255, 156, 85) 0px 0px 0px 12px, rgb(255, 85, 85) 0px 0px 0px 15px'
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

      {
        menusStore.isOpen(PromptsName)
          ? <div className="fixed max-w-360px top-64px right-32px"><MenusHocPrompts /></div>
          : <></>
      }

      <div
        className='fixed top-0 left-0 w-full h-36px bg-white rounded-b-8px px-12px'
        style={{
          // boxShadow: 'rgba(14, 63, 126, 0.06) 0px 0px 0px 1px, rgba(42, 51, 70, 0.03) 0px 1px 1px -0.5px, rgba(42, 51, 70, 0.04) 0px 2px 2px -1px, rgba(42, 51, 70, 0.04) 0px 3px 3px -1.5px, rgba(42, 51, 70, 0.03) 0px 5px 5px -2.5px, rgba(42, 51, 70, 0.03) 0px 10px 10px -5px, rgba(42, 51, 70, 0.03) 0px 24px 24px -8px'
          boxShadow: 'rgba(0, 0, 0, 0.4) 0px 2px 4px, rgba(0, 0, 0, 0.3) 0px 7px 13px -3px, rgba(0, 0, 0, 0.2) 0px -3px 0px inset'
        }}
      >
        <div className="h-full flex flex-row items-center justify-between">
          <div>
            <span className="text-14px font-bold">WENKO!</span>
          </div>
          <div className="">
            <Space size='small'>
              {
                menusStore.openMenus.size > 0 && Array.from(menusStore.openMenus.values()).map(menu => {
                  return (
                    <Button
                      key={menu.name}
                      size="small"
                      type={
                        menusStore.isOpen(menu.name) ? 'primary' : 'default'
                      }
                      onClick={() => {
                        menusStore.toggleMenu(menu.name)
                      }}
                    >{menu.display_name}</Button>
                  )
                })
              }
            </Space>
          </div>
        </div>
        {/* <Sender
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
        /> */}
      </div>
    </div>
  );
}

export default observer(Chat);
