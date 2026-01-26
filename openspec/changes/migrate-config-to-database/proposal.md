# Change: 将配置迁移到数据库并通过 Workflow 面板管理

## Why

当前系统配置（`chat_config.json` 和环境变量）分散在文件系统中，用户需要手动编辑 JSON 文件来修改 API 配置，这对非技术用户不友好且容易出错。将配置集中存储到数据库，并通过 Electron workflow 面板的"设置"选项卡提供图形化管理界面，可以提升用户体验和配置管理的便捷性。

## What Changes

- **新增** SQLite 数据库表 `app_settings` 存储应用配置
- **新增** Python 后端 API 端点管理配置的 CRUD 操作
- **新增** Workflow 面板"设置"选项卡，提供配置管理 UI
- **废弃** `chat_config.json` 文件依赖（完全迁移到数据库）
- **移除** 从环境变量读取配置的逻辑

## Impact

- Affected specs: `workflow-engine` (新增 settings-management 能力)
- Affected code:
  - `workflow/chat_db.py` - 新增 settings 表和操作函数
  - `workflow/main.py` - 新增 settings API 端点，修改 `load_chat_config()`
  - `workflow/memory_extractor.py` - 修改配置加载逻辑
  - `workflow/image_analyzer.py` - 修改配置加载逻辑
  - `electron/src/renderer/workflow/App.tsx` - 新增"设置"选项卡
  - 新增 `electron/src/renderer/workflow/components/features/settings/` 目录
