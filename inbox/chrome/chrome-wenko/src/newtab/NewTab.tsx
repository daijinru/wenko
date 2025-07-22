import { observer } from 'mobx-react-lite'
import Menus from './Menus'
import Documents from './Documents'

import './NewTab.css'

const NewTab = () => {
  return (
    <>
      <section>
        <Documents />
      </section>
      <section>
        <Menus />
      </section>
    </>
  )
}

export default observer(NewTab)
