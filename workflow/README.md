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

**方式一：使用启动脚本（推荐）**
```bash
./start.sh
```
启动脚本会自动检查并清理端口占用，然后启动服务。

**方式二：直接启动**
```bash
uv run python main.py
```

**注意**：如果遇到 `Address already in use` 错误，说明端口 8002 已被占用。可以：
- 使用启动脚本自动处理
- 手动清理：`lsof -ti :8002 | xargs kill -9`
- 或修改 `main.py` 中的端口号

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

### 工作流执行
- `POST /run` - 执行工作流

### 模板管理
- `POST /templates` - 创建模板
- `GET /templates` - 列出模板
- `GET /templates/{id}` - 获取模板
- `PUT /templates/{id}` - 更新模板
- `DELETE /templates/{id}` - 删除模板
- `GET /templates/search/{query}` - 搜索模板
- `POST /templates/{id}/execute` - 执行模板

### 系统接口
- `GET /health` - 健康检查
- `GET /steps` - 获取步骤注册表

## 测试工具

项目提供了 Web 测试界面，可通过 Electron 应用访问：
- 工作流执行测试
- 模板管理（创建、编辑、删除、搜索）
- 步骤注册表查看
- 服务健康检查

服务默认运行在 `http://localhost:8002`