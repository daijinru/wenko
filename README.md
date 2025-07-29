# 温故而知新

Come to get Yrself >< AI看板娘！

## Articles
- [DeepWiki](https://deepwiki.com/daijinru/wenko)
- [赛博仓鼠如何对抗碎片化阅读](https://mp.weixin.qq.com/s/hZ32EHZI1DGfCgnrbmCVwQ)

## Development Guider

### Environment Requirements

| Language | Version |
|----------|---------|
| Python       | 3.13.1+   |
| Node.js  | 18+     |

### Other Environment

Plz reading `scripts/ollama_init.md` and `scripts/docker.md` for setup service.

### Start the Service

Make sure config.json exists for the Main server.

```
{
  "OllamaURL": "http://localhost:11434/api/embeddings",
  "ModelProviderURI": "https://<Model_Provider>/v1/chat/completions",
  "ModelProviderModel": "<Model_Name>",
  "ModelProviderAPIKey": "",
  "ChromaDBURL": "http://localhost:8000/api/v2",
  "ChromDBTenants": "wenko",
  "ChromaDBDatabase": "wenko",
  "Collection": "embeddings_hnsw_ip"
}

```

```bash
# 1. project root run Service
./start.sh

# 2. go to chrome-wenko run Service
cd inbox/chrome/chrome-wenko
npm install
./start.sh

cd inbox/chrome/chrome-wenko/inject
./start.sh

# 3. chrome plugin development guider
# open Chrome browser, and open chrome://extensions/
# open “development mode” / "开发者模式"，点击“加载已解压的扩展程序”，choose `chrome-wenko/build`
```

### Live2D Development

```bash
git submodule update --remote --recursive
# make sure develop in master
cd live2d/live2d-widget
git checkout master
git pull
# install deps
yarn install
# just compile cause of support its resource from Main.py Server
yarn run build 
```

