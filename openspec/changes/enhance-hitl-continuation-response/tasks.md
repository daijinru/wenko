## 1. 核心功能实现

- [x] 1.1 在 `workflow/hitl_handler.py` 中添加 `assess_form_complexity()` 函数
  - 输入: form_data (dict), field_labels (dict)
  - 输出: ComplexityLevel (枚举: HIGH, MEDIUM, LOW)
  - 评估逻辑: 基于字段数量和内容长度

- [x] 1.2 在 `workflow/hitl_handler.py` 中添加 `get_response_guidance()` 函数
  - 输入: complexity_level (ComplexityLevel), action (str)
  - 输出: 响应质量指引文本
  - 注意: reject 操作始终返回简洁指引

- [x] 1.3 修改 `workflow/hitl_handler.py:build_continuation_context()` 函数
  - 调用 `assess_form_complexity()` 评估复杂度
  - 调用 `get_response_guidance()` 获取指引
  - 将指引整合到返回的上下文字符串中

## 2. 提示词优化

- [x] 2.1 更新 `workflow/chat_processor.py:HITL_CONTINUATION_PROMPT_TEMPLATE`
  - 强调"根据用户输入提供有价值的响应"
  - 添加"响应深度应与用户输入的详细程度相匹配"的指引
  - 保持 JSON 输出格式不变

## 3. UI 加载提示

- [x] 3.1 在 `electron/live2d/live2d-widget/src/chat.ts` 中添加加载提示
  - 在 HITL 表单提交后显示"AI 正在分析您的信息..."
  - 在 AI 响应开始流式输出时隐藏加载提示
  - 使用与现有加载状态一致的 UI 风格

## 4. 测试验证

- [ ] 4.1 手动测试高复杂度表单场景
  - 创建包含 5+ 字段的旅行规划表单
  - 验证 AI 响应包含详尽的建议和方案

- [ ] 4.2 手动测试中复杂度表单场景
  - 创建包含 3-4 字段的简单偏好表单
  - 验证 AI 响应有实质性内容但不过于冗长

- [ ] 4.3 手动测试低复杂度表单场景
  - 创建包含 1-2 字段的简单确认表单
  - 验证 AI 响应简洁但完整

- [ ] 4.4 手动测试 reject 场景
  - 对复杂表单选择"跳过"
  - 验证 AI 响应简洁，不强行提供详细建议

- [ ] 4.5 手动测试加载提示
  - 提交表单后验证加载提示显示
  - 验证 AI 响应开始后加载提示消失

## 5. 文档更新

- [ ] 5.1 更新 `openspec/specs/` 中的相关规范（归档时进行）
