## 1. 创建日志配置模块

- [x] 1.1 创建 `workflow/logger.py` 模块
  - 配置 `TimedRotatingFileHandler` 按日期切割
  - 设置日志格式：`%(asctime)s - %(name)s - %(levelname)s - %(message)s`
  - 自动创建 `logs/` 目录
  - 同时输出到文件和控制台
  - 保留 7 天历史日志（可配置）

- [x] 1.2 更新 `.gitignore` 添加 `logs/` 目录（已存在）

## 2. 更新主入口配置

- [x] 2.1 修改 `workflow/main.py`
  - 移除现有的 `logging.basicConfig` 配置
  - 导入并初始化新的日志配置
  - 确保在应用启动时初始化日志系统

## 3. 替换 print 为 logger

- [x] 3.1 替换 `workflow/main.py` 中的 print 调用
- [x] 3.2 替换 `workflow/chat_processor.py` 中的 print 调用
- [x] 3.3 替换 `workflow/hitl_handler.py` 中的 print 调用
- [x] 3.4 替换 `workflow/mcp_manager.py` 中的 print 调用
- [x] 3.5 替换 `workflow/mcp_tool_executor.py` 中的 print 调用
- [x] 3.6 替换 `workflow/memory_manager.py` 中的 print 调用（无 print）
- [x] 3.7 替换 `workflow/memory_extractor.py` 中的 print 调用
- [x] 3.8 替换 `workflow/emotion_detector.py` 中的 print 调用（无 print）
- [x] 3.9 替换 `workflow/intent_recognizer.py` 中的 print 调用
- [x] 3.10 替换 `workflow/intent_rules.py` 中的 print 调用
- [x] 3.11 替换 `workflow/response_strategy.py` 中的 print 调用（无 print）

## 4. 验证

- [x] 4.1 启动服务验证日志文件创建正常
- [x] 4.2 验证日志内容格式正确
- [x] 4.3 验证控制台输出正常
- [ ] 4.4 验证日期切割功能（可通过修改系统时间或等待日期变更测试）
