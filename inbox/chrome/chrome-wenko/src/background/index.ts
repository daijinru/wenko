console.log('background is running')

chrome.runtime.onMessage.addListener((request) => {
  if (request.type === 'COUNT') {
    console.log('background has received a message from popup, and count is ', request?.count)
  }
})

chrome.contextMenus.create({ 
  id: "highlightAndOpenPanel",
  title: "高亮选中文本并打开Wenko",  // 菜单显示名称 
  contexts: ["selection"]  // 仅在用户选中文本时显示 
});


chrome.contextMenus.onClicked.addListener((info,  tab) => {
  if (info.menuItemId  === "highlightAndOpenPanel") {
    const selectedText = info.selectionText; 
    
    if (tab && typeof tab.id === "number") {
      let returnHighlightId = '';
      // 向内容脚本发送高亮请求（传递选中文本）
      chrome.tabs.sendMessage(tab.id,  {
        action: "highlightText",
        text: selectedText 
      }, (response) => {
        returnHighlightId = response.highlightId; // 获取返回的高亮ID
      });
  
      // TODO 打开侧边面板并传递文本
      // @ts-ignore 
      chrome.sidePanel.open({  windowId: tab.windowId  });
      setTimeout(() => {
        chrome.runtime.sendMessage({ 
          action: "updateSidePanel",
          text: selectedText + '_' + returnHighlightId,
        });
      }, 1000)
    }
  }
});

chrome.runtime.onMessage.addListener((msg,  sender) => {
  if (msg.target  === "content-script") {
    chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
      chrome.tabs.sendMessage(tabs[0].id, msg);
    });
  }
});
