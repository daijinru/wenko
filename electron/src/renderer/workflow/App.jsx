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
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="工作流执行" key="workflow">
            <WorkflowTab />
          </TabPane>
          <TabPane tab="模板管理" key="templates">
            <TemplatesTab />
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
    </div>
  );
}

export default App;
