## 1. 数据库层实现

- [x] 1.1 在 `chat_db.py` 中添加 `app_settings` 表 schema (DB Version 5)
- [x] 1.2 实现 `get_setting(key)` 函数
- [x] 1.3 实现 `set_setting(key, value, value_type)` 函数
- [x] 1.4 实现 `get_all_settings()` 函数
- [x] 1.5 实现 `set_settings(settings_dict)` 批量更新函数
- [x] 1.6 实现 `reset_settings()` 重置为默认值函数
- [x] 1.7 实现从 `chat_config.json` 迁移数据的逻辑（首次启动时）

## 2. API 层实现

- [x] 2.1 在 `main.py` 中定义 Settings 相关的 Pydantic 模型
- [x] 2.2 实现 `GET /api/settings` 端点
- [x] 2.3 实现 `GET /api/settings/{key}` 端点
- [x] 2.4 实现 `PUT /api/settings/{key}` 端点
- [x] 2.5 实现 `PUT /api/settings` 批量更新端点
- [x] 2.6 实现 `POST /api/settings/reset` 重置端点
- [x] 2.7 修改 `load_chat_config()` 使用数据库读取配置

## 3. 配置加载逻辑迁移

- [x] 3.1 修改 `workflow/memory_extractor.py` 中的配置加载逻辑
- [x] 3.2 修改 `workflow/image_analyzer.py` 中的配置加载逻辑
- [x] 3.3 验证所有配置加载点都已迁移到数据库

## 4. 前端设置选项卡

- [x] 4.1 创建 `settings-tab.tsx` 设置选项卡主组件
- [x] 4.2 创建 `llm-config-section.tsx` LLM 配置区域组件
- [x] 4.3 创建 `api-key-input.tsx` API Key 输入组件（带显示/隐藏切换）
- [x] 4.4 在 `App.tsx` 中添加"设置"选项卡
- [x] 4.5 添加 API hooks (`use-settings.ts`)

## 5. 清理和文档

- [x] 5.1 删除 `chat_config.json` 和 `chat_config.example.json`
- [x] 5.2 更新 `workflow/README.md` 文档
- [x] 5.3 更新 `openspec/project.md` 配置相关说明

## 6. 验证

- [x] 6.1 测试首次启动时的配置初始化
- [x] 6.2 测试设置页面的配置修改和保存
- [x] 6.3 测试配置修改后立即生效（无需重启）
- [x] 6.4 测试 API Key 输入的显示/隐藏功能
