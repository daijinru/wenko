# Change: 添加文件日志系统

## Why

当前 workflow 后端服务的日志输出直接打印到控制台（stdout），存在以下问题：
1. 服务重启后日志丢失，无法追溯历史问题
2. 没有按日期分割，长期运行后难以管理
3. 混合使用 `print()` 和 `logging`，输出不统一

需要统一的文件日志系统，将所有打印输出写入到项目根目录的 `logs/` 文件夹，并按日期自动切割。

## What Changes

- 新增 `workflow/logger.py` 模块，提供统一的日志配置
- 配置 `logging` 模块使用 `TimedRotatingFileHandler` 按日期切割日志文件
- 日志文件存储在项目根目录 `logs/` 文件夹
- 日志文件命名格式：`workflow.YYYY-MM-DD.log`
- 替换各模块中的 `print()` 调用为 `logger.info()` 等适当级别
- 保留控制台输出（同时输出到文件和控制台）

## Impact

- Affected specs: 新增 `logging` capability
- Affected code:
  - `workflow/main.py` - 移除 `logging.basicConfig`，引入新的 logger 配置
  - `workflow/chat_processor.py` - 替换 print 为 logger
  - `workflow/hitl_handler.py` - 替换 print 为 logger
  - `workflow/mcp_manager.py` - 替换 print 为 logger
  - `workflow/mcp_tool_executor.py` - 替换 print 为 logger
  - `workflow/memory_manager.py` - 替换 print 为 logger
  - `workflow/memory_extractor.py` - 替换 print 为 logger
  - `workflow/emotion_detector.py` - 替换 print 为 logger
  - `workflow/intent_recognizer.py` - 替换 print 为 logger
  - `workflow/intent_rules.py` - 替换 print 为 logger
  - `workflow/response_strategy.py` - 替换 print 为 logger
