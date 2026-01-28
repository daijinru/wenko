# Change: 添加深度思考模式开关

## Why

大模型的"深度思考"（Extended Thinking / Reasoning）模式可以显著提升复杂问题的回答质量，但会带来额外的 token 消耗和更长的响应时间。用户应该能够根据实际需求自由选择是否启用此功能，以便在响应质量与成本/速度之间取得平衡。

## What Changes

- 在系统设置中添加"深度思考模式"开关（默认关闭）
- 在 LLM API 调用时根据设置决定是否启用 Extended Thinking 参数
- 在前端设置界面展示友好的提示信息，告知用户深度思考模式的影响
- 当深度思考模式关闭时，通过多种策略减弱/关闭模型的思考行为：
  - 设置 `thinking` 相关参数为关闭状态
  - 调整 `temperature` 参数以减少推理深度
  - 添加 prompt 级别的指令限制思考输出

## Impact

- Affected specs: `llm-settings` (新增能力)
- Affected code:
  - `workflow/chat_db.py` - 添加新的设置项
  - `workflow/main.py` - 修改 LLM API 调用逻辑
  - `electron/src/renderer/workflow/components/features/settings/llm-config-section.tsx` - 添加 UI 开关
  - `electron/src/renderer/workflow/hooks/use-settings.ts` - 添加类型定义

## User-Facing Message

当用户将鼠标悬停在深度思考开关上时，显示以下提示：

> **深度思考模式**
>
> 启用后，AI 将进行更深入的分析和推理，适合处理复杂问题。
>
> 请注意：此模式可能会：
> - 消耗更多 tokens（约 2-5 倍）
> - 响应时间更长（约 3-10 秒额外等待）
>
> 建议仅在需要深度分析时开启。
