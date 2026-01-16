# Change: Add HITL (Human-in-the-Loop) Middleware

## Why

当前系统中 AI 直接返回响应，缺乏用户在关键决策点进行干预的能力。HITL 中间件允许 AI 在需要时暂停执行流程，向用户请求确认、编辑或拒绝操作，通过动态生成的表单收集结构化输入。

## What Changes

- **ADDED**: HITL 中间件层，拦截需要用户确认的 AI 响应
- **ADDED**: 动态表单 Schema 系统，AI 根据上下文生成表单结构
- **ADDED**: 三种用户操作：approve（批准）、edit（编辑）、reject（拒绝）
- **ADDED**: 前端表单渲染引擎，根据 Schema 动态生成复合表单
- **ADDED**: 后端 API 端点处理 HITL 交互请求

## Impact

- Affected specs: `electron-app` (新增 HITL UI 组件)
- Affected code:
  - `workflow/main.py` - 新增 HITL API 端点
  - `workflow/hitl_handler.py` - 新增 HITL 处理模块
  - `electron/src/renderer/` - 新增 HITL 表单组件
