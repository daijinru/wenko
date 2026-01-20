// IPC Client for HITL Window
import type { HITLSubmitRequest, HITLResultResponse, HITLOpenRequest } from '../types/hitl';

/**
 * Submit HITL form response via IPC
 */
export async function submitHITL(data: HITLSubmitRequest): Promise<HITLResultResponse> {
  try {
    const result = await window.electronAPI.invoke<HITLResultResponse>('hitl:submit', data);
    return result;
  } catch (error) {
    console.error('[HITL IPC] Submit error:', error);
    return {
      success: false,
      action: data.action,
      error: error instanceof Error ? error.message : '提交失败',
    };
  }
}

/**
 * Cancel HITL request via IPC
 */
export async function cancelHITL(): Promise<HITLResultResponse> {
  try {
    const result = await window.electronAPI.invoke<HITLResultResponse>('hitl:cancel');
    return result;
  } catch (error) {
    console.error('[HITL IPC] Cancel error:', error);
    return {
      success: false,
      action: 'cancel',
      error: error instanceof Error ? error.message : '取消失败',
    };
  }
}

/**
 * Listen for HITL request data from main process
 */
export function onHITLRequestData(callback: (data: HITLOpenRequest) => void): () => void {
  return window.electronAPI.on('hitl:request-data', (data) => {
    callback(data as HITLOpenRequest);
  });
}
