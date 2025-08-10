import json
import requests

from .logger import logger

from .helper import process_stream_response
from .types import GraphState
from .config import config

from .prompts import AI_Kanban_System_Prompt, AI_Kanban_User_Prompt

def stream_kanban_daily(state: GraphState):
    """
    看板娘日常对话
    """
    logger.info("Entered stream kanban daily flow")
    content = state["user_input"]
            
    model_messages = [
        {"role": "system", "content": AI_Kanban_System_Prompt()},
        {"role": "user", "content": AI_Kanban_User_Prompt(content)},
    ]
    model_request_body = {
        "model": config.ModelProviderModel,
        "messages": model_messages,
        "stream": True,  # 开启流式
        "temperature": 0.8,
    }
    req_headers = {
        "Authorization": "Bearer " + config.ModelProviderAPIKey,
        "Content-Type": "application/json"
    }
    try:
        with requests.post(config.ModelProviderURI, json=model_request_body, headers=req_headers, stream=True) as resp:
            resp.raise_for_status()
            yield from process_stream_response(resp, logger, state)
            logger.info(f"stream kanban daily result: {state['model_response_content']}")
    except Exception as e:
        logger.error(f"kanban daily stream error: {e}")
        state["model_response_content"] = f"模型调用失败: {e}"
        payload = {"type": "statusText", "payload": state["model_response_content"], "actionID": ""}
        sse_msg = {
            "id": state.get("sse_id_counter", 0),
            "event": "text",
            "data": json.dumps(payload)
        }
        yield f"id: {sse_msg['id']}\nevent: {sse_msg['event']}\ndata: {sse_msg['data']}\n\n"

# 用于分析代码，给出代码解释的函数
def stream_code_explanation(state: GraphState):
    """
    代码解释流式处理
    """
    logger.info("Entered stream code explanation flow")
    content = state["user_input"]
    model_messages = [
        {"role": "user", "content": "请解释以下代码: " + content},
    ]
    model_request_body = {
        "model": config.ModelProviderModel,
        "messages": model_messages,
        "stream": True,  # 开启流式
        "temperature": 0.8,
    }
    req_headers = {
        "Authorization": "Bearer " + config.ModelProviderAPIKey,
        "Content-Type": "application/json"
    }
    try:
        with requests.post(config.ModelProviderURI, json=model_request_body, headers=req_headers, stream=True) as resp:
            resp.raise_for_status()
            yield from process_stream_response(resp, logger, state)
            logger.info(f"stream code explanation result: {state['model_response_content']}")
    except Exception as e:
        logger.error(f"code explanation stream error: {e}")
        state["model_response_content"] = f"模型调用失败: {e}"
        payload = {"type": "statusText", "payload": state["model_response_content"], "actionID": ""}
        sse_msg = {
            "id": state.get("sse_id_counter", 0),
            "event": "text",
            "data": json.dumps(payload)
        }
        yield f"id: {sse_msg['id']}\nevent: {sse_msg['event']}\ndata: {sse_msg['data']}\n\n"

def recognize_intent_with_llm(user_input: str) -> str:
    """
    使用大模型进行意图识别
    """
    # 定义意图分类的提示词
    intent_prompt = f"""
    请根据以下用户输入识别其意图，并只返回意图标签：
    
    用户输入: "{user_input}"
    
    可能的意图包括：
    - code_explain: 如果这是代码，请解释代码
    - kanban_daily: code_explain 以外的意图
    
    请只返回一个最匹配的意图标签。
    """
    
    model_messages = [
        {"role": "system", "content": "你是一个意图识别助手，只能返回指定的意图标签。"},
        {"role": "user", "content": intent_prompt}
    ]
    
    model_request_body = {
        "model": config.ModelProviderModel,
        "messages": model_messages,
        "temperature": 0,
        "max_tokens": 20
    }
    
    try:
        req_headers = {
            "Authorization": "Bearer " + config.ModelProviderAPIKey,
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            config.ModelProviderURI, 
            json=model_request_body, 
            headers=req_headers
        )
        response.raise_for_status()
        
        result = response.json()
        intent = result["choices"][0]["message"]["content"].strip().lower()
        # 预置意图列表
        valid_intents = ["task_flow", "code_explain", "kanban_daily"]
        if intent in valid_intents:
            return intent
        else:
            logger.warning(f"Invalid intent detected: {intent}, defaulting to 'unknown'")
            return "unknown"
            
    except Exception as e:
        logger.error(f"Intent recognition failed: {e}")
        return "unknown"
