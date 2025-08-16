const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 350,
    height: 400,
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

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
