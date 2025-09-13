"""LangGraph 工作流图定义模块

定义基于 LangGraph 的工作流执行图。
"""

import traceback
from typing import Any, Dict, List, TypedDict

from langgraph.graph import StateGraph
from executor import WorkflowExecutor


class WorkflowContext:
    """工作流上下文"""
    
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.executor = WorkflowExecutor()


class WorkflowState(TypedDict):
    """工作流状态"""
    steps: List[Dict[str, Any]]
    initial_context: Dict[str, Any]
    debug_mode: bool
    result: Dict[str, Any]
    error: str


def execute_workflow(state: WorkflowState) -> WorkflowState:
    """执行工作流"""
    try:
        context = WorkflowContext(debug_mode=state.get('debug_mode', False))
        
        result = context.executor.execute(
            steps=state['steps'],
            initial_context=state.get('initial_context', {})
        )
        
        return {
            **state,
            'result': result,
            'error': None
        }
        
    except Exception as e:
        error_msg = f"Workflow execution failed: {str(e)}\n{traceback.format_exc()}"
        return {
            **state,
            'result': None,
            'error': error_msg
        }


# 创建工作流图
workflow_graph = StateGraph(WorkflowState)

# 添加节点
workflow_graph.add_node("execute_workflow", execute_workflow)

# 设置入口点
workflow_graph.set_entry_point("execute_workflow")

# 添加边
workflow_graph.add_edge("execute_workflow", "__end__")

# 编译图
workflow_graph = workflow_graph.compile()