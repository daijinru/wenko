# 步骤模板 API 使用示例

本文档展示了如何使用新添加的步骤模板存储和 CRUD API 接口。

## API 接口概览

### 基础接口
- `GET /health` - 健康检查
- `GET /steps` - 获取步骤注册表
- `POST /run` - 执行工作流

### 步骤模板 CRUD 接口
- `POST /templates` - 创建步骤模板
- `GET /templates` - 列出步骤模板
- `GET /templates/{template_id}` - 获取特定步骤模板
- `PUT /templates/{template_id}` - 更新步骤模板
- `DELETE /templates/{template_id}` - 删除步骤模板
- `GET /templates/search/{query}` - 搜索步骤模板
- `POST /templates/{template_id}/execute` - 执行步骤模板

## 使用示例

### 1. 创建步骤模板

```bash
curl -X POST "http://localhost:8002/templates" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "字符串处理工作流",
    "description": "处理字符串操作的工作流示例",
    "steps": [
      {
        "type": "SetVar",
        "params": {
          "key": "text",
          "value": "  Hello World  "
        }
      },
      {
        "type": "StringOp",
        "params": {
          "operation": "strip",
          "input_key": "text",
          "output_key": "trimmed_text"
        }
      },
      {
        "type": "StringOp",
        "params": {
          "operation": "upper",
          "input_key": "trimmed_text",
          "output_key": "upper_text"
        }
      },
      {
        "type": "GetVar",
        "params": {
          "key": "upper_text"
        }
      }
    ],
    "tags": ["字符串", "处理", "示例"]
  }'
```

### 2. 列出所有步骤模板

```bash
curl -X GET "http://localhost:8002/templates"
```

### 3. 按标签过滤步骤模板

```bash
curl -X GET "http://localhost:8002/templates?tags=字符串,处理"
```

### 4. 获取特定步骤模板

```bash
curl -X GET "http://localhost:8002/templates/{template_id}"
```

### 5. 更新步骤模板

```bash
curl -X PUT "http://localhost:8002/templates/{template_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "高级字符串处理工作流",
    "description": "更高级的字符串处理工作流示例",
    "tags": ["字符串", "高级", "处理"]
  }'
```

### 6. 搜索步骤模板

```bash
curl -X GET "http://localhost:8002/templates/search/字符串"
```

### 7. 执行步骤模板

```bash
curl -X POST "http://localhost:8002/templates/{template_id}/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "initial_context": {
      "user_name": "张三",
      "system_info": "工作流系统 v1.0"
    }
  }'
```

### 8. 删除步骤模板

```bash
curl -X DELETE "http://localhost:8002/templates/{template_id}"
```

## 数据模型

### StepTemplate
```json
{
  "id": "uuid",
  "name": "模板名称",
  "description": "模板描述",
  "steps": [
    {
      "type": "步骤类型",
      "params": {
        "参数名": "参数值"
      }
    }
  ],
  "tags": ["标签1", "标签2"],
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

### CreateStepTemplateRequest
```json
{
  "name": "模板名称",
  "description": "模板描述（可选）",
  "steps": [
    {
      "type": "步骤类型",
      "params": {
        "参数名": "参数值"
      }
    }
  ],
  "tags": ["标签1", "标签2"]（可选）
}
```

### UpdateStepTemplateRequest
```json
{
  "name": "新模板名称（可选）",
  "description": "新模板描述（可选）",
  "steps": [
    {
      "type": "步骤类型",
      "params": {
        "参数名": "参数值"
      }
    }
  ]（可选）,
  "tags": ["新标签1", "新标签2"]（可选）
}
```

## 默认模板

系统启动时会自动创建以下默认模板：

1. **基础工作流** - 包含 EchoInput、SetVar、GetVar 的基础工作流示例
2. **数学计算工作流** - 包含数学运算的工作流示例

## 存储架构

当前使用内存存储，但已为未来数据库集成预留了接口：

- `StepTemplateStorageInterface` - 存储接口抽象层
- `StepTemplateStorage` - 内存存储实现
- 未来可轻松切换到数据库存储：`DatabaseStepTemplateStorage`

## 错误处理

所有 API 接口都包含适当的错误处理：

- 400 - 请求参数错误
- 404 - 资源不存在
- 500 - 服务器内部错误

错误响应格式：
```json
{
  "detail": "错误描述"
}
```
