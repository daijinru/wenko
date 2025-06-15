# Test

## Generate/Search Test
```bash
$ curl -X POST http://localhost:8080/generate -H "Content-Type: application/json" -d '{"text": "Hello World"}'
$ curl -X POST http://localhost:8080/generate -H "Content-Type: application/json" -d '{"text": "Hi World"}'
$ curl -X POST http://localhost:8080/search -H "Content-Type: application/json" -d '{"text": "world"}'
# 测试 compare 接口
# false
$ curl -X POST http://localhost:8080/compare -H "Content-Type: application/json" -d '{"text": "Hello World", "id": "95fe212025404260a325e7f30bb25dec"}'
# true => same words with threshold 0.8
$ curl -X POST http://localhost:8080/compare -H "Content-Type: application/json" -d '{"text": "行政手段方面，特朗普在 2025 年重返白宫后，针对美国整体 AI 战略提出了「保持和增强美国的全球 AI 统治地位」的核心目标，并获得了一些美国本土公司的支持。例如，OpenAI 提交的政策建议引发了广泛关注，其 CEO Sam Altman 在文件中将 DeepSeek 描述为「受中国政府掌控」的公司，并建议美国政府在芯片出口、数据限制等方面继续加大对中国 AI 发展的限制力度。", "id": "5a441db8c9184715a8a047fee38faf3c"}'

# 测试 task 接口
% curl -X POST http://localhost:8080/task -H "Content-Type: application/json" -d '{"text": "调用工具，帮助用户查询电影"}'
# 测试用户回答
# 如果 text 是空的，即用户认可
% curl -X POST http://localhost:8080/planning/task/answer -H "Content-Type: application/json" -d '{"text": "继续解释不同颜色光的散射", "actionId": "5cbdb867-2aeb-4e8d-9271-15d6058aec23"}'
% curl -X POST http://localhost:8080/planning/task/answer -H "Content-Type: application/json" -d '{"text": "", "actionId": "0ef22694-1f70-447a-be86-17c1044e939e"}'

# 工具指令
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPEN_ROUTER_API_KEY" \
  -d '{
  "model": "deepseek/deepseek-chat-v3-0324:free",
  "messages": [
    {
      "role": "user",
      "content": "查询电影"
    }
  ],
  "tools": [{
    "type": "function",
    "function": {
      "name": "ask_user",
      "description": "当你需要从用户那里获取额外信息、澄清问题或寻求指导时，使用此工具向用户提问。",
      "parameters": {
          "type": "object",
          "properties": {
              "question": {
                  "type": "string",
                  "description": "你想问用户的问题"
              }
          },
          "required": ["question"]
      }
  }],
}'
```

## List Documents
```bash
$ curl -X POST http://localhost:8080/documents -H "Content-Type: application/json" -d '{"limit": 100, "offset": 0 }'
```

## Chat Test
```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
  "model": "qwen/qwen3-32b:free",
  "messages": [
    {
      "role": "user",
      "content": "What is the meaning of life?"
    }
  ]
}'
```
