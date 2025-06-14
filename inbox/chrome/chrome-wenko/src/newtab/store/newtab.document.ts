import { makeAutoObservable, runInAction } from "mobx"
import { notification } from "antd";

class DocumentStore {
  documents: any[] = []

  constructor() {
    makeAutoObservable(this);
  }

  reload = () => {
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
        runInAction(() => {
          this.documents = docs
        })
      })
  }
  getRelations = (text) => {
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
        runInAction(() => {
          this.documents = docs
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
