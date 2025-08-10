```bash
# local Text Embedding
$ ollama pull nomic-embed-text

$ curl http://localhost:11434/api/embeddings -d '{
  "model": "nomic-embed-text",
  "prompt": "The sky is blue because of Rayleigh scattering"
}'
