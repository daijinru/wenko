import React, { useState, useEffect, useCallback } from 'react';
import {
  Tabs,
  Card,
  Button,
  Input,
  Checkbox,
  Tag,
  Alert,
  Modal,
  message,
  Spin,
  Space,
  Typography
} from 'antd';
import 'antd/dist/antd.css';
import './App.css';

const { TabPane } = Tabs;
const { TextArea } = Input;
const { Title, Text } = Typography;

const API_BASE = 'http://localhost:8002';

function App() {
  const [activeTab, setActiveTab] = useState('chatHistory');
  const [status, setStatus] = useState({ online: false, checking: true });

  // 聊天记录状态
  const [chatSessions, setChatSessions] = useState([]);
  const [chatSessionsLoading, setChatSessionsLoading] = useState(false);
  const [selectedSession, setSelectedSession] = useState(null);
  const [sessionMessages, setSessionMessages] = useState([]);
  const [sessionMessagesLoading, setSessionMessagesLoading] = useState(false);

  // 工作记忆状态
  const [workingMemories, setWorkingMemories] = useState([]);
  const [workingMemoriesLoading, setWorkingMemoriesLoading] = useState(false);
  const [selectedWorkingMemory, setSelectedWorkingMemory] = useState(null);
  const [transferDialogVisible, setTransferDialogVisible] = useState(false);
  const [transferForm, setTransferForm] = useState({
    category: 'fact',
    key: '',
    value: '',
    confidence: 0.8
  });
  // 工作记忆下探状态
  const [expandedWorkingMemory, setExpandedWorkingMemory] = useState(null);
  const [expandedMessages, setExpandedMessages] = useState([]);
  const [expandedMessagesLoading, setExpandedMessagesLoading] = useState(false);
  // 单条消息保存到长期记忆
  const [messageTransferDialogVisible, setMessageTransferDialogVisible] = useState(false);
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [messageTransferForm, setMessageTransferForm] = useState({
    category: 'fact',
    key: '',
    value: '',
    confidence: 0.8
  });

  // 长期记忆状态
  const [memories, setMemories] = useState([]);
  const [memoriesTotal, setMemoriesTotal] = useState(0);
  const [memoriesLoading, setMemoriesLoading] = useState(false);
  const [memoryFilter, setMemoryFilter] = useState({ category: '', search: '' });
  const [memoryDialogVisible, setMemoryDialogVisible] = useState(false);
  const [currentMemory, setCurrentMemory] = useState(null);
  const [memoryForm, setMemoryForm] = useState({
    category: 'fact',
    key: '',
    value: '',
    confidence: 0.9
  });
  const [selectedMemoryIds, setSelectedMemoryIds] = useState([]);

  // 检查服务状态
  const checkHealth = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/health`);
      await response.json();
      setStatus({ online: true, checking: false });
    } catch (error) {
      setStatus({ online: false, checking: false });
    }
  }, []);

  // 初始化
  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  // ============ 聊天记录相关函数 ============

  const loadChatSessions = async () => {
    setChatSessionsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/chat/history`);
      const data = await response.json();
      setChatSessions(data.sessions || []);
    } catch (error) {
      message.error(`加载聊天记录失败: ${error.message}`);
    } finally {
      setChatSessionsLoading(false);
    }
  };

  const viewSessionDetail = async (sessionId) => {
    setSelectedSession(sessionId);
    setSessionMessagesLoading(true);
    try {
      const response = await fetch(`${API_BASE}/chat/history/${sessionId}`);
      const data = await response.json();
      setSessionMessages(data.messages || []);
    } catch (error) {
      message.error(`加载会话详情失败: ${error.message}`);
      setSessionMessages([]);
    } finally {
      setSessionMessagesLoading(false);
    }
  };

  const deleteChatSession = async (sessionId) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个聊天会话吗？所有消息将被永久删除。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await fetch(`${API_BASE}/chat/history/${sessionId}`, {
            method: 'DELETE'
          });
          if (!response.ok) throw new Error('删除失败');
          message.success('删除成功');
          loadChatSessions();
          if (selectedSession === sessionId) {
            setSelectedSession(null);
            setSessionMessages([]);
          }
        } catch (error) {
          message.error(`删除失败: ${error.message}`);
        }
      }
    });
  };

  const clearAllChatHistory = async () => {
    Modal.confirm({
      title: '确认清空',
      content: '确定要清空所有聊天记录吗？此操作不可恢复！',
      okText: '清空全部',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await fetch(`${API_BASE}/chat/history`, { method: 'DELETE' });
          if (!response.ok) throw new Error('清空失败');
          const data = await response.json();
          message.success(`已清空 ${data.deleted_count || 0} 个会话`);
          setChatSessions([]);
          setSelectedSession(null);
          setSessionMessages([]);
        } catch (error) {
          message.error(`清空失败: ${error.message}`);
        }
      }
    });
  };

  const formatTime = (isoString) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // ============ 工作记忆相关函数 ============

  const loadWorkingMemories = async () => {
    setWorkingMemoriesLoading(true);
    try {
      const response = await fetch(`${API_BASE}/memory/working`);
      if (!response.ok) throw new Error('获取工作记忆列表失败');
      const data = await response.json();
      setWorkingMemories(data.memories || []);
    } catch (error) {
      message.error(error.message);
    } finally {
      setWorkingMemoriesLoading(false);
    }
  };

  const clearWorkingMemory = async (sessionId) => {
    Modal.confirm({
      title: '确认清除',
      content: '确定要清除这个会话的工作记忆吗？',
      okText: '清除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await fetch(`${API_BASE}/memory/working/${sessionId}`, {
            method: 'DELETE'
          });
          if (!response.ok) throw new Error('清除失败');
          message.success('工作记忆已清除');
          loadWorkingMemories();
          if (selectedWorkingMemory?.session_id === sessionId) {
            setSelectedWorkingMemory(null);
          }
        } catch (error) {
          message.error(`清除失败: ${error.message}`);
        }
      }
    });
  };

  const openTransferDialog = (workingMemory) => {
    setTransferForm({
      category: 'fact',
      key: workingMemory.current_topic ? 'topic_interest' : 'session_info',
      value: workingMemory.current_topic || JSON.stringify(workingMemory.context_variables, null, 2),
      confidence: 0.8
    });
    setSelectedWorkingMemory(workingMemory);
    setTransferDialogVisible(true);
  };

  const transferToLongTermMemory = async () => {
    if (!transferForm.key.trim()) {
      message.error('请输入记忆键名');
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/memory/long-term`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category: transferForm.category,
          key: transferForm.key,
          value: transferForm.value,
          confidence: transferForm.confidence,
          source: 'user_stated'
        })
      });
      if (!response.ok) throw new Error('保存失败');
      message.success('已保存到长期记忆');
      setTransferDialogVisible(false);
    } catch (error) {
      message.error(error.message);
    }
  };

  // 工作记忆下探 - 加载会话消息
  const toggleExpandWorkingMemory = async (sessionId) => {
    if (expandedWorkingMemory === sessionId) {
      // 收起
      setExpandedWorkingMemory(null);
      setExpandedMessages([]);
      return;
    }
    // 展开并加载消息
    setExpandedWorkingMemory(sessionId);
    setExpandedMessagesLoading(true);
    try {
      const response = await fetch(`${API_BASE}/chat/history/${sessionId}`);
      const data = await response.json();
      setExpandedMessages(data.messages || []);
    } catch (error) {
      message.error(`加载会话消息失败: ${error.message}`);
      setExpandedMessages([]);
    } finally {
      setExpandedMessagesLoading(false);
    }
  };

  // 打开单条消息保存到长期记忆对话框
  const openMessageTransferDialog = (msg) => {
    setSelectedMessage(msg);
    setMessageTransferForm({
      category: 'fact',
      key: msg.role === 'user' ? '用户输入' : 'AI回复',
      value: msg.content,
      confidence: 0.8
    });
    setMessageTransferDialogVisible(true);
  };

  // 保存单条消息到长期记忆
  const saveMessageToLongTermMemory = async () => {
    if (!messageTransferForm.key.trim()) {
      message.error('请输入记忆键名');
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/memory/long-term`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category: messageTransferForm.category,
          key: messageTransferForm.key,
          value: messageTransferForm.value,
          confidence: messageTransferForm.confidence,
          source: 'user_stated'
        })
      });
      if (!response.ok) throw new Error('保存失败');
      message.success('消息已保存到长期记忆');
      setMessageTransferDialogVisible(false);
      setSelectedMessage(null);
    } catch (error) {
      message.error(error.message);
    }
  };

  // ============ 长期记忆相关函数 ============

  const loadMemories = async (category = '') => {
    setMemoriesLoading(true);
    try {
      const params = new URLSearchParams();
      if (category) params.append('category', category);
      params.append('limit', '100');
      const response = await fetch(`${API_BASE}/memory/long-term?${params}`);
      if (!response.ok) throw new Error('获取记忆列表失败');
      const data = await response.json();
      setMemories(data.memories || []);
      setMemoriesTotal(data.total || 0);
    } catch (error) {
      message.error(error.message);
    } finally {
      setMemoriesLoading(false);
    }
  };

  const createMemory = async () => {
    try {
      const response = await fetch(`${API_BASE}/memory/long-term`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category: memoryForm.category,
          key: memoryForm.key,
          value: memoryForm.value,
          confidence: memoryForm.confidence,
          source: 'user_stated'
        })
      });
      if (!response.ok) throw new Error('创建记忆失败');
      message.success('记忆创建成功');
      setMemoryDialogVisible(false);
      loadMemories(memoryFilter.category);
    } catch (error) {
      message.error(error.message);
    }
  };

  const updateMemory = async () => {
    if (!currentMemory) return;
    try {
      const response = await fetch(`${API_BASE}/memory/long-term/${currentMemory.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category: memoryForm.category,
          key: memoryForm.key,
          value: memoryForm.value,
          confidence: memoryForm.confidence
        })
      });
      if (!response.ok) throw new Error('更新记忆失败');
      message.success('记忆更新成功');
      setMemoryDialogVisible(false);
      setCurrentMemory(null);
      loadMemories(memoryFilter.category);
    } catch (error) {
      message.error(error.message);
    }
  };

  const deleteMemory = (memoryId) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这条记忆吗？',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await fetch(`${API_BASE}/memory/long-term/${memoryId}`, {
            method: 'DELETE'
          });
          if (!response.ok) throw new Error('删除失败');
          message.success('记忆已删除');
          loadMemories(memoryFilter.category);
        } catch (error) {
          message.error(error.message);
        }
      }
    });
  };

  const batchDeleteMemories = () => {
    if (selectedMemoryIds.length === 0) {
      message.warning('请先选择要删除的记忆');
      return;
    }
    Modal.confirm({
      title: '确认批量删除',
      content: `确定要删除选中的 ${selectedMemoryIds.length} 条记忆吗？`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await fetch(`${API_BASE}/memory/long-term/batch-delete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids: selectedMemoryIds })
          });
          if (!response.ok) throw new Error('批量删除失败');
          const data = await response.json();
          message.success(`已删除 ${data.deleted_count} 条记忆`);
          setSelectedMemoryIds([]);
          loadMemories(memoryFilter.category);
        } catch (error) {
          message.error(error.message);
        }
      }
    });
  };

  const clearAllMemories = () => {
    Modal.confirm({
      title: '确认清空',
      content: '确定要清空所有长期记忆吗？此操作不可恢复！',
      okText: '清空全部',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await fetch(`${API_BASE}/memory/long-term`, { method: 'DELETE' });
          if (!response.ok) throw new Error('清空失败');
          const data = await response.json();
          message.success(`已清空 ${data.deleted_count} 条记忆`);
          setMemories([]);
          setMemoriesTotal(0);
        } catch (error) {
          message.error(error.message);
        }
      }
    });
  };

  const exportMemories = async () => {
    try {
      const response = await fetch(`${API_BASE}/memory/long-term/export`);
      if (!response.ok) throw new Error('导出失败');
      const data = await response.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `memories_${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      message.success('导出成功');
    } catch (error) {
      message.error(error.message);
    }
  };

  const openCreateMemoryDialog = () => {
    setCurrentMemory(null);
    setMemoryForm({ category: 'fact', key: '', value: '', confidence: 0.9 });
    setMemoryDialogVisible(true);
  };

  const openEditMemoryDialog = (memory) => {
    setCurrentMemory(memory);
    setMemoryForm({
      category: memory.category,
      key: memory.key,
      value: typeof memory.value === 'object' ? JSON.stringify(memory.value) : memory.value,
      confidence: memory.confidence
    });
    setMemoryDialogVisible(true);
  };

  const saveMemory = async () => {
    if (!memoryForm.key.trim()) {
      message.error('请输入记忆键名');
      return;
    }
    if (currentMemory) {
      await updateMemory();
    } else {
      await createMemory();
    }
  };

  const getCategoryColor = (category) => {
    switch (category) {
      case 'preference': return 'blue';
      case 'fact': return 'green';
      case 'pattern': return 'orange';
      default: return 'default';
    }
  };

  // ============ 聊天记录标签页 ============
  const ChatHistoryTab = () => (
    <div>
      <h4 className="classic-section-title">聊天记录</h4>
      <div className="classic-toolbar">
        <Button type="primary" size="small" onClick={loadChatSessions} loading={chatSessionsLoading}>
          刷新列表
        </Button>
        <Button size="small" danger onClick={clearAllChatHistory} disabled={chatSessions.length === 0}>
          清空所有记录
        </Button>
      </div>

      <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
        <div style={{ width: '40%', minWidth: '280px' }}>
          <h5 className="classic-section-title">会话列表</h5>
          <Spin spinning={chatSessionsLoading}>
            {chatSessions.length === 0 ? (
              <Alert message="暂无聊天记录" type="info" />
            ) : (
              <div className="classic-list" style={{ maxHeight: '450px' }}>
                {chatSessions.map(session => (
                  <div
                    key={session.id}
                    className={`classic-list-row ${selectedSession === session.id ? 'selected' : ''}`}
                    onClick={() => viewSessionDetail(session.id)}
                    style={{ display: 'block', padding: '8px' }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div style={{ flex: 1, overflow: 'hidden' }}>
                        <div style={{ fontWeight: 'bold', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {session.title || '(无标题)'}
                        </div>
                        <div style={{ fontSize: '10px', marginTop: '2px' }}>
                          <span>{formatTime(session.updated_at)}</span>
                          <Tag color="blue" style={{ marginLeft: '6px' }}>{session.message_count} 条</Tag>
                        </div>
                      </div>
                      <Button
                        size="small"
                        danger
                        onClick={(e) => { e.stopPropagation(); deleteChatSession(session.id); }}
                      >
                        删除
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Spin>
        </div>

        <div style={{ flex: 1, minWidth: '350px' }}>
          <h5 className="classic-section-title">消息详情</h5>
          <Spin spinning={sessionMessagesLoading}>
            {!selectedSession ? (
              <Alert message="请选择一个会话查看详情" type="info" />
            ) : sessionMessages.length === 0 ? (
              <Alert message="该会话暂无消息" type="info" />
            ) : (
              <div className="classic-inset" style={{ maxHeight: '450px', overflowY: 'auto' }}>
                {sessionMessages.map((msg, index) => (
                  <div
                    key={msg.id || index}
                    style={{
                      marginBottom: '8px',
                      padding: '6px 8px',
                      background: msg.role === 'user' ? '#e6f0ff' : '#e6ffe6',
                      borderLeft: `3px solid ${msg.role === 'user' ? '#3366cc' : '#339933'}`
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <Tag color={msg.role === 'user' ? 'blue' : 'green'}>
                        {msg.role === 'user' ? '用户' : 'AI'}
                      </Tag>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '10px', color: '#666' }}>{formatTime(msg.created_at)}</span>
                        <Button
                          size="small"
                          type="link"
                          style={{ fontSize: '10px', padding: 0 }}
                          onClick={() => openMessageTransferDialog(msg)}
                        >
                          保存为记忆
                        </Button>
                      </div>
                    </div>
                    <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: '12px' }}>
                      {msg.content}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Spin>
        </div>
      </div>
    </div>
  );

  // ============ 工作记忆标签页 ============
  const WorkingMemoryTab = () => (
    <div>
      <h4 className="classic-section-title">工作记忆</h4>
      <div className="classic-toolbar">
        <Button type="primary" size="small" onClick={loadWorkingMemories} loading={workingMemoriesLoading}>
          刷新列表
        </Button>
      </div>

      <Spin spinning={workingMemoriesLoading}>
        {workingMemories.length === 0 ? (
          <div className="working-memory-empty" style={{ marginTop: '12px' }}>
            <Alert message="暂无活跃会话" type="info" />
          </div>
        ) : (
          <div className="classic-list" style={{ maxHeight: '500px', marginTop: '12px' }}>
            {workingMemories.map(wm => (
              <div key={wm.session_id} className="memory-item">
                <div className="memory-item-header">
                  <Button
                    size="small"
                    type="text"
                    onClick={() => toggleExpandWorkingMemory(wm.session_id)}
                    style={{ padding: '0 4px', marginRight: '4px' }}
                  >
                    {expandedWorkingMemory === wm.session_id ? '▼' : '▶'}
                  </Button>
                  <span
                    className="memory-item-key"
                    style={{ cursor: 'pointer' }}
                    onClick={() => toggleExpandWorkingMemory(wm.session_id)}
                  >
                    会话: {wm.session_id.substring(0, 8)}...
                  </span>
                  {wm.last_emotion && <Tag color="cyan">{wm.last_emotion}</Tag>}
                  <Tag color="blue">轮次: {wm.turn_count}</Tag>
                  <div className="memory-item-actions">
                    <Button size="small" onClick={() => openTransferDialog(wm)}>
                      保存到长期记忆
                    </Button>
                    <Button size="small" danger onClick={() => clearWorkingMemory(wm.session_id)}>
                      清除
                    </Button>
                  </div>
                </div>

                <div className="working-memory-info" style={{ marginTop: '8px' }}>
                  <span className="working-memory-info-label">当前话题:</span>
                  <span className="working-memory-info-value">{wm.current_topic || '(无)'}</span>

                  <span className="working-memory-info-label">更新时间:</span>
                  <span className="working-memory-info-value">{formatTime(wm.updated_at)}</span>
                </div>

                {Object.keys(wm.context_variables || {}).length > 0 && (
                  <div style={{ marginTop: '8px' }}>
                    <span className="working-memory-info-label">上下文变量:</span>
                    <div className="memory-item-value">
                      {JSON.stringify(wm.context_variables, null, 2)}
                    </div>
                  </div>
                )}

                {/* 下探: 展开显示会话消息列表 */}
                {expandedWorkingMemory === wm.session_id && (
                  <div className="working-memory-drilldown" style={{ marginTop: '12px', paddingLeft: '20px' }}>
                    <div style={{ fontWeight: 'bold', marginBottom: '8px', fontSize: '11px', color: '#666' }}>
                      会话消息 (点击单条消息可保存到长期记忆)
                    </div>
                    <Spin spinning={expandedMessagesLoading}>
                      {expandedMessages.length === 0 ? (
                        <Alert message="该会话暂无消息" type="info" style={{ fontSize: '11px' }} />
                      ) : (
                        <div className="classic-inset" style={{ maxHeight: '300px', overflowY: 'auto' }}>
                          {expandedMessages.map((msg, index) => (
                            <div
                              key={msg.id || index}
                              className="drilldown-message"
                              style={{
                                marginBottom: '6px',
                                padding: '6px 8px',
                                background: msg.role === 'user' ? '#e6f0ff' : '#e6ffe6',
                                borderLeft: `3px solid ${msg.role === 'user' ? '#3366cc' : '#339933'}`,
                                cursor: 'pointer',
                                transition: 'background 0.2s'
                              }}
                              onClick={() => openMessageTransferDialog(msg)}
                              title="点击保存到长期记忆"
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                                <Tag color={msg.role === 'user' ? 'blue' : 'green'} style={{ fontSize: '10px' }}>
                                  {msg.role === 'user' ? '用户' : 'AI'}
                                </Tag>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                  <span style={{ fontSize: '10px', color: '#666' }}>{formatTime(msg.created_at)}</span>
                                  <Button
                                    size="small"
                                    type="link"
                                    style={{ fontSize: '10px', padding: 0 }}
                                    onClick={(e) => { e.stopPropagation(); openMessageTransferDialog(msg); }}
                                  >
                                    保存
                                  </Button>
                                </div>
                              </div>
                              <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: '11px' }}>
                                {msg.content.length > 200 ? msg.content.substring(0, 200) + '...' : msg.content}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </Spin>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Spin>
    </div>
  );

  // ============ 长期记忆标签页 ============
  const LongTermMemoryTab = () => (
    <div>
      <h4 className="classic-section-title">长期记忆</h4>
      <div className="classic-toolbar">
        <Button type="primary" size="small" onClick={() => loadMemories(memoryFilter.category)} loading={memoriesLoading}>
          刷新列表
        </Button>
        <Button size="small" onClick={openCreateMemoryDialog}>添加记忆</Button>
        <Button size="small" onClick={exportMemories}>导出 JSON</Button>
        <div className="classic-toolbar-separator" />
        <Button size="small" danger onClick={batchDeleteMemories} disabled={selectedMemoryIds.length === 0}>
          批量删除 ({selectedMemoryIds.length})
        </Button>
        <Button size="small" danger onClick={clearAllMemories} disabled={memories.length === 0}>
          清空所有
        </Button>
      </div>

      <div className="classic-filter-bar">
        <span className="classic-filter-label">类别:</span>
        <div className="classic-filter-buttons">
          {[
            { key: '', label: '全部' },
            { key: 'preference', label: '偏好' },
            { key: 'fact', label: '事实' },
            { key: 'pattern', label: '模式' }
          ].map(item => (
            <button
              key={item.key}
              className={`classic-filter-button ${memoryFilter.category === item.key ? 'active' : ''}`}
              onClick={() => {
                setMemoryFilter(prev => ({ ...prev, category: item.key }));
                loadMemories(item.key);
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
        <span style={{ marginLeft: 'auto', fontSize: '11px', color: '#666' }}>
          共 {memoriesTotal} 条记忆
        </span>
      </div>

      <Spin spinning={memoriesLoading}>
        {memories.length === 0 ? (
          <Alert message="暂无记忆数据" type="info" />
        ) : (
          <div className="classic-list" style={{ maxHeight: '400px' }}>
            {memories.map(memory => (
              <div key={memory.id} className="memory-item">
                <div className="memory-item-header">
                  <Checkbox
                    checked={selectedMemoryIds.includes(memory.id)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedMemoryIds(prev => [...prev, memory.id]);
                      } else {
                        setSelectedMemoryIds(prev => prev.filter(id => id !== memory.id));
                      }
                    }}
                  />
                  <Tag color={getCategoryColor(memory.category)}>{memory.category}</Tag>
                  <span className="memory-item-key">{memory.key}</span>
                  <Tag color="cyan">置信度: {Math.round(memory.confidence * 100)}%</Tag>
                  <span className="classic-tag classic-tag-info">{memory.source}</span>
                  <div className="memory-item-actions">
                    <Button size="small" onClick={() => openEditMemoryDialog(memory)}>编辑</Button>
                    <Button size="small" danger onClick={() => deleteMemory(memory.id)}>删除</Button>
                  </div>
                </div>
                <div className="memory-item-value">
                  {typeof memory.value === 'object' ? JSON.stringify(memory.value, null, 2) : memory.value}
                </div>
                <div className="memory-item-meta">
                  <span>访问 {memory.access_count} 次</span>
                  <span>创建: {formatTime(memory.created_at)}</span>
                  <span>最后访问: {formatTime(memory.last_accessed)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Spin>
    </div>
  );

  return (
    <div className="app-container">
      <div className="app-header">
        <h1>Emotion & Memory System</h1>
        <Space>
          <span className={`status-indicator ${status.online ? '' : 'offline'}`}></span>
          <span style={{ fontSize: '11px' }}>
            {status.checking ? '检查中...' : (status.online ? '在线' : '离线')}
          </span>
        </Space>
      </div>
      <div className="app-content">
        <Tabs activeKey={activeTab} onChange={(key) => {
          setActiveTab(key);
          if (key === 'chatHistory' && chatSessions.length === 0) {
            loadChatSessions();
          }
          if (key === 'workingMemory' && workingMemories.length === 0) {
            loadWorkingMemories();
          }
          if (key === 'longTermMemory' && memories.length === 0) {
            loadMemories('');
          }
        }}>
          <TabPane tab="聊天历史" key="chatHistory">
            <ChatHistoryTab />
          </TabPane>
          <TabPane tab="工作记忆" key="workingMemory">
            <WorkingMemoryTab />
          </TabPane>
          <TabPane tab="长期记忆" key="longTermMemory">
            <LongTermMemoryTab />
          </TabPane>
        </Tabs>
      </div>

      {/* 创建/编辑长期记忆对话框 */}
      <Modal
        title={currentMemory ? '编辑记忆' : '添加记忆'}
        visible={memoryDialogVisible}
        destroyOnClose={false}
        maskClosable={false}
        onOk={saveMemory}
        onCancel={() => { setMemoryDialogVisible(false); setCurrentMemory(null); }}
        width={500}
        okText="保存"
        cancelText="取消"
      >
        <div className="classic-field-group">
          <label className="classic-field-label">类别</label>
          <Space>
            {['preference', 'fact', 'pattern'].map(cat => (
              <Button
                key={cat}
                type={memoryForm.category === cat ? 'primary' : 'default'}
                size="small"
                onClick={() => setMemoryForm(prev => ({ ...prev, category: cat }))}
              >
                {cat === 'preference' ? '偏好' : cat === 'fact' ? '事实' : '模式'}
              </Button>
            ))}
          </Space>
        </div>
        <div className="classic-field-group">
          <label className="classic-field-label">键名 (Key)</label>
          <Input
            value={memoryForm.key}
            onChange={(e) => setMemoryForm(prev => ({ ...prev, key: e.target.value }))}
            placeholder="例如: preferred_language, name"
          />
        </div>
        <div className="classic-field-group">
          <label className="classic-field-label">值 (Value)</label>
          <TextArea
            value={memoryForm.value}
            onChange={(e) => setMemoryForm(prev => ({ ...prev, value: e.target.value }))}
            placeholder="输入记忆内容"
            rows={3}
          />
        </div>
        <div className="classic-field-group">
          <label className="classic-field-label">置信度: {Math.round(memoryForm.confidence * 100)}%</label>
          <input
            type="range"
            min="0"
            max="100"
            value={memoryForm.confidence * 100}
            onChange={(e) => setMemoryForm(prev => ({ ...prev, confidence: parseInt(e.target.value) / 100 }))}
            style={{ width: '100%' }}
          />
        </div>
      </Modal>

      {/* 工作记忆转存对话框 */}
      <Modal
        title="保存到长期记忆"
        visible={transferDialogVisible}
        destroyOnClose={false}
        maskClosable={false}
        onOk={transferToLongTermMemory}
        onCancel={() => setTransferDialogVisible(false)}
        width={500}
        okText="保存"
        cancelText="取消"
      >
        <div className="classic-field-group">
          <label className="classic-field-label">类别</label>
          <Space>
            {['preference', 'fact', 'pattern'].map(cat => (
              <Button
                key={cat}
                type={transferForm.category === cat ? 'primary' : 'default'}
                size="small"
                onClick={() => setTransferForm(prev => ({ ...prev, category: cat }))}
              >
                {cat === 'preference' ? '偏好' : cat === 'fact' ? '事实' : '模式'}
              </Button>
            ))}
          </Space>
        </div>
        <div className="classic-field-group">
          <label className="classic-field-label">键名 (Key)</label>
          <Input
            value={transferForm.key}
            onChange={(e) => setTransferForm(prev => ({ ...prev, key: e.target.value }))}
            placeholder="例如: topic_interest"
          />
        </div>
        <div className="classic-field-group">
          <label className="classic-field-label">值 (Value)</label>
          <TextArea
            value={transferForm.value}
            onChange={(e) => setTransferForm(prev => ({ ...prev, value: e.target.value }))}
            rows={4}
          />
        </div>
        <div className="classic-field-group">
          <label className="classic-field-label">置信度: {Math.round(transferForm.confidence * 100)}%</label>
          <input
            type="range"
            min="0"
            max="100"
            value={transferForm.confidence * 100}
            onChange={(e) => setTransferForm(prev => ({ ...prev, confidence: parseInt(e.target.value) / 100 }))}
            style={{ width: '100%' }}
          />
        </div>
      </Modal>

      {/* 单条消息保存到长期记忆对话框 */}
      <Modal
        title="保存消息到长期记忆"
        visible={messageTransferDialogVisible}
        destroyOnClose={false}
        maskClosable={false}
        onOk={saveMessageToLongTermMemory}
        onCancel={() => { setMessageTransferDialogVisible(false); setSelectedMessage(null); }}
        width={500}
        okText="保存"
        cancelText="取消"
      >
        {selectedMessage && (
          <div style={{ marginBottom: '12px', padding: '8px', background: '#f5f5f5', borderRadius: '4px' }}>
            <Tag color={selectedMessage.role === 'user' ? 'blue' : 'green'}>
              {selectedMessage.role === 'user' ? '用户消息' : 'AI回复'}
            </Tag>
            <span style={{ fontSize: '10px', color: '#666', marginLeft: '8px' }}>
              {formatTime(selectedMessage.created_at)}
            </span>
          </div>
        )}
        <div className="classic-field-group">
          <label className="classic-field-label">类别</label>
          <Space>
            {['preference', 'fact', 'pattern'].map(cat => (
              <Button
                key={cat}
                type={messageTransferForm.category === cat ? 'primary' : 'default'}
                size="small"
                onClick={() => setMessageTransferForm(prev => ({ ...prev, category: cat }))}
              >
                {cat === 'preference' ? '偏好' : cat === 'fact' ? '事实' : '模式'}
              </Button>
            ))}
          </Space>
        </div>
        <div className="classic-field-group">
          <label className="classic-field-label">键名 (Key)</label>
          <Input
            value={messageTransferForm.key}
            onChange={(e) => setMessageTransferForm(prev => ({ ...prev, key: e.target.value }))}
            placeholder="例如: 用户偏好, 重要事实"
          />
        </div>
        <div className="classic-field-group">
          <label className="classic-field-label">值 (Value)</label>
          <TextArea
            value={messageTransferForm.value}
            onChange={(e) => setMessageTransferForm(prev => ({ ...prev, value: e.target.value }))}
            rows={4}
          />
        </div>
        <div className="classic-field-group">
          <label className="classic-field-label">置信度: {Math.round(messageTransferForm.confidence * 100)}%</label>
          <input
            type="range"
            min="0"
            max="100"
            value={messageTransferForm.confidence * 100}
            onChange={(e) => setMessageTransferForm(prev => ({ ...prev, confidence: parseInt(e.target.value) / 100 }))}
            style={{ width: '100%' }}
          />
        </div>
      </Modal>
    </div>
  );
}

export default App;
