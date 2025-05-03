```bash
# local Text Embedding
$ ollama pull nomic-embed-text

$ curl http://localhost:11434/api/embeddings -d '{
  "model": "nomic-embed-text",
  "prompt": "The sky is blue because of Rayleigh scattering"
}'

# Test
$ curl -X POST http://localhost:8080/generate -H "Content-Type: application/json" -d '{"text": "Hello World"}'
$ curl -X POST http://localhost:8080/generate -H "Content-Type: application/json" -d '{"text": "Hi World"}'
$ curl -X POST http://localhost:8080/search -H "Content-Type: application/json" -d '{"text": "world"}'
```
