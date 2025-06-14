import { useState, useEffect } from 'react'

import Editor from './editor'

import { observer } from 'mobx-react-lite'
import documentStore from './store/newtab.document'

import Chat from './Chat'
import Documents from './Documents'

import './NewTab.css'

const NewTab = () => {
  const [editor, setEditor] = useState(false)

  useEffect(() => {
    documentStore.reload()
  }, [])

  return (
    <>
      <section>
        {
          editor
            ? <Editor />
            : <Documents />
        }
      </section>
      <section>
        <Chat />
      </section>
    </>
  )
}

export default observer(NewTab)
