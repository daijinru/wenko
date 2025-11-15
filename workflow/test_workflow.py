"""工作流系统测试脚本

测试工作流系统的各项功能。
"""

import asyncio
import json
import sys
from typing import Any, Dict, List

from graph import workflow_graph
from steps import STEP_REGISTRY


def test_step_registry():
    """测试步骤注册表"""
    print("\n=== 测试步骤注册表 ===")
    print(f"注册的步骤数量: {len(STEP_REGISTRY)}")
    print("已注册的步骤类型:")
    for step_name, step_class in STEP_REGISTRY.items():
        print(f"  - {step_name}: {step_class.__name__}")
    return len(STEP_REGISTRY) > 0


async def test_basic_workflow():
    """测试基础工作流"""
    print("\n=== 测试基础工作流 ===")
    
    steps = [
        {
            "type": "EchoInput",
            "params": {
                "message": "Test message"
            }
        },
        {
            "type": "SetVar",
            "params": {
                "key": "test_key",
                "value": "test_value"
            }
        },
        {
            "type": "GetVar",
            "params": {
                "key": "test_key"
            }
        }
    ]
    
    state = {
        "steps": steps,
        "initial_context": {},
        "debug_mode": False,
        "result": {},
        "error": None
    }
    
    try:
        result = await workflow_graph.ainvoke(state)
        if result["error"]:
            print(f"❌ 错误: {result['error']}")
            return False
        
        workflow_result = result["result"]
        if workflow_result["success"]:
            print(f"✅ 成功: {json.dumps(workflow_result['result'], indent=2, ensure_ascii=False)}")
            return True
        else:
            print(f"❌ 失败: {workflow_result['error']}")
            return False
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        return False


async def test_math_workflow():
    """测试数学计算工作流"""
    print("\n=== 测试数学计算工作流 ===")
    
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
            "type": "GetVar",
            "params": {
                "key": "sum"
            }
        }
    ]
    
    state = {
        "steps": steps,
        "initial_context": {},
        "debug_mode": False,
        "result": {},
        "error": None
    }
    
    try:
        result = await workflow_graph.ainvoke(state)
        if result["error"]:
            print(f"❌ 错误: {result['error']}")
            return False
        
        workflow_result = result["result"]
        if workflow_result["success"] and workflow_result["result"].get("sum") == 15:
            print(f"✅ 成功: sum = {workflow_result['result']['sum']}")
            return True
        else:
            print(f"❌ 失败: {workflow_result.get('error', '结果不正确')}")
            return False
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        return False


async def test_conditional_workflow():
    """测试条件控制工作流"""
    print("\n=== 测试条件控制工作流 ===")
    
    steps = [
        {
            "type": "SetVar",
            "params": {
                "key": "value",
                "value": 10
            }
        },
        {
            "type": "If",
            "params": {
                "condition_key": "value"
            }
        },
        {
            "type": "Then",
            "params": {
                "steps": [
                    {
                        "type": "SetVar",
                        "params": {
                            "key": "result",
                            "value": "positive"
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
                            "key": "result",
                            "value": "negative"
                        }
                    }
                ]
            }
        },
        {
            "type": "GetVar",
            "params": {
                "key": "result"
            }
        }
    ]
    
    state = {
        "steps": steps,
        "initial_context": {},
        "debug_mode": False,
        "result": {},
        "error": None
    }
    
    try:
        result = await workflow_graph.ainvoke(state)
        if result["error"]:
            print(f"❌ 错误: {result['error']}")
            return False
        
        workflow_result = result["result"]
        if workflow_result["success"]:
            result_value = workflow_result["result"].get("result")
            print(f"✅ 成功: result = {result_value}")
            return result_value == "positive"
        else:
            print(f"❌ 失败: {workflow_result.get('error', '未知错误')}")
            return False
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        return False


async def test_string_operations():
    """测试字符串操作"""
    print("\n=== 测试字符串操作 ===")
    
    steps = [
        {
            "type": "SetVar",
            "params": {
                "key": "text",
                "value": "  hello world  "
            }
        },
        {
            "type": "StringOp",
            "params": {
                "operation": "strip",
                "input_key": "text",
                "output_key": "trimmed"
            }
        },
        {
            "type": "GetVar",
            "params": {
                "key": "trimmed"
            }
        }
    ]
    
    state = {
        "steps": steps,
        "initial_context": {},
        "debug_mode": False,
        "result": {},
        "error": None
    }
    
    try:
        result = await workflow_graph.ainvoke(state)
        if result["error"]:
            print(f"❌ 错误: {result['error']}")
            return False
        
        workflow_result = result["result"]
        if workflow_result["success"]:
            trimmed = workflow_result["result"].get("trimmed")
            print(f"✅ 成功: trimmed = '{trimmed}'")
            return trimmed == "hello world"
        else:
            print(f"❌ 失败: {workflow_result.get('error', '未知错误')}")
            return False
    except Exception as e:
        print(f"❌ 异常: {str(e)}")
        return False


async def main():
    """主测试函数"""
    print("=" * 60)
    print("工作流系统测试")
    print("=" * 60)
    
    results = []
    
    # 测试步骤注册表
    results.append(("步骤注册表", test_step_registry()))
    
    # 测试基础工作流
    results.append(("基础工作流", await test_basic_workflow()))
    
    # 测试数学计算
    results.append(("数学计算工作流", await test_math_workflow()))
    
    # 测试条件控制
    results.append(("条件控制工作流", await test_conditional_workflow()))
    
    # 测试字符串操作
    results.append(("字符串操作", await test_string_operations()))
    
    # 输出测试总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过!")
        return 0
    else:
        print("⚠️  部分测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

