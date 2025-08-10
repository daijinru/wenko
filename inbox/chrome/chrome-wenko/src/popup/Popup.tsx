import { useState, useEffect } from 'react'
import { Divider } from 'antd'

import './Popup.css'

const saveOptionToStorage = (option: Record<string, any>, callback?: () => void) => {
  chrome.storage.sync.set(option, () => {
    if (callback) callback()
  })
}

export const Popup = () => {
  const [pauseUse, setPauseUse] = useState<boolean>(false)
  const [pauseRecord, setPauseRecord] = useState<boolean>(false)

  useEffect(() => {
    chrome.storage.sync.get(['pauseUse', 'pauseRecord'], (result) => {
      setPauseUse(!!result.pauseUse)
      setPauseRecord(!!result.pauseRecord)
    })
  }, [])

  const sendMessageToContent = (msg: any) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]?.id) {
        chrome.tabs.sendMessage(tabs[0].id, msg)
      }
    })
  }

  const onPauseUseChange = (e: any) => {
    const checked = e.target.checked
    setPauseUse(checked)
    saveOptionToStorage({ pauseUse: checked })
    sendMessageToContent({ action: 'wenko_popup_option', option: {pauseUse: checked} })
  }

  const onPauseRecordChange = (e: any) => {
    const checked = e.target.checked
    setPauseRecord(checked)
    saveOptionToStorage({ pauseRecord: checked })
    sendMessageToContent({ action: 'wenko_popup_option', option: {pauseRecord: checked} })
  }

  return (
    <main>
      <h3>Quick Options</h3>
      <Divider />
      <section >
        <label>
          <input type="checkbox" checked={pauseUse} onChange={onPauseUseChange} />
          Stop Load Widget
        </label>
        <label>
          <input type="checkbox" checked={pauseRecord} onChange={onPauseRecordChange} />
          Stop Record (but widget loaded)
        </label>
      </section>
    </main>
  )
}

export default Popup
