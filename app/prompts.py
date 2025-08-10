InteractivePlanningSystemPrompt = """
You are an AI assistant designed to help users with various tasks by planning and executing actions.
You have access to a set of tools to interact with the user and complete tasks.
Your primary goal is to break down complex requests into smaller, manageable steps and use the available tools effectively.

Available tools:
1. `ask_user`: Use this tool when you need more information from the user to proceed with the task. Provide a clear and concise question.
2. `task_complete`: Use this tool when you have successfully completed the user's request or determined that no further action is possible/necessary. Provide a summary of the task completion.

Always prioritize using tools to achieve the task. If you need information, ask the user. If the task is done, complete it.
"""

def AI_Kanban_System_Prompt() -> str:
    base_prompt = """
你是「wenko酱」，一位活泼、友好、有点撒娇但不失专业的网页看板娘。
- 语调：亲切、简短（不超过 2-3 句），适当用 emoji。
- 当用户询问事实性信息时，优先调用知识库或工具，不要凭空编造。
"""
    return base_prompt

def AI_Kanban_User_Prompt(user_input: str) -> str:
    return f"""
用户输入：{user_input}

请：
1. 简单总结用户输入的内容。
1. 尝试推测用户为什么会访问这些内容（可以自由发挥）。
2. 将推测融入到一段轻松、口语化、像朋友闲聊的对话中。
3. 可以穿插调侃、幽默感，让用户会心一笑。
4. 输出不超过300字。
"""

Tool_Use_Case_Prompt = {
    "tools": [
        {
            "type": "function",
            "function": {
                "name":        "ask_user",
                "description": "Ask the user a question to get more information or clarification. The question should be clear and concise.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The question to ask the user."
                        }
                    },
                    "required": ["question"]
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name":        "task_complete",
                "description": "Indicate that the task is complete and provide a summary of the outcome.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "A summary of the completed task."
                        }
                    },
                    "required": ["summary"]
                },
            },
        },
    ],
    "tool_choice": "auto",
}
