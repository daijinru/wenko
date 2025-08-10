import { makeAutoObservable, runInAction } from "mobx"
import { notification } from "antd"
import { fetchEventSource } from "@microsoft/fetch-event-source"
import newtabTask, { generateMsgId } from "./newtab.task"

// 添加一个 "_WENKO_STORE" 的 sessionStorage，用于存储数据
// 如果没有，则初始化为空对象
if (!localStorage.getItem("_WENKO_STORE")) {
  localStorage.setItem("_WENKO_STORE", JSON.stringify({}))
}
const getWenkoStore = () => {
  const store = JSON.parse(localStorage.getItem("_WENKO_STORE") || "{}")
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
  localStorage.setItem("_WENKO_STORE", JSON.stringify(store))
}

class DocumentStore {
  documents: any[] = []

  constructor() {
    makeAutoObservable(this)
  }

  keyword_classification: Record<string, any>[] = []
  reload = () => {
    // return
    // const store = getWenkoStore()
    // if (store.documents) {
    //   console.info('>< 读取缓存数据:', store.documents)
    //   this.documents = store.documents
    //   this.keyword_classification = store.keyword_classification
    //   return
    // }
    this.keyword_classification = [
      {Text: new Date().getTime().toString(), Weight: 0.3},
    ]
    notification.info({ message: '正在获取线索...' })
    this.getRelations()
    return
  }
  getRelations = () => {
    fetch("http://localhost:8080/search", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        texts: this.keyword_classification,
        n_results: 20,
      }),
    })
      .then(res => res.json())
      .then(docs => {
        if (!Array.isArray(docs)) {
          notification.warning({ message: '没有找到匹配的线索' })
          return
        }
        docs = docs.filter(doc => {
          if (!doc.metadata) doc.metadata = {}
          if (!doc.original) return false
          doc.metadata.original = JSON.parse(doc.original)
          doc.metadata.content = doc.content
          return true
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
