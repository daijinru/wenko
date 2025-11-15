"""工作流执行器模块

负责执行工作流步骤序列。
"""

import traceback
from typing import Any, Dict, List

from steps import StepContext, create_step
# 导入控制步骤以注册到步骤注册表
import control_steps


class WorkflowExecutor:
    """工作流执行器"""
    
    def __init__(self):
        pass
    
    def execute(self, steps: List[Dict[str, Any]], initial_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行工作流步骤序列
        
        Args:
            steps: 步骤配置列表
            initial_context: 初始上下文变量
            
        Returns:
            执行结果字典，包含 success, result, error 字段
        """
        # 确保 initial_context 是一个字典，并且不包含 'initial_context' 键
        # 避免将 initial_context 作为键添加到 context.variables 中
        clean_initial_context = {}
        if initial_context:
            # 如果 initial_context 本身包含 'initial_context' 键，展开它
            if 'initial_context' in initial_context and isinstance(initial_context['initial_context'], dict):
                clean_initial_context = {**initial_context['initial_context']}
                # 合并其他键（如果有）
                for key, value in initial_context.items():
                    if key != 'initial_context':
                        clean_initial_context[key] = value
            else:
                clean_initial_context = initial_context.copy()
        
        context = StepContext(clean_initial_context)
        
        try:
            results = []
            
            for step_config in steps:
                step_type = step_config.get('type')
                step_params = step_config.get('params', {})
                
                if not step_type:
                    raise ValueError("Step configuration missing 'type' field")
                
                # 创建并执行步骤
                step = create_step(step_type, step_params)
                result = step.execute(context)
                results.append(result)
            
            return {
                'success': True,
                'result': context.variables,
                'error': None
            }
            
        except Exception as e:
            error_msg = f"Workflow execution failed: {str(e)}"
            return {
                'success': False,
                'result': None,
                'error': error_msg
            }