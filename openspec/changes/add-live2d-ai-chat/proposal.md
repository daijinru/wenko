# Change: 为 Live2D 机器人添加 AI 对话功能

## Why

当前 Live2D 虚拟形象仅用于展示，缺乏与用户的交互能力。添加 AI 对话功能可以让用户直接与 Live2D 角色进行自然语言对话，提升用户体验并增加应用的实用价值。

## What Changes

- 在 Live2D 窗口添加对话输入界面（输入框 + 发送按钮）
- 实现前端与后端 AI 服务的 SSE 流式通信
- 在 Python 后端添加 `/chat` API 接口，支持流式响应
- 集成远程 LLM API（支持 OpenAI 兼容接口）进行对话生成
- 添加 `workflow/chat_config.json` 配置文件（git 忽略，保护 API Key）
- 对话响应通过 Live2D 角色的消息气泡展示
- 支持对话历史上下文管理

## Impact

- Affected specs: `electron-app`（新增 AI 对话能力）
- Affected code:
  - `electron/live2d/live2d-widget/src/` - 前端对话 UI 和逻辑
  - `workflow/` - 后端 Chat API 和远程 LLM 集成
  - `.gitignore` - 添加配置文件忽略规则
- Dependencies: 需要配置远程 LLM API（如 OpenAI、DeepSeek 等兼容接口）
