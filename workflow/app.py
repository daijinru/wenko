"""LangGraph Studio 应用入口文件

导出工作流图供 LangGraph Studio 使用。
"""

from graph import workflow_graph

# 导出工作流图供 LangGraph Studio 使用
__all__ = ["workflow_graph"]