# Cognitive Graph Specification

## Feature: LangGraph Cognitive Architecture

将桌面 AI 的核心运行时重构为基于 LangGraph 的状态机。

## ADDED Requirements

### Requirement: Graph State Schema
定义全局唯一的认知状态（Cognitive State），系统 MUST 使用此 State 作为真理来源。

#### Scenario: 状态持久化
*   Given 系统正在运行一个长任务
*   When 任务被中断或应用重启
*   Then 必须能从 State 完整恢复上下文，包括工作记忆、执行轨迹和挂起状态

#### Scenario: 状态隔离
*   Given 多个并发会话
*   Then 每个会话拥有独立的 Graph State 实例

### Requirement: Input Normalization Node
所有外部输入（UI 事件、文件拖拽、文本消息）MUST 先通过规范化节点进行处理。

#### Scenario: 多模态输入统一
*   Given 用户上传了一张图片并附带文本 "分析这个"
*   When 输入进入规范化节点
*   Then 输出的 State.semantic_input 应包含结构化的 `{ text: "分析这个", images: ["ref://..."], intent: "analyze" }`
*   And 后续推理节点无需处理原始的 HTTP 请求或 UI 事件对象

### Requirement: Emotion as Modulator
情绪系统 SHALL 仅作为参数调制器（Modulator），不作为流程控制器。

#### Scenario: 情绪影响回复风格
*   Given 用户情绪被识别为 "沮丧"
*   When 推理节点生成 Prompt
*   Then 应注入 system prompt instruction "Adopt a supportive and empathetic tone"
*   But 不应改变核心的任务处理逻辑路径（如仍然执行搜索任务，只是语气不同）

### Requirement: Human-in-the-loop (HITL) Protocol
HITL MUST 被视为一种标准的控制流状态，而非异常。

#### Scenario: 敏感操作确认
*   Given AI 决定执行一个高风险操作（如删除文件）
*   When 进入 HITL 节点
*   Then Graph 执行挂起（Suspended）
*   And State 记录 `hitl_request` 详情
*   And 前端收到 `interrupt` 事件渲染确认卡片

#### Scenario: 人工修正恢复
*   Given Graph 处于挂起状态
*   When 用户输入 "拒绝，并执行方案 B"
*   Then Graph 恢复执行（Resumed）
*   And State 更新包含用户的反馈指令
*   And 推理节点根据反馈重新规划路径

### Requirement: MCP Capability Integration
MCP 服务 SHALL 作为图中的能力节点被调用。

#### Scenario: 工具调用失败处理
*   Given 某个 MCP 工具调用超时
*   When 执行节点捕获异常
*   Then 不应直接崩溃
*   And 应将错误写入 State 的 `observation` 字段
*   And 返回给推理节点决定是重试、报错还是寻求 HITL 帮助

### Requirement: Memory Consolidation
记忆的读取和写入 MUST 通过专用节点完成。

#### Scenario: 长期记忆检索
*   Given 新的会话开始
*   When 进入记忆加载节点
*   Then 根据上下文检索相关的长期记忆
*   And 将其注入到 State 的 `working_memory` 中供推理节点使用
