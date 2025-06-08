/**
 * 生成层级化文案结构的提示词 
 * @param {Object} options 配置选项 
 * @param {string} [options.theme='产品文档'] 主题类型 
 * @param {number} [options.maxLevel=2] 最大层级深度 
 * @param {boolean} [options.withTechStack=true] 是否包含技术栈提示 
 * @returns {{
 *   systemPrompt: string,
 *   userPrompt: string,
 *   outputFormat: object 
 * }} 生成的提示词对象 
 */
function getPrompts(options = {}) {
  const {
    // @ts-ignore
    theme = '产品文档',
    // @ts-ignore
    maxLevel = 2,
    // @ts-ignore
    withTechStack = true 
  } = options;
 
  // 主题适配提示 
  const themePrompts = {
    '产品文档': '包含「功能模块」「技术架构」「用户场景」分类',
    '文学创作': '按「人物设定」「情节发展」「环境描写」组织',
    '技术方案': '需包含「系统设计」「接口规范」「部署方案」'
  };
 
  // 技术栈相关提示 
  const techPrompt = withTechStack 
    ? '技术类节点需标注具体技术栈（如React/Node.js ），用<tech>标签包裹'
    : '';
 
  return {
    systemPrompt: `你是一个专业的内容架构师，需要将零散的文本片段组织成${maxLevel}层级的树状结构。\n\n基本要求：\n1. 自动识别父子关系\n2. 保持原始文本完整性\n3. 遵循${theme}的常见分类方式`,
    
    userPrompt: `请将我的文本按以下规则处理：
1. 层级划分：
   - Level 0: ${themePrompts[theme] || themePrompts['产品文档']}
   - Level 1-${maxLevel}: 逐级细化 
2. 内容处理：
   - 保留换行符和项目符号 
   - 自动补全残缺句子 
   ${techPrompt}
3. 关系验证：
   - 每个片段必须有且只有一个父节点 
   - 不允许循环引用`,
 
    outputFormat: {
      description: `生成的${maxLevel}层JSON结构`,
      schema: {
        type: 'object',
        properties: {
          cards: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                id: { type: 'string', pattern: '^\\d+$' },
                content: { type: 'string' },
                level: { type: 'integer', minimum: 0, maximum: maxLevel },
                parentId: { 
                  type: 'string',
                  pattern: '^\\d+$',
                  description: `当level≥1时必填，指向有效的父节点ID`
                }
              },
              required: ['id', 'content', 'level']
            }
          },
          statistics: {
            type: 'object',
            properties: {
              totalNodes: { type: 'integer' },
              levelDistribution: {
                type: 'array',
                items: { type: 'integer' },
                maxItems: maxLevel + 1 
              }
            }
          }
        },
        required: ['cards']
      }
    }
  };
}
 
// 使用示例 
const prompts = getPrompts({ theme: '技术方案', maxLevel: 3 });
console.log(' 系统提示:', prompts.systemPrompt); 
console.log(' 用户提示:', prompts.userPrompt); 
console.log(' 输出格式要求:', JSON.stringify(prompts.outputFormat,  null, 2));