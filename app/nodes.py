from .helper import GraphState
from .logger import logger
from langchain_core.messages import ToolMessage
from .helper import add_sse_message
from .prompts import InteractivePlanningSystemPrompt, Tool_Use_Case_Prompt
from .config import config
import requests
import json
import io
from langchain_core.messages import HumanMessage, AIMessage
from .helper import generate_uuid

def user_profile_node(state: GraphState) -> GraphState:
    """
    用户画像节点，用于获取用户信息，并根据用户信息调整对话风格
    """
    # TODO: 实现用户偏好获取逻辑：获取用户编号，昵称、口味、长期上下文标记
    return state

def tool_nodes(state: GraphState) -> GraphState:
    """
    工具节点，用于处理工具调用
    """
    # TODO: 知识库检索、天气、日历、TTS
    # TODO：知识库检索：站内文档索引、FAQ 映射
    return state

def present_node(state: GraphState) -> GraphState:
    """
    展示节点，用于呈现结果
    """
    # TODO: 实现展示逻辑：动作（如果 live2D 支持）、网页操作、TTS、文本
    return state

def record_node(state: GraphState) -> GraphState:
    """
    记录节点，用于保存对话历史
    """
    # TODO: 实现记录逻辑：保存对话历史；作摘要处理并保存向量、图数据库
    return state

# 工作流：关键词分类
def kanban_daily_node(state: GraphState) -> GraphState:
    logger.info("Entered kanban daily node")
    # 关键词分类流程
    state["handle_sse_messages"] = "kanban_daily"
    return state

# 工作流：代码解释
def code_explain_node(state: GraphState) -> GraphState:
    logger.info("Entered code explain flow")
    # 代码解释流程
    state["handle_sse_messages"] = "code_explain"
    return state

def check_interrupt_node(state: GraphState) -> GraphState:
    if check_interrupt(state):
        logger.info("<LangGraph Loop> Task interrupted: User interruption")
        state["break_task"] = True
        state["task_completion_message"] = "任务中断: 用户中断"
        state = add_sse_message(state, "text", {"type": "statusText", "payload": state["task_completion_message"], "actionID": ""})
    return state

# 工作流：未知流程
def fallback_handler_node(state: GraphState) -> GraphState:
    # 未知流程直接结束
    logger.info("Entered other flow")
    state["break_task"] = True
    state["task_completion_message"] = "Unready to handle this intent"
    state = add_sse_message(state, "text", {"type": "statusText", "payload": state["task_completion_message"], "actionID": ""})
    return state

# Max loop counters
max_outer_loop = 2
max_inner_loop = 2
def check_loop_limits(state: GraphState) -> GraphState:
    if state["break_task"]:
        return state # Already marked for break

    if state["current_outer_loop"] >= max_outer_loop:
        state["break_task"] = True
        state["task_completion_message"] = "任务中断: 最大外层循环数"
        state = add_sse_message(state, "text", {"type": "statusText", "payload": state["task_completion_message"], "actionID": ""})
        return state

    state["current_outer_loop"] += 1
    logger.info(f"Current outer loop: {state['current_outer_loop']}")
    return state

def call_model(state: GraphState) -> GraphState:
    if state["break_task"]:
        return state

    model_messages = [
        {"role": "system", "content": InteractivePlanningSystemPrompt},
    ]
    # Add chat history, ensuring it's in the correct format for the model
    for msg in state["chat_history"]:
        if isinstance(msg, HumanMessage):
            model_messages.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            if msg.content:
                model_messages.append({"role": "assistant", "content": msg.content})
            if msg.tool_calls:
                # Convert LangChain tool_calls to model's expected format
                for tc in msg.tool_calls:
                    model_messages.append({
                        "role": "assistant",
                        "content": f"[TOOL_CALL][{tc['name']}][id:{tc.get('id', '')}] {json.dumps(tc['args'], ensure_ascii=False)}"
                    })
        elif isinstance(msg, ToolMessage):
            # 转为 assistant role，并在 content 里注明工具调用
            model_messages.append({
                "role": "assistant",
                "content": f"[TOOL_MESSAGE][{msg.tool_call_id}] {msg.content}"
            })


    model_request_body = {
        "model": config.ModelProviderModel,
        "messages": model_messages,
        "stream": True,
        "temperature": 0,
        "tools": Tool_Use_Case_Prompt["tools"],
        "tool_choice": Tool_Use_Case_Prompt["tool_choice"],
    }

    logger.info(f"🌍 Model request body: {json.dumps(model_request_body, indent=2)}")
    logger.info(f"🌍 Model provider URI: {config.ModelProviderURI}")

    try:
        req_headers = {
            "Authorization": "Bearer " + config.ModelProviderAPIKey,
            "Content-Type": "application/json"
        }
        
        # Use requests.post with stream=True for streaming response
        with requests.post(config.ModelProviderURI, json=model_request_body, headers=req_headers, stream=True) as resp:
            resp.raise_for_status()

            tool_call_detected = False
            tool_call_name = ""
            tool_call_arguments_builder = io.StringIO() # Use StringIO to build arguments

            text_message_id = generate_uuid()
            accumulated_content = ""
            
            for line in resp.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        data = decoded_line[6:]
                        if data == "[DONE]":
                            break
                        
                        try:
                            or_resp = json.loads(data)
                            if or_resp.get("choices") and len(or_resp["choices"]) > 0:
                                choice = or_resp["choices"][0]
                                delta = choice.get("delta", {})

                                content = delta.get("content")
                                if content:
                                    accumulated_content += content
                                    payload = {
                                        "type": "text",
                                        "payload": {
                                            "content": content,
                                            "meta": {"id": text_message_id},
                                        },
                                        "actionID": "",
                                    }
                                    state = add_sse_message(state, "text", payload)

                                tool_calls = delta.get("tool_calls")
                                if tool_calls and len(tool_calls) > 0:
                                    tool_call_detected = True
                                    # Assuming only one tool call per delta for simplicity, as in Go code
                                    function_call = tool_calls[0].get("function", {})
                                    if function_call.get("name"):
                                        tool_call_name = function_call["name"]
                                    if function_call.get("arguments"):
                                        tool_call_arguments_builder.write(function_call["arguments"])
                                        logger.info(f"><Detected tool call arguments chunk: {function_call['arguments']}")

                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse JSON from model stream: {e}, line: {decoded_line}")
                            continue
            
            state["model_response_content"] = accumulated_content
            state["tool_call_name"] = tool_call_name
            state["tool_call_arguments"] = tool_call_arguments_builder.getvalue()

            if not tool_call_detected:
                logger.warning(f"No tool call detected! Current outer loop: {state['current_outer_loop']} / {max_outer_loop}")
                # 用 HumanMessage 提示模型必须使用工具调用
                prompt = "你没有使用工具调用，请务必使用工具调用，重新回答用户的问题：" + accumulated_content
                state["chat_history"].append(HumanMessage(content=prompt))
                # 这会在下次 call_model 时作为用户输入，强制模型调用工具
                state["tool_call_name"] = "no_tool_detected" # Custom signal for routing
                state["tool_call_arguments"] = "" # Clear arguments
            else:
                if state["tool_call_name"]:
                    try:
                        tool_args_dict = json.loads(state["tool_call_arguments"])
                        tool_call_id = generate_uuid()
                        state["chat_history"].append(AIMessage(
                            content=accumulated_content,
                            tool_calls=[{
                                "id": tool_call_id,
                                "name": state["tool_call_name"],
                                "args": tool_args_dict
                            }]
                        ))
                        if state["tool_call_name"] == "ask_user":
                            state["action_id_waiting_for_answer"] = tool_call_id
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse tool arguments JSON: {state['tool_call_arguments']}")
                        state["chat_history"].append(AIMessage(content=accumulated_content))
                else:
                    state["chat_history"].append(AIMessage(content=accumulated_content))

    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling model provider: {e}")
        state["break_task"] = True
        state["task_completion_message"] = "调用大模型失败: " + str(e)
        state = add_sse_message(state, "text", {"type": "statusText", "payload": state["task_completion_message"], "actionID": ""})

    return state

def handle_tool_call(state: GraphState) -> GraphState:
    if state["break_task"]:
        return state

    tool_name = state["tool_call_name"]
    tool_args_str = state["tool_call_arguments"]

    if tool_name == "no_tool_detected":
        state["user_input"] = "你没有使用工具调用，请务必使用工具调用，重新回答用户的问题：" + state["user_input"]
        return state # This will route back to call_model

    try:
        tool_args = json.loads(tool_args_str)
    except json.JSONDecodeError as e:
        logger.error(f"Tool arguments JSON parsing failed for {tool_name}: {e}, args: {tool_args_str}")
        state["break_task"] = True
        state["task_completion_message"] = f"工具解析失败: {tool_name} - {e}"
        state = add_sse_message(state, "text", {"type": "statusText", "payload": state["task_completion_message"], "actionID": ""})
        return state

    if tool_name == "ask_user":
        action_id = state.get("action_id_waiting_for_answer")
        question = tool_args.get("question", "")
        payload = {
            "type": "ask",
            "payload": {
                "content": question,
                "meta": {
                    "answer": False,
                    "reason": "",
                    "id": action_id,
                },
            },
            "actionID": action_id,
        }
        state = add_sse_message(state, "text", payload)
        logger.info(f"Waiting for user answer for actionID: {action_id}")
        # 关键：直接结束本轮对话
        state["break_task"] = True
        state["task_completion_message"] = "等待用户回答"
        return state

    elif tool_name == "task_complete":
        summary = tool_args.get("summary", "")
        state["break_task"] = True
        state["task_completion_message"] = "任务已完成: " + summary
        state = add_sse_message(state, "text", {"type": "statusText", "payload": state["task_completion_message"], "actionID": ""})
        return state

    else:
        state["break_task"] = True
        state["task_completion_message"] = f"检测到未知工具调用: {tool_name}"
        state = add_sse_message(state, "text", {"type": "statusText", "payload": state["task_completion_message"], "actionID": ""})
        return state

# 将所有 _node 方法添加到 workflow 中
def add_nodes_to_workflow(workflow):
    workflow.add_node("user_profile", user_profile_node)
    workflow.add_node("tool", tool_nodes)
    workflow.add_node("present", present_node)
    workflow.add_node("record", record_node)
    workflow.add_node("kanban_daily", kanban_daily_node)
    workflow.add_node("code_explain", code_explain_node)
    workflow.add_node("check_interrupt", check_interrupt_node)
    workflow.add_node("unknown_handler", fallback_handler_node)
    workflow.add_node("check_loop_limits", check_loop_limits)
    workflow.add_node("call_model", call_model)
    workflow.add_node("handle_tool_call", handle_tool_call)

# Integrate LangGraph with Flask
def check_interrupt(state: GraphState) -> bool:
    # 遍历 chat_history，查找 content 为 "stop" 的 ToolMessage
    for msg in reversed(state["chat_history"]):
        if isinstance(msg, ToolMessage) and msg.content.strip().lower() == "stop":
            return True
    return False


