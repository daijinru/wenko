const { app, BrowserWindow } = require('electron');
const path = require('path');
const { ipcMain } = require('electron');
const express = require('express');

app.setName('Wenko');

// 创建Express服务器提供live2d静态文件访问
function createStaticServer() {
  const expressApp = express();
  const port = 8080;
  
  // 提供live2d目录的静态文件访问
  expressApp.use('/live2d', express.static(path.join(__dirname, 'live2d')));
  
  expressApp.listen(port, () => {
    console.log(`Static server running on http://localhost:${port}`);
  });
}

// 启动静态文件服务器
createStaticServer();

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 350,
    height: 400,
    title: 'Wenko',
    icon: path.join(__dirname, 'assets', 'favicon.ico'),
    frame: false,
    transparent: true,
    alwaysOnTop: false,
    resizable: true,
    hasShadow: false,
    fullscreenable: false,
    skipTaskbar: true,    // 不在任务栏显示
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false  // 关闭同源策略和 CSP 检查，方便开发加载任意脚本
    }
  });

  mainWindow.loadFile('index.html');
}

app.whenReady().then(async () => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

if (process.platform === 'darwin') {
  app.dock.setIcon(path.join(__dirname, 'assets', 'favicon.ico'));
}

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

ipcMain.on('wenko_shortcut', async (event, data) => {
  console.info('wenko_shortcut data received', data);
  // 处理快捷键事件: action: open
  const { action } = data;
  if (action === 'open') {
    // 打开窗口 800 x 600
    const shortcutWindow = new BrowserWindow({
      width: 800,
      height: 600,
      title: 'Wenko ShortCut',
      icon: path.join(__dirname, 'assets', 'favicon.ico'),
      frame: true,
      transparent: false,
      alwaysOnTop: false,
      resizable: true,
      hasShadow: true,
      fullscreenable: true,
      skipTaskbar: false,    // 在任务栏显示
      webPreferences: {
        preload: path.join(__dirname, 'preload.js'),
        nodeIntegration: false,
        contextIsolation: true,
        webSecurity: false  // 关闭同源策略和 CSP 检查，方便开发加载任意脚本
      }
    });
    shortcutWindow.loadFile('index.html');
  } else {
    console.warn('Unknown action:', action);
  }
});
