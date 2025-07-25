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
                    {
                      // 将 doc.metadata?.content 按 $-$ 分割，换行显示
                      doc.metadata?.content.split('$-$').map((item, index) => {
                        if (index == 0) return <Text>{item}</Text>
                        if (index == 1) return <Text keyboard>{item}</Text>
                        if (index == 2) return <Link href={item} target="_blank">{item}</Link>
                        if (index === 3) return <Text italic type="secondary">{item}</Text>
                      })
                    }
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
