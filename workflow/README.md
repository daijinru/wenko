# LangGraph 工作流系统

一个基于 LangGraph 和 FastAPI 的工作流编排系统，支持多种步骤类型和条件控制逻辑。

## 功能特性

- 🔄 **步骤编排**：支持 11 种基础步骤类型
- 🎯 **条件控制**：If/Then/Else 条件分支逻辑
- 📝 **变量管理**：上下文变量设置和占位符替换
- 🚀 **FastAPI 接口**：RESTful API 服务
- 🎨 **LangGraph Studio**：可视化工作流开发

## 快速开始

### 启动 FastAPI 服务
```bash
python main.py
```

### 启动 LangGraph Studio
```bash
uv run langgraph dev
```

## 支持的步骤类型

1. **EchoInput** - 回显输入
2. **SetVar** - 设置变量
3. **GetVar** - 获取变量
4. **FetchURL** - HTTP 请求
5. **ParseJSON** - JSON 解析
6. **JSONLookup** - JSON 查找
7. **JSONExtractValues** - JSON 值提取
8. **TemplateReplace** - 模板替换
9. **MultilineToSingleLine** - 多行转单行
10. **OutputResult** - 输出结果
11. **CopyVar** - 复制变量

## 条件控制

- **If** - 条件判断
- **Then** - 条件为真时执行
- **Else** - 条件为假时执行

## API 接口

- `POST /run` - 执行工作流
- `GET /health` - 健康检查