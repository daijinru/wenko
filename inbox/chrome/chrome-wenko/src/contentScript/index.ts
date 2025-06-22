console.info('contentScript is running')
// chrome.runtime.onMessage.addListener((request,  sender, sendResponse) => {
//   if (request.action  === "processText") {
//     const range = window.getSelection()?.getRangeAt(0)
//     if (!range) {
//       console.error("没有选中文本");
//       return;
//     }
//     const span = document.createElement("span"); 
//     span.style.backgroundColor  = "yellow";
//     range.surroundContents(span);
//   }
// });

let currentHighlightId: string = ''; // 用于存储当前高亮的ID
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action  === "highlightText") {
    // 高亮选中文本并生成唯一ID 
    const selection = window.getSelection(); 
    const range = selection?.getRangeAt(0); 
    const highlightId = `highlight-${Date.now()}`;
    // 该变量已在 background 声明
    currentHighlightId = highlightId; // 更新当前高亮ID
    if (!range) {
      console.error("没有选中文本");
      return;
    }
    const span = document.createElement("span"); 
    span.id  = highlightId;
    span.style.backgroundColor  = "rgba(255, 255, 0, 0.5)";
    range.surroundContents(span); 
    
    sendResponse({ highlightId }); // 返回ID供后台跟踪 
  }

  // 这里添加对 getPageInfo 的处理
  if (request.action  === "getPageInfo") {
    sendResponse({
      url: window.location.href,
      title: document.title,
      body: document.body.innerText ?? '',
    });
  }
});

let toastTimer: any = null
chrome.runtime.onMessage.addListener((msg)  => {
  console.info('contentScript received message:', msg)
  if (msg.type  === "TOAST") {
    if (toastTimer) {
      clearTimeout(toastTimer); // 清除之前的定时器
    }
    const existingToast = document.getElementById('wenko-toast');
    if (existingToast) {
      existingToast.remove(); // 移除已有的 toast
    }
    const toast = document.createElement('div');
    toast.id  = 'wenko-toast';
    toast.textContent  = msg.text; 
    toast.style  = 'position:fixed; top:100px; right: 20px; box-shadow: rgba(0, 0, 0, 0.35) 0px 5px 15px; background:yellow; color:#000; padding:15px; z-index:9999';
    document.body.appendChild(toast); 
    toastTimer = setTimeout(() => toast.remove(),  msg.duration || 3000); // 
  }
  if (msg.type === "LOG") {
    // 添加绿色的log
    console.info('LOG: ', msg.text);
  }
  if (msg.type === "HideSidePanel") {
    // 移除高亮
    const highlightElement = document.getElementById(currentHighlightId);
    if (highlightElement) {
      // highlightElement.style.backgroundColor = "transparent"; // 设置为透明
      // 删除原来添加的 html，恢复此前的内容
      highlightElement.replaceWith(...highlightElement.childNodes); // 替换为原始内容
    }
  }
});
