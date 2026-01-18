import { useState, useCallback } from 'react';
import { api, ApiError } from '@/lib/api-client';
import { useToast } from '@/hooks/use-toast';
import type {
  LongTermMemory,
  LongTermMemoriesResponse,
  CreateMemoryRequest,
  UpdateMemoryRequest,
  DeleteResponse,
  BatchDeleteRequest,
  MemoryCategory,
} from '@/types/api';

export function useLongTermMemory() {
  const { toast } = useToast();
  const [memories, setMemories] = useState<LongTermMemory[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState<MemoryCategory | ''>('');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const loadMemories = useCallback(
    async (category: MemoryCategory | '' = categoryFilter) => {
      setLoading(true);
      try {
        const params: Record<string, string | number> = { limit: 100 };
        if (category) {
          params.category = category;
        }
        const data = await api.get<LongTermMemoriesResponse>(
          '/memory/long-term',
          params
        );
        setMemories(data.memories || []);
        setTotal(data.total || 0);
      } catch (error) {
        const message = error instanceof ApiError ? error.message : '获取记忆列表失败';
        toast.error(message);
      } finally {
        setLoading(false);
      }
    },
    [toast, categoryFilter]
  );

  const createMemory = useCallback(
    async (data: CreateMemoryRequest) => {
      try {
        await api.post('/memory/long-term', data);
        toast.success('记忆创建成功');
        loadMemories();
        return true;
      } catch (error) {
        const message = error instanceof ApiError ? error.message : '创建记忆失败';
        toast.error(message);
        return false;
      }
    },
    [toast, loadMemories]
  );

  const updateMemory = useCallback(
    async (id: string, data: UpdateMemoryRequest) => {
      try {
        await api.put(`/memory/long-term/${id}`, data);
        toast.success('记忆更新成功');
        loadMemories();
        return true;
      } catch (error) {
        const message = error instanceof ApiError ? error.message : '更新记忆失败';
        toast.error(message);
        return false;
      }
    },
    [toast, loadMemories]
  );

  const deleteMemory = useCallback(
    async (id: string) => {
      try {
        await api.delete(`/memory/long-term/${id}`);
        toast.success('记忆已删除');
        loadMemories();
      } catch (error) {
        const message = error instanceof ApiError ? error.message : '删除失败';
        toast.error(message);
      }
    },
    [toast, loadMemories]
  );

  const batchDelete = useCallback(async () => {
    if (selectedIds.length === 0) {
      toast.warning('请先选择要删除的记忆');
      return;
    }
    try {
      const data = await api.post<DeleteResponse>('/memory/long-term/batch-delete', {
        ids: selectedIds,
      } as BatchDeleteRequest);
      toast.success(`已删除 ${data.deleted_count} 条记忆`);
      setSelectedIds([]);
      loadMemories();
    } catch (error) {
      const message = error instanceof ApiError ? error.message : '批量删除失败';
      toast.error(message);
    }
  }, [toast, selectedIds, loadMemories]);

  const clearAll = useCallback(async () => {
    try {
      const data = await api.delete<DeleteResponse>('/memory/long-term');
      toast.success(`已清空 ${data.deleted_count} 条记忆`);
      setMemories([]);
      setTotal(0);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : '清空失败';
      toast.error(message);
    }
  }, [toast]);

  const exportMemories = useCallback(async () => {
    try {
      const data = await api.get<unknown>('/memory/long-term/export');
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `memories_${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('导出成功');
    } catch (error) {
      const message = error instanceof ApiError ? error.message : '导出失败';
      toast.error(message);
    }
  }, [toast]);

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  }, []);

  const setFilter = useCallback(
    (category: MemoryCategory | '') => {
      setCategoryFilter(category);
      loadMemories(category);
    },
    [loadMemories]
  );

  return {
    memories,
    total,
    loading,
    categoryFilter,
    selectedIds,
    loadMemories,
    createMemory,
    updateMemory,
    deleteMemory,
    batchDelete,
    clearAll,
    exportMemories,
    toggleSelect,
    setFilter,
    setSelectedIds,
  };
}
