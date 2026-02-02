## ADDED Requirements

### Requirement: Log Viewer Tab

Electron workflow 面板 SHALL 提供日志查看功能，允许用户查看 workflow 后端生成的日志文件。

#### Scenario: View log files list
- **WHEN** 用户切换到「日志」Tab
- **THEN** 系统显示可用的日志文件列表（按日期）
- **AND** 默认选中最新日期的日志文件

#### Scenario: Load log content
- **WHEN** 用户选择某一日期的日志文件
- **THEN** 系统加载并显示该日志文件的内容
- **AND** 日志以等宽字体显示

#### Scenario: No logs available
- **WHEN** 日志目录为空或不存在日志文件
- **THEN** 系统显示「暂无日志」提示信息

### Requirement: Log Display Order Control

用户 SHALL 能够控制日志的显示顺序（正序或倒序）。

#### Scenario: Toggle display order
- **WHEN** 用户点击顺序切换按钮
- **THEN** 日志显示顺序在正序和倒序之间切换
- **AND** 默认使用倒序（最新日志在前）

### Requirement: Log Keyword Highlighting

用户 SHALL 能够输入关键字，系统高亮显示匹配的文本。

#### Scenario: Highlight matching keywords
- **WHEN** 用户在关键字输入框中输入文本
- **THEN** 日志内容中所有匹配的文本被高亮显示
- **AND** 匹配为大小写不敏感

#### Scenario: Clear keyword highlight
- **WHEN** 用户清空关键字输入框
- **THEN** 日志内容恢复正常显示，无高亮

### Requirement: Log Level Visualization

日志查看器 SHALL 对不同级别的日志使用不同的视觉样式。

#### Scenario: Display log levels with colors
- **WHEN** 日志内容被显示
- **THEN** INFO 级别日志使用默认颜色
- **AND** WARNING/WARN 级别日志使用橙色
- **AND** ERROR 级别日志使用红色
- **AND** DEBUG 级别日志使用蓝色

### Requirement: Log API Endpoints

后端 SHALL 提供 RESTful API 以支持日志查看功能。

#### Scenario: List available log files
- **WHEN** 前端请求 `GET /api/logs`
- **THEN** 后端返回可用日志文件列表
- **AND** 列表按日期降序排列
- **AND** 每个条目包含日期和文件大小

#### Scenario: Get log content with pagination
- **WHEN** 前端请求 `GET /api/logs/{date}?offset=0&limit=500&order=desc`
- **THEN** 后端返回指定日期的日志内容
- **AND** 支持分页参数 offset 和 limit
- **AND** 支持顺序参数 order（asc/desc）

#### Scenario: Request non-existent log
- **WHEN** 前端请求不存在的日期日志
- **THEN** 后端返回 404 状态码
