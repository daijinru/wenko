## 1. Schema 定义
- [x] 1.1 在 `workflow/hitl_schema.py` 中新增 `HITLDisplayType` 枚举（table, ascii）
- [x] 1.2 新增 `HITLTableData` 模型（headers, rows, alignment, caption）
- [x] 1.3 新增 `HITLAsciiData` 模型（content, title）
- [x] 1.4 新增 `HITLDisplayField` 模型，支持 type 判断
- [x] 1.5 新增 `HITLDisplayRequest` 模型，type 固定为 "visual_display"
- [x] 1.6 在 `electron/src/renderer/hitl/types/hitl.ts` 中添加对应 TypeScript 类型

## 2. 后端支持
- [x] 2.1 在 `workflow/hitl_handler.py` 中添加 `store_display_request` 函数
- [x] 2.2 修改 `extract_hitl_from_llm_response` 支持解析 visual_display 类型
- [x] 2.3 Visual Display 类型的响应处理（仅支持 dismiss/acknowledge）
- [x] 2.4 实现 `_persist_display_to_working_memory` 将 visual_display 数据持久化到上下文变量

## 3. 前端组件实现
- [x] 3.1 创建 `hitl-table.tsx` 组件，渲染表格数据
- [x] 3.2 创建 `hitl-ascii.tsx` 组件，渲染 ASCII 艺术
- [x] 3.3 创建 `hitl-display-field.tsx` 组件，根据 type 路由渲染
- [x] 3.4 创建 `hitl-display.tsx` 容器组件，展示标题、描述和 display fields
- [x] 3.5 修改 `App.tsx` 根据 request.type 决定渲染 HITLForm 还是 HITLDisplay

## 4. 弹窗交互调整
- [x] 4.1 Visual Display 弹窗仅显示"关闭"按钮，无需表单提交
- [x] 4.2 添加 `hitl-display-actions.tsx` 简化操作按钮组件
- [x] 4.3 调整 HITL 窗口高度计算，适配可能较长的表格/ASCII 内容

## 5. 上下文变量 Replay 支持
- [x] 5.1 修改 `context-variable-dialog.tsx` 中的 `isHITLContextValue` 识别 visual_display 类型
- [x] 5.2 新增 `isVisualDisplayContextValue` 类型守卫函数
- [x] 5.3 修改 `handleReplay` 函数，对 visual_display 类型使用 `type: 'visual_display'` 打开弹窗
- [x] 5.4 修改 `getEntryDisplayInfo` 函数，显示 visual_display 类型的预览信息

## 6. 测试验证
- [ ] 6.1 创建测试用例：AI 返回包含 table 的 visual_display 请求
- [ ] 6.2 创建测试用例：AI 返回包含 ascii 的 visual_display 请求
- [ ] 6.3 验证弹窗正确渲染 table 和 ascii 内容
- [ ] 6.4 验证关闭弹窗后对话正常继续
- [ ] 6.5 验证 visual_display 数据正确存储到上下文变量
- [ ] 6.6 验证上下文变量对话框能正确 replay visual_display 内容
