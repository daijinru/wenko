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
$ curl -X POST http://localhost:8080/compare -H "Content-Type: application/json" -d '{"text": "Hello World", "id": "24d4ac4f80454fcc8f41027983231324"}'
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
