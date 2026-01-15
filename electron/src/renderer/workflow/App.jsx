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
  Divider,
  Space,
  Typography
} from 'antd';
import 'antd/dist/antd.css'; // Import Antd CSS
import './App.css';

const { TabPane } = Tabs;
const { TextArea } = Input;
const { Title, Text, Paragraph } = Typography;

const API_BASE = 'http://localhost:8002';

function App() {
  const [activeTab, setActiveTab] = useState('workflow');
  const [status, setStatus] = useState({ online: false, checking: true });
  
  // 工作流执行状态
  const [workflowSteps, setWorkflowSteps] = useState('');
  const [workflowContext, setWorkflowContext] = useState('');
  const [debugMode, setDebugMode] = useState(false);
  const [workflowResult, setWorkflowResult] = useState(null);
  const [workflowLoading, setWorkflowLoading] = useState(false);
  
  // 模板管理状态
  const [templates, setTemplates] = useState([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [templateDialogVisible, setTemplateDialogVisible] = useState(false);
  const [currentTemplate, setCurrentTemplate] = useState(null);
  const [templateForm, setTemplateForm] = useState({
    name: '',
    description: '',
    tags: '',
    steps: ''
  });
  
  // 使用 useCallback 稳定表单更新函数，避免 Modal 重新渲染
  const updateTemplateForm = useCallback((field, value) => {
    setTemplateForm(prev => ({ ...prev, [field]: value }));
  }, []);
  
  // 步骤注册表状态
  const [steps, setSteps] = useState({});
  const [stepsLoading, setStepsLoading] = useState(false);
  
  // 健康检查状态
  const [healthResult, setHealthResult] = useState(null);

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
      const data = await response.json();
      setStatus({ online: true, checking: false });
      setHealthResult(data);
    } catch (error) {
      setStatus({ online: false, checking: false });
      setHealthResult({ error: error.message });
    }
  }, []);

  // 初始化
  useEffect(() => {
    checkHealth();
    loadSteps();
    loadTemplates();
  }, [checkHealth]);

  // 执行工作流
  const executeWorkflow = async () => {
    if (!workflowSteps.trim()) {
      message.error('请输入工作流步骤');
      return;
    }

    setWorkflowLoading(true);
    try {
      const steps = JSON.parse(workflowSteps);
      const initial_context = workflowContext.trim() ? JSON.parse(workflowContext) : {};

      const response = await fetch(`${API_BASE}/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          steps,
          initial_context,
          debug_mode: debugMode
        })
      });

      const data = await response.json();
      setWorkflowResult(data);
      if (data.success) {
        message.success('工作流执行成功');
      } else {
        message.error('工作流执行失败');
      }
    } catch (error) {
      setWorkflowResult({ error: error.message });
      message.error(`执行失败: ${error.message}`);
    } finally {
      setWorkflowLoading(false);
    }
  };

  // 加载示例
  const loadExample = () => {
    const example = [
      {
        "type": "EchoInput",
        "params": {
          "message": "Hello, World!"
        }
      },
      {
        "type": "SetVar",
        "params": {
          "key": "greeting",
          "value": "Welcome to LangGraph Workflow!"
        }
      },
      {
        "type": "GetVar",
        "params": {
          "key": "greeting"
        }
      }
    ];
    
    setWorkflowSteps(JSON.stringify(example, null, 2));
    setWorkflowContext(JSON.stringify({test: "value"}, null, 2));
  };

  // 清空工作流
  const clearWorkflow = () => {
    setWorkflowSteps('');
    setWorkflowContext('');
    setWorkflowResult(null);
  };

  // 加载模板列表
  const loadTemplates = async () => {
    setTemplatesLoading(true);
    try {
      const response = await fetch(`${API_BASE}/templates`);
      const data = await response.json();
      setTemplates(data.templates || []);
    } catch (error) {
      message.error(`加载模板失败: ${error.message}`);
    } finally {
      setTemplatesLoading(false);
    }
  };

  // 搜索模板
  const searchTemplates = async () => {
    if (!searchQuery.trim()) {
      loadTemplates();
      return;
    }

    setTemplatesLoading(true);
    try {
      const response = await fetch(`${API_BASE}/templates/search/${encodeURIComponent(searchQuery)}`);
      const data = await response.json();
      setTemplates(data.templates || []);
    } catch (error) {
      message.error(`搜索失败: ${error.message}`);
    } finally {
      setTemplatesLoading(false);
    }
  };

  // 查看模板
  const viewTemplate = async (templateId) => {
    try {
      const response = await fetch(`${API_BASE}/templates/${templateId}`);
      const data = await response.json();
      const template = data.template;
      
      Modal.info({
        title: template.name,
        width: 600,
        content: (
          <div>
            <Paragraph><Text strong>描述:</Text> {template.description || '无'}</Paragraph>
            <Paragraph>
              <Text strong>标签:</Text>{' '}
              {template.tags && template.tags.length > 0 
                ? template.tags.map(tag => <Tag key={tag}>{tag}</Tag>)
                : '无'}
            </Paragraph>
            <Divider />
            <Paragraph><Text strong>步骤:</Text></Paragraph>
            <pre style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px', overflow: 'auto' }}>
              {JSON.stringify(template.steps, null, 2)}
            </pre>
          </div>
        )
      });
    } catch (error) {
      message.error(`查看模板失败: ${error.message}`);
    }
  };

  // 分析模板步骤，推断需要的初始上下文
  const analyzeTemplateContext = (steps) => {
    const contextVars = {};
    
    steps.forEach(step => {
      const stepType = step.type;
      const params = step.params || {};
      
      // 根据步骤类型分析需要的上下文变量
      switch (stepType) {
        case 'GetVar':
          if (params.key) {
            contextVars[params.key] = 'value'; // 示例值
          }
          break;
        case 'MathOp':
          if (params.operand1_key) {
            contextVars[params.operand1_key] = 10; // 示例数字
          }
          if (params.operand2_key) {
            contextVars[params.operand2_key] = 5; // 示例数字
          }
          break;
        case 'If':
          if (params.condition_key) {
            contextVars[params.condition_key] = true; // 示例布尔值
          }
          break;
        case 'StringOp':
          if (params.input_key) {
            contextVars[params.input_key] = 'example text'; // 示例字符串
          }
          break;
        case 'EchoInput':
          if (params.input_key) {
            contextVars[params.input_key] = 'input value'; // 示例值
          }
          break;
        case 'TemplateReplace':
          if (params.template_key) {
            contextVars[params.template_key] = 'Hello {{name}}'; // 示例模板
          }
          // 分析模板中的占位符
          const template = params.template || '';
          const placeholders = template.match(/\{\{([^}]+)\}\}/g);
          if (placeholders) {
            placeholders.forEach(ph => {
              const varName = ph.replace(/\{\{|\}\}/g, '').trim();
              if (!contextVars[varName]) {
                contextVars[varName] = 'value'; // 示例值
              }
            });
          }
          break;
        case 'JSONExtractValues':
          if (params.json_key) {
            contextVars[params.json_key] = '{"key": "value"}'; // 示例JSON字符串
          }
          break;
      }
    });
    
    // 如果没有找到任何需要的变量，返回空对象
    return Object.keys(contextVars).length > 0 ? contextVars : {};
  };

  // 执行模板
  const executeTemplate = async (templateId) => {
    // 先获取模板信息
    let template = null;
    try {
      const response = await fetch(`${API_BASE}/templates/${templateId}`);
      const data = await response.json();
      template = data.template;
    } catch (error) {
      message.error(`获取模板失败: ${error.message}`);
      return;
    }
    
    // 分析模板需要的初始上下文
    const suggestedContext = analyzeTemplateContext(template.steps || []);
    const defaultContextValue = JSON.stringify(suggestedContext, null, 2);
    
    let currentContextValue = defaultContextValue;
    let contextError = '';
    let isValidJson = true;
    
    // 创建模态框内容
    const modalContent = (
      <div>
        <Alert
          message="请提供初始上下文"
          description={`执行模板 "${template.name}" 需要提供初始上下文（JSON格式）。已根据模板步骤自动推断出建议的上下文变量。`}
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Paragraph>
          <Text strong>初始上下文 (JSON格式) <span style={{ color: '#ff4d4f' }}>*</span>:</Text>
        </Paragraph>
        <TextArea 
          id="templateContext"
          rows={10}
          placeholder='{"key": "value", "number": 123}'
          defaultValue={defaultContextValue}
          onChange={(e) => {
            const value = e.target.value;
            currentContextValue = value;
            
            // 验证 JSON 格式
            if (value.trim()) {
              try {
                JSON.parse(value);
                contextError = '';
                isValidJson = true;
                // 清除错误显示
                const errorEl = document.getElementById('templateContextError');
                if (errorEl) {
                  errorEl.style.display = 'none';
                }
                // 清除边框颜色
                e.target.style.borderColor = '';
              } catch (err) {
                contextError = 'JSON 格式错误: ' + err.message;
                isValidJson = false;
                // 显示错误
                let errorEl = document.getElementById('templateContextError');
                if (!errorEl) {
                  errorEl = document.createElement('p');
                  errorEl.id = 'templateContextError';
                  errorEl.style.color = '#ff4d4f';
                  errorEl.style.marginTop = '8px';
                  errorEl.style.marginBottom = '0px';
                  e.target.parentNode.appendChild(errorEl);
                }
                errorEl.textContent = contextError;
                errorEl.style.display = 'block';
                // 设置边框颜色
                e.target.style.borderColor = '#ff4d4f';
              }
            } else {
              contextError = '请输入初始上下文（不能为空）';
              isValidJson = false;
              let errorEl = document.getElementById('templateContextError');
                if (!errorEl) {
                  errorEl = document.createElement('p');
                errorEl.id = 'templateContextError';
                errorEl.style.color = '#ff4d4f';
                errorEl.style.marginTop = '8px';
                errorEl.style.marginBottom = '0px';
                e.target.parentNode.appendChild(errorEl);
              }
              errorEl.textContent = contextError;
              errorEl.style.display = 'block';
              e.target.style.borderColor = '#ff4d4f';
            }
          }}
          style={{ 
            fontFamily: 'Monaco, Menlo, Courier New, monospace'
          }}
        />
        <Paragraph style={{ color: '#8c8c8c', fontSize: '12px', marginTop: 8, marginBottom: 0 }}>
          <Text strong>提示:</Text> 请输入有效的 JSON 对象来初始化工作流的上下文变量。
          <br />
          示例: {'{"key": "value", "number": 123, "flag": true}'}
          <br />
          如果不需要初始化变量，可以使用空对象: {'{}'}
        </Paragraph>
      </div>
    );
    
    let modalInstance = null;
    
    modalInstance = Modal.confirm({
      title: '执行模板 - 提供初始上下文',
      width: 650,
      content: modalContent,
      okText: '执行',
      cancelText: '取消',
      onOk: async () => {
        try {
          const contextText = document.getElementById('templateContext')?.value?.trim() || currentContextValue.trim();
          
          // 验证不能为空
          if (!contextText || contextText.trim() === '') {
            message.error('初始上下文不能为空，请输入有效的 JSON 对象（至少是 {}）');
            return Promise.reject('Validation failed'); // 阻止关闭模态框
          }
          
          // 验证 JSON 格式
          let initial_context = {};
          try {
            initial_context = JSON.parse(contextText);
          } catch (err) {
            message.error(`JSON 格式错误: ${err.message}`);
            return Promise.reject('Validation failed'); // 阻止关闭模态框
          }
          
          // 验证必须是对象类型
          if (typeof initial_context !== 'object' || Array.isArray(initial_context)) {
            message.error('初始上下文必须是 JSON 对象，不能是数组或其他类型');
            return Promise.reject('Validation failed'); // 阻止关闭模态框
          }
          
          // 关闭确认对话框
          // Antd Modal.confirm onOk handles close if promise resolves
          
          // 显示加载提示
          const hideLoading = message.loading('正在执行模板...', 0);
          
          try {
            const response = await fetch(`${API_BASE}/templates/${templateId}/execute`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({ initial_context })
            });

            const data = await response.json();
            hideLoading();
            
            Modal.success({
              title: '执行结果',
              width: 700,
              content: (
                <div>
                  <Paragraph>
                    <Text strong>执行状态:</Text>{' '}
                    <Tag color={data.success ? 'green' : 'red'}>
                      {data.success ? '成功' : '失败'}
                    </Tag>
                  </Paragraph>
                  {data.error && (
                    <Alert 
                      message="执行错误" 
                      description={data.error} 
                      type="error" 
                      style={{ marginBottom: 16 }}
                    />
                  )}
                  <Paragraph><Text strong>结果:</Text></Paragraph>
                  <pre style={{ 
                    background: '#f5f5f5', 
                    padding: '12px', 
                    borderRadius: '4px', 
                    overflow: 'auto', 
                    maxHeight: '400px',
                    fontFamily: 'Monaco, Menlo, Courier New, monospace',
                    fontSize: '12px'
                  }}>
                    {JSON.stringify(data, null, 2)}
                  </pre>
                </div>
              )
            });
          } catch (error) {
            hideLoading();
            message.error(`执行失败: ${error.message}`);
          }
        } catch (error) {
          if (error !== 'Validation failed') {
            message.error(`处理失败: ${error.message}`);
          }
          return Promise.reject(error); // 阻止关闭模态框
        }
      }
    });
  };

  // 编辑模板
  const editTemplate = async (templateId) => {
    try {
      const response = await fetch(`${API_BASE}/templates/${templateId}`);
      const data = await response.json();
      const template = data.template;

      setCurrentTemplate(templateId);
      setTemplateForm({
        name: template.name,
        description: template.description || '',
        tags: template.tags ? template.tags.join(', ') : '',
        steps: JSON.stringify(template.steps, null, 2)
      });
      setTemplateDialogVisible(true);
    } catch (error) {
      message.error(`加载模板失败: ${error.message}`);
    }
  };

  // 显示创建模板对话框
  const showCreateTemplate = () => {
    setCurrentTemplate(null);
    setTemplateForm({
      name: '',
      description: '',
      tags: '',
      steps: ''
    });
    setTemplateDialogVisible(true);
  };

  // 保存模板
  const saveTemplate = async () => {
    if (!templateForm.name.trim()) {
      message.error('请输入模板名称');
      throw new Error('模板名称不能为空');
    }

    if (!templateForm.steps.trim()) {
      message.error('请输入步骤');
      throw new Error('步骤不能为空');
    }

    try {
      const tags = templateForm.tags.trim() 
        ? templateForm.tags.split(',').map(t => t.trim()).filter(t => t) 
        : [];
      
      // 验证步骤 JSON 格式
      let steps;
      try {
        steps = JSON.parse(templateForm.steps);
      } catch (e) {
        message.error(`步骤 JSON 格式错误: ${e.message}`);
        throw new Error(`步骤 JSON 格式错误: ${e.message}`);
      }

      const requestBody = {
        name: templateForm.name.trim(),
        description: templateForm.description.trim() || null,
        steps,
        tags: tags.length > 0 ? tags : null
      };

      let response;
      if (currentTemplate) {
        response = await fetch(`${API_BASE}/templates/${currentTemplate}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestBody)
        });
      } else {
        response = await fetch(`${API_BASE}/templates`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestBody)
        });
      }

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '保存失败');
      }

      message.success('保存成功！');
      loadTemplates();
      // 注意：不在这里关闭 Modal，让 onOk 处理
    } catch (error) {
      message.error(`保存失败: ${error.message}`);
      throw error; // 重新抛出错误，让 onOk 知道保存失败
    }
  };

  // 删除模板
  const deleteTemplate = async (templateId) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个模板吗？',
      onOk: async () => {
        try {
          const response = await fetch(`${API_BASE}/templates/${templateId}`, {
            method: 'DELETE'
          });

          if (!response.ok) {
            throw new Error('删除失败');
          }

          message.success('删除成功！');
          loadTemplates();
        } catch (error) {
          message.error(`删除失败: ${error.message}`);
        }
      }
    });
  };

  // 加载步骤列表
  const loadSteps = async () => {
    setStepsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/steps`);
      const data = await response.json();
      setSteps(data.steps || {});
    } catch (error) {
      message.error(`加载步骤失败: ${error.message}`);
    } finally {
      setStepsLoading(false);
    }
  };

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

  // 工作流执行标签页
  const WorkflowTab = () => (
    <div>
      <Title level={4}>执行工作流</Title>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <Text strong>工作流步骤 (JSON)</Text>
          <TextArea
            value={workflowSteps}
            onChange={(e) => setWorkflowSteps(e.target.value)}
            placeholder='[{"type": "EchoInput", "params": {"message": "Hello"}}, {"type": "SetVar", "params": {"key": "test", "value": "value"}}]'
            rows={8}
            style={{ fontFamily: 'Monaco, Menlo, Courier New, monospace' }}
          />
        </div>
        <div>
          <Text strong>初始上下文 (JSON, 可选)</Text>
          <TextArea
            value={workflowContext}
            onChange={(e) => setWorkflowContext(e.target.value)}
            placeholder='{"key": "value"}'
            rows={4}
            style={{ fontFamily: 'Monaco, Menlo, Courier New, monospace' }}
          />
        </div>
        <Checkbox checked={debugMode} onChange={(e) => setDebugMode(e.target.checked)}>
          调试模式
        </Checkbox>
        <Space>
          <Button type="primary" onClick={executeWorkflow} loading={workflowLoading}>
            执行工作流
          </Button>
          <Button onClick={loadExample}>加载示例</Button>
          <Button onClick={clearWorkflow}>清空</Button>
        </Space>
        {workflowResult && (
          <div className={`result-box ${workflowResult.success ? 'success' : 'error'}`}>
            <pre>{JSON.stringify(workflowResult, null, 2)}</pre>
          </div>
        )}
      </Space>
    </div>
  );

  // 模板管理标签页
  const TemplatesTab = () => (
    <div>
      <Title level={4}>模板管理</Title>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Space style={{ width: '100%', marginBottom: 16 }} size="small">
          <Input
            style={{ flex: 1 }}
            placeholder="搜索模板..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onPressEnter={searchTemplates}
          />
          <Button onClick={searchTemplates}>搜索</Button>
          <Button onClick={loadTemplates}>刷新列表</Button>
        </Space>
        <Button type="primary" onClick={showCreateTemplate}>
          创建新模板
        </Button>
        <Spin spinning={templatesLoading}>
          {templates.length === 0 ? (
            <Alert message="暂无模板" type="info" />
          ) : (
            <div>
              {templates.map(template => (
                <Card
                  key={template.id}
                  className="template-card"
                  title={template.name}
                  extra={
                    <Space>
                      <Button size="small" onClick={() => viewTemplate(template.id)}>查看</Button>
                      <Button size="small" type="primary" onClick={() => executeTemplate(template.id)}>执行</Button>
                      <Button size="small" onClick={() => editTemplate(template.id)}>编辑</Button>
                      <Button size="small" danger onClick={() => deleteTemplate(template.id)}>删除</Button>
                    </Space>
                  }
                >
                  <Paragraph>{template.description || '无描述'}</Paragraph>
                  <div className="template-tags">
                    {template.tags && template.tags.map(tag => (
                      <Tag key={tag} color="blue">{tag}</Tag>
                    ))}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </Spin>
      </Space>
    </div>
  );

  // 步骤注册表标签页
  const StepsTab = () => (
    <div>
      <Title level={4}>步骤注册表</Title>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Button onClick={loadSteps} loading={stepsLoading}>刷新步骤列表</Button>
        <div className="steps-grid">
          {Object.entries(steps).map(([stepName, stepClass]) => (
            <div key={stepName} className="step-item">
              {stepName} ({stepClass})
            </div>
          ))}
        </div>
      </Space>
    </div>
  );

  // 健康检查标签页
  const HealthTab = () => (
    <div>
      <Title level={4}>健康检查</Title>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Button type="primary" onClick={checkHealth}>检查服务状态</Button>
        {healthResult && (
          <div className={`result-box ${healthResult.error ? 'error' : 'success'}`}>
            <pre>{JSON.stringify(healthResult, null, 2)}</pre>
          </div>
        )}
      </Space>
    </div>
  );

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
        <h1>🚀 Workflow API 测试工具</h1>
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
          <TabPane tab="工作流执行" key="workflow">
            <WorkflowTab />
          </TabPane>
          <TabPane tab="模板管理" key="templates">
            <TemplatesTab />
          </TabPane>
          <TabPane tab="聊天记录" key="chatHistory">
            <ChatHistoryTab />
          </TabPane>
          <TabPane tab="记忆管理" key="memory">
            <MemoryTab />
          </TabPane>
          <TabPane tab="步骤注册表" key="steps">
            <StepsTab />
          </TabPane>
          <TabPane tab="健康检查" key="health">
            <HealthTab />
          </TabPane>
        </Tabs>
      </div>
      
      {/* 创建/编辑模板对话框 - 移到 App 组件顶层，避免重新创建 */}
      <Modal
        title={currentTemplate ? '编辑模板' : '创建模板'}
        visible={templateDialogVisible}
        destroyOnClose={false}
        maskClosable={false}
        onOk={async () => {
          // 在 Ant Design 4.x 中，onOk 如果是异步函数，会显示 loading，但我们需要手动控制关闭
          try {
            await saveTemplate();
            // 保存成功后关闭 Modal
            setTemplateDialogVisible(false);
          } catch (error) {
            // 保存失败时不关闭 Modal，错误已在 saveTemplate 中处理
            console.error('保存模板失败:', error);
            // 这里我们不需要返回 false，因为 onOk 默认不关闭如果 Promise reject
            return Promise.reject(error);
          }
        }}
        onCancel={() => {
          setTemplateDialogVisible(false);
        }}
        width={800}
        okText="保存"
        cancelText="取消"
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Text strong>模板名称</Text>
            <Input
              value={templateForm.name}
              onChange={(e) => updateTemplateForm('name', e.target.value)}
              placeholder="输入模板名称"
            />
          </div>
          <div>
            <Text strong>描述</Text>
            <Input
              value={templateForm.description}
              onChange={(e) => updateTemplateForm('description', e.target.value)}
              placeholder="输入模板描述"
            />
          </div>
          <div>
            <Text strong>标签 (逗号分隔)</Text>
            <Input
              value={templateForm.tags}
              onChange={(e) => updateTemplateForm('tags', e.target.value)}
              placeholder="例如: 基础,示例"
            />
          </div>
          <div>
            <Text strong>步骤 (JSON)</Text>
            <TextArea
              value={templateForm.steps}
              onChange={(e) => updateTemplateForm('steps', e.target.value)}
              placeholder='[{"type": "EchoInput", "params": {"message": "Hello"}}]'
              rows={10}
              style={{ fontFamily: 'Monaco, Menlo, Courier New, monospace' }}
            />
          </div>
        </Space>
      </Modal>

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
