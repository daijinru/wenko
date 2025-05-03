```bash
# local Text Embedding
$ ollama pull nomic-embed-text

$ curl http://localhost:11434/api/embeddings -d '{
  "model": "nomic-embed-text",
  "prompt": "The sky is blue because of Rayleigh scattering"
}'

# Test
$ curl -X POST http://localhost:8080/generate -d "Hello World"
$ curl -X POST http://localhost:8080/generate -d "Hi World"
$ curl -X POST http://localhost:8080/search -d "world"
```
