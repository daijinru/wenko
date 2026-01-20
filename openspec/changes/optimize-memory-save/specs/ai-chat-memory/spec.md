## ADDED Requirements

### Requirement: Smart Memory Extraction API

系统 SHALL 提供智能记忆提取 API，用于从消息内容中自动提取结构化的记忆信息。

API 端点 SHALL 为 `POST /memory/extract`，接受以下参数：
- `content`: 消息文本内容（必填）
- `role`: 消息角色，`user` 或 `assistant`（可选，用于优化提取策略）

API 返回 SHALL 包含：
- `key`: 提取的记忆键名（消息摘要）
- `value`: 记忆值（原文或结构化信息）
- `category`: 推断的记忆类别（`preference` | `fact` | `pattern`）
- `confidence`: 置信度（0.0 - 1.0）

#### Scenario: Extract memory from user preference message

- **GIVEN** 用户消息内容为 "我喜欢用 Python 写代码，因为它简洁易读"
- **WHEN** 客户端调用 `POST /memory/extract` 并传入该内容
- **THEN** API SHALL 返回提取结果
- **AND** `key` 应类似于 "编程语言偏好"
- **AND** `category` 应为 `preference`
- **AND** `confidence` 应 >= 0.8

#### Scenario: Extract memory from fact message

- **GIVEN** 用户消息内容为 "我是一名软件工程师，在北京工作"
- **WHEN** 客户端调用 `POST /memory/extract`
- **THEN** API SHALL 返回提取结果
- **AND** `key` 应类似于 "用户职业" 或 "工作地点"
- **AND** `category` 应为 `fact`

#### Scenario: Extract from AI response

- **GIVEN** AI 回复内容为 "根据您的偏好，我为您推荐使用 VS Code 作为 Python 开发环境"
- **AND** `role` 参数为 `assistant`
- **WHEN** 客户端调用 `POST /memory/extract`
- **THEN** API SHALL 提取 AI 给出的建议作为记忆
- **AND** `key` 应类似于 "开发工具推荐"

#### Scenario: Handle empty or meaningless content

- **GIVEN** 消息内容为 "好的" 或 "嗯"
- **WHEN** 客户端调用 `POST /memory/extract`
- **THEN** API SHALL 返回空结果或低置信度结果
- **AND** `confidence` 应 < 0.5

### Requirement: Automatic Memory Extraction in Save Dialog

前端"保存到长期记忆"对话框 SHALL 在打开时自动调用智能提取 API。

#### Scenario: Auto-extract on dialog open

- **GIVEN** 用户在聊天历史中点击"保存到长期记忆"按钮
- **WHEN** 保存对话框打开
- **THEN** 系统 SHALL 自动调用 `/memory/extract` API
- **AND** 显示加载状态
- **AND** 完成后预填充表单字段

#### Scenario: Pre-fill form with extracted data

- **GIVEN** 智能提取 API 返回成功
- **WHEN** 提取完成
- **THEN** 对话框 SHALL 使用提取的 `key` 填充键名字段
- **AND** 使用提取的 `value` 填充值字段
- **AND** 使用提取的 `category` 设置类别选择
- **AND** 使用提取的 `confidence` 设置置信度滑块

#### Scenario: Fallback on extraction failure

- **GIVEN** 智能提取 API 调用失败或返回低置信度
- **WHEN** 对话框需要显示表单
- **THEN** 系统 SHALL 使用默认值填充表单
- **AND** 键名默认为"用户输入"（用户消息）或"AI回复"（助手消息）
- **AND** 值默认为消息原文
- **AND** 可选择显示提示说明提取失败

## MODIFIED Requirements

### Requirement: Long-term Memory Storage

系统 SHALL 支持跨会话的长期记忆存储，用于保存用户偏好、重要事实和交互模式。

长期记忆条目 SHALL 包含以下字段：
- `id`: 记忆条目唯一标识符
- `session_id`: 来源会话 ID
- `category`: 记忆类别（`preference` | `fact` | `pattern`）
- `key`: 记忆键名
- `value`: 记忆内容（支持 JSON 结构）
- `confidence`: 置信度（0.0 - 1.0）
- `source`: 来源（`user_stated` | `inferred` | `system`）
- `created_at`: 创建时间
- `last_accessed`: 最后访问时间
- `access_count`: 访问次数

#### Scenario: Create long-term memory from user statement

- **GIVEN** 用户在对话中明确表达偏好或事实
- **WHEN** LLM 识别到可存储的信息并输出 `memory_update.should_store=true`
- **THEN** 系统 SHALL 创建长期记忆条目
- **AND** 设置 `source` 为 `user_stated`
- **AND** 设置 `confidence` 为 0.9 或更高

#### Scenario: Auto-save all identified facts and preferences

- **GIVEN** 用户在对话中表达了事实、结论或偏好
- **WHEN** LLM 分析消息后识别到可存储的信息
- **THEN** 系统 SHALL 自动保存所有识别的信息到长期记忆
- **AND** 为每个识别的信息创建独立的记忆条目
- **AND** 设置适当的 `category` 和 `confidence`

#### Scenario: Retrieve relevant long-term memories

- **GIVEN** 存在多条长期记忆
- **WHEN** 用户发送新消息
- **THEN** 系统 SHALL 检索与消息相关的长期记忆
- **AND** 按相关性评分排序
- **AND** 返回最多 N 条相关记忆（N 由配置参数 `MEMORY_RETRIEVAL_LIMIT` 控制，默认 5）

#### Scenario: Memory access tracking

- **GIVEN** 长期记忆被检索并使用
- **WHEN** 记忆内容被包含在 LLM 上下文中
- **THEN** 系统 SHALL 更新 `last_accessed` 为当前时间
- **AND** 递增 `access_count`
