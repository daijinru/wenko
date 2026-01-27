const { app, BrowserWindow, Notification } = require('electron');
const path = require('path');
const { ipcMain } = require('electron');
const express = require('express');

app.setName('Wenko');

// HITL window singleton management
let hitlWindow = null;
let hitlTimeoutId = null;
let mainWindow = null;
let currentHITLRequest = null;

// Image preview window management
let imagePreviewWindow = null;
let currentImageData = null;

// Reminder window management
let reminderWindow = null;
let currentReminderPlan = null;
let reminderQueue = []; // Queue for multiple reminders

// API configuration
const HITL_API_URL = 'http://localhost:8002/hitl/respond';
const IMAGE_ANALYZE_API_URL = 'http://localhost:8002/chat/image';

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
    // Skip sending cancel message for readonly mode (context variable replay)
    if (currentHITLRequest && !currentHITLRequest.request?.readonly) {
      const cancelResult = {
        success: true,
        action: 'cancel',
        message: '用户取消'
      };
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('hitl:result', cancelResult);
      }
    }
    currentHITLRequest = null;
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
  console.log('[HITL] Opening window:', data.request?.title, 'readonly:', data.request?.readonly);

  const { request, sessionId } = data;
  currentHITLRequest = { request, sessionId };

  // Create or focus HITL window
  createHITLWindow(request);

  // Setup TTL timeout (skip for readonly mode)
  if (!request.readonly) {
    const ttlSeconds = request.ttl_seconds || 300;
    setupHITLTimeout(ttlSeconds);
  }

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

  // Only send cancel result to Live2D for non-readonly mode
  const isReadonly = currentHITLRequest?.request?.readonly;

  if (!isReadonly && mainWindow && !mainWindow.isDestroyed()) {
    const cancelResult = {
      success: true,
      action: 'cancel',
      message: '用户取消'
    };
    mainWindow.webContents.send('hitl:result', cancelResult);
  }

  closeHITLWindow();

  return { success: true, action: 'cancel' };
});

// ============ Image Preview Window Management ============

/**
 * Create Image Preview window
 */
function createImagePreviewWindow() {
  if (imagePreviewWindow && !imagePreviewWindow.isDestroyed()) {
    imagePreviewWindow.focus();
    return imagePreviewWindow;
  }

  imagePreviewWindow = new BrowserWindow({
    width: 500,
    height: 550,
    title: 'Image Preview',
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

  imagePreviewWindow.loadFile(path.join(__dirname, 'dist/src/renderer/image-preview/index.html'));

  imagePreviewWindow.once('ready-to-show', () => {
    imagePreviewWindow.show();
    // Send image data to preview window
    if (currentImageData) {
      imagePreviewWindow.webContents.send('image-preview:data', currentImageData);
    }
  });

  imagePreviewWindow.on('closed', () => {
    // Send cancel to Live2D if window closed without action
    if (currentImageData && mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('image-preview:result', {
        success: false,
        action: 'cancel'
      });
    }
    currentImageData = null;
    imagePreviewWindow = null;
  });

  return imagePreviewWindow;
}

/**
 * Close Image Preview window
 */
function closeImagePreviewWindow() {
  currentImageData = null;
  if (imagePreviewWindow && !imagePreviewWindow.isDestroyed()) {
    imagePreviewWindow.close();
  }
  imagePreviewWindow = null;
}

// ============ Image Preview IPC Handlers ============

/**
 * Open image preview window
 */
ipcMain.handle('image-preview:open', async (event, data) => {
  console.log('[ImagePreview] Opening window');

  const { imageData, sessionId } = data;
  currentImageData = { imageData, sessionId };

  createImagePreviewWindow();

  return { success: true };
});

/**
 * Analyze image
 */
ipcMain.handle('image-preview:analyze', async (event, data) => {
  console.log('[ImagePreview] Analyzing image');

  const { imageData, sessionId } = data;

  try {
    const response = await fetch(IMAGE_ANALYZE_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image: imageData,
        session_id: sessionId,
        action: 'analyze_only'
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      return { success: false, error: `API error: ${response.status}` };
    }

    // Parse SSE response to get extracted text
    const text = await response.text();
    console.log('[ImagePreview] Raw SSE response:', text);
    let extractedText = '';

    // Parse SSE events
    const lines = text.split('\n');
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const jsonStr = line.substring(6);
          console.log('[ImagePreview] Parsing JSON:', jsonStr);
          const data = JSON.parse(jsonStr);
          if (data.type === 'text' && data.payload?.content) {
            extractedText += data.payload.content;
          }
        } catch (e) {
          console.error('[ImagePreview] JSON parse error:', e.message);
        }
      }
    }
    console.log('[ImagePreview] Extracted text:', extractedText);

    return {
      success: true,
      extractedText: extractedText || 'No text found'
    };
  } catch (error) {
    console.error('[ImagePreview] Analyze error:', error);
    return {
      success: false,
      error: error.message || 'Network error'
    };
  }
});

/**
 * Save extracted text to memory
 */
ipcMain.handle('image-preview:save-memory', async (event, data) => {
  console.log('[ImagePreview] Saving to memory');

  const { extractedText, sessionId } = data;

  try {
    // Call the memory API to save
    console.log('[ImagePreview] Calling API with action: analyze_for_memory');
    const response = await fetch(IMAGE_ANALYZE_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image: currentImageData?.imageData,
        session_id: sessionId,
        action: 'analyze_for_memory'
      })
    });

    if (!response.ok) {
      console.error('[ImagePreview] API error:', response.status);
      return { success: false, error: `API error: ${response.status}` };
    }

    // Parse SSE to check for HITL
    const text = await response.text();
    console.log('[ImagePreview] Save-memory raw SSE response:', text);
    let hitlPayload = null;

    const lines = text.split('\n');
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const jsonStr = line.substring(6);
          console.log('[ImagePreview] Save-memory parsing JSON:', jsonStr);
          const data = JSON.parse(jsonStr);
          if (data.type === 'hitl' && data.payload) {
            console.log('[ImagePreview] Found HITL payload:', data.payload);
            hitlPayload = data.payload;
          }
        } catch (e) {
          console.error('[ImagePreview] JSON parse error:', e.message);
        }
      }
    }

    // If HITL request found, open HITL window
    if (hitlPayload) {
      closeImagePreviewWindow();

      // Send result to Live2D with HITL data
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('image-preview:result', {
          success: true,
          action: 'hitl',
          hitlRequest: hitlPayload
        });
      }

      return { success: true, hasHITL: true };
    }

    return { success: true };
  } catch (error) {
    console.error('[ImagePreview] Save memory error:', error);
    return { success: false, error: error.message || 'Network error' };
  }
});

/**
 * Cancel image preview
 */
ipcMain.handle('image-preview:cancel', async (event) => {
  console.log('[ImagePreview] Cancel');
  closeImagePreviewWindow();
  return { success: true };
});

/**
 * Close image preview window
 */
ipcMain.handle('image-preview:close', async (event) => {
  console.log('[ImagePreview] Close');
  closeImagePreviewWindow();
  return { success: true };
});

// ============ Reminder Window Management ============

const SETTINGS_API_URL = 'http://localhost:8002/api/settings';

/**
 * Get reminder settings from backend
 */
async function getReminderSettings() {
  try {
    const response = await fetch(SETTINGS_API_URL);
    if (!response.ok) {
      console.error('[Reminder] Settings API error:', response.status);
      return { windowEnabled: true, notificationEnabled: true };
    }
    const data = await response.json();
    const settings = data.settings || {};
    return {
      windowEnabled: settings['system.reminder_window_enabled'] !== false,
      notificationEnabled: settings['system.os_notification_enabled'] !== false,
    };
  } catch (error) {
    console.error('[Reminder] Failed to get settings:', error.message);
    return { windowEnabled: true, notificationEnabled: true };
  }
}

/**
 * Create Reminder window for plan display
 */
function createReminderWindow(plan) {
  if (reminderWindow && !reminderWindow.isDestroyed()) {
    reminderWindow.focus();
    return reminderWindow;
  }

  reminderWindow = new BrowserWindow({
    width: 400,
    height: 320,
    title: '计划提醒',
    parent: mainWindow,
    modal: false,
    show: false,
    center: true,
    resizable: false,
    minimizable: false,
    maximizable: false,
    alwaysOnTop: true,
    titleBarStyle: 'hidden',
    trafficLightPosition: { x: 10, y: 10 },
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false
    }
  });

  reminderWindow.loadFile(path.join(__dirname, 'dist/src/renderer/reminder/index.html'));

  reminderWindow.once('ready-to-show', () => {
    // Show without stealing focus
    reminderWindow.showInactive();
  });

  // Wait for React to mount before sending data
  reminderWindow.webContents.once('did-finish-load', () => {
    if (currentReminderPlan) {
      reminderWindow.webContents.send('reminder:data', currentReminderPlan);
    }
  });

  reminderWindow.on('closed', () => {
    // If window closed without action, treat as dismiss
    if (currentReminderPlan) {
      currentReminders.delete(currentReminderPlan.id);
    }
    currentReminderPlan = null;
    reminderWindow = null;
    // Process next reminder in queue
    processReminderQueue();
  });

  return reminderWindow;
}

/**
 * Close reminder window
 */
function closeReminderWindow() {
  // Clear plan reference before close to prevent 'closed' event from double-processing
  const planId = currentReminderPlan?.id;
  currentReminderPlan = null;
  if (reminderWindow && !reminderWindow.isDestroyed()) {
    reminderWindow.close();
  }
  reminderWindow = null;
  // Ensure ID is removed from tracking set
  if (planId) {
    currentReminders.delete(planId);
  }
}

/**
 * Get current reminder data (called by renderer)
 */
ipcMain.handle('reminder:get-data', async (event) => {
  if (currentReminderPlan) {
    return currentReminderPlan;
  }
  return null;
});

/**
 * Show OS notification for a plan
 */
function showOSNotification(plan, openWindowOnClick = false) {
  if (!Notification.isSupported()) {
    console.log('[Reminder] Notifications not supported');
    return;
  }

  const notification = new Notification({
    title: '计划提醒',
    body: plan.title,
    silent: false,
  });

  notification.on('click', () => {
    if (openWindowOnClick) {
      triggerReminderWindow(plan);
    }
  });

  notification.show();
}

/**
 * Add reminder to queue and process
 */
function queueReminder(plan, settings) {
  reminderQueue.push({ plan, settings });
  if (!reminderWindow || reminderWindow.isDestroyed()) {
    processReminderQueue();
  }
}

/**
 * Process next reminder in queue
 */
function processReminderQueue() {
  if (reminderQueue.length === 0) return;
  if (reminderWindow && !reminderWindow.isDestroyed()) return;

  const { plan, settings } = reminderQueue.shift();

  if (settings.windowEnabled) {
    currentReminderPlan = plan;
    createReminderWindow(plan);
  }
}

/**
 * Trigger reminder window for a plan (from notification click)
 */
function triggerReminderWindow(plan) {
  currentReminderPlan = plan;
  currentReminders.add(plan.id);
  createReminderWindow(plan);
  // Focus the window since user clicked notification
  if (reminderWindow && !reminderWindow.isDestroyed()) {
    reminderWindow.focus();
  }
}

// ============ Plan Reminder Polling ============

const PLANS_API_URL = 'http://localhost:8002/plans';
const PLAN_POLL_INTERVAL = 15 * 1000; // 15 seconds - more responsive for timely reminders
let planPollIntervalId = null;
let currentReminders = new Set(); // Track reminders being shown to avoid duplicates

/**
 * Poll for due plans and send reminders
 */
async function pollDuePlans() {
  try {
    const response = await fetch(`${PLANS_API_URL}/due`);
    if (!response.ok) {
      console.error('[PlanReminder] API error:', response.status);
      return;
    }

    const data = await response.json();
    const plans = data.plans || [];

    if (plans.length === 0) return;

    // Get user settings
    const settings = await getReminderSettings();

    // If both disabled, skip all reminders
    if (!settings.windowEnabled && !settings.notificationEnabled) {
      console.log('[PlanReminder] Both reminder methods disabled, skipping');
      return;
    }

    for (const plan of plans) {
      // Skip if reminder already being shown
      if (currentReminders.has(plan.id)) {
        continue;
      }

      console.log('[PlanReminder] Due plan found:', plan.title);

      // Mark as being shown
      currentReminders.add(plan.id);

      const planData = {
        id: plan.id,
        title: plan.title,
        description: plan.description,
        target_time: plan.target_time,
        repeat_type: plan.repeat_type,
      };

      // Trigger based on settings
      if (settings.notificationEnabled && settings.windowEnabled) {
        // Both enabled: send notification, click opens window
        showOSNotification(planData, true);
        queueReminder(planData, settings);
      } else if (settings.windowEnabled) {
        // Only window enabled: directly open window
        queueReminder(planData, settings);
      } else if (settings.notificationEnabled) {
        // Only notification enabled: just send notification
        showOSNotification(planData, false);
      }
    }
  } catch (error) {
    console.error('[PlanReminder] Poll error:', error.message);
  }
}

/**
 * Start plan polling service
 */
function startPlanPolling() {
  if (planPollIntervalId) {
    return; // Already running
  }

  console.log('[PlanReminder] Starting polling service');

  // Poll immediately on start
  pollDuePlans();

  // Then poll every interval
  planPollIntervalId = setInterval(pollDuePlans, PLAN_POLL_INTERVAL);
}

/**
 * Stop plan polling service
 */
function stopPlanPolling() {
  if (planPollIntervalId) {
    console.log('[PlanReminder] Stopping polling service');
    clearInterval(planPollIntervalId);
    planPollIntervalId = null;
  }
}

// Start polling when app is ready
app.whenReady().then(() => {
  // Delay start to allow main window to initialize
  setTimeout(startPlanPolling, 5000);
});

// Stop polling when all windows close
app.on('window-all-closed', () => {
  stopPlanPolling();
});

// ============ Plan Reminder IPC Handlers ============

/**
 * Handle plan completion from Reminder window
 */
ipcMain.handle('reminder:complete', async (event, planId) => {
  console.log('[Reminder] Complete plan:', planId);

  try {
    const response = await fetch(`${PLANS_API_URL}/${planId}/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!response.ok) {
      return { success: false, error: `API error: ${response.status}` };
    }

    const result = await response.json();

    // Remove from current reminders
    currentReminders.delete(planId);

    // Close reminder window
    closeReminderWindow();

    return { success: true, plan: result };
  } catch (error) {
    console.error('[Reminder] Complete error:', error);
    return { success: false, error: error.message };
  }
});

/**
 * Handle plan dismissal from Reminder window
 */
ipcMain.handle('reminder:dismiss', async (event, planId) => {
  console.log('[Reminder] Dismiss plan:', planId);

  try {
    const response = await fetch(`${PLANS_API_URL}/${planId}/dismiss`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!response.ok) {
      return { success: false, error: `API error: ${response.status}` };
    }

    const result = await response.json();

    // Remove from current reminders
    currentReminders.delete(planId);

    // Close reminder window
    closeReminderWindow();

    return { success: true, plan: result };
  } catch (error) {
    console.error('[Reminder] Dismiss error:', error);
    return { success: false, error: error.message };
  }
});

/**
 * Handle plan snooze from Reminder window
 */
ipcMain.handle('reminder:snooze', async (event, data) => {
  const { planId, snoozeMinutes } = data;
  console.log('[Reminder] Snooze plan:', planId, 'for', snoozeMinutes, 'minutes');

  try {
    const response = await fetch(`${PLANS_API_URL}/${planId}/snooze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ snooze_minutes: snoozeMinutes }),
    });

    if (!response.ok) {
      return { success: false, error: `API error: ${response.status}` };
    }

    const result = await response.json();

    // Remove from current reminders (will reappear after snooze)
    currentReminders.delete(planId);

    // Close reminder window
    closeReminderWindow();

    return { success: true, plan: result };
  } catch (error) {
    console.error('[Reminder] Snooze error:', error);
    return { success: false, error: error.message };
  }
});
