# Spec: Context Variable Display

## Overview

为工作记忆提供增强的上下文变量展示功能，包括操作列按钮、对话框 Table 列表预览和复用 HITL 窗口进行只读回显。

## ADDED Requirements

### Requirement: Context Variable Button in Actions Column

系统 MUST 在工作记忆项存在上下文变量时，在操作列显示"上下文"按钮。

#### Scenario: Display context button when variables exist

- **Given**: 一个工作记忆项的 `context_variables` 包含至少一个属性
- **When**: 用户查看工作记忆列表
- **Then**: 该行的操作列显示"上下文"按钮，位于"清除"按钮右侧

#### Scenario: Hide context button when no variables

- **Given**: 一个工作记忆项的 `context_variables` 为空对象或 null
- **When**: 用户查看工作记忆列表
- **Then**: 该行的操作列不显示"上下文"按钮

---

### Requirement: Context Variable Dialog with Table

系统 SHALL 在用户点击"上下文"按钮后弹出对话框，以 Table 形式展示所有上下文变量列表。

#### Scenario: Open dialog on button click

- **Given**: 用户在工作记忆列表中看到"上下文"按钮
- **When**: 用户点击"上下文"按钮
- **Then**: 弹出对话框，以 Table 形式显示该工作记忆的所有上下文变量

#### Scenario: Display variables as table

- **Given**: 工作记忆项有上下文变量
- **When**: 对话框打开
- **Then**: 以表格形式展示变量列表，包含键名、类型、预览、操作列

#### Scenario: Table action column with replay button

- **Given**: 对话框显示上下文变量 Table
- **When**: 用户查看 Table
- **Then**: 每行的操作列包含"replay"按钮

#### Scenario: Close dialog

- **Given**: 上下文变量对话框已打开
- **When**: 用户点击"关闭"按钮或对话框外部区域
- **Then**: 对话框关闭

---

### Requirement: Replay Context Variable in HITL Window

系统 SHALL 在用户点击"replay"按钮后，复用 HITL 窗口以只读模式展示该上下文变量的详细内容。

#### Scenario: Open HITL window in readonly mode

- **Given**: 用户在对话框 Table 中看到某行的"replay"按钮
- **When**: 用户点击"replay"按钮
- **Then**: 打开 HITL 窗口，以只读模式展示该上下文变量的内容

#### Scenario: Readonly fields display

- **Given**: HITL 窗口以只读模式打开
- **When**: 窗口渲染完成
- **Then**: 所有字段显示为只读状态，无法编辑

#### Scenario: Only close button in readonly mode

- **Given**: HITL 窗口以只读模式打开
- **When**: 用户查看操作区域
- **Then**: 仅显示"关闭"按钮，不显示"approve"或"reject"按钮

#### Scenario: Close readonly HITL window

- **Given**: HITL 窗口以只读模式打开
- **When**: 用户点击"关闭"按钮
- **Then**: HITL 窗口关闭

---

## REMOVED Requirements

### Requirement: Inline Context Variable Details

移除展开行中的 `<details>` 上下文变量折叠展示。

#### Scenario: No inline details in expanded row

- **Given**: 用户展开一个工作记忆项的详情行
- **When**: 详情行显示
- **Then**: 不再显示"上下文变量" `<details>` 折叠元素

## Related Capabilities

- `working-memory`: 工作记忆管理功能
- `hitl-window`: HITL 表单窗口（复用进行只读回显）
