"""工作流使用示例

展示如何使用工作流系统的各种功能。
"""

import asyncio
import json
from typing import Any, Dict, List

from graph import workflow_graph


def example_basic_workflow():
    """基础工作流示例"""
    print("\n=== 基础工作流示例 ===")
    
    steps = [
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
    ]
    
    return steps


def example_conditional_workflow():
    """条件控制工作流示例"""
    print("\n=== 条件控制工作流示例 ===")
    
    steps = [
        {
            "type": "SetVar",
            "params": {
                "key": "user_age",
                "value": 25
            }
        },
        {
            "type": "If",
            "params": {
                "condition_key": "user_age"
            }
        },
        {
            "type": "Then",
            "params": {
                "steps": [
                    {
                        "type": "SetVar",
                        "params": {
                            "key": "message",
                            "value": "User is an adult"
                        }
                    }
                ]
            }
        },
        {
            "type": "Else",
            "params": {
                "steps": [
                    {
                        "type": "SetVar",
                        "params": {
                            "key": "message",
                            "value": "User is a minor"
                        }
                    }
                ]
            }
        },
        {
            "type": "GetVar",
            "params": {
                "key": "message"
            }
        }
    ]
    
    return steps


def example_math_workflow():
    """数学计算工作流示例"""
    print("\n=== 数学计算工作流示例 ===")
    
    steps = [
        {
            "type": "SetVar",
            "params": {
                "key": "a",
                "value": 10
            }
        },
        {
            "type": "SetVar",
            "params": {
                "key": "b",
                "value": 5
            }
        },
        {
            "type": "MathOp",
            "params": {
                "operation": "add",
                "operand1_key": "a",
                "operand2_key": "b",
                "output_key": "sum"
            }
        },
        {
            "type": "MathOp",
            "params": {
                "operation": "multiply",
                "operand1_key": "sum",
                "operand2_value": 2,
                "output_key": "final_result"
            }
        },
        {
            "type": "GetVar",
            "params": {
                "key": "final_result"
            }
        }
    ]
    
    return steps


async def run_example(name: str, steps: List[Dict[str, Any]], initial_context: Dict[str, Any] = None):
    """运行示例工作流"""
    print(f"\n运行示例: {name}")
    print(f"步骤数量: {len(steps)}")
    
    # 构建工作流状态
    state = {
        "steps": steps,
        "initial_context": initial_context or {},
        "debug_mode": True,
        "result": {},
        "error": None
    }
    
    try:
        # 执行工作流
        result = await workflow_graph.ainvoke(state)
        
        print("\n执行结果:")
        if result["error"]:
            print(f"错误: {result['error']}")
        else:
            workflow_result = result["result"]
            if workflow_result["success"]:
                print(f"成功: {json.dumps(workflow_result['result'], indent=2, ensure_ascii=False)}")
            else:
                print(f"失败: {workflow_result['error']}")
                
    except Exception as e:
        print(f"执行异常: {str(e)}")


def string_operations_workflow_example():
    """字符串操作工作流示例"""
    
    steps = [
        {
            "type": "SetVar",
            "params": {
                "key": "text",
                "value": "  Hello World  "
            }
        },
        {
            "type": "StringOp",
            "params": {
                "operation": "strip",
                "input_key": "text",
                "output_key": "trimmed_text"
            }
        },
        {
            "type": "StringOp",
            "params": {
                "operation": "upper",
                "input_key": "trimmed_text",
                "output_key": "upper_text"
            }
        },
        {
            "type": "GetVar",
            "params": {
                "key": "upper_text"
            }
        }
    ]
    
    return steps


def condition_workflow_example():
    """条件判断工作流示例"""
    
    steps = [
        {
            "type": "SetVar",
            "params": {
                "key": "score",
                "value": 85
            }
        },
        {
            "type": "Condition",
            "params": {
                "condition_type": "greater_than",
                "left_key": "score",
                "right_value": 80,
                "output_key": "is_passing"
            }
        },
        {
            "type": "GetVar",
            "params": {
                "key": "is_passing"
            }
        }
    ]
    
    return steps


def list_operations_workflow_example():
    """列表操作工作流示例"""
    
    steps = [
        {
            "type": "SetVar",
            "params": {
                "key": "numbers",
                "value": [3, 1, 4, 1, 5, 9, 2, 6]
            }
        },
        {
             "type": "ListOp",
             "params": {
                 "operation": "sort",
                 "list_key": "numbers",
                 "output_key": "sorted_numbers"
             }
         },
         {
             "type": "ListOp",
             "params": {
                 "operation": "length",
                 "list_key": "sorted_numbers",
                 "output_key": "list_length"
             }
         },
        {
            "type": "GetVar",
            "params": {
                "key": "list_length"
            }
        }
    ]
    
    return steps


def time_operations_workflow_example():
    """时间操作工作流示例"""
    
    steps = [
        {
            "type": "TimeOp",
            "params": {
                "operation": "now",
                "output_key": "current_time"
            }
        },
        {
             "type": "TimeOp",
             "params": {
                 "operation": "format",
                 "datetime_key": "current_time",
                 "format": "%Y-%m-%d %H:%M:%S",
                 "output_key": "formatted_time"
             }
         },
        {
            "type": "GetVar",
            "params": {
                "key": "formatted_time"
            }
        }
    ]
    
    return steps


def random_workflow_example():
    """随机数工作流示例"""
    
    steps = [
        {
             "type": "Random",
             "params": {
                 "operation": "integer",
                 "min": 1,
                 "max": 100,
                 "output_key": "random_number"
             }
         },
        {
            "type": "SetVar",
            "params": {
                "key": "choices",
                "value": ["red", "green", "blue", "yellow"]
            }
        },
        {
            "type": "Random",
            "params": {
                "operation": "choice",
                "choices_key": "choices",
                "output_key": "random_choice"
            }
        },
        {
            "type": "GetVar",
            "params": {
                "key": "random_choice"
            }
        }
    ]
    
    return steps


async def main():
    """主函数"""
    print("LangGraph 工作流系统示例")
    print("=" * 50)
    
    # 运行基础工作流示例
    await run_example(
        "基础工作流",
        example_basic_workflow(),
        initial_context={"input": "来自初始上下文的输入"}
    )
    
    # 运行条件控制工作流示例
    await run_example(
        "条件控制工作流",
        example_conditional_workflow(),
        initial_context={"user_name": "张三", "system_info": "工作流系统 v1.0"}
    )
    
    # 运行数学计算工作流示例
    await run_example(
        "数学计算工作流",
        example_math_workflow(),
        initial_context={"calculation_type": "基础数学运算", "precision": 2}
    )
    
    # 运行字符串操作工作流示例
    await run_example(
        "字符串操作工作流",
        string_operations_workflow_example(),
        initial_context={"text": "  Hello World  ", "words": ["apple", "banana", "cherry"]}
    )
    
    # 运行条件判断工作流示例
    await run_example(
        "条件判断工作流",
        condition_workflow_example(),
        initial_context={"score": 85, "threshold": 80, "student_name": "Bob"}
    )
    
    # 运行列表操作工作流示例
    await run_example(
        "列表操作工作流",
        list_operations_workflow_example(),
        initial_context={"numbers": [3, 1, 4, 1, 5, 9, 2, 6], "items": ["apple", "banana", "apple", "cherry"]}
    )
    
    # 运行时间操作工作流示例
    await run_example(
        "时间操作工作流",
        time_operations_workflow_example(),
        initial_context={}
    )
    
    # 运行随机数工作流示例
    await run_example(
        "随机数工作流",
        random_workflow_example(),
        initial_context={"choices": ["red", "green", "blue", "yellow"]}
    )
    
    print("\n所有示例执行完成!")


if __name__ == "__main__":
    asyncio.run(main())