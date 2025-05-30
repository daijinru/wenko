```bash
$ docker pull chromadb/chroma
$ docker run -p 8000:8000 -v /Users/daijinru/datas/chroma_db/chroma:/chroma/chroma -v /Users/daijinru/datas/chroma_db/data:/data chromadb/chroma
# windows
$ docker run -p 8000:8000 -v C:\\Users\\daijinru\\datas\\chroma_db\\chroma:/chroma/chroma -v C:\\Users\\daijinru\\datas\\chroma_db\\data:/data chromadb/chroma
```
