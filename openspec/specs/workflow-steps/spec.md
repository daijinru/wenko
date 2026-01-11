# Workflow Steps

工作流步骤类型规范，定义所有可用的步骤及其行为。

## Requirements

### Requirement: EchoInput Step

系统 SHALL 提供 `EchoInput` 步骤，用于回显输入内容。

#### Scenario: Echo input value
- **GIVEN** 步骤配置 `{ "step": "EchoInput", "id": "echo1" }`
- **WHEN** 输入值为 `"Hello"`
- **THEN** 输出值为 `"Hello"`

### Requirement: SetVar Step

系统 SHALL 提供 `SetVar` 步骤，用于设置上下文变量。

#### Scenario: Set variable with value
- **GIVEN** 步骤配置 `{ "step": "SetVar", "id": "set1", "input": { "var_name": "foo", "value": "bar" } }`
- **WHEN** 步骤执行
- **THEN** 上下文变量 `foo` 被设置为 `"bar"`

### Requirement: GetVar Step

系统 SHALL 提供 `GetVar` 步骤，用于获取上下文变量值。

#### Scenario: Get existing variable
- **GIVEN** 上下文变量 `foo` 值为 `"bar"`
- **WHEN** 执行 `{ "step": "GetVar", "id": "get1", "input": { "var_name": "foo" } }`
- **THEN** 输出值为 `"bar"`

#### Scenario: Get non-existing variable
- **GIVEN** 上下文变量 `missing` 不存在
- **WHEN** 执行获取 `missing` 变量
- **THEN** 输出为空字符串或默认值

### Requirement: FetchURL Step

系统 SHALL 提供 `FetchURL` 步骤，用于发起 HTTP 请求。

#### Scenario: Fetch URL with GET method
- **GIVEN** 步骤配置包含有效的 URL
- **WHEN** 步骤执行
- **THEN** 返回 HTTP 响应内容

#### Scenario: Fetch URL with custom method
- **GIVEN** 步骤配置包含 `method` 和 `body` 字段
- **WHEN** 步骤执行
- **THEN** 使用指定的 HTTP 方法和请求体

### Requirement: ParseJSON Step

系统 SHALL 提供 `ParseJSON` 步骤，用于解析 JSON 字符串。

#### Scenario: Parse valid JSON
- **GIVEN** 输入为有效 JSON 字符串 `'{"key": "value"}'`
- **WHEN** 步骤执行
- **THEN** 输出为解析后的对象

#### Scenario: Parse invalid JSON
- **GIVEN** 输入为无效 JSON 字符串
- **WHEN** 步骤执行
- **THEN** 返回错误信息

### Requirement: JSONLookup Step

系统 SHALL 提供 `JSONLookup` 步骤，用于通过路径查询 JSON 对象。

#### Scenario: Lookup nested value
- **GIVEN** JSON 对象 `{"user": {"name": "Alice"}}` 和路径 `user.name`
- **WHEN** 步骤执行
- **THEN** 输出为 `"Alice"`

#### Scenario: Lookup with array index
- **GIVEN** JSON 对象 `{"items": [1, 2, 3]}` 和路径 `items[0]`
- **WHEN** 步骤执行
- **THEN** 输出为 `1`

### Requirement: JSONExtractValues Step

系统 SHALL 提供 `JSONExtractValues` 步骤，用于提取 JSON 对象的多个值。

#### Scenario: Extract multiple values
- **GIVEN** JSON 对象和键列表 `["name", "age"]`
- **WHEN** 步骤执行
- **THEN** 返回包含指定键值的新对象

### Requirement: TemplateReplace Step

系统 SHALL 提供 `TemplateReplace` 步骤，用于模板字符串替换。

#### Scenario: Replace template variables
- **GIVEN** 模板 `"Hello, {{name}}!"` 和变量 `{"name": "World"}`
- **WHEN** 步骤执行
- **THEN** 输出为 `"Hello, World!"`

### Requirement: MultilineToSingleLine Step

系统 SHALL 提供 `MultilineToSingleLine` 步骤，用于将多行文本转换为单行。

#### Scenario: Convert multiline text
- **GIVEN** 输入为 `"line1\nline2\nline3"`
- **WHEN** 步骤执行
- **THEN** 输出为 `"line1 line2 line3"` (或使用指定分隔符)

### Requirement: OutputResult Step

系统 SHALL 提供 `OutputResult` 步骤，用于标记最终输出结果。

#### Scenario: Mark output result
- **GIVEN** 输入值为 `"final result"`
- **WHEN** 步骤执行
- **THEN** 该值被标记为工作流最终输出

### Requirement: CopyVar Step

系统 SHALL 提供 `CopyVar` 步骤，用于复制变量到新名称。

#### Scenario: Copy variable
- **GIVEN** 变量 `source` 值为 `"data"` 和目标名 `target`
- **WHEN** 步骤执行
- **THEN** 变量 `target` 值为 `"data"`
