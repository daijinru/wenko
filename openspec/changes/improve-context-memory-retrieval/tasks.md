# Tasks: Context and Memory Retrieval Improvements

## 1. HITL 表单数据持久化

- [x] 1.1 修改 `hitl_handler._process_form_data()` 将表单数据写入 `working_memory.context_variables`
- [x] 1.2 修改 `hitl_handler._save_to_memory()` 同步更新工作记忆
- [x] 1.3 修改 `chat_processor.build_hitl_continuation_prompt()` 注入完整工作记忆上下文
- [x] 1.4 添加工作记忆 `context_variables` 大小限制（防止膨胀）
- [x] 1.5 验证：通过 HITL 收集行程后，后续对话能正确引用

## 2. 人称代词归一化

- [x] 2.1 在 `memory_manager.py` 新增 `normalize_pronouns()` 函数
- [x] 2.2 定义人称代词映射表 `PRONOUN_NORMALIZE_MAP`
- [x] 2.3 修改 `extract_keywords()` 调用归一化
- [x] 2.4 修改 `_calculate_keyword_score()` 对 memory.key 进行归一化匹配
- [x] 2.5 验证：存储 "你喜欢的颜色"，输入 "我喜欢的颜色" 能命中

## 3. 子串匹配兜底策略

- [x] 3.1 新增 `_recall_candidates_substring()` 函数
- [x] 3.2 修改 `retrieve_relevant_memories()` 在 FTS5 结果不足时触发子串匹配
- [x] 3.3 实现候选去重合并逻辑
- [x] 3.4 验证：输入 "颜色" 能匹配到 "你喜欢的颜色"

## 4. 评分算法优化

- [x] 4.1 修改 `_calculate_keyword_score()` 支持部分匹配评分
- [x] 4.2 调整评分权重，新增 `partial_match` 权重配置
- [x] 4.3 添加评分调试日志（可选开关）
- [x] 4.4 验证：部分匹配的记忆排序正确

## 5. 测试与验证

- [x] 5.1 编写单元测试：`test_normalize_pronouns()`
- [x] 5.2 编写单元测试：`test_substring_matching()`
- [x] 5.3 编写集成测试：HITL → 后续对话上下文保持
- [x] 5.4 编写集成测试：多种表述方式的记忆检索
- [x] 5.5 手动测试：完整用户流程验证

## Dependencies

- Task 2 和 Task 3 可并行开发
- Task 4 依赖 Task 2、Task 3 完成
- Task 1 独立于其他任务，可最先开始
- Task 5 在所有功能完成后执行
