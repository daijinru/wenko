"""FastAPI 应用主文件

提供 RESTful API 接口来执行工作流。
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import uvicorn

from graph import workflow_graph
from steps import STEP_REGISTRY


# Chat 相关配置和模型
class ChatMessage(BaseModel):
    """对话消息"""
    role: str  # 'user' | 'assistant'
    content: str


class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    session_id: Optional[str] = None
    history: Optional[List[ChatMessage]] = None


class ChatConfig(BaseModel):
    """对话配置"""
    api_base: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    system_prompt: str = "你是一个友好的 AI 助手。"
    max_tokens: int = 1024
    temperature: float = 0.7


def load_chat_config() -> ChatConfig:
    """加载对话配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), "chat_config.json")

    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"配置文件不存在: {config_path}。请复制 chat_config.example.json 为 chat_config.json 并填写 API Key。"
        )

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    return ChatConfig(**config_data)


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


class StepRegistryResponse(BaseModel):
    """步骤注册表响应"""
    steps: Dict[str, str]
    count: int


# 步骤模板相关模型
class StepTemplate(BaseModel):
    """步骤模板"""
    id: str
    name: str
    description: Optional[str] = None
    steps: List[Dict[str, Any]]
    tags: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime


class CreateStepTemplateRequest(BaseModel):
    """创建步骤模板请求"""
    name: str
    description: Optional[str] = None
    steps: List[Dict[str, Any]]
    tags: Optional[List[str]] = None


class UpdateStepTemplateRequest(BaseModel):
    """更新步骤模板请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None


class StepTemplateListResponse(BaseModel):
    """步骤模板列表响应"""
    templates: List[StepTemplate]
    count: int


class StepTemplateResponse(BaseModel):
    """步骤模板响应"""
    template: StepTemplate


class DeleteResponse(BaseModel):
    """删除响应"""
    success: bool
    message: str


# 存储接口抽象层
class StepTemplateStorageInterface:
    """步骤模板存储接口（为未来数据库集成预留）"""
    
    def create_template(self, request: CreateStepTemplateRequest) -> StepTemplate:
        """创建步骤模板"""
        raise NotImplementedError
    
    def get_template(self, template_id: str) -> Optional[StepTemplate]:
        """获取步骤模板"""
        raise NotImplementedError
    
    def list_templates(self, tags: Optional[List[str]] = None) -> List[StepTemplate]:
        """列出步骤模板"""
        raise NotImplementedError
    
    def update_template(self, template_id: str, request: UpdateStepTemplateRequest) -> Optional[StepTemplate]:
        """更新步骤模板"""
        raise NotImplementedError
    
    def delete_template(self, template_id: str) -> bool:
        """删除步骤模板"""
        raise NotImplementedError
    
    def search_templates(self, query: str) -> List[StepTemplate]:
        """搜索步骤模板"""
        raise NotImplementedError


# 内存存储管理器
class StepTemplateStorage(StepTemplateStorageInterface):
    """步骤模板存储管理器（内存版本）"""
    
    def __init__(self):
        self._templates: Dict[str, StepTemplate] = {}
        self._load_default_templates()
    
    def _load_default_templates(self):
        """加载默认模板"""
        # 字符串操作工作流模板
        string_template = StepTemplate(
            id=str(uuid.uuid4()),
            name="字符串操作工作流",
            description="演示字符串处理操作的工作流示例",
            steps=[
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
            ],
            tags=["字符串", "处理"],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self._templates[string_template.id] = string_template
    
    def create_template(self, request: CreateStepTemplateRequest) -> StepTemplate:
        """创建步骤模板"""
        template = StepTemplate(
            id=str(uuid.uuid4()),
            name=request.name,
            description=request.description,
            steps=request.steps,
            tags=request.tags or [],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self._templates[template.id] = template
        return template
    
    def get_template(self, template_id: str) -> Optional[StepTemplate]:
        """获取步骤模板"""
        return self._templates.get(template_id)
    
    def list_templates(self, tags: Optional[List[str]] = None) -> List[StepTemplate]:
        """列出步骤模板"""
        templates = list(self._templates.values())
        
        if tags:
            # 过滤包含指定标签的模板
            filtered_templates = []
            for template in templates:
                if any(tag in (template.tags or []) for tag in tags):
                    filtered_templates.append(template)
            return filtered_templates
        
        return templates
    
    def update_template(self, template_id: str, request: UpdateStepTemplateRequest) -> Optional[StepTemplate]:
        """更新步骤模板"""
        if template_id not in self._templates:
            return None
        
        template = self._templates[template_id]
        
        # 更新字段
        if request.name is not None:
            template.name = request.name
        if request.description is not None:
            template.description = request.description
        if request.steps is not None:
            template.steps = request.steps
        if request.tags is not None:
            template.tags = request.tags
        
        template.updated_at = datetime.now()
        
        return template
    
    def delete_template(self, template_id: str) -> bool:
        """删除步骤模板"""
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False
    
    def search_templates(self, query: str) -> List[StepTemplate]:
        """搜索步骤模板"""
        query_lower = query.lower()
        results = []
        
        for template in self._templates.values():
            # 在名称、描述和标签中搜索
            if (query_lower in template.name.lower() or
                (template.description and query_lower in template.description.lower()) or
                any(query_lower in tag.lower() for tag in (template.tags or []))):
                results.append(template)
        
        return results


# 全局存储实例
# 当前使用内存存储，未来可以轻松切换到数据库存储
# 例如：template_storage = DatabaseStepTemplateStorage(connection_string="...")
template_storage = StepTemplateStorage()


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


@app.get("/steps", response_model=StepRegistryResponse)
async def get_step_registry():
    """获取步骤注册表接口"""
    # 将步骤类转换为类名字符串
    steps_info = {step_name: step_class.__name__ for step_name, step_class in STEP_REGISTRY.items()}
    
    return StepRegistryResponse(
        steps=steps_info,
        count=len(STEP_REGISTRY)
    )


# 步骤模板 CRUD 接口
@app.post("/templates", response_model=StepTemplateResponse)
async def create_step_template(request: CreateStepTemplateRequest):
    """创建步骤模板"""
    try:
        template = template_storage.create_template(request)
        return StepTemplateResponse(template=template)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"创建模板失败: {str(e)}")


@app.get("/templates", response_model=StepTemplateListResponse)
async def list_step_templates(tags: Optional[str] = None):
    """列出步骤模板"""
    try:
        tag_list = tags.split(",") if tags else None
        templates = template_storage.list_templates(tag_list)
        return StepTemplateListResponse(templates=templates, count=len(templates))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模板列表失败: {str(e)}")


@app.get("/templates/{template_id}", response_model=StepTemplateResponse)
async def get_step_template(template_id: str):
    """获取步骤模板"""
    template = template_storage.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return StepTemplateResponse(template=template)


@app.put("/templates/{template_id}", response_model=StepTemplateResponse)
async def update_step_template(template_id: str, request: UpdateStepTemplateRequest):
    """更新步骤模板"""
    template = template_storage.update_template(template_id, request)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return StepTemplateResponse(template=template)


@app.delete("/templates/{template_id}", response_model=DeleteResponse)
async def delete_step_template(template_id: str):
    """删除步骤模板"""
    success = template_storage.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="模板不存在")
    return DeleteResponse(success=True, message="模板删除成功")


@app.get("/templates/search/{query}", response_model=StepTemplateListResponse)
async def search_step_templates(query: str):
    """搜索步骤模板"""
    try:
        templates = template_storage.search_templates(query)
        return StepTemplateListResponse(templates=templates, count=len(templates))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索模板失败: {str(e)}")


@app.post("/templates/{template_id}/execute", response_model=WorkflowResponse)
async def execute_template(template_id: str, initial_context: Optional[Dict[str, Any]] = None):
    """执行步骤模板"""
    template = template_storage.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    try:
        # 构建工作流状态
        state = {
            "steps": template.steps,
            "initial_context": initial_context or {},
            "debug_mode": False,
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
            error=f"执行模板失败: {str(e)}"
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


async def stream_chat_response(request: ChatRequest):
    """流式调用 LLM API 并生成 SSE 事件"""
    try:
        config = load_chat_config()
    except FileNotFoundError as e:
        yield f'event: error\ndata: {json.dumps({"type": "error", "payload": {"message": str(e)}})}\n\n'
        return
    except Exception as e:
        yield f'event: error\ndata: {json.dumps({"type": "error", "payload": {"message": f"配置加载失败: {str(e)}"}})}\n\n'
        return

    # 构建消息列表
    messages = [{"role": "system", "content": config.system_prompt}]

    # 添加历史消息
    if request.history:
        for msg in request.history:
            messages.append({"role": msg.role, "content": msg.content})

    # 添加当前用户消息
    messages.append({"role": "user", "content": request.message})

    # 调用 OpenAI 兼容 API
    api_url = f"{config.api_base.rstrip('/')}/chat/completions"

    request_body = {
        "model": config.model,
        "messages": messages,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
        "stream": True
    }

    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                api_url,
                json=request_body,
                headers=headers
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield f'event: error\ndata: {json.dumps({"type": "error", "payload": {"message": f"API 请求失败: {response.status_code} - {error_text.decode()}"}})}\n\n'
                    return

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield f'event: text\ndata: {json.dumps({"type": "text", "payload": {"content": content}})}\n\n'
                        except json.JSONDecodeError:
                            continue

        yield f'event: done\ndata: {json.dumps({"type": "done"})}\n\n'

    except httpx.TimeoutException:
        yield f'event: error\ndata: {json.dumps({"type": "error", "payload": {"message": "API 请求超时"}})}\n\n'
    except httpx.ConnectError:
        yield f'event: error\ndata: {json.dumps({"type": "error", "payload": {"message": "无法连接到 API 服务器"}})}\n\n'
    except Exception as e:
        yield f'event: error\ndata: {json.dumps({"type": "error", "payload": {"message": f"请求错误: {str(e)}"}})}\n\n'


@app.post("/chat")
async def chat(request: ChatRequest):
    """对话接口 - 返回 SSE 流式响应"""
    return StreamingResponse(
        stream_chat_response(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True
    )