# Workflow Engine Design

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
├─────────────────────────────────────────────────────────────┤
│  POST /run          GET /health         GET /steps          │
├─────────────────────────────────────────────────────────────┤
│                     LangGraph Engine                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Step 1    │→ │   Step 2    │→ │   Step N    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                          ↓                                   │
│                  ┌───────────────┐                          │
│                  │    Context    │                          │
│                  │  (variables)  │                          │
│                  └───────────────┘                          │
├─────────────────────────────────────────────────────────────┤
│                     Step Registry                            │
│  EchoInput | SetVar | GetVar | FetchURL | ParseJSON | ...   │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### StepRegistry

步骤注册表采用装饰器模式，允许动态注册步骤处理函数：

```python
step_registry = StepRegistry()

@step_registry.register("StepName")
def step_handler(context: dict, input_value: str) -> str:
    # 处理逻辑
    return result
```

### Context (State)

执行上下文使用 Pydantic 模型定义，包含：
- `variables`: 变量存储 (dict)
- `last_output`: 上一步骤的输出
- `steps`: 待执行的步骤列表
- `results`: 步骤执行结果

### Conditional Logic

条件分支通过解析 JSON 结构实现：
- 支持变量比较 (`equals`)
- 支持嵌套条件块
- `then` 和 `else` 分支可包含任意步骤序列

## Design Decisions

### D1: LangGraph 作为执行引擎

**决策**: 使用 LangGraph 而非自定义执行循环

**理由**:
- LangGraph 提供状态图抽象，便于表达工作流
- 内置 Studio 支持可视化调试
- 便于未来扩展 LLM 集成

### D2: 同步步骤执行

**决策**: 步骤按顺序同步执行

**理由**:
- 简化状态管理
- 避免并发问题
- 满足当前用例需求

**未来考虑**: 可添加并行执行支持

### D3: JSON 工作流定义

**决策**: 使用 JSON 格式定义工作流

**理由**:
- 便于前端构建和传输
- 人类可读
- 易于持久化存储
