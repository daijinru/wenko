import { makeAutoObservable, runInAction } from "mobx"
import { last } from "lodash-es"
import { fetchEventSource } from "@microsoft/fetch-event-source"
import { isObject } from "lodash-es"
import { message } from "antd"

export const generateMsgId = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

export type PayloadMessageType = {
  type: string
  payload: {
    content: string
    meta: {
      id: string
      [key: string]: any
    }
  }
}
export type SSE_DataType = {
  type: string
  payload: string
  actionID: string
}
export type Message = {
  id: string
  type: string
  role: string
  content: string
  action?: string
}

class PlanningTaskStore {
  isFocus: boolean = false
  isTaskMode: boolean = false
  isWaitForAnswer: boolean = false
  isLoading: boolean = false

  messages: Message[] = []

  userValue:string = ''
  setUserValue(value: string) {
    this.userValue = value
  }

  constructor() {
    makeAutoObservable(this)
    window['_NewTab'] = this
  }
  
  onNewTask = async (text: string) => {
    const userTaskMessage = {
      id: generateMsgId(),
      type: 'text',
      role: 'user',
      content: text,
    }
    runInAction(() => {
      this.messages = []
      this.messages.push(userTaskMessage)
      this.isTaskMode = true
      this.isLoading = true
      this.userValue = ''
    })

    await fetchEventSource('http://localhost:8080/task', {
      method: 'POST',
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        text,
      }),
      onopen: res => {
        console.info('>< onopen:', res)
        if (!res.ok) {
          message.warning(res.status + ': ' + res.statusText)
          return Promise.resolve()
        }
        if (res.ok) return Promise.resolve()
      },
      onmessage: line => {
        try {
          const parsed: SSE_DataType = JSON.parse(line.data)
          this.handleMessage(parsed)
        } catch (error) {
          console.error(error)
        }
      },
      onclose: () => {
        runInAction(() => {
          this.isLoading = false
        })
      },
      onerror: err => {
        console.error('>< onerror: ' + err)
      },
    })
  }

  handleMessage = (data: SSE_DataType) => {
    // 状态文本处理
    if (data?.type === 'statusText') {
      const newMessage = {
        id: generateMsgId(),
        type: 'statusText',
        role: 'assistant',
        content: data?.payload,
      }
      runInAction(() => {
        this.messages.push(newMessage)
      })
      return
    }
    // console.info('>< parsed:', parsed)

    // 正文处理
    const payload: PayloadMessageType = JSON.parse(data?.payload)
    if (data?.type === 'text' && isObject(payload)) {
      if (payload?.type === 'text') {
        const newMessage = {
          id: payload.payload.meta.id,
          type: 'text',
          role: 'assistant',
          content: payload.payload.content || '',
        }

        this.appendMessage(newMessage)

      } else if (payload?.type === 'ask') {
        /** ask 类型问题，基本类型同样是 text，通过 action 区分 */
        const newMessage = {
          id: data.actionID,
          type: 'text',
          role: 'assistant',
          content: payload.payload.content || '',
          action: 'ask',
        }
        this.appendMessage(newMessage)
        runInAction(() => {
          // 遇到 ask 类型问题，停止 loading
          this.isLoading = false
          this.isWaitForAnswer = true
        })
      }
    }
  }

  appendMessage = (message: Message) => {
    const lastMessage = this.messages.findLast(msg => msg.id === message.id)
    if (!lastMessage) {
      runInAction(() => {
        this.messages.push(message)
      })
      return
    }
    const updatedMessage = {...lastMessage, content: lastMessage.content + message.content }
    runInAction(() => {
      this.messages = [...this.messages.slice(0, -1), updatedMessage]
    })
  }

  onCancelTask = () => {
    fetch("http://localhost:8080/planning/task/interrupt", {
      method: 'POST',
      headers: {
        "Content-Type": "application/json",
      },
    })
      .then(res => res.json())
      .then(res => {
        runInAction(() => {
          this.isLoading = false
          this.isTaskMode = false
        })
      })
  }

  /** 获取最新问题的actionID */
  getAnswerActionID(): string {
    let askMessage = last(this.messages)
    // 遍历 messages，找到最后一个 action 为 ask 的消息
    for (let i = this.messages.length - 1; i >= 0; i--) {
      if (this.messages[i].action === 'ask') {
        askMessage = this.messages[i]
        return askMessage.id
      }
    }
    console.info('<getAnswerActionID> possibly error happen: ', askMessage, this.messages)
    return ''
  }
  /** 用户输入模式：仅支持任务模式-等待回答状态，不支持无明确目标的自由交流 */
  onAnswer = (content: string) => {
    const newMessage = {
      type: 'text',
      role: 'user',
      content,
      id: generateMsgId(),
    }
    this.messages.push(newMessage)
    this.userValue = ''

    if (this.isTaskMode) {
      if (this.isWaitForAnswer) {
        fetch("http://localhost:8080/planning/task/answer", {
          method: 'POST',
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            text: content,
            actionID: this.getAnswerActionID(),
          }),
        })
          .then(res => res.json())
          .then(res => {
            runInAction(() => {
              this.isWaitForAnswer = false
            })
        })
      } else {
      }
    }
  }
}

export default new PlanningTaskStore()

