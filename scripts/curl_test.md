# Test

## Generate/Search Test
```bash
$ curl -X POST http://localhost:8080/generate -H "Content-Type: application/json" -d '{"text": "Hello World"}'
$ curl -X POST http://localhost:8080/generate -H "Content-Type: application/json" -d '{"text": "Hi World"}'
$ curl -X POST http://localhost:8080/search -H "Content-Type: application/json" -d '{"text": "world"}'
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
