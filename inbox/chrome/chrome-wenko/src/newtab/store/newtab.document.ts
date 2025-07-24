import { makeAutoObservable, runInAction } from "mobx"
import { notification } from "antd"
import { fetchEventSource } from "@microsoft/fetch-event-source"
import newtabTask, { generateMsgId } from "./newtab.task"

// 添加一个 "_WENKO_STORE" 的 sessionStorage，用于存储数据
// 如果没有，则初始化为空对象
if (!sessionStorage.getItem("_WENKO_STORE")) {
  sessionStorage.setItem("_WENKO_STORE", JSON.stringify({}))
}
const getWenkoStore = () => {
  const store = JSON.parse(sessionStorage.getItem("_WENKO_STORE") || "{}")
  const date = new Date().toISOString().split("T")[0]
  if (store.date === date) {
    return store
  }
  return {}
}
const setWenkoStore = (key: string | Record<string, any>, value?: any) => {
  const store = getWenkoStore()
  if (typeof key === 'string') {
    store[key] = value
  } else if (typeof key === 'object') {
    Object.assign(store, key)
  }
  sessionStorage.setItem("_WENKO_STORE", JSON.stringify(store))
}


class DocumentStore {
  documents: any[] = []

  constructor() {
    makeAutoObservable(this)
  }

  keyword_classification = ''
  reload = () => {
    const store = getWenkoStore()
    if (store.documents) {
      console.info('>< 读取缓存数据:', store.documents)
      this.documents = store.documents
      this.keyword_classification = store.keyword_classification
      return
    }
    notification.info({ message: '无缓存数据，正在生成...' })
    // fetch http://localhost:8080/documents
    this.keyword_classification = ''
    fetchEventSource('http://localhost:8080/task', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        id: generateMsgId(),
        text: '[keyword_classification]',
      }),
      onopen: (res) => {
        console.log('open', res)
        if (res.ok) return Promise.resolve()
      },
      onmessage: (line) => {
        try {
          const parsed = JSON.parse(line.data)
          console.log('<intent parsed>', parsed)
          const payload = parsed.payload
          if (payload.type !== 'text') return
          runInAction(() => {
            this.keyword_classification = this.keyword_classification + payload.payload.content
          })
        } catch (error) {
          console.error(error)
        }
      },
      onclose: () => {
        console.log('<intent parsed> close', this.keyword_classification)
        notification.success({ message: this.keyword_classification })
        newtabTask.addUserMessage(this.keyword_classification)
        this.getRelations(this.keyword_classification)
      },
      onerror: (err) => {
        console.log('error', err)
      },
    })
    return
  }
  getRelations = (text) => {
    // 通过 $-$ 切割 text，取第一个元素
    text = text.split('$-$')[0]
    if (!text) return
    fetch("http://localhost:8080/search", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        texts: [{ Text: text, Weight: 0.6 }]
      }),
    })
      .then(res => res.json())
      .then(docs => {
        if (!Array.isArray(docs)) {
          notification.warning({ message: '没有找到匹配的线索' })
          return
        }
        docs.forEach(doc => {
          if (!doc.metadata) doc.metadata = {}
          doc.metadata.content = doc.content
        })
        // 随机处理 docs
        docs = docs.sort(() => Math.random() - 0.5)
        console.info('>< 线索:', docs)
        runInAction(() => {
          this.documents = docs
        })
        setWenkoStore({
          documents: docs,
          keyword_classification: this.keyword_classification,
          date: new Date().toISOString().split("T")[0],
        })
      })
  }
  deleteRecord = async (id: string) => {
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
          this.reload()
        } else {
          console.warn('删除失败', id)
          alert('删除失败')
        }
      })
  }
}

export default new DocumentStore()
