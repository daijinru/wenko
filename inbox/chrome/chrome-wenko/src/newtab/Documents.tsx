import { useRef, useEffect } from "react"
import { Card, Space, Button, Tooltip } from "antd"
import { observer } from "mobx-react-lite"
import { BulbTwoTone, DeleteTwoTone } from '@ant-design/icons'

import documentStore from "./store/newtab.document"

const Documents = () => {

  const hashCount = useRef(0)
  const getRelations = (text) => {
    // 主动修改路由 #1 #2，形成可回退的路由
    window.location.hash = `#` + hashCount.current++
    documentStore.getRelations(text)
  }

  // 监听 hash router 变化
  useEffect(() => {
    window.onhashchange = () => {
      if (window.location.hash === '') {
        documentStore.reload()
      }
    }
  }, [])

  return (
    <div className="!pb-400px min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4 md:p-6 lg:p-8">
      <div className="columns-1 sm:columns-2 lg:columns-3 xl:columns-4 gap-4 md:gap-6 space-y-4 md:space-y-6">
        {
          documentStore.documents.map(doc => {
            return (
              <Card
                size='small'
                key={doc.id}
                className="break-inside-avoid mb-4 md:mb-6 shadow-sm hover:shadow-md transition-shadow duration-300 bg-white/80 backdrop-blur-sm border-slate-200/50"
                extra={
                  <Space size="small">
                    <Tooltip title="删除">
                      <Button onClick={() => documentStore.deleteRecord(doc.id)} icon={<DeleteTwoTone twoToneColor={"#eb2f96"} />} type="text"></Button>
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
  );
}

export default observer(Documents)
