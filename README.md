# 温故而知新

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
