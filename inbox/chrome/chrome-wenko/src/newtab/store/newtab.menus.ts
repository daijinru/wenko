import { runInAction, makeAutoObservable } from "mobx";


export interface MenuItem {
  name: string
  display_name?: string
  is_open: boolean
  zIndex?: number
}

class MenusStore {
  openMenus = new Map<string, MenuItem>()
  zIndex = 1000

  constructor() {
    makeAutoObservable(this);

    window['_menusStore'] = this
  }
  /** 切换指定菜单的开关状态 */
  toggleMenu = (name: string) => {
    runInAction(() => {
      const m = this.openMenus.get(name)
      if (m) {
        this.setOpen(m, !m.is_open)
      }
    })
  }
  /** 仅打开指定菜单并关闭其它菜单 */
  openOnlyOne = (name: string) => {
    runInAction(() => {
      this.openMenus.forEach(m => {
        if (m.name === name) {
          this.setOpen(m, true)
        } else {
          this.setOpen(m, false)
        }
      })
    })
  }
  /** 主动开关菜单项 */
  setOpen = (menu: MenuItem, open: boolean) => {
    runInAction(() => {
      if (open) {
        menu.zIndex = this.zIndex++
      }
      menu.is_open = open
    })
  }
  /** 获取指定menu item的开关状态 */
  isOpen = (name: string) => {
    const m = this.openMenus.get(name)
    return m ? m.is_open : false
  }
  getZIndex = (name: string) => {
    const m = this.openMenus.get(name)
    return m ? m.zIndex : 1000
  }
  /** 批量加入菜单项(初始化) */
  joinMenus = (menus: MenuItem[]) => {
    runInAction(() => {
      menus.forEach(menu => {
        menu.zIndex = this.zIndex++
        this.openMenus.set(menu.name, menu)
      })
    })
  }
}

export default new MenusStore()