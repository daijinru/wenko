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
import 'antd/dist/antd.css'; // Import Antd CSS
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

  // 记忆管理状态
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

  // 加载聊天会话列表
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

  // 查看会话详情
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

  // 删除单个会话
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

          if (!response.ok) {
            throw new Error('删除失败');
          }

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

  // 清空所有聊天记录
  const clearAllChatHistory = async () => {
    Modal.confirm({
      title: '确认清空',
      content: '确定要清空所有聊天记录吗？此操作不可恢复！',
      okText: '清空全部',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await fetch(`${API_BASE}/chat/history`, {
            method: 'DELETE'
          });

          if (!response.ok) {
            throw new Error('清空失败');
          }

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

  // 格式化时间
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

  // ============ 记忆管理函数 ============

  // 加载记忆列表
  const loadMemories = async (category = '') => {
    setMemoriesLoading(true);
    try {
      const params = new URLSearchParams();
      if (category) params.append('category', category);
      params.append('limit', '100');

      const response = await fetch(`${API_BASE}/memory/long-term?${params}`);
      if (!response.ok) {
        throw new Error('获取记忆列表失败');
      }
      const data = await response.json();
      setMemories(data.memories || []);
      setMemoriesTotal(data.total || 0);
    } catch (error) {
      message.error(error.message);
    } finally {
      setMemoriesLoading(false);
    }
  };

  // 创建记忆
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

      if (!response.ok) {
        throw new Error('创建记忆失败');
      }

      message.success('记忆创建成功');
      setMemoryDialogVisible(false);
      loadMemories(memoryFilter.category);
    } catch (error) {
      message.error(error.message);
    }
  };

  // 更新记忆
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

      if (!response.ok) {
        throw new Error('更新记忆失败');
      }

      message.success('记忆更新成功');
      setMemoryDialogVisible(false);
      setCurrentMemory(null);
      loadMemories(memoryFilter.category);
    } catch (error) {
      message.error(error.message);
    }
  };

  // 删除单条记忆
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

          if (!response.ok) {
            throw new Error('删除失败');
          }

          message.success('记忆已删除');
          loadMemories(memoryFilter.category);
        } catch (error) {
          message.error(error.message);
        }
      }
    });
  };

  // 批量删除记忆
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

          if (!response.ok) {
            throw new Error('批量删除失败');
          }

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

  // 清空所有记忆
  const clearAllMemories = () => {
    Modal.confirm({
      title: '确认清空',
      content: '确定要清空所有长期记忆吗？此操作不可恢复！',
      okText: '清空全部',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await fetch(`${API_BASE}/memory/long-term`, {
            method: 'DELETE'
          });

          if (!response.ok) {
            throw new Error('清空失败');
          }

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

  // 导出记忆
  const exportMemories = async () => {
    try {
      const response = await fetch(`${API_BASE}/memory/long-term/export`);
      if (!response.ok) {
        throw new Error('导出失败');
      }

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

  // 打开创建记忆对话框
  const openCreateMemoryDialog = () => {
    setCurrentMemory(null);
    setMemoryForm({
      category: 'fact',
      key: '',
      value: '',
      confidence: 0.9
    });
    setMemoryDialogVisible(true);
  };

  // 打开编辑记忆对话框
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

  // 保存记忆（创建或更新）
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

  // 获取类别标签颜色
  const getCategoryColor = (category) => {
    switch (category) {
      case 'preference': return 'blue';
      case 'fact': return 'green';
      case 'pattern': return 'orange';
      default: return 'default';
    }
  };

  // 聊天记录标签页
  const ChatHistoryTab = () => (
    <div>
      <Title level={4}>聊天记录</Title>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Space>
          <Button type="primary" onClick={loadChatSessions} loading={chatSessionsLoading}>
            刷新列表
          </Button>
          <Button danger onClick={clearAllChatHistory} disabled={chatSessions.length === 0}>
            清空所有记录
          </Button>
        </Space>

        <div style={{ display: 'flex', gap: '16px' }}>
          {/* 会话列表 */}
          <div style={{ width: '40%', minWidth: '300px' }}>
            <Title level={5}>会话列表</Title>
            <Spin spinning={chatSessionsLoading}>
              {chatSessions.length === 0 ? (
                <Alert message="暂无聊天记录" type="info" />
              ) : (
                <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
                  {chatSessions.map(session => (
                    <Card
                      key={session.id}
                      size="small"
                      style={{
                        marginBottom: '8px',
                        cursor: 'pointer',
                        borderColor: selectedSession === session.id ? '#1890ff' : undefined,
                        backgroundColor: selectedSession === session.id ? '#e6f7ff' : undefined
                      }}
                      onClick={() => viewSessionDetail(session.id)}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div style={{ flex: 1, overflow: 'hidden' }}>
                          <Text strong style={{
                            display: 'block',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis'
                          }}>
                            {session.title || '(无标题)'}
                          </Text>
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            {formatTime(session.updated_at)}
                          </Text>
                          <Tag color="blue" style={{ marginLeft: '8px' }}>
                            {session.message_count} 条消息
                          </Tag>
                        </div>
                        <Button
                          size="small"
                          danger
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteChatSession(session.id);
                          }}
                        >
                          删除
                        </Button>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </Spin>
          </div>

          {/* 消息详情 */}
          <div style={{ flex: 1, minWidth: '400px' }}>
            <Title level={5}>消息详情</Title>
            <Spin spinning={sessionMessagesLoading}>
              {!selectedSession ? (
                <Alert message="请选择一个会话查看详情" type="info" />
              ) : sessionMessages.length === 0 ? (
                <Alert message="该会话暂无消息" type="info" />
              ) : (
                <div style={{
                  maxHeight: '500px',
                  overflowY: 'auto',
                  padding: '12px',
                  backgroundColor: '#fafafa',
                  borderRadius: '4px'
                }}>
                  {sessionMessages.map((msg, index) => (
                    <div
                      key={msg.id || index}
                      style={{
                        marginBottom: '12px',
                        padding: '8px 12px',
                        borderRadius: '8px',
                        backgroundColor: msg.role === 'user' ? '#e6f7ff' : '#f6ffed',
                        borderLeft: `3px solid ${msg.role === 'user' ? '#1890ff' : '#52c41a'}`
                      }}
                    >
                      <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        marginBottom: '4px'
                      }}>
                        <Tag color={msg.role === 'user' ? 'blue' : 'green'}>
                          {msg.role === 'user' ? '用户' : 'AI'}
                        </Tag>
                        <Text type="secondary" style={{ fontSize: '11px' }}>
                          {formatTime(msg.created_at)}
                        </Text>
                      </div>
                      <div style={{
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        fontSize: '14px'
                      }}>
                        {msg.content}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Spin>
          </div>
        </div>
      </Space>
    </div>
  );

  // 记忆管理标签页
  const MemoryTab = () => (
    <div>
      <Title level={4}>记忆管理</Title>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 工具栏 */}
        <Space wrap>
          <Button type="primary" onClick={() => loadMemories(memoryFilter.category)} loading={memoriesLoading}>
            刷新列表
          </Button>
          <Button onClick={openCreateMemoryDialog}>
            添加记忆
          </Button>
          <Button onClick={exportMemories}>
            导出 JSON
          </Button>
          <Button danger onClick={batchDeleteMemories} disabled={selectedMemoryIds.length === 0}>
            批量删除 ({selectedMemoryIds.length})
          </Button>
          <Button danger onClick={clearAllMemories} disabled={memories.length === 0}>
            清空所有
          </Button>
        </Space>

        {/* 筛选器 */}
        <Space>
          <Text>类别筛选:</Text>
          <Button
            type={memoryFilter.category === '' ? 'primary' : 'default'}
            size="small"
            onClick={() => {
              setMemoryFilter(prev => ({ ...prev, category: '' }));
              loadMemories('');
            }}
          >
            全部
          </Button>
          <Button
            type={memoryFilter.category === 'preference' ? 'primary' : 'default'}
            size="small"
            onClick={() => {
              setMemoryFilter(prev => ({ ...prev, category: 'preference' }));
              loadMemories('preference');
            }}
          >
            偏好
          </Button>
          <Button
            type={memoryFilter.category === 'fact' ? 'primary' : 'default'}
            size="small"
            onClick={() => {
              setMemoryFilter(prev => ({ ...prev, category: 'fact' }));
              loadMemories('fact');
            }}
          >
            事实
          </Button>
          <Button
            type={memoryFilter.category === 'pattern' ? 'primary' : 'default'}
            size="small"
            onClick={() => {
              setMemoryFilter(prev => ({ ...prev, category: 'pattern' }));
              loadMemories('pattern');
            }}
          >
            模式
          </Button>
          <Text type="secondary" style={{ marginLeft: '16px' }}>
            共 {memoriesTotal} 条记忆
          </Text>
        </Space>

        {/* 记忆列表 */}
        <Spin spinning={memoriesLoading}>
          {memories.length === 0 ? (
            <Alert message="暂无记忆数据" type="info" />
          ) : (
            <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
              {memories.map(memory => (
                <Card
                  key={memory.id}
                  size="small"
                  style={{ marginBottom: '8px' }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <Checkbox
                      checked={selectedMemoryIds.includes(memory.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedMemoryIds(prev => [...prev, memory.id]);
                        } else {
                          setSelectedMemoryIds(prev => prev.filter(id => id !== memory.id));
                        }
                      }}
                      style={{ marginRight: '12px', marginTop: '4px' }}
                    />
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                        <Tag color={getCategoryColor(memory.category)}>{memory.category}</Tag>
                        <Text strong>{memory.key}</Text>
                        <Tag color="cyan">置信度: {Math.round(memory.confidence * 100)}%</Tag>
                        <Tag>{memory.source}</Tag>
                      </div>
                      <div style={{
                        padding: '8px',
                        backgroundColor: '#f5f5f5',
                        borderRadius: '4px',
                        marginBottom: '4px'
                      }}>
                        <Text style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                          {typeof memory.value === 'object' ? JSON.stringify(memory.value, null, 2) : memory.value}
                        </Text>
                      </div>
                      <Space size="small">
                        <Text type="secondary" style={{ fontSize: '11px' }}>
                          访问 {memory.access_count} 次
                        </Text>
                        <Text type="secondary" style={{ fontSize: '11px' }}>
                          创建: {formatTime(memory.created_at)}
                        </Text>
                        <Text type="secondary" style={{ fontSize: '11px' }}>
                          最后访问: {formatTime(memory.last_accessed)}
                        </Text>
                      </Space>
                    </div>
                    <Space>
                      <Button size="small" onClick={() => openEditMemoryDialog(memory)}>
                        编辑
                      </Button>
                      <Button size="small" danger onClick={() => deleteMemory(memory.id)}>
                        删除
                      </Button>
                    </Space>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </Spin>
      </Space>
    </div>
  );

  return (
    <div className="app-container">
      <div className="app-header">
        <h1>Emotion & Memory System</h1>
        <Space>
          <span className={`status-indicator ${status.online ? '' : 'offline'}`}></span>
          <Text style={{ color: 'white' }}>
            {status.checking ? '检查中...' : (status.online ? '在线' : '离线')}
          </Text>
        </Space>
      </div>
      <div className="app-content">
        <Tabs activeKey={activeTab} onChange={(key) => {
          setActiveTab(key);
          // 切换到聊天记录 Tab 时自动加载数据
          if (key === 'chatHistory' && chatSessions.length === 0) {
            loadChatSessions();
          }
          // 切换到记忆管理 Tab 时自动加载数据
          if (key === 'memory' && memories.length === 0) {
            loadMemories('');
          }
        }}>
          <TabPane tab="聊天记录" key="chatHistory">
            <ChatHistoryTab />
          </TabPane>
          <TabPane tab="记忆管理" key="memory">
            <MemoryTab />
          </TabPane>
        </Tabs>
      </div>

      {/* 创建/编辑记忆对话框 */}
      <Modal
        title={currentMemory ? '编辑记忆' : '添加记忆'}
        visible={memoryDialogVisible}
        destroyOnClose={false}
        maskClosable={false}
        onOk={saveMemory}
        onCancel={() => {
          setMemoryDialogVisible(false);
          setCurrentMemory(null);
        }}
        width={600}
        okText="保存"
        cancelText="取消"
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Text strong>类别</Text>
            <div style={{ marginTop: '8px' }}>
              <Button
                type={memoryForm.category === 'preference' ? 'primary' : 'default'}
                onClick={() => setMemoryForm(prev => ({ ...prev, category: 'preference' }))}
                style={{ marginRight: '8px' }}
              >
                偏好 (preference)
              </Button>
              <Button
                type={memoryForm.category === 'fact' ? 'primary' : 'default'}
                onClick={() => setMemoryForm(prev => ({ ...prev, category: 'fact' }))}
                style={{ marginRight: '8px' }}
              >
                事实 (fact)
              </Button>
              <Button
                type={memoryForm.category === 'pattern' ? 'primary' : 'default'}
                onClick={() => setMemoryForm(prev => ({ ...prev, category: 'pattern' }))}
              >
                模式 (pattern)
              </Button>
            </div>
          </div>
          <div>
            <Text strong>键名 (Key)</Text>
            <Input
              value={memoryForm.key}
              onChange={(e) => setMemoryForm(prev => ({ ...prev, key: e.target.value }))}
              placeholder="例如: preferred_language, name, coding_style"
            />
          </div>
          <div>
            <Text strong>值 (Value)</Text>
            <TextArea
              value={memoryForm.value}
              onChange={(e) => setMemoryForm(prev => ({ ...prev, value: e.target.value }))}
              placeholder="输入记忆内容"
              rows={4}
            />
          </div>
          <div>
            <Text strong>置信度: {Math.round(memoryForm.confidence * 100)}%</Text>
            <Input
              type="range"
              min="0"
              max="100"
              value={memoryForm.confidence * 100}
              onChange={(e) => setMemoryForm(prev => ({ ...prev, confidence: parseInt(e.target.value) / 100 }))}
              style={{ width: '100%' }}
            />
          </div>
        </Space>
      </Modal>
    </div>
  );
}

export default App;
