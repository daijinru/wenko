import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api-client';
import type { LogFileInfo, LogFilesListResponse, LogContentResponse } from '@/types/api';

export type LogOrder = 'asc' | 'desc';

interface UseLogsState {
  files: LogFileInfo[];
  selectedDate: string | null;
  lines: string[];
  total: number;
  offset: number;
  limit: number;
  hasMore: boolean;
  order: LogOrder;
  loading: boolean;
  loadingContent: boolean;
  error: string | null;
}

export function useLogs() {
  const [state, setState] = useState<UseLogsState>({
    files: [],
    selectedDate: null,
    lines: [],
    total: 0,
    offset: 0,
    limit: 500,
    hasMore: false,
    order: 'desc',
    loading: true,
    loadingContent: false,
    error: null,
  });

  const loadFiles = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const response = await api.get<LogFilesListResponse>('/api/logs');
      setState(prev => ({
        ...prev,
        files: response.files,
        loading: false,
        // Auto-select latest date if available
        selectedDate: prev.selectedDate || (response.files[0]?.date ?? null),
      }));
    } catch (err) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : '加载日志文件列表失败',
      }));
    }
  }, []);

  const loadContent = useCallback(async (
    date: string,
    offset: number = 0,
    limit: number = 500,
    order: LogOrder = 'desc',
  ) => {
    setState(prev => ({ ...prev, loadingContent: true, error: null }));
    try {
      const response = await api.get<LogContentResponse>(`/api/logs/${date}`, {
        offset,
        limit,
        order,
      });
      setState(prev => ({
        ...prev,
        selectedDate: date,
        lines: response.lines,
        total: response.total,
        offset: response.offset,
        limit: response.limit,
        hasMore: response.has_more,
        order,
        loadingContent: false,
      }));
    } catch (err) {
      setState(prev => ({
        ...prev,
        loadingContent: false,
        error: err instanceof Error ? err.message : '加载日志内容失败',
      }));
    }
  }, []);

  const selectDate = useCallback((date: string) => {
    loadContent(date, 0, state.limit, state.order);
  }, [loadContent, state.limit, state.order]);

  const toggleOrder = useCallback(() => {
    const newOrder: LogOrder = state.order === 'desc' ? 'asc' : 'desc';
    if (state.selectedDate) {
      loadContent(state.selectedDate, 0, state.limit, newOrder);
    }
  }, [loadContent, state.selectedDate, state.limit, state.order]);

  const loadMore = useCallback(() => {
    if (state.selectedDate && state.hasMore) {
      const newOffset = state.offset + state.limit;
      loadContent(state.selectedDate, newOffset, state.limit, state.order);
    }
  }, [loadContent, state.selectedDate, state.offset, state.limit, state.hasMore, state.order]);

  const refresh = useCallback(() => {
    if (state.selectedDate) {
      loadContent(state.selectedDate, 0, state.limit, state.order);
    }
  }, [loadContent, state.selectedDate, state.limit, state.order]);

  // Load file list on mount
  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  // Load content when selectedDate is set
  useEffect(() => {
    if (state.selectedDate && state.lines.length === 0 && !state.loadingContent) {
      loadContent(state.selectedDate, 0, state.limit, state.order);
    }
  }, [state.selectedDate, state.lines.length, state.loadingContent, loadContent, state.limit, state.order]);

  return {
    ...state,
    loadFiles,
    loadContent,
    selectDate,
    toggleOrder,
    loadMore,
    refresh,
  };
}
