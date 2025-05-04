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
});
