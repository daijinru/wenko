# Workflow Memory UI Specification

## ADDED Requirements

### Requirement: Working Memory Panel

Workflow 面板 SHALL 提供独立的工作记忆展示面板，展示当前会话的工作记忆状态。

#### Scenario: 查看当前工作记忆

- **WHEN** 用户切换到"工作记忆"Tab
- **THEN** 系统显示当前会话的工作记忆信息
- **AND** 信息包含：session_id、current_topic、turn_count、last_emotion、context_variables

#### Scenario: 清除工作记忆

- **WHEN** 用户点击"清除记忆"按钮
- **THEN** 系统清除当前会话的工作记忆
- **AND** 面板显示空状态

#### Scenario: 无活跃会话

- **WHEN** 当前没有活跃的聊天会话
- **THEN** 工作记忆面板显示"暂无活跃会话"提示

### Requirement: Working Memory to Long-term Memory Transfer

工作记忆面板 SHALL 支持将当前会话信息保存到长期记忆，实现记忆的持久化。

#### Scenario: 打开转存对话框

- **WHEN** 用户点击"保存到长期记忆"按钮
- **THEN** 系统显示记忆转存对话框
- **AND** 对话框预填充当前工作记忆的相关信息（如 current_topic）

#### Scenario: 预填充表单字段

- **WHEN** 记忆转存对话框打开
- **THEN** "值"字段预填充为 current_topic 的内容
- **AND** "类别"默认选择为"事实"(fact)
- **AND** "置信度"默认为 0.8

#### Scenario: 成功保存到长期记忆

- **WHEN** 用户填写完表单并点击"保存"
- **THEN** 系统调用长期记忆创建 API
- **AND** 新记忆的 source 字段标记为 "user_stated"
- **AND** 显示保存成功提示

#### Scenario: 取消转存操作

- **WHEN** 用户在对话框中点击"取消"
- **THEN** 对话框关闭
- **AND** 不进行任何保存操作

### Requirement: Classic macOS Visual Style

Workflow 面板 SHALL 采用经典 macOS (Mac OS 9/Classic) 风格的视觉设计。

#### Scenario: 经典配色方案

- **WHEN** 用户打开 Workflow 面板
- **THEN** 界面使用经典灰色/米色配色方案
- **AND** 不使用现代渐变效果

#### Scenario: 经典边框效果

- **WHEN** 界面元素需要边框装饰
- **THEN** 使用凸起(raised)或凹陷(inset)的 3D 边框效果
- **AND** 边框颜色符合经典 macOS 设计规范

#### Scenario: 经典按钮样式

- **WHEN** 用户与按钮交互
- **THEN** 按钮呈现经典的 3D 凸起效果
- **AND** 点击时呈现凹陷效果
- **AND** 悬停时有视觉反馈

### Requirement: Memory Type Separation

Workflow 面板 SHALL 将工作记忆和长期记忆在 UI 层面分开管理。

#### Scenario: Tab 结构

- **WHEN** 用户打开 Workflow 面板
- **THEN** 显示三个 Tab：聊天历史、工作记忆、长期记忆
- **AND** 每个 Tab 对应独立的功能面板

#### Scenario: 长期记忆面板

- **WHEN** 用户切换到"长期记忆"Tab
- **THEN** 显示长期记忆的完整管理界面
- **AND** 支持筛选、搜索、CRUD 操作
- **AND** 采用经典列表/表格样式展示

## MODIFIED Requirements

### Requirement: Memory List Display

长期记忆列表 SHALL 采用经典 macOS 列表样式，保持所有现有功能。

#### Scenario: 交替行颜色

- **WHEN** 显示记忆列表
- **THEN** 奇数行和偶数行使用不同的背景色
- **AND** 符合经典 macOS 列表设计

#### Scenario: 选中状态

- **WHEN** 用户选中列表项
- **THEN** 选中项使用经典蓝色高亮
- **AND** 文字颜色变为白色

#### Scenario: 悬停状态

- **WHEN** 用户鼠标悬停在列表项上
- **THEN** 列表项显示悬停高亮效果
