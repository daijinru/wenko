// IPC Client for ECS Window
import type { ECSSubmitRequest, ECSResultResponse, ECSOpenRequest } from '../types/ecs';

/**
 * Submit ECS form response via IPC
 */
export async function submitECS(data: ECSSubmitRequest): Promise<ECSResultResponse> {
  try {
    const result = await window.electronAPI.invoke<ECSResultResponse>('ecs:submit', data);
    return result;
  } catch (error) {
    console.error('[ECS IPC] Submit error:', error);
    return {
      success: false,
      action: data.action,
      error: error instanceof Error ? error.message : '提交失败',
    };
  }
}

/**
 * Cancel ECS request via IPC
 */
export async function cancelECS(): Promise<ECSResultResponse> {
  try {
    const result = await window.electronAPI.invoke<ECSResultResponse>('ecs:cancel');
    return result;
  } catch (error) {
    console.error('[ECS IPC] Cancel error:', error);
    return {
      success: false,
      action: 'cancel',
      error: error instanceof Error ? error.message : '取消失败',
    };
  }
}

/**
 * Listen for ECS request data from main process
 */
export function onECSRequestData(callback: (data: ECSOpenRequest) => void): () => void {
  return window.electronAPI.on('ecs:request-data', (data) => {
    callback(data as ECSOpenRequest);
  });
}
