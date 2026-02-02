## ADDED Requirements

### Requirement: File-Based Logging

系统 SHALL 将所有日志输出写入到项目根目录的 `logs/` 文件夹中的日志文件。

#### Scenario: 日志文件创建
- **WHEN** workflow 后端服务启动
- **THEN** 系统自动创建 `logs/` 目录（如不存在）
- **AND** 创建当日日志文件 `workflow.YYYY-MM-DD.log`

#### Scenario: 日志内容写入
- **WHEN** 任何模块调用 logger 记录日志
- **THEN** 日志内容写入当前日期的日志文件
- **AND** 日志格式为 `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

### Requirement: Daily Log Rotation

系统 SHALL 按日期自动切割日志文件。

#### Scenario: 日期切割
- **WHEN** 系统日期变更
- **THEN** 新的日志写入新日期的日志文件
- **AND** 旧日志文件保留为 `workflow.YYYY-MM-DD.log` 格式

#### Scenario: 历史日志保留
- **WHEN** 日志文件超过保留期限（默认 7 天）
- **THEN** 系统自动删除过期的日志文件

### Requirement: Dual Output

系统 SHALL 同时将日志输出到文件和控制台。

#### Scenario: 控制台输出
- **WHEN** 任何日志被记录
- **THEN** 日志同时显示在控制台（stdout）
- **AND** 写入到日志文件

### Requirement: Unified Logging Interface

所有模块 SHALL 使用统一的 logging 接口，禁止直接使用 `print()` 进行日志输出。

#### Scenario: 模块日志记录
- **WHEN** 模块需要记录调试或运行信息
- **THEN** 使用 `logging.getLogger(__name__)` 获取 logger
- **AND** 使用 `logger.debug()`, `logger.info()`, `logger.warning()`, `logger.error()` 记录日志
