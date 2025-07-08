import { useEffect, useMemo } from "react"
import { observer } from "mobx-react-lite"
import { Space, Button } from "antd"

import taskStore from "./store/newtab.task"
import menusStore from "./store/newtab.menus"

import MenusHoc from "./common/menus.hoc"
import Prompts, { NAME as PromptsName, MENU as PromptsMenu  } from "./common/Prompts"
import TaskChat, { NAME as TaskChatName, MENU as TaskChatMenu } from "./common/Task.chat"

import './Menus.css'

const MenusHocPrompts = () => {
  return (
    <MenusHoc menu={PromptsMenu}>
      <Prompts onSend={text => {
        taskStore.onNewTask(text)
        menusStore.openOnlyOne(TaskChatName)
      }} />
    </MenusHoc>
  )
}
const MenusHocTaskChat = () => {
  return (
    <MenusHoc menu={TaskChatMenu}>
      <TaskChat />
    </MenusHoc>
  )
}

const Chat = () => {
  useEffect(() => {
    menusStore.joinMenus([PromptsMenu, TaskChatMenu])
  }, [])

  return (
    <>
      <div
        className={`fixed w-360px top-64px right-32px ${
          menusStore.isOpen(PromptsName) ? 'slide-in' : 'slide-out'
        }`}
        style={{
          zIndex: menusStore.getZIndex(PromptsName)
        }}
      >
        <MenusHocPrompts />
      </div>

      <div
        className={`fixed w-360px top-64px right-32px ${
          menusStore.isOpen(TaskChatName) ? 'slide-in' : 'slide-out'
        }`}
        style={{
          zIndex: menusStore.getZIndex(TaskChatName)
        }}
      >
        <MenusHocTaskChat />
      </div>

      <div
        className='fixed top-0 left-0 w-full h-48px bg-white rounded-b-8px px-12px'
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
                  if (menu.name === TaskChatName) {
                    return (
                      <Button
                        key={menu.name}
                        size="small"
                        disabled={taskStore.messages.length === 0}
                        type={
                          menusStore.isOpen(menu.name) ? 'primary' : 'default'
                        }
                        onClick={() => {
                          menusStore.toggleMenu(menu.name)
                        }}
                      >{menu.display_name}</Button>
                    )
                  }
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
      </div>
    </>
  );
}

export default observer(Chat);
