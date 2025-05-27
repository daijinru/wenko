import { useState, useEffect } from 'react'
import { Card, Button, notification } from 'antd'
import { DoubleRightOutlined } from '@ant-design/icons'

export const NewTab = () => {
  const [documents, setDocuments] = useState([])
  useEffect(() => {
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
        setDocuments(docs)
      })
  }, [])

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
      console.info('>< 线索:', docs)
      setDocuments(docs)
    })
  }

  return (
    <section>
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4 md:p-6 lg:p-8">
        <div className="columns-1 sm:columns-2 lg:columns-3 xl:columns-4 gap-4 md:gap-6 space-y-4 md:space-y-6">
          {
            documents.map(doc => {
              return (
                <Card
                  size='small'
                  key={doc.id}
                  className="break-inside-avoid mb-4 md:mb-6 shadow-sm hover:shadow-md transition-shadow duration-300 bg-white/80 backdrop-blur-sm border-slate-200/50"
                  extra={<Button onClick={() => getRelations(doc.metadata?.content)} icon={<DoubleRightOutlined />} type="text"></Button>}
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
  )
}

export default NewTab
