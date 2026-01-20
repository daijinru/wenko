# Spec: HITL UI in Electron New Window

## Overview

本规范定义了 HITL (Human-in-the-Loop) 表单界面在独立 Electron 窗口中的实现要求，以及 Electron IPC 通讯机制。

## MODIFIED Requirements

### Requirement: HITL 表单渲染位置

HITL 表单 SHALL 在独立的 Electron 窗口中渲染，而非在 Live2D Widget 的 ShadowRoot 中通过原生 DOM 渲染。Live2D 与 HITL 窗口之间 SHALL 通过 Electron IPC 进行通讯。

#### Scenario: AI 发起 HITL 请求时打开新窗口

**Given** AI 返回的响应包含 `hitl_request` 数据
**When** Live2D 通过 `electronAPI.invoke('hitl:open-window', ...)` 请求打开窗口
**Then** Main Process 创建新的 BrowserWindow
**And** 窗口加载 HITL React 应用
**And** 窗口显示表单，标题为 `hitl_request.title`
**And** 表单包含 `hitl_request.fields` 定义的所有字段

#### Scenario: 用户提交 HITL 表单

**Given** HITL 窗口已显示表单
**When** 用户填写表单并点击"确认"按钮
**Then** HITL 窗口调用 `electronAPI.invoke('hitl:submit', ...)` 提交数据
**And** Main Process 调用后端 `POST /hitl/respond` API
**And** Main Process 通过 IPC 发送结果给 Live2D 窗口
**And** HITL 窗口关闭

#### Scenario: 用户跳过 HITL 表单

**Given** HITL 窗口已显示表单
**When** 用户点击"跳过"按钮
**Then** HITL 窗口调用 `electronAPI.invoke('hitl:submit', { action: 'reject' })`
**And** Main Process 调用后端 API
**And** Main Process 通过 IPC 发送结果给 Live2D 窗口
**And** HITL 窗口关闭

#### Scenario: 用户关闭 HITL 窗口

**Given** HITL 窗口已显示表单
**When** 用户点击窗口关闭按钮
**Then** 系统 SHALL 视为取消操作
**And** Main Process 通过 IPC 发送取消结果给 Live2D 窗口

---

## ADDED Requirements

### Requirement: Electron IPC 通讯机制

系统 MUST 提供基于 Electron IPC 的跨窗口通讯机制，用于 Live2D 窗口与 HITL 窗口之间的数据传递。

#### Scenario: Live2D 请求打开 HITL 窗口

**Given** Live2D 接收到 SSE hitl 事件
**When** Live2D 调用 `electronAPI.invoke('hitl:open-window', { request, sessionId })`
**Then** Main Process 接收请求并创建 HITL 窗口
**And** Main Process 返回 Promise 表示窗口已创建

#### Scenario: HITL 窗口接收表单数据

**Given** HITL 窗口已创建
**When** 窗口完成加载
**Then** Main Process SHALL 通过 IPC 发送 `hitl:request-data` 消息
**And** HITL 窗口接收并渲染表单数据

#### Scenario: Live2D 接收 HITL 结果

**Given** 用户在 HITL 窗口完成操作
**When** Main Process 处理完响应
**Then** Main Process SHALL 通过 IPC 发送 `hitl:result` 消息给 Live2D 窗口
**And** 消息 MUST 包含:
  - `success`: 操作是否成功
  - `action`: 用户操作类型 ('approve' | 'reject' | 'cancel')
  - `continuationData`: 可选的继续对话数据

---

### Requirement: HITL 窗口生命周期管理

Main Process MUST 管理 HITL 窗口的完整生命周期，确保窗口正确创建、显示和销毁。

#### Scenario: HITL 窗口单例管理

**Given** 已存在一个打开的 HITL 窗口
**When** 收到新的 `hitl:open-window` 请求
**Then** 系统 SHALL 聚焦到现有窗口
**And** 系统 SHALL 不创建新窗口

#### Scenario: HITL 窗口配置

**Given** 创建新的 HITL 窗口
**Then** 窗口 SHALL 设为 Live2D 主窗口的子窗口
**And** 窗口 SHALL 居中显示
**And** 窗口 SHALL 使用隐藏的原生标题栏
**And** 窗口 SHALL 可调整大小但不可最大化

#### Scenario: HITL 窗口超时处理

**Given** HITL 窗口已打开
**And** HITL 请求定义了 `ttl_seconds`
**When** 超过 TTL 时间用户未操作
**Then** 系统 SHALL 自动关闭窗口
**And** 系统 SHALL 视为取消操作

---

### Requirement: HITL 表单样式一致性

HITL 窗口界面 MUST 与 Workflow 其他界面保持 Classic Mac OS 9 风格一致。

#### Scenario: 窗口使用 Classic 样式

**Given** HITL 窗口显示
**Then** 窗口内容区 SHALL 应用 `window` CSS 类
**And** 标题栏 SHALL 应用 `title-bar` CSS 类
**And** 标题文本 SHALL 应用 `title-bar-text` CSS 类

#### Scenario: 按钮使用 Classic 样式

**Given** HITL 窗口显示
**Then** "确认"按钮 SHALL 使用 `primary` class 样式
**And** "跳过"按钮 SHALL 使用默认按钮样式
**And** 按钮 SHALL 具有 Classic Mac OS 的凸起边框效果

#### Scenario: 表单控件使用 Workflow 组件

**Given** HITL 表单包含各类字段
**Then** 文本输入 SHALL 复用 Workflow 的 `Input` 组件
**And** 多行文本 SHALL 复用 Workflow 的 `Textarea` 组件
**And** 复选框 SHALL 复用 Workflow 的 `Checkbox` 组件
**And** 滑块 SHALL 复用 Workflow 的 `Slider` 组件

---

### Requirement: HITL 字段类型支持

HITL 表单 MUST 支持所有已定义的字段类型，包括：text, textarea, select, multiselect, radio, checkbox, number, slider, date, boolean。

#### Scenario: 渲染 text 类型字段

**Given** 字段定义 `{ type: 'text', name: 'username', label: '用户名' }`
**Then** 系统 SHALL 渲染单行文本输入框
**And** 输入框 placeholder 为字段的 `placeholder` 值

#### Scenario: 渲染 textarea 类型字段

**Given** 字段定义 `{ type: 'textarea', name: 'notes', label: '备注' }`
**Then** 系统 SHALL 渲染多行文本输入框
**And** 输入框高度可调整

#### Scenario: 渲染 select 类型字段

**Given** 字段定义包含 `type: 'select'` 和 `options` 数组
**Then** 系统 SHALL 渲染下拉选择框
**And** 下拉选项为 `options` 中定义的选项

#### Scenario: 渲染 radio 类型字段

**Given** 字段定义包含 `type: 'radio'` 和 `options` 数组
**Then** 系统 SHALL 渲染单选按钮组
**And** 每个选项对应一个单选按钮

#### Scenario: 渲染 checkbox 类型字段

**Given** 字段定义包含 `type: 'checkbox'` 和 `options` 数组
**Then** 系统 SHALL 渲染复选框组
**And** 每个选项对应一个复选框
**And** 表单数据为选中值的数组

#### Scenario: 渲染 slider 类型字段

**Given** 字段定义 `{ type: 'slider', min: 0, max: 100, step: 1 }`
**Then** 系统 SHALL 渲染滑块控件
**And** 滑块范围为 min 到 max
**And** 显示当前选中值

#### Scenario: 渲染 boolean 类型字段

**Given** 字段定义 `{ type: 'boolean', name: 'agree', label: '同意条款' }`
**Then** 系统 SHALL 渲染单个复选框
**And** 表单数据为 true 或 false

#### Scenario: 必填字段标记

**Given** 字段定义 `required: true`
**Then** 字段标签后 MUST 显示红色 `*` 标记

---

### Requirement: HITL 错误处理

HITL 窗口 MUST 处理验证错误和提交错误，并向用户显示友好的错误信息。

#### Scenario: 必填字段验证失败

**Given** 用户未填写必填字段
**When** 用户点击"确认"按钮
**Then** 后端返回验证错误
**And** 窗口 SHALL 显示错误消息
**And** 窗口 SHALL 保持打开状态

#### Scenario: 提交失败错误处理

**Given** HITL 响应提交失败（网络错误等）
**Then** 窗口 SHALL 显示错误消息
**And** 用户可以重新提交

---

### Requirement: HITL 继续对话集成

HITL 响应后的 AI 继续对话 MUST 正确触发和显示。

#### Scenario: 触发继续对话

**Given** HITL 响应成功且包含 `continuation_data`
**When** Live2D 窗口接收到 `hitl:result` 消息
**Then** Live2D SHALL 调用 `POST /hitl/continue` 获取 AI 继续响应
**And** Live2D SHALL 在对话气泡中显示流式文本

#### Scenario: 链式 HITL 请求

**Given** 继续对话返回新的 HITL 请求
**Then** Live2D SHALL 再次调用 `electronAPI.invoke('hitl:open-window', ...)`
**And** 系统 SHALL 打开新的 HITL 窗口处理请求

---

### Requirement: preload.cjs API 扩展

preload 脚本 MUST 扩展 `electronAPI` 以支持 IPC 监听功能。

#### Scenario: 监听 IPC 消息

**Given** 渲染进程需要监听主进程消息
**When** 调用 `electronAPI.on(channel, callback)`
**Then** 系统 SHALL 注册 IPC 监听器
**And** 返回 unsubscribe 函数用于移除监听

#### Scenario: 一次性监听

**Given** 渲染进程需要一次性监听主进程消息
**When** 调用 `electronAPI.once(channel, callback)`
**Then** 系统 SHALL 注册一次性监听器
**And** 消息接收后自动移除监听
