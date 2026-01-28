## MODIFIED Requirements

### Requirement: HITL Continuation

当用户响应 HITL 表单后（无论 approve 或 reject），系统 SHALL **自动**将响应传递给 AI，使 AI 能够继续对话。**AI 的响应质量应与用户输入的复杂度成正比**。

#### Scenario: User submits complex form and receives detailed response

- **GIVEN** 用户填写了一个复杂的 HITL 表单（字段数 >= 5 或内容总长度 >= 200 字符）
- **WHEN** 用户点击"确认"提交表单
- **THEN** AI 的响应**必须**包含以下内容：
  - 对用户需求的分析和理解确认
  - 至少 3-5 条具体、可操作的建议或方案
  - 根据用户约束条件（如预算、时间）的调整建议
  - 用户可能没想到但有价值的补充信息
- **AND** 响应长度应与用户输入的详细程度相匹配

#### Scenario: User submits medium complexity form

- **GIVEN** 用户填写了一个中等复杂度的 HITL 表单（字段数 >= 3 或内容总长度 >= 100 字符）
- **WHEN** 用户点击"确认"提交表单
- **THEN** AI 的响应**应该**包含：
  - 对用户选择的确认
  - 2-3 条具体建议
  - 如需要，可追问更多细节
- **AND** 响应应有实质性内容，避免空洞的确认

#### Scenario: User submits simple form

- **GIVEN** 用户填写了一个简单的 HITL 表单（字段数 < 3 且内容总长度 < 100 字符）
- **WHEN** 用户点击"确认"提交表单
- **THEN** AI 简洁地回应用户的选择
- **AND** 可询问是否需要进一步帮助

#### Scenario: User approves HITL form and AI continues automatically

- **WHEN** 用户点击"确认"提交 HITL 表单
- **THEN** 系统**自动**触发 AI 继续对话（无需用户额外操作）
- **AND** AI 的响应显示在聊天界面中
- **AND** 对话可以继续进行

#### Scenario: User rejects HITL form and AI continues automatically

- **WHEN** 用户点击"跳过"拒绝 HITL 表单
- **THEN** 系统**自动**触发 AI 继续对话（与 approve 行为一致）
- **AND** AI 收到用户拒绝的信息
- **AND** AI 根据用户的拒绝行为做出适当响应（如换一种方式提问、跳过该话题等）

## ADDED Requirements

### Requirement: Form Complexity Assessment

系统 SHALL 评估 HITL 表单提交的复杂度，以指导 AI 响应的详细程度。

#### Scenario: High complexity form detection

- **GIVEN** 用户提交的表单数据
- **WHEN** 字段数量 >= 5 **或** 所有字段内容总长度 >= 200 字符
- **THEN** 系统将表单标记为"高复杂度"
- **AND** 为 LLM 提供详尽响应指引

#### Scenario: Medium complexity form detection

- **GIVEN** 用户提交的表单数据
- **WHEN** 字段数量 >= 3 **或** 所有字段内容总长度 >= 100 字符
- **AND** 不满足高复杂度条件
- **THEN** 系统将表单标记为"中复杂度"
- **AND** 为 LLM 提供适中的响应指引

#### Scenario: Low complexity form detection

- **GIVEN** 用户提交的表单数据
- **WHEN** 字段数量 < 3 **且** 所有字段内容总长度 < 100 字符
- **THEN** 系统将表单标记为"低复杂度"
- **AND** 为 LLM 提供简洁响应指引

### Requirement: Response Quality Guidance

系统 SHALL 在 HITL continuation 提示词中包含响应质量指引，确保 AI 响应与用户输入的努力程度相匹配。

#### Scenario: High complexity response guidance

- **GIVEN** 表单被评估为高复杂度
- **WHEN** 构建 HITL continuation 上下文
- **THEN** 上下文中包含以下指引：
  - 分析用户的需求和偏好
  - 提供具体、可操作的建议（至少3-5条）
  - 给出分步骤的计划或方案
  - 根据用户的约束条件调整建议
  - 主动补充有价值的信息

#### Scenario: Reject action maintains simple response

- **GIVEN** 用户选择了"跳过"（reject）
- **WHEN** 构建 HITL continuation 上下文
- **THEN** 无论原表单复杂度如何，使用简洁响应指引
- **AND** 不要求 AI 提供详细建议

### Requirement: HITL Continuation Loading Indicator

系统 SHALL 在 HITL 表单提交后显示加载提示，以设定用户对详细响应的预期。

#### Scenario: Show loading indicator after form submission

- **WHEN** 用户提交 HITL 表单（approve 或 reject）
- **THEN** 系统显示"AI 正在分析您的信息..."加载提示
- **AND** 加载提示使用与现有加载状态一致的 UI 风格

#### Scenario: Hide loading indicator when response starts

- **GIVEN** 加载提示正在显示
- **WHEN** AI 响应开始流式输出
- **THEN** 加载提示消失
- **AND** AI 响应内容正常显示在聊天界面
