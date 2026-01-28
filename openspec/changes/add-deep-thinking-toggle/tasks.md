# Tasks: 添加深度思考模式开关

## 1. 后端实现

### 1.1 数据库设置
- [x] 1.1.1 在 `chat_db.py` 的 `_DEFAULT_SETTINGS` 中添加 `llm.deep_thinking_enabled` 设置项（默认值 `false`）

### 1.2 LLM 调用逻辑
- [x] 1.2.1 在 `main.py` 中创建 `get_deep_thinking_params()` 辅助函数，根据设置返回相应的 API 参数
- [x] 1.2.2 修改 `stream_chat_response()` 函数，在构建 `request_body` 时应用深度思考参数
- [x] 1.2.3 修改 `stream_hitl_continuation()` 函数，同样应用深度思考参数
- [x] 1.2.4 添加 prompt 级别的思考控制指令（当深度思考关闭时追加到系统提示词）

### 1.3 输出后处理（可选）
- [x] 1.3.1 在 SSE 响应处理中添加 `<thinking>` 标签过滤逻辑（作为兜底策略）

## 2. 前端实现

### 2.1 类型定义
- [x] 2.1.1 在 `use-settings.ts` 的 `Settings` 接口中添加 `llm.deep_thinking_enabled` 字段

### 2.2 设置界面
- [x] 2.2.1 在 `llm-config-section.tsx` 中添加深度思考开关组件
- [x] 2.2.2 添加开关的提示信息（tooltip 或描述文本），说明 token 消耗和等待时间影响
- [x] 2.2.3 使用合适的图标或样式突出显示这是一个可能增加成本的选项

## 3. 测试验证

- [x] 3.1 验证设置项能正确保存和读取
- [x] 3.2 验证开关关闭时，API 请求使用低温度参数
- [x] 3.3 验证开关开启时，API 请求保持用户配置的温度
- [x] 3.4 验证前端开关状态与后端设置同步
- [x] 3.5 验证提示信息正确显示

## 4. 文档更新

- [x] 4.1 更新 `openspec/project.md` 中的设置项列表（如需要）
