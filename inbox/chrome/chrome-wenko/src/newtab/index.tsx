import React from 'react'
import ReactDOM from 'react-dom/client'
import NewTab from './NewTab'
import './index.css'

import 'virtual:windi.css'

ReactDOM.createRoot(document.getElementById('app') as HTMLElement).render(
  <NewTab />
)
