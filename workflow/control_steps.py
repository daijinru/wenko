"""条件控制步骤模块

实现 If/Then/Else 条件控制逻辑。
"""

from typing import Any, Dict, List
from steps import Step, StepContext, create_step


class IfStep(Step):
    """条件判断步骤"""
    
    def execute(self, context: StepContext) -> Any:
        resolved_params = self.resolve_params(context)
        condition_key = resolved_params['condition_key']
        
        condition_value = context.get(condition_key)
        
        # 将条件结果存储到上下文中，供 Then/Else 步骤使用
        context.set('_last_condition_result', bool(condition_value))
        
        return bool(condition_value)


class ThenStep(Step):
    """条件为真时执行的步骤"""
    
    def execute(self, context: StepContext) -> Any:
        # 检查上一个条件的结果
        condition_result = context.get('_last_condition_result')
        
        if condition_result:
            # 条件为真，执行子步骤
            resolved_params = self.resolve_params(context)
            steps_config = resolved_params.get('steps', [])
            
            results = []
            for step_config in steps_config:
                step = create_step(step_config['type'], step_config['params'])
                result = step.execute(context)
                results.append(result)
            
            return results
        
        return None


class ElseStep(Step):
    """条件为假时执行的步骤"""
    
    def execute(self, context: StepContext) -> Any:
        # 检查上一个条件的结果
        condition_result = context.get('_last_condition_result')
        
        if not condition_result:
            # 条件为假，执行子步骤
            resolved_params = self.resolve_params(context)
            steps_config = resolved_params.get('steps', [])
            
            results = []
            for step_config in steps_config:
                step = create_step(step_config['type'], step_config['params'])
                result = step.execute(context)
                results.append(result)
            
            return results
        
        return None


# 将控制步骤添加到步骤注册表
from steps import STEP_REGISTRY

STEP_REGISTRY.update({
    'If': IfStep,
    'Then': ThenStep,
    'Else': ElseStep,
})