import { useEffect } from "react"
import { Card, Space, Button, Tooltip, Typography } from "antd"
import { observer } from "mobx-react-lite"
import { DeleteTwoTone } from '@ant-design/icons'

import documentStore from "./store/newtab.document"

const { Text, Link } = Typography

const Documents = () => {

  // 监听 hash router 变化
  useEffect(() => {
    documentStore.reload()
  }, [])

  return (
    <div className="!pb-400px min-h-screen p-4 md:p-6 lg:p-8 !pt-60px">
      <div className="columns-1 sm:columns-2 lg:columns-3 xl:columns-4 gap-4 md:gap-6 space-y-4 md:space-y-6">
        {
          documentStore.documents.map(doc => {
            return (
              <Card
                size='small'
                key={doc.id}
                className="break-inside-avoid mb-4 md:mb-6 border-slate-200/50"
                extra={
                  <Space size="small">
                    <Tooltip title="删除">
                      <Button onClick={() => documentStore.deleteRecord(doc.id)} icon={<DeleteTwoTone twoToneColor={"#eb2f96"} />} type="text"></Button>
                    </Tooltip>
                  </Space>
                }
              >
                <div className="p-4 md:p-6">
                  <p className="text-12 overflow-hidden text-slate-700 leading-relaxed">
                    <Space direction="vertical" size="small">
                      <Text>{doc.metadata?.original?.title}</Text>
                      <Link onClick={() => {
                        window.open(doc.metadata?.original?.url, '_blank')
                      }} target="_blank">{doc.metadata?.original?.url}</Link>
                      <Text keyboard>{doc.metadata?.original?.time}</Text>
                      <Tooltip title={doc.metadata?.content}>
                        <Text italic type="secondary">{doc.metadata?.content.substr(0, 50)}...</Text>
                      </Tooltip>
                    </Space>
                  </p>
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
