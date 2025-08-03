console.log('background is running')

chrome.contextMenus.removeAll(() => {
  chrome.contextMenus.create({
    id: "wenko_highlight",
    title: "🍉 Wenko Highlight",  // 菜单显示名称 
    contexts: ["selection"]  // 仅在用户选中文本时显示 
  });

  chrome.contextMenus.create({
    id: "wenko_saveText",
    title: "🍌 Wenko Save Text",  // 菜单显示名称
    contexts: ["selection"]  // 仅在用户选中文本时显示
  });
})

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "wenko_highlight") {
    if (tab && typeof tab.id === "number") {
      // 发送消息到内容脚本
      chrome.tabs.sendMessage(
        tab.id, { action: "wenko_highlight", selectedText: info.selectionText }
      )
    }
  }
  
  if (info.menuItemId === "wenko_saveText") {
    if (tab && typeof tab.id === "number") {
      // 发送消息到内容脚本
      chrome.tabs.sendMessage(
        tab.id, { action: "wenko_saveText", selectedText: info.selectionText }
      )
    }
  }
})

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
