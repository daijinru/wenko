const { app, BrowserWindow } = require('electron');
const path = require('path');
const { ipcMain } = require('electron');
const express = require('express');

app.setName('Wenko');

// HITL window singleton management
let hitlWindow = null;
let hitlTimeoutId = null;
let mainWindow = null;
let currentHITLRequest = null;

// HITL API configuration
const HITL_API_URL = 'http://localhost:8002/hitl/respond';

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
  mainWindow = new BrowserWindow({
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
      preload: path.join(__dirname, 'preload.cjs'),
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
    // 打开窗口用于 workflow API 测试
    const shortcutWindow = new BrowserWindow({
      width: 1200,
      height: 800,
      title: 'Memory Palace',
      icon: path.join(__dirname, 'assets', 'favicon.ico'),
      titleBarStyle: 'hidden',
      trafficLightPosition: { x: 10, y: 6 },
      transparent: false,
      alwaysOnTop: false,
      resizable: true,
      hasShadow: true,
      fullscreenable: true,
      skipTaskbar: false,    // 在任务栏显示
      webPreferences: {
        preload: path.join(__dirname, 'preload.cjs'),
        nodeIntegration: false,
        contextIsolation: true,
        webSecurity: false  // 关闭同源策略和 CSP 检查，方便开发加载任意脚本
      }
    });
    shortcutWindow.loadFile(path.join(__dirname, 'dist/src/renderer/workflow/index.html'));
  } else {
    console.warn('Unknown action:', action);
  }
});

// ============ HITL Window Management ============

/**
 * Create HITL window for form display
 */
function createHITLWindow(request) {
  // If window already exists, focus it
  if (hitlWindow && !hitlWindow.isDestroyed()) {
    hitlWindow.focus();
    return hitlWindow;
  }

  hitlWindow = new BrowserWindow({
    width: 480,
    height: 600,
    title: request.title || 'HITL',
    parent: mainWindow,
    modal: false,
    show: false,
    center: true,
    resizable: true,
    minimizable: false,
    maximizable: false,
    titleBarStyle: 'hidden',
    trafficLightPosition: { x: 10, y: 10 },
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false
    }
  });

  hitlWindow.loadFile(path.join(__dirname, 'dist/src/renderer/hitl/index.html'));

  // Show window when ready
  hitlWindow.once('ready-to-show', () => {
    hitlWindow.show();
    // Send request data to HITL window
    hitlWindow.webContents.send('hitl:request-data', currentHITLRequest);
  });

  // Handle window close (treat as cancel)
  hitlWindow.on('closed', () => {
    if (hitlTimeoutId) {
      clearTimeout(hitlTimeoutId);
      hitlTimeoutId = null;
    }
    // If window closed without submit, treat as cancel
    if (currentHITLRequest) {
      const cancelResult = {
        success: true,
        action: 'cancel',
        message: '用户取消'
      };
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('hitl:result', cancelResult);
      }
      currentHITLRequest = null;
    }
    hitlWindow = null;
  });

  return hitlWindow;
}

/**
 * Close HITL window
 */
function closeHITLWindow() {
  if (hitlTimeoutId) {
    clearTimeout(hitlTimeoutId);
    hitlTimeoutId = null;
  }
  if (hitlWindow && !hitlWindow.isDestroyed()) {
    // Clear currentHITLRequest before closing to prevent cancel event
    currentHITLRequest = null;
    hitlWindow.close();
  }
  hitlWindow = null;
}

/**
 * Setup TTL timeout for HITL window
 */
function setupHITLTimeout(ttlSeconds) {
  if (hitlTimeoutId) {
    clearTimeout(hitlTimeoutId);
  }
  hitlTimeoutId = setTimeout(() => {
    console.log('[HITL] Window timeout, closing...');
    if (hitlWindow && !hitlWindow.isDestroyed()) {
      const timeoutResult = {
        success: false,
        action: 'timeout',
        error: '请求已超时'
      };
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('hitl:result', timeoutResult);
      }
      currentHITLRequest = null;
      hitlWindow.close();
    }
  }, ttlSeconds * 1000);
}

// ============ HITL IPC Handlers ============

/**
 * Handle request to open HITL window
 */
ipcMain.handle('hitl:open-window', async (event, data) => {
  console.log('[HITL] Opening window:', data.request?.title);

  const { request, sessionId } = data;
  currentHITLRequest = { request, sessionId };

  // Create or focus HITL window
  createHITLWindow(request);

  // Setup TTL timeout
  const ttlSeconds = request.ttl_seconds || 300;
  setupHITLTimeout(ttlSeconds);

  return { success: true };
});

/**
 * Handle HITL form submission
 */
ipcMain.handle('hitl:submit', async (event, data) => {
  console.log('[HITL] Submit:', data.action);

  const { requestId, sessionId, action, formData } = data;

  try {
    // Call backend API
    const response = await fetch(HITL_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        request_id: requestId,
        session_id: sessionId,
        action: action,
        data: formData
      })
    });

    if (!response.ok) {
      const errorData = await response.json();
      const errorResult = {
        success: false,
        action: action,
        error: errorData.detail || 'HITL 提交失败'
      };
      // Send error to HITL window (don't close)
      return errorResult;
    }

    const result = await response.json();
    console.log('[HITL] Backend response:', result);

    // Build result for Live2D
    const hitlResult = {
      success: result.success,
      action: action,
      message: result.message,
      error: result.error,
      continuationData: result.continuation_data
    };

    // If success, send result to Live2D and close window
    if (result.success) {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('hitl:result', hitlResult);
      }
      closeHITLWindow();
    }

    return hitlResult;
  } catch (error) {
    console.error('[HITL] Submit error:', error);
    return {
      success: false,
      action: action,
      error: error.message || '网络错误'
    };
  }
});

/**
 * Handle HITL cancel request
 */
ipcMain.handle('hitl:cancel', async (event) => {
  console.log('[HITL] Cancel requested');

  const cancelResult = {
    success: true,
    action: 'cancel',
    message: '用户取消'
  };

  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('hitl:result', cancelResult);
  }

  closeHITLWindow();

  return cancelResult;
});
