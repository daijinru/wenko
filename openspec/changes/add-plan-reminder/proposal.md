# Change: Add Plan Reminder Feature

## Why

用户在对话中经常会提到时间相关的计划和安排（如"我要在下周三下午3点开会"），但当前系统无法识别并在指定时间提醒用户。需要一种新的记忆类型来存储时间敏感的计划，并在到期时通过 Live2D 主动提醒用户。

## What Changes

- **新增记忆类型**: 添加 `plan` 类别到记忆系统，专门存储带有时间属性的计划/提醒
- **时间意图识别**: LLM 识别用户消息中的时间相关意图，触发 HITL 表单收集详细信息
- **HITL 计划表单**: 新增专门的计划收集表单，包含日期、时间、事项、提醒方式等字段
- **Workflow 面板管理**: 用户可在 Workflow 面板主动添加、查看、编辑和删除计划
- **计划存储结构**: 设计新的数据结构存储计划（包含目标时间、提醒时间、重复规则等）
- **轮询检查服务**: Electron 进程轮询检查到期计划
- **Live2D 主动提醒**: 通过 Live2D 角色语音/动作提醒用户

## Impact

- Affected specs: 新增 `plan-reminder` capability
- Affected code:
  - `workflow/memory_manager.py` - 扩展 MemoryCategory 枚举
  - `workflow/chat_processor.py` - 添加计划识别指令
  - `workflow/hitl_schema.py` - 可能需要新增日期时间字段类型
  - `workflow/hitl_handler.py` - 处理计划类型的 HITL 响应
  - `workflow/main.py` - 新增计划 CRUD API 端点
  - `electron/main.cjs` - 添加轮询逻辑和提醒触发
  - `electron/live2d/live2d-widget/src/chat.ts` - 处理提醒事件
  - `electron/src/renderer/` - 新增 Plans 管理页面组件
