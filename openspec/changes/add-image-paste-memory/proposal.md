# Change: 为 Live2D AI Chat 添加图片粘贴和文本识别到长期记忆功能

## Why

当前 Live2D AI Chat 仅支持文本输入。用户经常需要从图片中提取信息（如截图中的笔记、书籍摘录、名片等），手动输入既繁琐又容易出错。添加图片粘贴功能，结合 AI 视觉能力分析图片中的文本内容，并将其自动保存到长期记忆系统，可以大幅提升信息录入效率。

## What Changes

### 前端 (Electron/Live2D Widget)
- 在聊天输入框添加图片粘贴（Ctrl+V）支持
- 添加图片预览 UI，显示待发送的图片缩略图
- 添加图片上传按钮作为备选输入方式
- 粘贴图片后显示"分析图片"按钮触发 AI 分析
- 显示分析结果并提供"保存到记忆"确认 UI

### 后端 (Python/FastAPI)
- 新增 `/chat/image` API 端点，接收 Base64 图片数据
- 集成 Vision LLM API（如 GPT-4o-mini with vision）分析图片
- 调用 AI 提取图片中的文本内容
- 使用现有 `memory_extractor` 从提取的文本中智能识别记忆信息
- 将识别的记忆通过现有 `memory_manager` 保存到长期记忆

### 用户体验流程
1. 用户在聊天框粘贴图片
2. 显示图片预览和"分析图片"按钮
3. 点击后调用后端 Vision API 分析
4. AI 返回图片中的文本内容
5. 系统询问是否保存到长期记忆
6. 用户确认后，使用 HITL 流程让用户编辑/确认记忆内容
7. 保存到长期记忆系统

## Impact

- Affected specs: `electron-app`（新增图片输入能力）
- Affected code:
  - `electron/live2d/live2d-widget/src/chat.ts` - 添加图片粘贴处理逻辑
  - `electron/live2d/live2d-widget/src/widget.ts` - 图片预览 UI
  - `workflow/main.py` - 新增 `/chat/image` API
  - `workflow/image_analyzer.py` - 新增图片分析模块
- Dependencies: 需要支持 Vision 的 LLM API（如 GPT-4o、Claude 3 等）
