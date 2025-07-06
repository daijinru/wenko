import { runInAction, makeAutoObservable } from "mobx";


export interface MenuItem {
  name: string
  display_name?: string
  is_open: boolean
}

class MenusStore {
  openMenus = new Map<string, MenuItem>()

  constructor() {
    makeAutoObservable(this);

    window['_menusStore'] = this
  }

  toggleMenu = (name: string) => {
    runInAction(() => {
      const m = this.openMenus.get(name)
      if (m) {
        m.is_open = !m.is_open
      }
    })
  }

  isOpen = (name: string) => {
    const m = this.openMenus.get(name)
    return m ? m.is_open : false
  }

  joinMenu = (menu: MenuItem) => {
    runInAction(() => {
      this.openMenus.set(menu.name, menu)
    })
  }
}

export default new MenusStore()