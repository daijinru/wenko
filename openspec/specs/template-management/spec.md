# Template Management

工作流模板管理能力规范。

## Requirements

### Requirement: Create Template

系统 SHALL 允许用户创建新的工作流模板。

#### Scenario: Create template with valid data
- **GIVEN** 模板数据包含 `name`, `description`, `steps`
- **WHEN** 调用 `POST /templates`
- **THEN** 模板被创建并返回包含 `id` 的响应

#### Scenario: Create template without required fields
- **GIVEN** 模板数据缺少必需字段
- **WHEN** 调用 `POST /templates`
- **THEN** 返回 422 验证错误

### Requirement: List Templates

系统 SHALL 允许用户列出所有已保存的模板。

#### Scenario: List all templates
- **GIVEN** 系统中存在多个模板
- **WHEN** 调用 `GET /templates`
- **THEN** 返回模板列表 (包含 `id`, `name`, `description`)

#### Scenario: List templates when empty
- **GIVEN** 系统中没有模板
- **WHEN** 调用 `GET /templates`
- **THEN** 返回空数组 `[]`

### Requirement: Get Template

系统 SHALL 允许用户通过 ID 获取单个模板详情。

#### Scenario: Get existing template
- **GIVEN** 存在 ID 为 `abc123` 的模板
- **WHEN** 调用 `GET /templates/abc123`
- **THEN** 返回完整的模板数据

#### Scenario: Get non-existing template
- **GIVEN** ID `notfound` 的模板不存在
- **WHEN** 调用 `GET /templates/notfound`
- **THEN** 返回 404 错误

### Requirement: Update Template

系统 SHALL 允许用户更新已存在的模板。

#### Scenario: Update template fields
- **GIVEN** 存在 ID 为 `abc123` 的模板
- **WHEN** 调用 `PUT /templates/abc123` 并提供更新数据
- **THEN** 模板被更新并返回更新后的数据

#### Scenario: Update non-existing template
- **GIVEN** ID `notfound` 的模板不存在
- **WHEN** 调用 `PUT /templates/notfound`
- **THEN** 返回 404 错误

### Requirement: Delete Template

系统 SHALL 允许用户删除模板。

#### Scenario: Delete existing template
- **GIVEN** 存在 ID 为 `abc123` 的模板
- **WHEN** 调用 `DELETE /templates/abc123`
- **THEN** 模板被删除并返回成功响应

#### Scenario: Delete non-existing template
- **GIVEN** ID `notfound` 的模板不存在
- **WHEN** 调用 `DELETE /templates/notfound`
- **THEN** 返回 404 错误

### Requirement: Search Templates

系统 SHALL 允许用户按关键词搜索模板。

#### Scenario: Search by keyword
- **GIVEN** 模板 `A` 名称包含 "fetch"，模板 `B` 不包含
- **WHEN** 调用 `GET /templates/search?q=fetch`
- **THEN** 仅返回模板 `A`

#### Scenario: Search with no results
- **GIVEN** 没有模板匹配关键词 "xyz"
- **WHEN** 调用 `GET /templates/search?q=xyz`
- **THEN** 返回空数组

### Requirement: Execute Template

系统 SHALL 允许用户直接执行已保存的模板。

#### Scenario: Execute template with input
- **GIVEN** 存在包含步骤的模板
- **WHEN** 调用 `POST /templates/{id}/run` 并提供输入
- **THEN** 执行模板定义的工作流并返回结果

#### Scenario: Execute template without required input
- **GIVEN** 模板需要初始输入
- **WHEN** 调用时未提供输入
- **THEN** 使用空输入执行或返回错误

### Requirement: Template Persistence

系统 SHALL 持久化存储模板数据。

#### Scenario: Templates survive restart
- **GIVEN** 用户创建了模板
- **WHEN** 服务重启
- **THEN** 之前创建的模板仍然可访问

#### Scenario: Storage location
- **GIVEN** 系统启动
- **WHEN** 检查模板存储
- **THEN** 模板存储在 `templates.json` 文件中
