# Tasks: 为 Live2D AI Chat 添加图片粘贴和文本识别到长期记忆功能

## 1. 后端图片分析 API

- [x] 1.1 创建 `workflow/image_analyzer.py` 模块
  - 定义 `analyze_image_text(image_base64: str) -> str` 函数
  - 调用 Vision LLM API 提取图片中的文本内容
  - 支持 OpenAI GPT-4o 和其他兼容 API

- [x] 1.2 在 `workflow/main.py` 添加 `/chat/image` API 端点
  - 接收 Base64 编码的图片数据
  - 调用 `image_analyzer` 分析图片
  - 返回提取的文本内容
  - 支持 SSE 流式响应（与现有 `/chat` 保持一致）

- [x] 1.3 添加图片分析到记忆的集成
  - 使用现有 `memory_extractor` 从提取的文本智能识别记忆
  - 生成 HITL 请求让用户确认记忆内容
  - 通过 SSE 事件返回 HITL 表单

## 2. 前端图片粘贴功能

- [x] 2.1 在 `chat.ts` 添加图片粘贴处理
  - 监听 `paste` 事件检测图片数据
  - 将图片转换为 Base64 格式
  - 使用 IPC 调用打开 Electron 新窗口

- [x] 2.2 创建图片预览 Electron 窗口
  - 创建 `electron/src/renderer/image-preview/` 渲染器
  - 显示粘贴的图片预览
  - 添加"分析"和"取消"按钮
  - 显示分析结果和保存选项

- [x] 2.3 更新 `electron/main.cjs` 添加 IPC 处理
  - `image-preview:open` - 打开图片预览窗口
  - `image-preview:analyze` - 调用后端分析图片
  - `image-preview:save-memory` - 触发 HITL 保存记忆流程
  - `image-preview:cancel` / `image-preview:close` - 关闭窗口

## 3. 图片到记忆的 HITL 流程

- [x] 3.1 设计图片分析结果的 HITL 表单
  - 显示提取的文本内容（可编辑）
  - 显示 AI 建议的记忆 key/value/category
  - 提供"保存"、"编辑"、"跳过"选项

- [x] 3.2 集成现有 HITL 系统
  - 复用 `hitl_handler` 处理用户响应
  - 保存确认的记忆到 `long_term_memory`

## 4. 测试和优化

- [ ] 4.1 测试常见图片格式支持
  - PNG、JPG、GIF、WebP
  - 截图、照片、扫描件

- [ ] 4.2 测试边界情况
  - 无文本内容的图片
  - 大尺寸图片压缩
  - 多语言文本识别

- [ ] 4.3 优化用户体验
  - 添加图片压缩减少传输时间
  - 添加分析进度提示
  - 错误处理和友好提示
