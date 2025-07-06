import React, { useEffect } from "react";
import menusStore, { MenuItem } from "../store/newtab.menus";
import { observer } from "mobx-react-lite";

interface MenusHocProps {
  menu: MenuItem;
  children: React.ReactNode;
}

const MenusHoc: React.FC<MenusHocProps> = ({ menu, children }) => {
  return <>
    <div
      className='bg-[rgba(255,255,255,0.95)] rounded-8px p-8px'
      style={{
        // boxShadow: 'rgba(9, 9, 9, 0.06) 0px 0px 0px 1px, rgba(42, 51, 70, 0.03) 0px 1px 1px -0.5px, rgba(42, 51, 70, 0.04) 0px 2px 2px -1px, rgba(42, 51, 70, 0.04) 0px 3px 3px -1.5px, rgba(42, 51, 70, 0.03) 0px 5px 5px -2.5px, rgba(42, 51, 70, 0.03) 0px 10px 10px -5px, rgba(42, 51, 70, 0.03) 0px 24px 24px -8px'
        // boxShadow: 'rgba(0, 0, 0, 0.4) 0px 2px 4px, rgba(0, 0, 0, 0.3) 0px 7px 13px -3px, rgba(0, 0, 0, 0.2) 0px -3px 0px inset'
        boxShadow: 'rgb(85, 91, 255) 0px 0px 0px 3px, rgb(31, 193, 27) 0px 0px 0px 6px, rgb(255, 217, 19) 0px 0px 0px 9px, rgb(255, 156, 85) 0px 0px 0px 12px, rgb(255, 85, 85) 0px 0px 0px 15px',
      }}
    >
      {children}
    </div>
  </>;
};

export default observer(MenusHoc);