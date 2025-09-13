"""FastAPI 应用主文件

提供 RESTful API 接口来执行工作流。
"""

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from graph import workflow_graph


# 请求模型
class WorkflowRequest(BaseModel):
    """工作流执行请求"""
    steps: List[Dict[str, Any]]
    initial_context: Optional[Dict[str, Any]] = None
    debug_mode: Optional[bool] = False


# 响应模型
class WorkflowResponse(BaseModel):
    """工作流执行响应"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    service: str


# 创建 FastAPI 应用
app = FastAPI(
    title="LangGraph 工作流系统",
    description="基于 LangGraph 和 FastAPI 的工作流编排系统",
    version="0.1.0"
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    return HealthResponse(
        status="healthy",
        service="workflow-system"
    )


@app.post("/run", response_model=WorkflowResponse)
async def run_workflow(request: WorkflowRequest):
    """执行工作流接口"""
    try:
        # 构建工作流状态
        state = {
            "steps": request.steps,
            "initial_context": request.initial_context or {},
            "debug_mode": request.debug_mode or False,
            "result": {},
            "error": None
        }
        
        # 执行工作流
        result = await workflow_graph.ainvoke(state)
        
        # 返回结果
        if result["error"]:
            return WorkflowResponse(
                success=False,
                result=None,
                error=result["error"]
            )
        else:
            return WorkflowResponse(
                success=result["result"]["success"],
                result=result["result"]["result"],
                error=result["result"]["error"]
            )
            
    except Exception as e:
        return WorkflowResponse(
            success=False,
            result=None,
            error=f"Unexpected error: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )