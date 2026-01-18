import { useState, useCallback } from 'react';
import { api, ApiError } from '@/lib/api-client';
import { useToast } from '@/hooks/use-toast';
import type {
  WorkingMemory,
  WorkingMemoriesResponse,
  ChatMessage,
  SessionMessagesResponse,
} from '@/types/api';

export function useWorkingMemory() {
  const { toast } = useToast();
  const [memories, setMemories] = useState<WorkingMemory[]>([]);
  const [loading, setLoading] = useState(false);

  // Drilldown state
  const [expandedSessionId, setExpandedSessionId] = useState<string | null>(null);
  const [expandedMessages, setExpandedMessages] = useState<ChatMessage[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);

  const loadMemories = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get<WorkingMemoriesResponse>('/memory/working');
      setMemories(data.memories || []);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : '获取工作记忆列表失败';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  const clearMemory = useCallback(
    async (sessionId: string) => {
      try {
        await api.delete(`/memory/working/${sessionId}`);
        toast.success('工作记忆已清除');
        loadMemories();
        if (expandedSessionId === sessionId) {
          setExpandedSessionId(null);
          setExpandedMessages([]);
        }
      } catch (error) {
        const message = error instanceof ApiError ? error.message : '清除失败';
        toast.error(message);
      }
    },
    [toast, loadMemories, expandedSessionId]
  );

  const toggleExpand = useCallback(
    async (sessionId: string) => {
      if (expandedSessionId === sessionId) {
        setExpandedSessionId(null);
        setExpandedMessages([]);
        return;
      }

      setExpandedSessionId(sessionId);
      setMessagesLoading(true);
      try {
        const data = await api.get<SessionMessagesResponse>(
          `/chat/history/${sessionId}`
        );
        setExpandedMessages(data.messages || []);
      } catch (error) {
        const message = error instanceof ApiError ? error.message : '加载会话消息失败';
        toast.error(message);
        setExpandedMessages([]);
      } finally {
        setMessagesLoading(false);
      }
    },
    [toast, expandedSessionId]
  );

  return {
    memories,
    loading,
    expandedSessionId,
    expandedMessages,
    messagesLoading,
    loadMemories,
    clearMemory,
    toggleExpand,
  };
}
