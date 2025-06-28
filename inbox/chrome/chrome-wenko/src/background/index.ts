console.log('background is running')

chrome.contextMenus.create({
  id: "highlightAndOpenPanel",
  title: "高亮选中文本并打开Wenko",  // 菜单显示名称 
  contexts: ["selection"]  // 仅在用户选中文本时显示 
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "highlightAndOpenPanel") {
    if (tab && typeof tab.id === "number") {
      chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['inject/inject.js'], // 注入React挂载脚本
      }, () => {
        if (chrome.runtime.lastError) {
          console.error('inject.js 注入失败:', chrome.runtime.lastError.message)
        } else {
          console.log('inject.js 注入成功')
          // 如果需要，可以发送消息继续通信
          // chrome.tabs.sendMessage(tab.id!, { action: 'yourAction', payload: info.selectionText })
        }
      })
    }
  }
});

// 自动注入示例（可选），监听所有http(s)网页加载完毕自动注入
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url?.startsWith('http')) {
    chrome.scripting.executeScript({
      target: { tabId },
      files: ['inject/inject.js'],
    }, () => {
      if (chrome.runtime.lastError) {
        console.error('自动注入inject.js失败:', chrome.runtime.lastError.message)
      } else {
        console.log('自动注入inject.js成功')
      }
    })
  }
});
