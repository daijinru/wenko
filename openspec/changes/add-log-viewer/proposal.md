# Change: Add Log Viewer to Electron Panel

## Why

系统已经实现了基于文件的日志记录功能（`workflow/logs/workflow.YYYY-MM-DD.log`），但用户目前无法在 Electron 面板中查看这些日志。提供日志查看器可以帮助用户调试问题、监控系统行为，而无需直接访问文件系统。

## What Changes

- 在 Electron workflow 面板中添加新的「日志」Tab
- 提供后端 API 以列出可用的日志文件和读取日志内容
- 支持按日期选择日志文件
- 支持日志顺序切换（正序/倒序）
- 支持关键字高亮显示

## Impact

- Affected specs: `electron-app`
- Affected code:
  - `workflow/main.py` - 添加日志 API 端点
  - `electron/src/renderer/workflow/App.tsx` - 添加日志 Tab
  - `electron/src/renderer/workflow/components/features/logs/` - 新建日志查看器组件
  - `electron/src/renderer/workflow/hooks/use-logs.ts` - 新建日志数据 hook
