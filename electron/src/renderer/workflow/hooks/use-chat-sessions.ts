import { useState, useCallback } from 'react';
import { api, ApiError } from '@/lib/api-client';
import { useToast } from '@/hooks/use-toast';
import type {
  ChatSession,
  ChatMessage,
  ChatHistoryResponse,
  SessionMessagesResponse,
  DeleteResponse,
} from '@/types/api';

export function useChatSessions() {
  const { toast } = useToast();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);

  const loadSessions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get<ChatHistoryResponse>('/chat/history');
      setSessions(data.sessions || []);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : '加载聊天记录失败';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  const loadSessionMessages = useCallback(
    async (sessionId: string) => {
      setSelectedSessionId(sessionId);
      setMessagesLoading(true);
      try {
        const data = await api.get<SessionMessagesResponse>(
          `/chat/history/${sessionId}`
        );
        setMessages(data.messages || []);
      } catch (error) {
        const message = error instanceof ApiError ? error.message : '加载会话详情失败';
        toast.error(message);
        setMessages([]);
      } finally {
        setMessagesLoading(false);
      }
    },
    [toast]
  );

  const deleteSession = useCallback(
    async (sessionId: string) => {
      try {
        await api.delete(`/chat/history/${sessionId}`);
        toast.success('删除成功');
        loadSessions();
        if (selectedSessionId === sessionId) {
          setSelectedSessionId(null);
          setMessages([]);
        }
      } catch (error) {
        const message = error instanceof ApiError ? error.message : '删除失败';
        toast.error(message);
      }
    },
    [toast, loadSessions, selectedSessionId]
  );

  const clearAllSessions = useCallback(async () => {
    try {
      const data = await api.delete<DeleteResponse>('/chat/history');
      toast.success(`已清空 ${data.deleted_count || 0} 个会话`);
      setSessions([]);
      setSelectedSessionId(null);
      setMessages([]);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : '清空失败';
      toast.error(message);
    }
  }, [toast]);

  return {
    sessions,
    loading,
    selectedSessionId,
    messages,
    messagesLoading,
    loadSessions,
    loadSessionMessages,
    deleteSession,
    clearAllSessions,
    setSelectedSessionId,
  };
}
