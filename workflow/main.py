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
import memory_extractor
import chat_processor
import hitl_handler
import image_analyzer
import mcp_manager
import mcp_tool_executor
from emotion_detector import parse_llm_output
from hitl_schema import (
    HITLAction,
    HITLDisplayRequest,
    HITLRequest,
    HITLResponseData,
    HITLResponseResult,
)


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


class ImageChatRequest(BaseModel):
    """图片分析请求"""
    image: str  # Base64 encoded image (data URL or raw base64)
    session_id: Optional[str] = None
    action: str = "analyze_for_memory"  # analyze_only | analyze_for_memory


class ChatConfig(BaseModel):
    """对话配置"""
    api_base: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    system_prompt: str = "你是一个友好的 AI 助手。"
    max_tokens: int = 1024
    temperature: float = 0.7


def load_chat_config() -> ChatConfig:
    """从数据库加载对话配置"""
    settings = chat_db.get_all_settings()

    return ChatConfig(
        api_base=settings.get("llm.api_base", "https://api.openai.com/v1"),
        api_key=settings.get("llm.api_key", ""),
        model=settings.get("llm.model", "gpt-4o-mini"),
        system_prompt=settings.get("llm.system_prompt", "你是一个友好的 AI 助手。"),
        max_tokens=settings.get("llm.max_tokens", 1024),
        temperature=settings.get("llm.temperature", 0.7),
    )


def is_deep_thinking_enabled() -> bool:
    """检查是否启用深度思考模式"""
    value = chat_db.get_setting("llm.deep_thinking_enabled")
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)


def get_deep_thinking_params(config: ChatConfig) -> dict:
    """根据深度思考设置返回 LLM API 参数

    当深度思考关闭时：
    - 使用较低的温度减少发散思考
    - 添加 reasoning_effort: "low" (OpenAI o1/o3 系列)
    - 不添加 thinking 参数 (Claude 默认关闭)

    当深度思考开启时：
    - 保持用户配置的温度
    - 添加 reasoning_effort: "high" (OpenAI o1/o3 系列)
    - 添加 thinking 参数启用深度思考 (Claude API)

    注意：不同 API 支持的参数不同，不支持的参数会被忽略。

    Args:
        config: 对话配置

    Returns:
        包含 temperature 和其他思考控制参数的字典
    """
    if is_deep_thinking_enabled():
        return {
            "temperature": config.temperature,
            # OpenAI o1/o3 系列模型支持的参数
            "reasoning_effort": "high",
            # Claude API 支持的参数（需要启用 extended thinking）
            "thinking": {
                "type": "enabled",
                "budget_tokens": 10000,  # 默认 10K tokens 思考预算
            },
        }
    else:
        # 深度思考关闭：使用多种策略减弱思考
        return {
            # 基础策略：降低温度减少发散思考
            "temperature": min(config.temperature, 0.3),
            # OpenAI o1/o3 系列：使用低推理努力
            "reasoning_effort": "low",
            # Claude API：不添加 thinking 参数即为关闭
            # DeepSeek：reasoning 模型无法关闭思考，只能通过模型选择
        }


def build_request_body_with_thinking(
    config: ChatConfig,
    messages: list,
    stream: bool = True,
) -> dict:
    """构建包含深度思考参数的请求体

    根据深度思考设置和 API 兼容性构建请求体。
    对于不支持某些参数的 API，这些参数会被安全忽略。

    Args:
        config: 对话配置
        messages: 消息列表
        stream: 是否流式响应

    Returns:
        完整的 API 请求体
    """
    deep_thinking_enabled = is_deep_thinking_enabled()
    deep_thinking_params = get_deep_thinking_params(config)

    request_body = {
        "model": config.model,
        "messages": messages,
        "max_tokens": config.max_tokens,
        "temperature": deep_thinking_params["temperature"],
        "stream": stream,
    }

    # 根据深度思考状态添加额外参数
    if deep_thinking_enabled:
        # 添加 reasoning_effort（OpenAI 兼容）
        request_body["reasoning_effort"] = deep_thinking_params.get("reasoning_effort", "high")
        # 添加 thinking 参数（Claude 兼容）
        if "thinking" in deep_thinking_params:
            request_body["thinking"] = deep_thinking_params["thinking"]
    else:
        # 关闭时也设置 reasoning_effort 为 low
        request_body["reasoning_effort"] = deep_thinking_params.get("reasoning_effort", "low")

    # 打印请求参数日志（不包含 messages 内容，避免日志过大）
    log_params = {k: v for k, v in request_body.items() if k != "messages"}
    log_params["messages_count"] = len(messages)
    print(f"[DeepThinking] enabled={deep_thinking_enabled}, request_params={log_params}")

    return request_body


# 深度思考关闭时追加的提示词
DISABLE_THINKING_PROMPT_SUFFIX = "\n\n请直接回答问题，不需要展示思考过程。保持简洁明了。"


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
    import asyncio
    # 启动时初始化数据库
    chat_db.init_database()
    # 初始化 MCP 管理器 (auto-starts servers with auto_start=True)
    mcp_manager.init_mcp_manager()

    # Fetch tools list for all running MCP servers to populate cache
    pm = mcp_manager.get_process_manager()
    running_servers = pm.get_running_servers()
    if running_servers:
        print(f"[MCP] Fetching tools list for {len(running_servers)} running servers...")
        # Give servers a moment to initialize
        await asyncio.sleep(0.5)
        for server in running_servers:
            try:
                tools = await mcp_tool_executor.list_service_tools(server.name)
                print(f"[MCP] Cached {len(tools)} tools from server: {server.name}")
            except Exception as e:
                print(f"[MCP] Failed to fetch tools list from {server.name}: {e}")

    yield
    # 关闭时清理 MCP 服务进程
    stopped_count = mcp_manager.shutdown_mcp_manager()
    if stopped_count > 0:
        print(f"[MCP] Stopped {stopped_count} running MCP servers on shutdown")


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


# ============ MCP Tool Result Follow-up ============

# Prompt template for generating a final response after tool execution
MCP_FOLLOWUP_PROMPT = """你是一个友好的 AI 助手。你刚才调用了一个工具，以下是工具返回的结果。
请根据工具结果为用户生成一个自然、有用的回复。

工具名称: {tool_name}
工具服务: {service_name}
调用状态: {status}
{result_section}

用户原始请求上下文: {user_context}

以纯 JSON 格式回复:
{{"emotion":{{"primary":"neutral","category":"neutral","confidence":0.8}},"response":"你的回复","memory_update":{{"should_store":false,"entries":[]}}}}

直接输出 JSON:"""


async def call_llm_with_tool_result(
    config: "ChatConfig",
    tool_result: "mcp_tool_executor.ToolCallResult",
    user_context: str,
) -> Optional[str]:
    """Call LLM again with tool result to generate a natural response.

    Args:
        config: Chat config with API credentials
        tool_result: Result from MCP tool execution
        user_context: Original user request context for reference

    Returns:
        LLM's response text, or None if failed
    """
    import time
    start = time.time()

    status = "成功" if tool_result.success else "失败"
    if tool_result.success:
        result_section = f"工具返回结果:\n{tool_result.result}"
    else:
        result_section = f"错误信息: {tool_result.error}"

    system_prompt = MCP_FOLLOWUP_PROMPT.format(
        tool_name=tool_result.tool_name,
        service_name=tool_result.service_name,
        status=status,
        result_section=result_section,
        user_context=user_context[:500],  # Truncate to avoid overly long prompts
    )

    if not is_deep_thinking_enabled():
        system_prompt += DISABLE_THINKING_PROMPT_SUFFIX

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "请根据工具结果给出回复。"},
    ]

    api_url = f"{config.api_base.rstrip('/')}/chat/completions"
    request_body = build_request_body_with_thinking(config, messages, stream=False)
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }

    try:
        print(f"[MCP Followup] Calling LLM with tool result...")
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(api_url, json=request_body, headers=headers)
            if resp.status_code != 200:
                print(f"[MCP Followup] API error: {resp.status_code}")
                return None

            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"[MCP Followup] Got response in {time.time() - start:.2f}s, length={len(content)}")
            return content
    except Exception as e:
        print(f"[MCP Followup] Failed: {e}")
        return None


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
    intent_result = None

    if use_memory_system:
        try:
            # 先运行意图识别（使用 async 版本支持 Layer 2 LLM）
            if chat_processor.is_intent_recognition_enabled():
                async with httpx.AsyncClient() as intent_client:
                    intent_result = await chat_processor.recognize_intent_async(
                        message=request.message,
                        llm_client=intent_client,
                        api_base=config.api_base,
                        api_key=config.api_key,
                        model=config.model,
                    )

            # 构建带记忆的上下文
            chat_context = chat_processor.build_chat_context(session_id, request.message)
            # 将意图识别结果注入到上下文
            chat_context.intent_result = intent_result
            messages = chat_processor.build_memory_aware_messages(chat_context)
        except Exception as e:
            print(f"构建记忆上下文失败，回退到简单模式: {e}")
            use_memory_system = False

    if not use_memory_system:
        # 简单模式：使用配置的 system_prompt
        system_prompt = config.system_prompt
        # 深度思考关闭时追加提示词
        if not is_deep_thinking_enabled():
            system_prompt += DISABLE_THINKING_PROMPT_SUFFIX
        messages = [{"role": "system", "content": system_prompt}]
        if request.history:
            for msg in request.history:
                messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": request.message})

    # 调用 OpenAI 兼容 API
    api_url = f"{config.api_base.rstrip('/')}/chat/completions"

    # 使用统一的请求体构建函数，包含深度思考参数（会打印请求参数日志）
    request_body = build_request_body_with_thinking(config, messages, stream=True)

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
        # 打印响应状态日志
        has_thinking_tags = "<thinking>" in assistant_response.lower() if assistant_response else False
        deep_thinking_mode = is_deep_thinking_enabled()
        print(f"[DeepThinking] Response received: length={len(assistant_response)}, has_thinking_tags={has_thinking_tags}, deep_thinking_enabled={deep_thinking_mode}")

        # 应用 thinking 标签过滤（深度思考关闭时）
        final_response = chat_processor.filter_thinking_tags(assistant_response)

        # 如果进行了过滤，打印过滤结果
        if len(final_response) != len(assistant_response):
            print(f"[DeepThinking] Thinking tags filtered: original_length={len(assistant_response)}, filtered_length={len(final_response)}")

        hitl_request = None

        if use_memory_system and assistant_response and chat_context:
            try:
                # 解析 LLM 的 JSON 输出
                chat_result = chat_processor.process_llm_response(assistant_response, chat_context)
                final_response = chat_result.response
                detected_emotion = chat_result.emotion

                # 检查是否有 HITL 请求
                if chat_processor.is_hitl_enabled():
                    print(f"[HITL] Checking for HITL in response (length={len(assistant_response)})")
                    hitl_request = hitl_handler.extract_hitl_from_llm_response(assistant_response)
                    if hitl_request:
                        if isinstance(hitl_request, HITLDisplayRequest):
                            print(f"[HITL] Found visual_display request: id={hitl_request.id}, title={hitl_request.title}, displays={len(hitl_request.displays)}")
                            hitl_handler.store_display_request(hitl_request, session_id)
                        else:
                            print(f"[HITL] Found form request: id={hitl_request.id}, title={hitl_request.title}, fields={len(hitl_request.fields)}")
                            hitl_handler.store_hitl_request(hitl_request, session_id)
                    else:
                        print("[HITL] No HITL request found in response")

                # 发送解析后的响应文本
                yield f'event: text\ndata: {json.dumps({"type": "text", "payload": {"content": final_response}})}\n\n'

                # 发送情绪信息
                if detected_emotion:
                    yield f'event: emotion\ndata: {json.dumps({"type": "emotion", "payload": {"primary": detected_emotion.primary, "category": detected_emotion.category, "confidence": detected_emotion.confidence}})}\n\n'

                # 发送记忆保存事件
                if chat_result.memories_to_store:
                    memory_payload = {
                        "count": len(chat_result.memories_to_store),
                        "entries": chat_result.memories_to_store,
                    }
                    yield f'event: memory_saved\ndata: {json.dumps({"type": "memory_saved", "payload": memory_payload})}\n\n'

                # 发送 HITL 请求事件
                if hitl_request:
                    print(f"[HITL] Sending HITL SSE event for request {hitl_request.id}, type={hitl_request.type}")
                    if isinstance(hitl_request, HITLDisplayRequest):
                        # visual_display 类型
                        hitl_payload = {
                            "id": hitl_request.id,
                            "type": hitl_request.type,
                            "title": hitl_request.title,
                            "description": hitl_request.description,
                            "displays": [
                                {
                                    "type": d.type.value if hasattr(d.type, 'value') else str(d.type),
                                    "data": d.data,
                                }
                                for d in hitl_request.displays
                            ],
                            "dismiss_label": hitl_request.dismiss_label,
                            "session_id": session_id,
                        }
                    else:
                        # form 类型
                        hitl_payload = {
                            "id": hitl_request.id,
                            "type": hitl_request.type,
                            "title": hitl_request.title,
                            "description": hitl_request.description,
                            "fields": [
                                {
                                    "name": f.name,
                                    "type": f.type.value,
                                    "label": f.label,
                                    "required": f.required,
                                    "placeholder": f.placeholder,
                                    "default": f.default,
                                    "options": [{"value": o.value, "label": o.label} for o in f.options] if f.options else None,
                                    "min": f.min,
                                    "max": f.max,
                                    "step": f.step,
                                }
                                for f in hitl_request.fields
                            ],
                            "actions": {
                                "approve": {"label": hitl_request.actions.approve.label, "style": hitl_request.actions.approve.style.value},
                                "edit": {"label": hitl_request.actions.edit.label, "style": hitl_request.actions.edit.style.value},
                                "reject": {"label": hitl_request.actions.reject.label, "style": hitl_request.actions.reject.style.value},
                            },
                            "session_id": session_id,
                        }
                    yield f'event: hitl\ndata: {json.dumps({"type": "hitl", "payload": hitl_payload})}\n\n'

                # 检查是否有 MCP 工具调用请求
                tool_call_request = chat_processor.extract_tool_call(assistant_response)
                if tool_call_request:
                    print(f"[MCP] Found tool_call: name={tool_call_request.name}, method={tool_call_request.method}")
                    # 执行工具调用
                    tool_result = await mcp_tool_executor.execute_mcp_tool(
                        service_name=tool_call_request.name,
                        method=tool_call_request.method,
                        arguments=tool_call_request.arguments,
                    )
                    # 发送工具调用结果 SSE 事件
                    tool_result_payload = {
                        "success": tool_result.success,
                        "tool_name": tool_result.tool_name,
                        "service_name": tool_result.service_name,
                        "result": tool_result.result,
                        "error": tool_result.error,
                    }
                    yield f'event: tool_result\ndata: {json.dumps({"type": "tool_result", "payload": tool_result_payload})}\n\n'
                    print(f"[MCP] Tool result sent: success={tool_result.success}")

                    # 二次调用 LLM，将工具结果转化为自然语言回复
                    followup_response = await call_llm_with_tool_result(
                        config=config,
                        tool_result=tool_result,
                        user_context=request.message,
                    )
                    if followup_response:
                        # 解析 followup 响应
                        try:
                            followup_parsed = parse_llm_output(followup_response)
                            followup_text = followup_parsed.response
                            print(f"[MCP Followup] Parsed response: {len(followup_text)} chars")
                        except Exception:
                            followup_text = chat_processor.extract_response_text(followup_response)
                            print(f"[MCP Followup] Using raw response: {len(followup_text)} chars")

                        # 发送 followup 响应
                        yield f'event: text\ndata: {json.dumps({"type": "text", "payload": {"content": followup_text}})}\n\n'
                        # 更新 final_response 用于保存到数据库
                        final_response = followup_text

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


# ============ 图片分析 API ============

async def stream_image_analysis(request: ImageChatRequest):
    """分析图片并提取文本，可选生成记忆保存 HITL 请求。

    支持两种模式：
    - analyze_only: 仅分析图片返回文本
    - analyze_for_memory: 分析后生成 HITL 让用户确认保存到记忆
    """
    session_id = request.session_id or str(uuid.uuid4())

    try:
        # Step 1: 使用 Vision API 分析图片
        extracted_text = await image_analyzer.analyze_image_text(request.image)

        # 发送提取的文本
        text_content = f"📷 图片文本识别结果：\n\n{extracted_text}"
        yield f'event: text\ndata: {json.dumps({"type": "text", "payload": {"content": text_content}})}\n\n'

        # 检查是否有有效文本内容
        if not image_analyzer.has_text_content(extracted_text):
            no_text_msg = "\n\n图片中未识别到可保存的文本内容。"
            yield f'event: text\ndata: {json.dumps({"type": "text", "payload": {"content": no_text_msg}})}\n\n'
            yield f'event: done\ndata: {json.dumps({"type": "done"})}\n\n'
            return

        # Step 2: 如果是 analyze_for_memory 模式，尝试提取记忆信息
        if request.action == "analyze_for_memory":
            try:
                # 使用 memory_extractor 从文本中提取记忆信息
                memory_result = await memory_extractor.extract_memory_from_message(
                    content=extracted_text,
                    role="user",
                    source="image",  # 标记来源为图片OCR
                )

                # 调试日志
                if memory_result:
                    print(f"[ImageAnalysis] memory_result: key={memory_result.key}, category={memory_result.category}, confidence={memory_result.confidence}")
                else:
                    print("[ImageAnalysis] memory_result is None")

                if memory_result and memory_result.confidence >= 0.3:
                    # 生成 HITL 请求让用户确认
                    from hitl_schema import (
                        HITLRequest as HITLRequestModel,
                        HITLField,
                        HITLFieldType,
                        HITLOption,
                        HITLActions,
                        HITLActionButton,
                        HITLActionStyle,
                        HITLContext,
                    )

                    # 基础字段
                    fields = [
                        HITLField(
                            name="key",
                            type=HITLFieldType.TEXT,
                            label="记忆名称",
                            required=True,
                            placeholder="例如：会议笔记、书籍摘录、周五聚餐",
                            default=memory_result.key,
                        ),
                        HITLField(
                            name="value",
                            type=HITLFieldType.TEXTAREA,
                            label="记忆内容",
                            required=True,
                            placeholder="提取的文本内容",
                            default=memory_result.value,
                        ),
                        HITLField(
                            name="category",
                            type=HITLFieldType.SELECT,
                            label="类别",
                            required=True,
                            default=memory_result.category,
                            options=[
                                HITLOption(value="preference", label="偏好"),
                                HITLOption(value="fact", label="事实"),
                                HITLOption(value="pattern", label="模式"),
                                HITLOption(value="plan", label="计划"),
                            ],
                        ),
                    ]

                    # 如果是计划类别，添加计划特定字段
                    if memory_result.category == "plan":
                        fields.extend([
                            HITLField(
                                name="target_time",
                                type=HITLFieldType.TEXT,
                                label="目标时间",
                                required=True,
                                placeholder="例如：2025-01-28T14:00:00",
                                default=memory_result.target_time or "",
                            ),
                            HITLField(
                                name="location",
                                type=HITLFieldType.TEXT,
                                label="地点",
                                required=False,
                                placeholder="例如：会议室A、星巴克",
                                default=memory_result.location or "",
                            ),
                            HITLField(
                                name="participants",
                                type=HITLFieldType.TEXT,
                                label="参与者",
                                required=False,
                                placeholder="例如：张三,李四",
                                default=memory_result.participants or "",
                            ),
                        ])

                    # 确定 intent 和 memory_category
                    if memory_result.category == "plan":
                        intent = "collect_plan"
                        hitl_type = "image_plan_confirm"
                        hitl_title = "保存计划到日程"
                        hitl_description = "AI 从图片中识别到计划安排，请确认是否保存到日程。"
                    else:
                        intent = "collect_preference"
                        hitl_type = "image_memory_confirm"
                        hitl_title = "保存图片内容到长期记忆"
                        hitl_description = "AI 从图片中提取了以下信息，请确认是否保存。"

                    hitl_request = HITLRequestModel(
                        id=str(uuid.uuid4()),
                        type=hitl_type,
                        title=hitl_title,
                        description=hitl_description,
                        fields=fields,
                        actions=HITLActions(
                            approve=HITLActionButton(label="保存", style=HITLActionStyle.PRIMARY),
                            edit=HITLActionButton(label="编辑", style=HITLActionStyle.DEFAULT),
                            reject=HITLActionButton(label="跳过", style=HITLActionStyle.SECONDARY),
                        ),
                        context=HITLContext(
                            intent=intent,
                            memory_category=memory_result.category,
                        ),
                    )

                    # 存储 HITL 请求
                    hitl_handler.store_hitl_request(hitl_request, session_id)

                    # 发送 HITL 事件
                    hitl_payload = {
                        "id": hitl_request.id,
                        "type": hitl_request.type,
                        "title": hitl_request.title,
                        "description": hitl_request.description,
                        "fields": [
                            {
                                "name": f.name,
                                "type": f.type.value,
                                "label": f.label,
                                "required": f.required,
                                "placeholder": f.placeholder,
                                "default": f.default,
                                "options": [{"value": o.value, "label": o.label} for o in f.options] if f.options else None,
                            }
                            for f in hitl_request.fields
                        ],
                        "actions": {
                            "approve": {"label": hitl_request.actions.approve.label, "style": hitl_request.actions.approve.style.value},
                            "edit": {"label": hitl_request.actions.edit.label, "style": hitl_request.actions.edit.style.value},
                            "reject": {"label": hitl_request.actions.reject.label, "style": hitl_request.actions.reject.style.value},
                        },
                        "session_id": session_id,
                    }
                    yield f'event: hitl\ndata: {json.dumps({"type": "hitl", "payload": hitl_payload})}\n\n'
                else:
                    no_memory_msg = "\n\n未能从文本中提取出适合保存的记忆信息。"
                    yield f'event: text\ndata: {json.dumps({"type": "text", "payload": {"content": no_memory_msg}})}\n\n'

            except Exception as e:
                print(f"Memory extraction failed: {e}")
                error_msg = f"\n\n记忆提取失败: {str(e)}"
                yield f'event: text\ndata: {json.dumps({"type": "text", "payload": {"content": error_msg}})}\n\n'

        yield f'event: done\ndata: {json.dumps({"type": "done"})}\n\n'

    except ValueError as e:
        yield f'event: error\ndata: {json.dumps({"type": "error", "payload": {"message": str(e)}})}\n\n'
    except Exception as e:
        yield f'event: error\ndata: {json.dumps({"type": "error", "payload": {"message": f"图片分析失败: {str(e)}"}})}\n\n'


@app.post("/chat/image")
async def chat_image(request: ImageChatRequest):
    """图片分析接口 - 返回 SSE 流式响应

    使用 Vision LLM 分析图片中的文本内容，可选保存到长期记忆。
    """
    return StreamingResponse(
        stream_image_analysis(request),
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
    # Plan-specific fields (only when category == 'plan')
    target_time: Optional[str] = None
    reminder_offset_minutes: Optional[int] = None
    repeat_type: Optional[str] = None
    plan_status: Optional[str] = None
    snooze_until: Optional[str] = None


class MemoryEntryCreateRequest(BaseModel):
    """创建记忆条目请求"""
    category: str
    key: str
    value: Any
    confidence: float = 0.9
    source: str = "user_stated"
    # Plan-specific fields (only when category == 'plan')
    target_time: Optional[str] = None
    reminder_offset_minutes: Optional[int] = None
    repeat_type: Optional[str] = None


class MemoryEntryUpdateRequest(BaseModel):
    """更新记忆条目请求"""
    key: Optional[str] = None
    value: Optional[Any] = None
    category: Optional[str] = None
    confidence: Optional[float] = None
    # Plan-specific fields (only when category == 'plan')
    target_time: Optional[str] = None
    reminder_offset_minutes: Optional[int] = None
    repeat_type: Optional[str] = None


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
        target_time=entry.target_time.isoformat() if entry.target_time else None,
        reminder_offset_minutes=entry.reminder_offset_minutes,
        repeat_type=entry.repeat_type,
        plan_status=entry.plan_status,
        snooze_until=entry.snooze_until.isoformat() if entry.snooze_until else None,
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
    """手动创建长期记忆条目

    如果 category 是 'plan'，则创建计划条目并设置提醒相关字段。
    """
    try:
        if request.category == 'plan' and request.target_time:
            # Create as plan entry with time-specific fields
            from datetime import datetime as dt
            target_time = dt.fromisoformat(request.target_time.replace("Z", "+00:00"))
            plan = memory_manager.create_plan(
                title=request.key,
                description=request.value if isinstance(request.value, str) else str(request.value),
                target_time=target_time,
                reminder_offset_minutes=request.reminder_offset_minutes if request.reminder_offset_minutes is not None else 10,
                repeat_type=request.repeat_type or "none",
            )
            # Get the memory entry to return full info
            entry = memory_manager.get_memory_entry(plan.id)
            if entry:
                return _memory_entry_to_info(entry)
            # Fallback: construct from plan
            return MemoryEntryInfo(
                id=plan.id,
                category='plan',
                key=plan.title,
                value=plan.description or '',
                confidence=1.0,
                source='user_stated',
                created_at=plan.created_at.isoformat(),
                last_accessed=plan.updated_at.isoformat(),
                access_count=0,
                target_time=plan.target_time.isoformat(),
                reminder_offset_minutes=plan.reminder_offset_minutes,
                repeat_type=plan.repeat_type,
                plan_status=plan.status,
            )
        else:
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
    """更新长期记忆条目

    如果是 plan 类别，同时更新计划相关字段。
    """
    try:
        # Check if this is a plan entry
        existing = memory_manager.get_memory_entry(memory_id)
        if existing and existing.category == 'plan':
            # Update as plan entry
            from datetime import datetime as dt
            target_time = None
            if request.target_time:
                target_time = dt.fromisoformat(request.target_time.replace("Z", "+00:00"))

            plan = memory_manager.update_plan(
                plan_id=memory_id,
                title=request.key,
                description=request.value if isinstance(request.value, str) else str(request.value) if request.value else None,
                target_time=target_time,
                reminder_offset_minutes=request.reminder_offset_minutes,
                repeat_type=request.repeat_type,
            )
            if not plan:
                raise HTTPException(status_code=404, detail="记忆不存在")
            entry = memory_manager.get_memory_entry(memory_id)
            if entry:
                return _memory_entry_to_info(entry)
            raise HTTPException(status_code=404, detail="记忆不存在")
        else:
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


class WorkingMemoryListResponse(BaseModel):
    """工作记忆列表响应"""
    memories: List[WorkingMemoryInfo]
    total: int


@app.get("/memory/working", response_model=WorkingMemoryListResponse)
async def list_working_memories(limit: int = 100):
    """获取所有活跃的工作记忆列表"""
    try:
        memories = memory_manager.list_working_memories(limit=limit)
        result = [
            WorkingMemoryInfo(
                session_id=wm.session_id,
                current_topic=wm.current_topic,
                context_variables=wm.context_variables,
                turn_count=wm.turn_count,
                last_emotion=wm.last_emotion,
                created_at=wm.created_at.isoformat(),
                updated_at=wm.updated_at.isoformat(),
            )
            for wm in memories
        ]
        return WorkingMemoryListResponse(memories=result, total=len(result))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取工作记忆列表失败: {str(e)}")


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


@app.delete("/memory/working/{session_id}", response_model=DeleteResponse)
async def delete_working_memory(session_id: str):
    """清除指定会话的工作记忆"""
    try:
        success = memory_manager.delete_working_memory(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="工作记忆不存在")
        return DeleteResponse(success=True, message="工作记忆已清除")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清除工作记忆失败: {str(e)}")


# ============ Memory Extract API ============

class MemoryExtractRequest(BaseModel):
    """智能提取记忆请求"""
    content: str
    role: str = "user"  # user | assistant


class MemoryExtractResponse(BaseModel):
    """智能提取记忆响应"""
    key: str
    value: str
    category: str
    confidence: float


@app.post("/memory/extract", response_model=MemoryExtractResponse)
async def extract_memory(request: MemoryExtractRequest):
    """从消息内容中智能提取记忆信息

    使用 LLM 分析消息，自动提取键名、值、类别和置信度。
    适用于"保存到长期记忆"对话框的预填充。
    """
    try:
        # Try LLM extraction
        result = await memory_extractor.extract_memory_from_message(
            content=request.content,
            role=request.role,
        )

        if result and result.confidence >= 0.3:
            return MemoryExtractResponse(
                key=result.key,
                value=result.value,
                category=result.category,
                confidence=result.confidence,
            )

        # Fallback to default extraction
        default = memory_extractor.get_default_extraction(
            content=request.content,
            role=request.role,
        )
        return MemoryExtractResponse(
            key=default.key,
            value=default.value,
            category=default.category,
            confidence=default.confidence,
        )
    except Exception as e:
        # On error, return default extraction
        default = memory_extractor.get_default_extraction(
            content=request.content,
            role=request.role,
        )
        return MemoryExtractResponse(
            key=default.key,
            value=default.value,
            category=default.category,
            confidence=default.confidence,
        )


# ============ HITL API ============

class HITLRespondRequest(BaseModel):
    """HITL 响应请求"""
    request_id: str
    session_id: str
    action: str  # approve | edit | reject
    data: Optional[Dict[str, Any]] = None


class HITLContinuationDataResponse(BaseModel):
    """HITL continuation data for frontend"""
    request_title: str
    action: str
    form_data: Optional[Dict[str, Any]] = None
    field_labels: Dict[str, str] = {}


class HITLRespondResponse(BaseModel):
    """HITL 响应结果"""
    success: bool
    next_action: str = "continue"
    message: Optional[str] = None
    error: Optional[str] = None
    continuation_data: Optional[HITLContinuationDataResponse] = None


@app.post("/hitl/respond", response_model=HITLRespondResponse)
async def hitl_respond(request: HITLRespondRequest):
    """处理用户对 HITL 请求的响应

    用户可以选择 approve（批准）、edit（编辑后提交）或 reject（拒绝/跳过）。
    """
    try:
        # 转换 action 字符串为枚举
        try:
            action = HITLAction(request.action)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的 action: {request.action}，必须是 approve/edit/reject"
            )

        # 构建响应数据
        response_data = HITLResponseData(
            request_id=request.request_id,
            session_id=request.session_id,
            action=action,
            data=request.data,
        )

        # 处理响应
        result = hitl_handler.process_hitl_response(response_data)

        # Convert continuation_data if present
        continuation_data_response = None
        if result.continuation_data:
            continuation_data_response = HITLContinuationDataResponse(
                request_title=result.continuation_data.request_title,
                action=result.continuation_data.action,
                form_data=result.continuation_data.form_data,
                field_labels=result.continuation_data.field_labels,
            )

        return HITLRespondResponse(
            success=result.success,
            next_action=result.next_action,
            message=result.message,
            error=result.error,
            continuation_data=continuation_data_response,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理 HITL 响应失败: {str(e)}")


@app.get("/hitl/status/{request_id}")
async def hitl_status(request_id: str):
    """检查 HITL 请求状态"""
    request_data = hitl_handler.get_hitl_request(request_id)
    if request_data is None:
        return {"exists": False, "expired": True}

    request, session_id, expires_at = request_data
    return {
        "exists": True,
        "expired": False,
        "session_id": session_id,
        "title": request.title,
        "expires_at": expires_at.isoformat(),
    }


class HITLContinueRequest(BaseModel):
    """HITL 继续请求"""
    session_id: str
    continuation_data: HITLContinuationDataResponse


async def stream_hitl_continuation(request: HITLContinueRequest):
    """流式调用 LLM API 继续 HITL 后的对话

    使用 continuation_data 构建上下文，调用 LLM 继续对话。
    """
    import time
    start_time = time.time()
    print(f"[HITL-Continue] Starting continuation for session {request.session_id[:8]}...")

    try:
        config = load_chat_config()
    except FileNotFoundError as e:
        yield f'event: error\ndata: {json.dumps({"type": "error", "payload": {"message": str(e)}})}\n\n'
        return
    except Exception as e:
        yield f'event: error\ndata: {json.dumps({"type": "error", "payload": {"message": f"配置加载失败: {str(e)}"}})}\n\n'
        return

    session_id = request.session_id

    # Build continuation context from the HITL response data
    from hitl_schema import HITLContinuationData
    continuation_data = HITLContinuationData(
        request_title=request.continuation_data.request_title,
        action=request.continuation_data.action,
        form_data=request.continuation_data.form_data,
        field_labels=request.continuation_data.field_labels,
    )

    context_start = time.time()
    hitl_context = hitl_handler.build_continuation_context(continuation_data)
    print(f"[HITL-Continue] Context built in {time.time() - context_start:.2f}s, length={len(hitl_context)}")

    # Build the continuation prompt
    prompt_start = time.time()
    system_prompt = chat_processor.build_hitl_continuation_prompt(session_id, hitl_context)
    print(f"[HITL-Continue] Prompt built in {time.time() - prompt_start:.2f}s, length={len(system_prompt)}")

    # 深度思考关闭时追加提示词
    if not is_deep_thinking_enabled():
        system_prompt += DISABLE_THINKING_PROMPT_SUFFIX

    # Prepare messages for LLM
    # Note: Many LLM APIs require at least one user message to respond properly
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "请根据我刚才提交的表单信息给出回复。"},
    ]
    print(f"[HITL-Continue] Total prompt length: {len(system_prompt)} chars, messages: {len(messages)}")

    # Call LLM API
    api_url = f"{config.api_base.rstrip('/')}/chat/completions"

    # 使用统一的请求体构建函数，包含深度思考参数
    request_body = build_request_body_with_thinking(config, messages, stream=True)

    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json"
    }

    assistant_response = ""
    detected_emotion = None

    try:
        print(f"[HITL-Continue] Sending request to {api_url}...")
        api_start = time.time()
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                api_url,
                json=request_body,
                headers=headers
            ) as response:
                print(f"[HITL-Continue] Got response status {response.status_code} in {time.time() - api_start:.2f}s")
                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"[HITL-Continue] API error: {error_text.decode()}")
                    yield f'event: error\ndata: {json.dumps({"type": "error", "payload": {"message": f"API 请求失败: {response.status_code} - {error_text.decode()}"}})}\n\n'
                    return

                first_chunk_time = None
                line_count = 0
                async for line in response.aiter_lines():
                    line_count += 1
                    # Debug: print first few lines
                    if line_count <= 3:
                        print(f"[HITL-Continue] Line {line_count}: {line[:100] if len(line) > 100 else line}")

                    if line.startswith("data: "):
                        if first_chunk_time is None:
                            first_chunk_time = time.time()
                            print(f"[HITL-Continue] First chunk received in {first_chunk_time - api_start:.2f}s")
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                assistant_response += content
                        except json.JSONDecodeError as e:
                            print(f"[HITL-Continue] JSON decode error: {e}, data: {data[:100] if len(data) > 100 else data}")
                            continue

                print(f"[HITL-Continue] Total lines received: {line_count}")

        print(f"[HITL-Continue] Response complete: length={len(assistant_response)}, total_time={time.time() - start_time:.2f}s")

        # Process the complete response
        # 打印响应状态日志
        has_thinking_tags = "<thinking>" in assistant_response.lower() if assistant_response else False
        deep_thinking_mode = is_deep_thinking_enabled()
        print(f"[DeepThinking] HITL continuation response: length={len(assistant_response)}, has_thinking_tags={has_thinking_tags}, deep_thinking_enabled={deep_thinking_mode}")

        # 应用 thinking 标签过滤（深度思考关闭时）
        final_response = chat_processor.filter_thinking_tags(assistant_response)

        # 如果进行了过滤，打印过滤结果
        if len(final_response) != len(assistant_response):
            print(f"[DeepThinking] Thinking tags filtered: original_length={len(assistant_response)}, filtered_length={len(final_response)}")

        hitl_request = None

        if assistant_response:
            try:
                # Parse LLM's JSON output
                print(f"[HITL-Continue] Processing LLM response: {assistant_response[:200]}...")
                chat_context = chat_processor.build_chat_context(session_id, hitl_context)
                chat_result = chat_processor.process_llm_response(assistant_response, chat_context)
                final_response = chat_result.response
                detected_emotion = chat_result.emotion
                print(f"[HITL-Continue] Parsed response: length={len(final_response)}, emotion={detected_emotion}")

                # Check for HITL request (chained HITL support)
                if chat_processor.is_hitl_enabled():
                    hitl_request = hitl_handler.extract_hitl_from_llm_response(assistant_response)
                    if hitl_request:
                        if isinstance(hitl_request, HITLDisplayRequest):
                            print(f"[HITL-Continue] Found visual_display request: id={hitl_request.id}")
                            hitl_handler.store_display_request(hitl_request, session_id)
                        else:
                            print(f"[HITL-Continue] Found form request: id={hitl_request.id}")
                            hitl_handler.store_hitl_request(hitl_request, session_id)

                # Send parsed response text
                print(f"[HITL-Continue] Sending text event: {final_response[:100] if len(final_response) > 100 else final_response}")
                yield f'event: text\ndata: {json.dumps({"type": "text", "payload": {"content": final_response}})}\n\n'

                # Send emotion info
                if detected_emotion:
                    yield f'event: emotion\ndata: {json.dumps({"type": "emotion", "payload": {"primary": detected_emotion.primary, "category": detected_emotion.category, "confidence": detected_emotion.confidence}})}\n\n'

                # Send HITL request event (for chained HITL)
                if hitl_request:
                    print(f"[HITL-Continue] Sending HITL SSE event for request {hitl_request.id}, type={hitl_request.type}")
                    if isinstance(hitl_request, HITLDisplayRequest):
                        hitl_payload = {
                            "id": hitl_request.id,
                            "type": hitl_request.type,
                            "title": hitl_request.title,
                            "description": hitl_request.description,
                            "displays": [
                                {
                                    "type": d.type.value if hasattr(d.type, 'value') else str(d.type),
                                    "data": d.data,
                                }
                                for d in hitl_request.displays
                            ],
                            "dismiss_label": hitl_request.dismiss_label,
                            "session_id": session_id,
                        }
                    else:
                        hitl_payload = {
                            "id": hitl_request.id,
                            "type": hitl_request.type,
                            "title": hitl_request.title,
                            "description": hitl_request.description,
                            "fields": [
                                {
                                    "name": f.name,
                                    "type": f.type.value,
                                    "label": f.label,
                                    "required": f.required,
                                    "placeholder": f.placeholder,
                                    "default": f.default,
                                    "options": [{"value": o.value, "label": o.label} for o in f.options] if f.options else None,
                                    "min": f.min,
                                    "max": f.max,
                                    "step": f.step,
                                }
                                for f in hitl_request.fields
                            ],
                            "actions": {
                                "approve": {"label": hitl_request.actions.approve.label, "style": hitl_request.actions.approve.style.value},
                                "edit": {"label": hitl_request.actions.edit.label, "style": hitl_request.actions.edit.style.value},
                                "reject": {"label": hitl_request.actions.reject.label, "style": hitl_request.actions.reject.style.value},
                            },
                            "session_id": session_id,
                        }
                    yield f'event: hitl\ndata: {json.dumps({"type": "hitl", "payload": hitl_payload})}\n\n'

                # 检查是否有 MCP 工具调用请求 (HITL continuation)
                tool_call_request = chat_processor.extract_tool_call(assistant_response)
                if tool_call_request:
                    print(f"[MCP] Found tool_call in continuation: name={tool_call_request.name}, method={tool_call_request.method}")
                    tool_result = await mcp_tool_executor.execute_mcp_tool(
                        service_name=tool_call_request.name,
                        method=tool_call_request.method,
                        arguments=tool_call_request.arguments,
                    )
                    tool_result_payload = {
                        "success": tool_result.success,
                        "tool_name": tool_result.tool_name,
                        "service_name": tool_result.service_name,
                        "result": tool_result.result,
                        "error": tool_result.error,
                    }
                    yield f'event: tool_result\ndata: {json.dumps({"type": "tool_result", "payload": tool_result_payload})}\n\n'
                    print(f"[MCP] Tool result sent: success={tool_result.success}")

                    # 二次调用 LLM，将工具结果转化为自然语言回复
                    followup_response = await call_llm_with_tool_result(
                        config=config,
                        tool_result=tool_result,
                        user_context=hitl_context,
                    )
                    if followup_response:
                        # 解析 followup 响应
                        try:
                            followup_parsed = parse_llm_output(followup_response)
                            followup_text = followup_parsed.response
                            print(f"[MCP Followup] Parsed response: {len(followup_text)} chars")
                        except Exception:
                            followup_text = chat_processor.extract_response_text(followup_response)
                            print(f"[MCP Followup] Using raw response: {len(followup_text)} chars")

                        # 发送 followup 响应
                        yield f'event: text\ndata: {json.dumps({"type": "text", "payload": {"content": followup_text}})}\n\n'
                        # 更新 final_response 用于保存到数据库
                        final_response = followup_text

            except Exception as e:
                print(f"解析 LLM continuation 响应失败: {e}")
                final_response = chat_processor.extract_response_text(assistant_response)
                yield f'event: text\ndata: {json.dumps({"type": "text", "payload": {"content": final_response}})}\n\n'

        # Save assistant message to database
        if final_response:
            try:
                chat_db.add_message(session_id, "assistant", final_response)
            except Exception as e:
                print(f"保存助手消息失败: {e}")

        yield f'event: done\ndata: {json.dumps({"type": "done"})}\n\n'

    except httpx.TimeoutException:
        yield f'event: error\ndata: {json.dumps({"type": "error", "payload": {"message": "API 请求超时"}})}\n\n'
    except httpx.ConnectError:
        yield f'event: error\ndata: {json.dumps({"type": "error", "payload": {"message": "无法连接到 API 服务器"}})}\n\n'
    except Exception as e:
        yield f'event: error\ndata: {json.dumps({"type": "error", "payload": {"message": f"请求错误: {str(e)}"}})}\n\n'


@app.post("/hitl/continue")
async def hitl_continue(request: HITLContinueRequest):
    """HITL 继续对话接口 - 返回 SSE 流式响应

    在用户响应 HITL 表单后，自动调用此接口继续对话。
    """
    return StreamingResponse(
        stream_hitl_continuation(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============ Settings API ============

class SettingInfo(BaseModel):
    """设置项信息"""
    key: str
    value: Any
    value_type: str
    description: Optional[str] = None
    created_at: str
    updated_at: str


class SettingsListResponse(BaseModel):
    """设置列表响应"""
    settings: Dict[str, Any]


class SettingsDetailListResponse(BaseModel):
    """设置详情列表响应"""
    settings: List[SettingInfo]


class SettingUpdateRequest(BaseModel):
    """更新单个设置请求"""
    value: Any
    value_type: Optional[str] = None


class SettingsBatchUpdateRequest(BaseModel):
    """批量更新设置请求"""
    settings: Dict[str, Any]


class SettingsBatchUpdateResponse(BaseModel):
    """批量更新设置响应"""
    success: bool
    updated_count: int


class SettingsResetResponse(BaseModel):
    """重置设置响应"""
    success: bool
    reset_count: int


@app.get("/api/settings", response_model=SettingsListResponse)
async def get_all_settings():
    """获取所有配置项"""
    try:
        settings = chat_db.get_all_settings()
        return SettingsListResponse(settings=settings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@app.get("/api/settings/detail", response_model=SettingsDetailListResponse)
async def get_all_settings_detail():
    """获取所有配置项的详细信息（包括元数据）"""
    try:
        settings_list = chat_db.get_all_settings_with_metadata()
        result = [
            SettingInfo(
                key=s["key"],
                value=s["typed_value"],
                value_type=s["value_type"],
                description=s.get("description"),
                created_at=s["created_at"],
                updated_at=s["updated_at"],
            )
            for s in settings_list
        ]
        return SettingsDetailListResponse(settings=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置详情失败: {str(e)}")


@app.get("/api/settings/{key:path}")
async def get_setting(key: str):
    """获取单个配置项"""
    try:
        value = chat_db.get_setting(key)
        if value is None:
            raise HTTPException(status_code=404, detail=f"配置项 '{key}' 不存在")
        return {"key": key, "value": value}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@app.put("/api/settings/{key:path}")
async def update_setting(key: str, request: SettingUpdateRequest):
    """更新单个配置项"""
    try:
        success = chat_db.set_setting(key, request.value, request.value_type)
        if not success:
            raise HTTPException(status_code=500, detail="更新配置失败")
        return {"key": key, "value": request.value, "success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@app.put("/api/settings", response_model=SettingsBatchUpdateResponse)
async def batch_update_settings(request: SettingsBatchUpdateRequest):
    """批量更新配置项"""
    try:
        updated_count = chat_db.set_settings(request.settings)
        return SettingsBatchUpdateResponse(success=True, updated_count=updated_count)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量更新配置失败: {str(e)}")


@app.post("/api/settings/reset", response_model=SettingsResetResponse)
async def reset_settings():
    """重置所有配置为默认值"""
    try:
        reset_count = chat_db.reset_settings()
        return SettingsResetResponse(success=True, reset_count=reset_count)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置配置失败: {str(e)}")


# ============ Plans API ============

class PlanInfo(BaseModel):
    """计划信息"""
    id: str
    session_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    target_time: str
    reminder_offset_minutes: int
    repeat_type: str
    status: str
    snooze_until: Optional[str] = None
    created_at: str
    updated_at: str


class PlanCreateRequest(BaseModel):
    """创建计划请求"""
    title: str
    description: Optional[str] = None
    target_time: str  # ISO format datetime
    reminder_offset_minutes: int = 10
    repeat_type: str = "none"
    session_id: Optional[str] = None


class PlanUpdateRequest(BaseModel):
    """更新计划请求"""
    title: Optional[str] = None
    description: Optional[str] = None
    target_time: Optional[str] = None
    reminder_offset_minutes: Optional[int] = None
    repeat_type: Optional[str] = None
    status: Optional[str] = None


class PlanListResponse(BaseModel):
    """计划列表响应"""
    plans: List[PlanInfo]
    total: int


class PlanSnoozeRequest(BaseModel):
    """推迟计划请求"""
    snooze_minutes: int = 10


def _plan_entry_to_info(entry: memory_manager.PlanEntry) -> PlanInfo:
    """Convert PlanEntry to PlanInfo."""
    return PlanInfo(
        id=entry.id,
        session_id=entry.session_id,
        title=entry.title,
        description=entry.description,
        target_time=entry.target_time.isoformat(),
        reminder_offset_minutes=entry.reminder_offset_minutes,
        repeat_type=entry.repeat_type,
        status=entry.status,
        snooze_until=entry.snooze_until.isoformat() if entry.snooze_until else None,
        created_at=entry.created_at.isoformat(),
        updated_at=entry.updated_at.isoformat(),
    )


@app.get("/plans", response_model=PlanListResponse)
async def list_plans(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """获取计划列表

    支持按状态筛选和分页。
    """
    try:
        entries = memory_manager.list_plans(
            status=status,
            limit=limit,
            offset=offset,
        )
        total = memory_manager.count_plans(status=status)

        plans = [_plan_entry_to_info(e) for e in entries]
        return PlanListResponse(plans=plans, total=total)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取计划列表失败: {str(e)}")


@app.get("/plans/due", response_model=PlanListResponse)
async def get_due_plans(limit: int = 10):
    """获取到期的计划

    返回所有 status 为 pending 且提醒时间已到的计划。
    用于 Electron 轮询。
    """
    try:
        entries = memory_manager.get_due_plans(limit=limit)
        plans = [_plan_entry_to_info(e) for e in entries]
        return PlanListResponse(plans=plans, total=len(plans))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取到期计划失败: {str(e)}")


@app.post("/plans", response_model=PlanInfo)
async def create_plan(request: PlanCreateRequest):
    """创建新计划"""
    try:
        target_time = datetime.fromisoformat(request.target_time.replace("Z", "+00:00"))
        entry = memory_manager.create_plan(
            title=request.title,
            description=request.description,
            target_time=target_time,
            session_id=request.session_id,
            reminder_offset_minutes=request.reminder_offset_minutes,
            repeat_type=request.repeat_type,
        )
        return _plan_entry_to_info(entry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"时间格式错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"创建计划失败: {str(e)}")


@app.get("/plans/{plan_id}", response_model=PlanInfo)
async def get_plan(plan_id: str):
    """获取特定计划详情"""
    try:
        entry = memory_manager.get_plan(plan_id)
        if not entry:
            raise HTTPException(status_code=404, detail="计划不存在")
        return _plan_entry_to_info(entry)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取计划失败: {str(e)}")


@app.put("/plans/{plan_id}", response_model=PlanInfo)
async def update_plan(plan_id: str, request: PlanUpdateRequest):
    """更新计划"""
    try:
        target_time = None
        if request.target_time:
            target_time = datetime.fromisoformat(request.target_time.replace("Z", "+00:00"))

        entry = memory_manager.update_plan(
            plan_id=plan_id,
            title=request.title,
            description=request.description,
            target_time=target_time,
            reminder_offset_minutes=request.reminder_offset_minutes,
            repeat_type=request.repeat_type,
            status=request.status,
        )
        if not entry:
            raise HTTPException(status_code=404, detail="计划不存在")
        return _plan_entry_to_info(entry)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"更新计划失败: {str(e)}")


@app.delete("/plans/{plan_id}", response_model=DeleteResponse)
async def delete_plan(plan_id: str):
    """删除计划"""
    try:
        success = memory_manager.delete_plan(plan_id)
        if not success:
            raise HTTPException(status_code=404, detail="计划不存在")
        return DeleteResponse(success=True, message="计划删除成功")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除计划失败: {str(e)}")


@app.post("/plans/{plan_id}/complete", response_model=PlanInfo)
async def complete_plan(plan_id: str):
    """完成计划

    如果是重复计划，会自动创建下一个周期的计划。
    """
    try:
        entry = memory_manager.complete_plan(plan_id)
        if not entry:
            raise HTTPException(status_code=404, detail="计划不存在")
        return _plan_entry_to_info(entry)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"完成计划失败: {str(e)}")


@app.post("/plans/{plan_id}/dismiss", response_model=PlanInfo)
async def dismiss_plan(plan_id: str):
    """取消计划"""
    try:
        entry = memory_manager.dismiss_plan(plan_id)
        if not entry:
            raise HTTPException(status_code=404, detail="计划不存在")
        return _plan_entry_to_info(entry)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消计划失败: {str(e)}")


@app.post("/plans/{plan_id}/snooze", response_model=PlanInfo)
async def snooze_plan(plan_id: str, request: PlanSnoozeRequest):
    """推迟计划提醒"""
    try:
        entry = memory_manager.snooze_plan(plan_id, request.snooze_minutes)
        if not entry:
            raise HTTPException(status_code=404, detail="计划不存在")
        return _plan_entry_to_info(entry)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推迟计划失败: {str(e)}")


# ============ MCP Service Management API ============

class MCPServerCreateRequest(BaseModel):
    """创建 MCP 服务请求"""
    name: str
    command: str
    args: List[str] = []
    env: Dict[str, str] = {}
    enabled: bool = True
    auto_start: bool = False
    description: Optional[str] = None
    trigger_keywords: List[str] = []


class MCPServerUpdateRequest(BaseModel):
    """更新 MCP 服务请求"""
    name: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    enabled: Optional[bool] = None
    auto_start: Optional[bool] = None
    description: Optional[str] = None
    trigger_keywords: Optional[List[str]] = None


class MCPServerInfoResponse(BaseModel):
    """MCP 服务信息响应"""
    id: str
    name: str
    command: str
    args: List[str]
    env: Dict[str, str]
    enabled: bool
    auto_start: bool = False
    created_at: str
    status: str
    error_message: Optional[str] = None
    pid: Optional[int] = None
    description: Optional[str] = None
    trigger_keywords: List[str] = []


class MCPServerListResponse(BaseModel):
    """MCP 服务列表响应"""
    servers: List[MCPServerInfoResponse]
    total: int


class MCPServerActionResponse(BaseModel):
    """MCP 服务操作响应"""
    success: bool
    message: Optional[str] = None
    server: Optional[MCPServerInfoResponse] = None


def _mcp_server_to_response(info: mcp_manager.MCPServerInfo) -> MCPServerInfoResponse:
    """Convert MCPServerInfo to response model."""
    return MCPServerInfoResponse(
        id=info.id,
        name=info.name,
        command=info.command,
        args=info.args,
        env=info.env,
        enabled=info.enabled,
        auto_start=info.auto_start,
        created_at=info.created_at,
        status=info.status.value if hasattr(info.status, 'value') else str(info.status),
        error_message=info.error_message,
        pid=info.pid,
        description=info.description,
        trigger_keywords=info.trigger_keywords,
    )


@app.get("/api/mcp/servers", response_model=MCPServerListResponse)
async def list_mcp_servers():
    """获取所有 MCP 服务列表及状态"""
    try:
        print("[MCP API] GET /api/mcp/servers - listing all servers")
        pm = mcp_manager.get_process_manager()
        servers = pm.list_servers_with_status()
        print(f"[MCP API] Listed {len(servers)} servers")
        return MCPServerListResponse(
            servers=[_mcp_server_to_response(s) for s in servers],
            total=len(servers)
        )
    except Exception as e:
        print(f"[MCP API] Error listing servers: {e}")
        raise HTTPException(status_code=500, detail=f"获取 MCP 服务列表失败: {str(e)}")


@app.post("/api/mcp/servers", response_model=MCPServerInfoResponse, status_code=201)
async def create_mcp_server(request: MCPServerCreateRequest):
    """注册新的 MCP 服务"""
    try:
        print(f"[MCP API] POST /api/mcp/servers - creating server: name={request.name}, command={request.command}")
        registry = mcp_manager.get_registry()
        config = mcp_manager.MCPServerConfig(
            name=request.name,
            command=request.command,
            args=request.args,
            env=request.env,
            enabled=request.enabled,
            auto_start=request.auto_start,
            description=request.description,
            trigger_keywords=request.trigger_keywords,
        )
        created = registry.add_server(config)
        print(f"[MCP API] Server created: id={created.id}, name={created.name}")

        # Get info with status
        pm = mcp_manager.get_process_manager()
        info = pm.get_server_info(created.id)
        if info:
            return _mcp_server_to_response(info)

        raise HTTPException(status_code=500, detail="服务创建成功但无法获取状态")
    except ValueError as e:
        print(f"[MCP API] Create server failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[MCP API] Create server error: {e}")
        raise HTTPException(status_code=500, detail=f"创建 MCP 服务失败: {str(e)}")


@app.get("/api/mcp/servers/{server_id}", response_model=MCPServerInfoResponse)
async def get_mcp_server(server_id: str):
    """获取单个 MCP 服务详情"""
    try:
        print(f"[MCP API] GET /api/mcp/servers/{server_id}")
        pm = mcp_manager.get_process_manager()
        info = pm.get_server_info(server_id)
        if not info:
            print(f"[MCP API] Server not found: id={server_id}")
            raise HTTPException(status_code=404, detail="MCP 服务不存在")
        print(f"[MCP API] Found server: name={info.name}, status={info.status}")
        return _mcp_server_to_response(info)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[MCP API] Get server error: {e}")
        raise HTTPException(status_code=500, detail=f"获取 MCP 服务失败: {str(e)}")


@app.put("/api/mcp/servers/{server_id}", response_model=MCPServerInfoResponse)
async def update_mcp_server(server_id: str, request: MCPServerUpdateRequest):
    """更新 MCP 服务配置"""
    try:
        print(f"[MCP API] PUT /api/mcp/servers/{server_id} - updating")
        pm = mcp_manager.get_process_manager()

        # Check if running - warn user
        status = pm.get_status(server_id)
        if status == mcp_manager.MCPServerStatus.RUNNING:
            print(f"[MCP API] Update blocked: server {server_id} is running")
            raise HTTPException(
                status_code=400,
                detail="服务正在运行，请先停止服务再更新配置"
            )

        registry = mcp_manager.get_registry()
        updated = registry.update_server(
            server_id,
            name=request.name,
            command=request.command,
            args=request.args,
            env=request.env,
            enabled=request.enabled,
            auto_start=request.auto_start,
            description=request.description,
            trigger_keywords=request.trigger_keywords,
        )
        if not updated:
            print(f"[MCP API] Update failed: server not found id={server_id}")
            raise HTTPException(status_code=404, detail="MCP 服务不存在")

        info = pm.get_server_info(server_id)
        if info:
            print(f"[MCP API] Server updated: name={info.name}")
            return _mcp_server_to_response(info)

        raise HTTPException(status_code=500, detail="更新成功但无法获取状态")
    except HTTPException:
        raise
    except ValueError as e:
        print(f"[MCP API] Update validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[MCP API] Update error: {e}")
        raise HTTPException(status_code=500, detail=f"更新 MCP 服务失败: {str(e)}")


@app.delete("/api/mcp/servers/{server_id}", status_code=204)
async def delete_mcp_server(server_id: str):
    """删除 MCP 服务"""
    try:
        print(f"[MCP API] DELETE /api/mcp/servers/{server_id}")
        pm = mcp_manager.get_process_manager()
        registry = mcp_manager.get_registry()

        # Stop if running
        print(f"[MCP API] Stopping server before delete: id={server_id}")
        pm.stop_server(server_id)

        # Delete config
        success = registry.delete_server(server_id)
        if not success:
            print(f"[MCP API] Delete failed: server not found id={server_id}")
            raise HTTPException(status_code=404, detail="MCP 服务不存在")

        print(f"[MCP API] Server deleted: id={server_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        print(f"[MCP API] Delete error: {e}")
        raise HTTPException(status_code=500, detail=f"删除 MCP 服务失败: {str(e)}")


@app.post("/api/mcp/servers/{server_id}/start", response_model=MCPServerActionResponse)
async def start_mcp_server(server_id: str):
    """启动 MCP 服务"""
    try:
        print(f"[MCP API] POST /api/mcp/servers/{server_id}/start")
        pm = mcp_manager.get_process_manager()

        # Check if server exists
        info = pm.get_server_info(server_id)
        if not info:
            print(f"[MCP API] Start failed: server not found id={server_id}")
            raise HTTPException(status_code=404, detail="MCP 服务不存在")

        print(f"[MCP API] Starting server: name={info.name}")
        success = pm.start_server(server_id)

        # Get updated info
        info = pm.get_server_info(server_id)
        if info:
            print(f"[MCP API] Start result: success={success}, status={info.status}, pid={info.pid}")

            # If server started successfully, fetch its tools list for caching
            if success and info.status == mcp_manager.MCPServerStatus.RUNNING:
                try:
                    print(f"[MCP API] Fetching tools list for newly started server: {info.name}")
                    import asyncio
                    # Give the server a moment to initialize
                    await asyncio.sleep(0.5)
                    tools = await mcp_tool_executor.list_service_tools(info.name)
                    print(f"[MCP API] Cached {len(tools)} tools from server: {info.name}")
                except Exception as e:
                    print(f"[MCP API] Failed to fetch tools list: {e}")

            return MCPServerActionResponse(
                success=success,
                message="服务启动成功" if success else info.error_message,
                server=_mcp_server_to_response(info),
            )

        return MCPServerActionResponse(
            success=success,
            message="服务启动成功" if success else "启动失败",
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[MCP API] Start error: {e}")
        raise HTTPException(status_code=500, detail=f"启动 MCP 服务失败: {str(e)}")


@app.post("/api/mcp/servers/{server_id}/stop", response_model=MCPServerActionResponse)
async def stop_mcp_server(server_id: str):
    """停止 MCP 服务"""
    try:
        print(f"[MCP API] POST /api/mcp/servers/{server_id}/stop")
        pm = mcp_manager.get_process_manager()

        # Check if server exists
        info = pm.get_server_info(server_id)
        if not info:
            print(f"[MCP API] Stop failed: server not found id={server_id}")
            raise HTTPException(status_code=404, detail="MCP 服务不存在")

        print(f"[MCP API] Stopping server: name={info.name}, pid={info.pid}")
        success = pm.stop_server(server_id)

        # Get updated info
        info = pm.get_server_info(server_id)
        if info:
            print(f"[MCP API] Stop result: success={success}, status={info.status}")
            return MCPServerActionResponse(
                success=success,
                message="服务已停止" if success else info.error_message,
                server=_mcp_server_to_response(info),
            )

        return MCPServerActionResponse(
            success=success,
            message="服务已停止" if success else "停止失败",
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[MCP API] Stop error: {e}")
        raise HTTPException(status_code=500, detail=f"停止 MCP 服务失败: {str(e)}")


@app.post("/api/mcp/servers/{server_id}/restart", response_model=MCPServerActionResponse)
async def restart_mcp_server(server_id: str):
    """重启 MCP 服务"""
    try:
        print(f"[MCP API] POST /api/mcp/servers/{server_id}/restart")
        pm = mcp_manager.get_process_manager()

        # Check if server exists
        info = pm.get_server_info(server_id)
        if not info:
            print(f"[MCP API] Restart failed: server not found id={server_id}")
            raise HTTPException(status_code=404, detail="MCP 服务不存在")

        print(f"[MCP API] Restarting server: name={info.name}")
        success = pm.restart_server(server_id)

        # Get updated info
        info = pm.get_server_info(server_id)
        if info:
            print(f"[MCP API] Restart result: success={success}, status={info.status}, pid={info.pid}")

            # If server restarted successfully, fetch its tools list for caching
            if success and info.status == mcp_manager.MCPServerStatus.RUNNING:
                try:
                    print(f"[MCP API] Fetching tools list for restarted server: {info.name}")
                    import asyncio
                    # Give the server a moment to initialize
                    await asyncio.sleep(0.5)
                    # Clear old cache and fetch new tools
                    mcp_tool_executor.get_executor().clear_tools_cache(info.name)
                    tools = await mcp_tool_executor.list_service_tools(info.name)
                    print(f"[MCP API] Cached {len(tools)} tools from server: {info.name}")
                except Exception as e:
                    print(f"[MCP API] Failed to fetch tools list: {e}")

            return MCPServerActionResponse(
                success=success,
                message="服务重启成功" if success else info.error_message,
                server=_mcp_server_to_response(info),
            )

        return MCPServerActionResponse(
            success=success,
            message="服务重启成功" if success else "重启失败",
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[MCP API] Restart error: {e}")
        raise HTTPException(status_code=500, detail=f"重启 MCP 服务失败: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True
    )