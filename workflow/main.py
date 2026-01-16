"""FastAPI 应用主文件

情感记忆 AI 系统 - 提供聊天、情感检测和记忆管理 API。
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import uvicorn

import chat_db
import memory_manager
import chat_processor


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


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    service: str


class DeleteResponse(BaseModel):
    """删除响应"""
    success: bool
    message: str


# 聊天记录相关模型
class ChatSessionInfo(BaseModel):
    """会话信息"""
    id: str
    created_at: str
    updated_at: str
    title: Optional[str] = None
    message_count: int = 0


class ChatMessageInfo(BaseModel):
    """消息信息"""
    id: int
    session_id: str
    role: str
    content: str
    created_at: str


class ChatHistoryListResponse(BaseModel):
    """聊天会话列表响应"""
    sessions: List[ChatSessionInfo]
    count: int


class ChatSessionDetailResponse(BaseModel):
    """会话详情响应"""
    session: ChatSessionInfo
    messages: List[ChatMessageInfo]


class ChatHistoryDeleteResponse(BaseModel):
    """删除聊天记录响应"""
    success: bool
    deleted_count: Optional[int] = None


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    chat_db.init_database()
    yield
    # 关闭时的清理操作（如需要）


# 创建 FastAPI 应用
app = FastAPI(
    title="情感记忆 AI 系统",
    description="提供聊天、情感检测和记忆管理功能的 API",
    version="0.2.0",
    lifespan=lifespan
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    return HealthResponse(
        status="healthy",
        service="emotion-memory-system"
    )


async def stream_chat_response(request: ChatRequest):
    """流式调用 LLM API 并生成 SSE 事件

    如果提供了 session_id，消息会自动保存到数据库。
    支持记忆和情绪系统（可通过 USE_MEMORY_EMOTION_SYSTEM 环境变量开关）。
    """
    try:
        config = load_chat_config()
    except FileNotFoundError as e:
        yield f'event: error\ndata: {json.dumps({"type": "error", "payload": {"message": str(e)}})}\n\n'
        return
    except Exception as e:
        yield f'event: error\ndata: {json.dumps({"type": "error", "payload": {"message": f"配置加载失败: {str(e)}"}})}\n\n'
        return

    # 确定 session_id
    session_id = request.session_id or str(uuid.uuid4())

    # 如果提供了 session_id，保存用户消息到数据库
    if request.session_id:
        try:
            chat_db.add_message(request.session_id, "user", request.message)
        except Exception as e:
            print(f"保存用户消息失败: {e}")

    # 检查是否启用记忆/情绪系统
    use_memory_system = chat_processor.is_memory_emotion_enabled()

    # 构建消息列表
    chat_context = None
    if use_memory_system:
        try:
            # 构建带记忆的上下文
            chat_context = chat_processor.build_chat_context(session_id, request.message)
            messages = chat_processor.build_memory_aware_messages(chat_context)
        except Exception as e:
            print(f"构建记忆上下文失败，回退到简单模式: {e}")
            use_memory_system = False

    if not use_memory_system:
        # 简单模式：使用配置的 system_prompt
        messages = [{"role": "system", "content": config.system_prompt}]
        if request.history:
            for msg in request.history:
                messages.append({"role": msg.role, "content": msg.content})
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

    # 用于收集完整的助手响应
    assistant_response = ""
    detected_emotion = None

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
                                assistant_response += content
                                # 在记忆模式下，先收集完整响应再解析
                                if not use_memory_system:
                                    yield f'event: text\ndata: {json.dumps({"type": "text", "payload": {"content": content}})}\n\n'
                        except json.JSONDecodeError:
                            continue

        # 处理完整响应
        final_response = assistant_response
        if use_memory_system and assistant_response and chat_context:
            try:
                # 解析 LLM 的 JSON 输出
                chat_result = chat_processor.process_llm_response(assistant_response, chat_context)
                final_response = chat_result.response
                detected_emotion = chat_result.emotion

                # 发送解析后的响应文本
                yield f'event: text\ndata: {json.dumps({"type": "text", "payload": {"content": final_response}})}\n\n'

                # 发送情绪信息
                if detected_emotion:
                    yield f'event: emotion\ndata: {json.dumps({"type": "emotion", "payload": {"primary": detected_emotion.primary, "category": detected_emotion.category, "confidence": detected_emotion.confidence}})}\n\n'

            except Exception as e:
                print(f"解析 LLM 响应失败: {e}")
                # 回退：直接使用原始响应
                final_response = chat_processor.extract_response_text(assistant_response)
                yield f'event: text\ndata: {json.dumps({"type": "text", "payload": {"content": final_response}})}\n\n'

        # 保存助手消息到数据库
        if request.session_id and final_response:
            try:
                chat_db.add_message(request.session_id, "assistant", final_response)
            except Exception as e:
                print(f"保存助手消息失败: {e}")

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


# ============ 聊天历史记录 API ============

@app.get("/chat/history", response_model=ChatHistoryListResponse)
async def get_chat_history(limit: int = 100, offset: int = 0):
    """获取聊天会话列表

    返回所有会话，按 updated_at 降序排列。
    """
    try:
        sessions = chat_db.list_sessions(limit=limit, offset=offset)
        session_list = [
            ChatSessionInfo(
                id=s["id"],
                created_at=s["created_at"],
                updated_at=s["updated_at"],
                title=s.get("title"),
                message_count=s.get("message_count", 0)
            )
            for s in sessions
        ]
        return ChatHistoryListResponse(sessions=session_list, count=len(session_list))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")


@app.get("/chat/history/{session_id}", response_model=ChatSessionDetailResponse)
async def get_chat_session(session_id: str):
    """获取特定会话的详情和消息列表"""
    try:
        result = chat_db.get_session_with_messages(session_id)
        if not result:
            raise HTTPException(status_code=404, detail="会话不存在")

        session = result["session"]
        messages = result["messages"]

        # 计算消息数
        message_count = len(messages)

        session_info = ChatSessionInfo(
            id=session["id"],
            created_at=session["created_at"],
            updated_at=session["updated_at"],
            title=session.get("title"),
            message_count=message_count
        )

        message_list = [
            ChatMessageInfo(
                id=m["id"],
                session_id=m["session_id"],
                role=m["role"],
                content=m["content"],
                created_at=m["created_at"]
            )
            for m in messages
        ]

        return ChatSessionDetailResponse(session=session_info, messages=message_list)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话详情失败: {str(e)}")


@app.delete("/chat/history/{session_id}", response_model=ChatHistoryDeleteResponse)
async def delete_chat_session(session_id: str):
    """删除特定会话及其所有消息"""
    try:
        success = chat_db.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")
        return ChatHistoryDeleteResponse(success=True)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")


@app.delete("/chat/history", response_model=ChatHistoryDeleteResponse)
async def clear_chat_history():
    """清空所有聊天记录"""
    try:
        deleted_count = chat_db.delete_all_sessions()
        return ChatHistoryDeleteResponse(success=True, deleted_count=deleted_count)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空聊天记录失败: {str(e)}")


# ============ Memory Management API ============

class MemoryEntryInfo(BaseModel):
    """记忆条目信息"""
    id: str
    session_id: Optional[str] = None
    category: str
    key: str
    value: Any
    confidence: float
    source: str
    created_at: str
    last_accessed: str
    access_count: int


class MemoryEntryCreateRequest(BaseModel):
    """创建记忆条目请求"""
    category: str
    key: str
    value: Any
    confidence: float = 0.9
    source: str = "user_stated"


class MemoryEntryUpdateRequest(BaseModel):
    """更新记忆条目请求"""
    key: Optional[str] = None
    value: Optional[Any] = None
    category: Optional[str] = None
    confidence: Optional[float] = None


class MemoryListResponse(BaseModel):
    """记忆列表响应"""
    memories: List[MemoryEntryInfo]
    total: int


class MemoryBatchDeleteRequest(BaseModel):
    """批量删除请求"""
    ids: List[str]


class MemoryBatchDeleteResponse(BaseModel):
    """批量删除响应"""
    success: bool
    deleted_count: int


class MemoryImportRequest(BaseModel):
    """导入记忆请求"""
    memories: List[MemoryEntryCreateRequest]
    mode: str = "skip"  # skip | overwrite | merge


class MemoryImportResponse(BaseModel):
    """导入记忆响应"""
    success: bool
    imported_count: int
    skipped_count: int


class WorkingMemoryInfo(BaseModel):
    """工作记忆信息"""
    session_id: str
    current_topic: Optional[str] = None
    context_variables: Dict[str, Any] = {}
    turn_count: int
    last_emotion: Optional[str] = None
    created_at: str
    updated_at: str


def _memory_entry_to_info(entry: memory_manager.MemoryEntry) -> MemoryEntryInfo:
    """Convert MemoryEntry to MemoryEntryInfo."""
    return MemoryEntryInfo(
        id=entry.id,
        session_id=entry.session_id,
        category=entry.category,
        key=entry.key,
        value=entry.value,
        confidence=entry.confidence,
        source=entry.source,
        created_at=entry.created_at.isoformat(),
        last_accessed=entry.last_accessed.isoformat(),
        access_count=entry.access_count,
    )


@app.get("/memory/long-term", response_model=MemoryListResponse)
async def list_long_term_memories(
    category: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    order_by: str = "last_accessed",
):
    """获取长期记忆列表

    支持按类别筛选和分页。
    """
    try:
        entries = memory_manager.list_memory_entries(
            category=category,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )
        total = memory_manager.count_memory_entries(category=category)

        memories = [_memory_entry_to_info(e) for e in entries]
        return MemoryListResponse(memories=memories, total=total)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取记忆列表失败: {str(e)}")


@app.get("/memory/long-term/{memory_id}", response_model=MemoryEntryInfo)
async def get_long_term_memory(memory_id: str):
    """获取特定长期记忆详情"""
    try:
        entry = memory_manager.get_memory_entry(memory_id)
        if not entry:
            raise HTTPException(status_code=404, detail="记忆不存在")
        return _memory_entry_to_info(entry)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取记忆失败: {str(e)}")


@app.post("/memory/long-term", response_model=MemoryEntryInfo)
async def create_long_term_memory(request: MemoryEntryCreateRequest):
    """手动创建长期记忆条目"""
    try:
        entry = memory_manager.create_memory_entry(
            category=request.category,
            key=request.key,
            value=request.value,
            confidence=request.confidence,
            source=request.source,
        )
        return _memory_entry_to_info(entry)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"创建记忆失败: {str(e)}")


@app.put("/memory/long-term/{memory_id}", response_model=MemoryEntryInfo)
async def update_long_term_memory(memory_id: str, request: MemoryEntryUpdateRequest):
    """更新长期记忆条目"""
    try:
        entry = memory_manager.update_memory_entry(
            memory_id=memory_id,
            key=request.key,
            value=request.value,
            category=request.category,
            confidence=request.confidence,
        )
        if not entry:
            raise HTTPException(status_code=404, detail="记忆不存在")
        return _memory_entry_to_info(entry)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"更新记忆失败: {str(e)}")


@app.delete("/memory/long-term/{memory_id}", response_model=DeleteResponse)
async def delete_long_term_memory(memory_id: str):
    """删除特定长期记忆"""
    try:
        success = memory_manager.delete_memory_entry(memory_id)
        if not success:
            raise HTTPException(status_code=404, detail="记忆不存在")
        return DeleteResponse(success=True, message="记忆删除成功")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除记忆失败: {str(e)}")


@app.delete("/memory/long-term", response_model=MemoryBatchDeleteResponse)
async def clear_all_long_term_memories():
    """清空所有长期记忆"""
    try:
        deleted_count = memory_manager.delete_all_memories()
        return MemoryBatchDeleteResponse(success=True, deleted_count=deleted_count)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空记忆失败: {str(e)}")


@app.post("/memory/long-term/batch-delete", response_model=MemoryBatchDeleteResponse)
async def batch_delete_long_term_memories(request: MemoryBatchDeleteRequest):
    """批量删除长期记忆"""
    try:
        deleted_count = 0
        for memory_id in request.ids:
            if memory_manager.delete_memory_entry(memory_id):
                deleted_count += 1
        return MemoryBatchDeleteResponse(success=True, deleted_count=deleted_count)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量删除失败: {str(e)}")


@app.get("/memory/long-term/export")
async def export_long_term_memories():
    """导出所有长期记忆为 JSON"""
    try:
        entries = memory_manager.list_memory_entries(limit=10000)
        export_data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "memories": [
                {
                    "category": e.category,
                    "key": e.key,
                    "value": e.value,
                    "confidence": e.confidence,
                    "source": e.source,
                }
                for e in entries
            ]
        }
        return export_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出记忆失败: {str(e)}")


@app.post("/memory/long-term/import", response_model=MemoryImportResponse)
async def import_long_term_memories(request: MemoryImportRequest):
    """导入长期记忆

    mode:
    - skip: 跳过已存在的（按 key 判断）
    - overwrite: 覆盖已存在的
    - merge: 合并（更新 confidence 为较高值）
    """
    try:
        imported_count = 0
        skipped_count = 0

        # Get existing keys for duplicate detection
        existing = memory_manager.list_memory_entries(limit=10000)
        existing_keys = {e.key: e for e in existing}

        for mem in request.memories:
            if mem.key in existing_keys:
                if request.mode == "skip":
                    skipped_count += 1
                    continue
                elif request.mode == "overwrite":
                    memory_manager.delete_memory_entry(existing_keys[mem.key].id)
                elif request.mode == "merge":
                    existing_entry = existing_keys[mem.key]
                    memory_manager.update_memory_entry(
                        existing_entry.id,
                        value=mem.value,
                        confidence=max(existing_entry.confidence, mem.confidence),
                    )
                    imported_count += 1
                    continue

            memory_manager.create_memory_entry(
                category=mem.category,
                key=mem.key,
                value=mem.value,
                confidence=mem.confidence,
                source=mem.source,
            )
            imported_count += 1

        return MemoryImportResponse(
            success=True,
            imported_count=imported_count,
            skipped_count=skipped_count,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"导入记忆失败: {str(e)}")


@app.get("/memory/working/{session_id}", response_model=WorkingMemoryInfo)
async def get_working_memory(session_id: str):
    """获取会话的工作记忆"""
    try:
        wm = memory_manager.get_working_memory(session_id)
        if not wm:
            raise HTTPException(status_code=404, detail="工作记忆不存在")
        return WorkingMemoryInfo(
            session_id=wm.session_id,
            current_topic=wm.current_topic,
            context_variables=wm.context_variables,
            turn_count=wm.turn_count,
            last_emotion=wm.last_emotion,
            created_at=wm.created_at.isoformat(),
            updated_at=wm.updated_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取工作记忆失败: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True
    )