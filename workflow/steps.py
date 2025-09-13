"""工作流步骤定义模块

定义了所有可用的工作流步骤类型和执行逻辑。
"""

import json
import re
import time
import random
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import httpx


class StepContext:
    """步骤执行上下文"""
    
    def __init__(self, variables: Optional[Dict[str, Any]] = None):
        self.variables = variables or {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取变量值"""
        return self.variables.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置变量值"""
        self.variables[key] = value
    
    def update(self, variables: Dict[str, Any]) -> None:
        """批量更新变量"""
        self.variables.update(variables)


class Step(ABC):
    """步骤基类"""
    
    def __init__(self, step_type: str, params: Dict[str, Any]):
        self.step_type = step_type
        self.params = params
    
    @abstractmethod
    def execute(self, context: StepContext) -> Any:
        """执行步骤"""
        pass
    
    def resolve_params(self, context: StepContext) -> Dict[str, Any]:
        """解析参数中的占位符"""
        resolved = {}
        for key, value in self.params.items():
            if isinstance(value, str) and value.startswith('{{') and value.endswith('}}'):
                var_name = value[2:-2].strip()
                resolved[key] = context.get(var_name)
            else:
                resolved[key] = value
        return resolved


class EchoInputStep(Step):
    """回显输入步骤"""
    
    def execute(self, context: StepContext) -> Any:
        resolved_params = self.resolve_params(context)
        input_key = resolved_params.get('input_key', 'input')
        output_key = resolved_params.get('output_key', 'output')
        
        input_value = context.get(input_key)
        context.set(output_key, input_value)
        return input_value


class SetVarStep(Step):
    """设置变量步骤"""
    
    def execute(self, context: StepContext) -> Any:
        resolved_params = self.resolve_params(context)
        key = resolved_params['key']
        
        # 支持直接设置值或从其他键复制值
        if 'value' in resolved_params:
            value = resolved_params['value']
        elif 'from_key' in resolved_params:
            from_key = resolved_params['from_key']
            value = context.get(from_key)
            if value is None:
                raise KeyError(f"Source key '{from_key}' not found in context")
        else:
            raise ValueError("SetVar step requires either 'value' or 'from_key' parameter")
        
        context.set(key, value)
        return value


class GetVarStep(Step):
    """获取变量步骤"""
    
    def execute(self, context: StepContext) -> Any:
        resolved_params = self.resolve_params(context)
        key = resolved_params['key']
        default = resolved_params.get('default')
        
        value = context.get(key, default)
        return value


class FetchURLStep(Step):
    """HTTP 请求步骤"""
    
    def execute(self, context: StepContext) -> Any:
        resolved_params = self.resolve_params(context)
        url = resolved_params['url']
        method = resolved_params.get('method', 'GET').upper()
        headers = resolved_params.get('headers', {})
        data = resolved_params.get('data')
        output_key = resolved_params.get('output_key', 'response')
        
        try:
            with httpx.Client() as client:
                if method == 'GET':
                    response = client.get(url, headers=headers)
                elif method == 'POST':
                    response = client.post(url, headers=headers, json=data)
                elif method == 'PUT':
                    response = client.put(url, headers=headers, json=data)
                elif method == 'DELETE':
                    response = client.delete(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                result = response.text
                
                context.set(output_key, result)
                return result
        except Exception as e:
            error_msg = f"HTTP request failed: {str(e)}"
            context.set(f"{output_key}_error", error_msg)
            raise RuntimeError(error_msg)


class ParseJSONStep(Step):
    """JSON 解析步骤"""
    
    def execute(self, context: StepContext) -> Any:
        resolved_params = self.resolve_params(context)
        input_key = resolved_params['input_key']
        output_key = resolved_params.get('output_key', 'parsed_json')
        
        json_str = context.get(input_key)
        if json_str is None:
            raise ValueError(f"Input key '{input_key}' not found in context")
        
        try:
            parsed_data = json.loads(json_str)
            context.set(output_key, parsed_data)
            return parsed_data
        except json.JSONDecodeError as e:
            error_msg = f"JSON parsing failed: {str(e)}"
            context.set(f"{output_key}_error", error_msg)
            raise ValueError(error_msg)


class JSONLookupStep(Step):
    """JSON 查找步骤"""
    
    def execute(self, context: StepContext) -> Any:
        resolved_params = self.resolve_params(context)
        json_key = resolved_params['json_key']
        lookup_key = resolved_params['lookup_key']
        output_key = resolved_params.get('output_key', 'lookup_result')
        
        json_data = context.get(json_key)
        if json_data is None:
            raise ValueError(f"JSON key '{json_key}' not found in context")
        
        if not isinstance(json_data, dict):
            raise ValueError(f"Value at '{json_key}' is not a dictionary")
        
        result = json_data.get(lookup_key)
        context.set(output_key, result)
        return result


class JSONExtractValuesStep(Step):
    """JSON 值提取步骤"""
    
    def execute(self, context: StepContext) -> Any:
        resolved_params = self.resolve_params(context)
        json_key = resolved_params['json_key']
        output_key = resolved_params.get('output_key', 'extracted_values')
        
        json_data = context.get(json_key)
        if json_data is None:
            raise ValueError(f"JSON key '{json_key}' not found in context")
        
        if isinstance(json_data, dict):
            values = list(json_data.values())
        elif isinstance(json_data, list):
            values = json_data
        else:
            values = [json_data]
        
        context.set(output_key, values)
        return values


class TemplateReplaceStep(Step):
    """模板替换步骤"""
    
    def execute(self, context: StepContext) -> Any:
        resolved_params = self.resolve_params(context)
        template_key = resolved_params['template_key']
        output_key = resolved_params.get('output_key', 'filled_template')
        
        template = context.get(template_key)
        if template is None:
            raise ValueError(f"Template key '{template_key}' not found in context")
        
        # 使用正则表达式替换 {{variable}} 格式的占位符
        def replace_placeholder(match):
            var_name = match.group(1).strip()
            return str(context.get(var_name, match.group(0)))
        
        filled_template = re.sub(r'\{\{([^}]+)\}\}', replace_placeholder, template)
        context.set(output_key, filled_template)
        return filled_template


class MultilineToSingleLineStep(Step):
    """多行转单行步骤"""
    
    def execute(self, context: StepContext) -> Any:
        resolved_params = self.resolve_params(context)
        input_key = resolved_params['input_key']
        output_key = resolved_params.get('output_key', 'single_line')
        separator = resolved_params.get('separator', ' | ')
        
        multiline_text = context.get(input_key)
        if multiline_text is None:
            raise ValueError(f"Input key '{input_key}' not found in context")
        
        single_line = separator.join(line.strip() for line in str(multiline_text).split('\n') if line.strip())
        context.set(output_key, single_line)
        return single_line


class OutputResultStep(Step):
    """输出结果步骤"""
    
    def execute(self, context: StepContext) -> Any:
        resolved_params = self.resolve_params(context)
        input_key = resolved_params.get('input_key')
        message = resolved_params.get('message', '')
        
        if input_key:
            result = context.get(input_key)
        else:
            result = message
        
        return result


class CopyVarStep(Step):
    """复制变量步骤"""
    
    def execute(self, context: StepContext) -> Any:
        resolved_params = self.resolve_params(context)
        from_key = resolved_params['from_key']
        to_key = resolved_params['to_key']
        
        value = context.get(from_key)
        if value is None:
            raise ValueError(f"Source key '{from_key}' not found in context")
        
        context.set(to_key, value)
        return value


class MathOpStep(Step):
    """数学运算步骤"""
    
    def execute(self, context: StepContext) -> Any:
        resolved_params = self.resolve_params(context)
        operation = resolved_params['operation']
        operand1_key = resolved_params.get('operand1_key')
        operand2_key = resolved_params.get('operand2_key')
        operand1_value = resolved_params.get('operand1_value')
        operand2_value = resolved_params.get('operand2_value')
        output_key = resolved_params.get('output_key', 'math_result')
        
        # 获取操作数
        if operand1_key:
            operand1 = context.get(operand1_key)
        elif operand1_value is not None:
            operand1 = operand1_value
        else:
            raise ValueError("MathOp step requires either 'operand1_key' or 'operand1_value'")
        
        if operand2_key:
            operand2 = context.get(operand2_key)
        elif operand2_value is not None:
            operand2 = operand2_value
        else:
            raise ValueError("MathOp step requires either 'operand2_key' or 'operand2_value'")
        
        # 确保操作数是数字
        try:
            operand1 = float(operand1)
            operand2 = float(operand2)
        except (ValueError, TypeError):
            raise ValueError("MathOp operands must be numeric")
        
        # 执行数学运算
        if operation == 'add':
            result = operand1 + operand2
        elif operation == 'subtract':
            result = operand1 - operand2
        elif operation == 'multiply':
            result = operand1 * operand2
        elif operation == 'divide':
            if operand2 == 0:
                raise ValueError("Division by zero")
            result = operand1 / operand2
        elif operation == 'power':
            result = operand1 ** operand2
        elif operation == 'modulo':
            if operand2 == 0:
                raise ValueError("Modulo by zero")
            result = operand1 % operand2
        else:
            raise ValueError(f"Unsupported math operation: {operation}")
        
        # 如果结果是整数，转换为int类型
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        
        context.set(output_key, result)
        return result


class StringOpStep(Step):
    """字符串操作步骤"""
    
    def execute(self, context: StepContext) -> Any:
        resolved_params = self.resolve_params(context)
        operation = resolved_params['operation']
        input_key = resolved_params.get('input_key')
        input_value = resolved_params.get('input_value')
        output_key = resolved_params.get('output_key', 'string_result')
        
        # 获取输入字符串
        if input_key:
            text = context.get(input_key)
        elif input_value is not None:
            text = input_value
        else:
            raise ValueError("StringOp step requires either 'input_key' or 'input_value'")
        
        text = str(text)
        
        # 执行字符串操作
        if operation == 'upper':
            result = text.upper()
        elif operation == 'lower':
            result = text.lower()
        elif operation == 'strip':
            result = text.strip()
        elif operation == 'length':
            result = len(text)
        elif operation == 'reverse':
            result = text[::-1]
        elif operation == 'split':
            delimiter = resolved_params.get('delimiter', ' ')
            result = text.split(delimiter)
        elif operation == 'join':
            delimiter = resolved_params.get('delimiter', ' ')
            if isinstance(text, list):
                result = delimiter.join(str(item) for item in text)
            else:
                raise ValueError("Join operation requires a list input")
        elif operation == 'replace':
            old_str = resolved_params.get('old_str', '')
            new_str = resolved_params.get('new_str', '')
            result = text.replace(old_str, new_str)
        elif operation == 'substring':
            start = resolved_params.get('start', 0)
            end = resolved_params.get('end', len(text))
            result = text[start:end]
        else:
            raise ValueError(f"Unsupported string operation: {operation}")
        
        context.set(output_key, result)
        return result


class ConditionStep(Step):
    """条件判断步骤"""
    
    def execute(self, context: StepContext) -> Any:
        resolved_params = self.resolve_params(context)
        condition_type = resolved_params['condition_type']
        left_key = resolved_params.get('left_key')
        left_value = resolved_params.get('left_value')
        right_key = resolved_params.get('right_key')
        right_value = resolved_params.get('right_value')
        output_key = resolved_params.get('output_key', 'condition_result')
        
        # 获取左操作数
        if left_key:
            left = context.get(left_key)
        elif left_value is not None:
            left = left_value
        else:
            raise ValueError("Condition step requires either 'left_key' or 'left_value'")
        
        # 获取右操作数
        if right_key:
            right = context.get(right_key)
        elif right_value is not None:
            right = right_value
        else:
            raise ValueError("Condition step requires either 'right_key' or 'right_value'")
        
        # 执行条件判断
        if condition_type == 'equals':
            result = left == right
        elif condition_type == 'not_equals':
            result = left != right
        elif condition_type == 'greater_than':
            result = left > right
        elif condition_type == 'less_than':
            result = left < right
        elif condition_type == 'greater_equal':
            result = left >= right
        elif condition_type == 'less_equal':
            result = left <= right
        elif condition_type == 'contains':
            result = str(right) in str(left)
        elif condition_type == 'starts_with':
            result = str(left).startswith(str(right))
        elif condition_type == 'ends_with':
            result = str(left).endswith(str(right))
        else:
            raise ValueError(f"Unsupported condition type: {condition_type}")
        
        context.set(output_key, result)
        return result


class ListOpStep(Step):
    """列表操作步骤"""
    
    def execute(self, context: StepContext) -> Any:
        resolved_params = self.resolve_params(context)
        operation = resolved_params['operation']
        list_key = resolved_params.get('list_key')
        list_value = resolved_params.get('list_value')
        output_key = resolved_params.get('output_key', 'list_result')
        
        # 获取列表
        if list_key:
            lst = context.get(list_key)
        elif list_value is not None:
            lst = list_value
        else:
            raise ValueError("ListOp step requires either 'list_key' or 'list_value'")
        
        if not isinstance(lst, list):
            if isinstance(lst, str):
                lst = list(lst)
            else:
                lst = [lst]
        
        # 执行列表操作
        if operation == 'length':
            result = len(lst)
        elif operation == 'first':
            result = lst[0] if lst else None
        elif operation == 'last':
            result = lst[-1] if lst else None
        elif operation == 'append':
            item = resolved_params.get('item')
            if item is not None:
                lst.append(item)
            result = lst
        elif operation == 'sort':
            reverse = resolved_params.get('reverse', False)
            result = sorted(lst, reverse=reverse)
        elif operation == 'unique':
            result = list(dict.fromkeys(lst))  # 保持顺序的去重
        elif operation == 'sum':
            result = sum(float(x) for x in lst if isinstance(x, (int, float)) or str(x).replace('.', '').isdigit())
        elif operation == 'max':
            result = max(lst) if lst else None
        elif operation == 'min':
            result = min(lst) if lst else None
        elif operation == 'slice':
            start = resolved_params.get('start', 0)
            end = resolved_params.get('end', len(lst))
            result = lst[start:end]
        else:
            raise ValueError(f"Unsupported list operation: {operation}")
        
        context.set(output_key, result)
        return result


class TimeOpStep(Step):
    """时间操作步骤"""
    
    def execute(self, context: StepContext) -> Any:
        resolved_params = self.resolve_params(context)
        operation = resolved_params['operation']
        output_key = resolved_params.get('output_key', 'time_result')
        
        # 执行时间操作
        if operation == 'now':
            result = datetime.now().isoformat()
        elif operation == 'timestamp':
            result = int(time.time())
        elif operation == 'format':
            dt_key = resolved_params.get('datetime_key')
            dt_value = resolved_params.get('datetime_value')
            format_str = resolved_params.get('format', '%Y-%m-%d %H:%M:%S')
            
            if dt_key:
                dt = context.get(dt_key)
            elif dt_value:
                dt = dt_value
            else:
                dt = datetime.now()
            
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            elif isinstance(dt, (int, float)):
                dt = datetime.fromtimestamp(dt)
            
            result = dt.strftime(format_str)
        elif operation == 'add_days':
            dt_key = resolved_params.get('datetime_key')
            dt_value = resolved_params.get('datetime_value')
            days = resolved_params.get('days', 0)
            
            if dt_key:
                dt = context.get(dt_key)
            elif dt_value:
                dt = dt_value
            else:
                dt = datetime.now()
            
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            
            result = (dt + timedelta(days=days)).isoformat()
        elif operation == 'sleep':
            seconds = resolved_params.get('seconds', 1)
            time.sleep(seconds)
            result = f"Slept for {seconds} seconds"
        else:
            raise ValueError(f"Unsupported time operation: {operation}")
        
        context.set(output_key, result)
        return result


class RandomStep(Step):
    """随机数生成步骤"""
    
    def execute(self, context: StepContext) -> Any:
        resolved_params = self.resolve_params(context)
        operation = resolved_params['operation']
        output_key = resolved_params.get('output_key', 'random_result')
        
        # 执行随机操作
        if operation == 'integer':
            min_val = resolved_params.get('min', 0)
            max_val = resolved_params.get('max', 100)
            result = random.randint(min_val, max_val)
        elif operation == 'float':
            min_val = resolved_params.get('min', 0.0)
            max_val = resolved_params.get('max', 1.0)
            result = random.uniform(min_val, max_val)
        elif operation == 'choice':
            choices_key = resolved_params.get('choices_key')
            choices_value = resolved_params.get('choices_value')
            
            if choices_key:
                choices = context.get(choices_key)
            elif choices_value:
                choices = choices_value
            else:
                raise ValueError("Random choice requires either 'choices_key' or 'choices_value'")
            
            if not isinstance(choices, list) or not choices:
                raise ValueError("Choices must be a non-empty list")
            
            result = random.choice(choices)
        elif operation == 'uuid':
            import uuid
            result = str(uuid.uuid4())
        else:
            raise ValueError(f"Unsupported random operation: {operation}")
        
        context.set(output_key, result)
        return result


class LogStep(Step):
    """日志记录步骤"""
    
    def execute(self, context: StepContext) -> Any:
        resolved_params = self.resolve_params(context)
        level = resolved_params.get('level', 'info')
        message_key = resolved_params.get('message_key')
        message_value = resolved_params.get('message_value')
        
        # 获取消息
        if message_key:
            message = context.get(message_key)
        elif message_value is not None:
            message = message_value
        else:
            raise ValueError("Log step requires either 'message_key' or 'message_value'")
        
        # 格式化日志消息
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] [{level.upper()}] {message}"
        
        # 输出日志（这里简单打印，实际应用中可以使用logging模块）
        print(log_message)
        
        return log_message


# 步骤注册表
STEP_REGISTRY = {
    'EchoInput': EchoInputStep,
    'SetVar': SetVarStep,
    'GetVar': GetVarStep,
    'FetchURL': FetchURLStep,
    'ParseJSON': ParseJSONStep,
    'JSONLookup': JSONLookupStep,
    'JSONExtractValues': JSONExtractValuesStep,
    'TemplateReplace': TemplateReplaceStep,
    'MultilineToSingleLine': MultilineToSingleLineStep,
    'OutputResult': OutputResultStep,
    'CopyVar': CopyVarStep,
    'MathOp': MathOpStep,
    'StringOp': StringOpStep,
    'Condition': ConditionStep,
    'ListOp': ListOpStep,
    'TimeOp': TimeOpStep,
    'Random': RandomStep,
    'Log': LogStep,
}


def create_step(step_type: str, params: Dict[str, Any]) -> Step:
    """创建步骤实例"""
    if step_type not in STEP_REGISTRY:
        raise ValueError(f"Unknown step type: {step_type}")
    
    step_class = STEP_REGISTRY[step_type]
    return step_class(step_type, params)