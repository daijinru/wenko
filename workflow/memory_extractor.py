"""Memory Extractor Module

Provides smart memory extraction from messages using LLM.
Extracts key, value, category, and confidence from message content.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx

import chat_db


@dataclass
class ExtractedMemory:
    """Extracted memory from message content."""
    key: str
    value: str
    category: str  # preference | fact | pattern | plan
    confidence: float
    # Plan-specific fields (only when category == 'plan')
    target_time: Optional[str] = None  # ISO format datetime
    location: Optional[str] = None
    participants: Optional[str] = None


EXTRACT_PROMPT_TEMPLATE = """分析以下消息内容，提取可以保存为长期记忆的信息。

消息角色: {role}
消息内容: {content}

请提取以下信息并以 JSON 格式返回：
1. key: 记忆的键名（简洁的摘要，3-15个中文字，如"编程语言偏好"、"用户姓名"、"周五团队聚餐"）
2. value: 记忆的值，格式为：
   先写核心要点摘要（1-3句话）
   然后空一行
   最后附上"以下是原文："并换行后附上原始内容
3. category: 类别，必须是以下之一：
   - preference: 用户偏好、观点、看法、价值观（包含"我认为"、"我觉得"、"我相信"、"在我看来"等）
   - fact: 客观事实、个人信息、经历、发现（姓名、职业、地点、学到的东西等）
   - pattern: 行为模式（沟通风格、使用习惯、思维方式）
   - plan: 计划、安排、预约、日程（会议、聚餐、约会、活动、提醒事项等包含时间的安排）
4. confidence: 置信度（0.0-1.0，表示该信息值得保存的确定性）

如果 category 是 plan，还需要额外提取：
5. target_time: 计划的目标时间（ISO 8601格式，如"2025-01-28T14:00:00"）。如果只有日期没有时间，默认为当天09:00。如果是相对时间（如"明天"、"下周一"），请转换为具体日期（当前日期参考：{current_date}）
6. location: 地点（如果有的话）
7. participants: 参与者（如果有的话，用逗号分隔多人）

特别注意：
- 包含具体时间和事件的内容（如会议通知、聚餐邀请、约会安排）应使用 plan 类别
- 计划类信息的 key 应该简洁描述事件，如"周五团队聚餐"、"项目评审会议"
- 个人观点、看法、深度思考非常值得保存，使用 preference 类别
- 用户的发现、洞见、结论也值得保存，根据内容选择 preference 或 fact
- 如果消息内容没有值得保存的信息（如简单的问候、确认），返回 confidence < 0.5
- key 应该是描述性的标签，不是消息原文
- value 必须包含摘要和原文两部分

只返回 JSON，不要其他文字。对于非 plan 类别：
{{"key":"提取的键名","value":"核心要点摘要。\\n\\n以下是原文：\\n原始内容","category":"类别","confidence":0.9}}

对于 plan 类别：
{{"key":"事件名称","value":"事件摘要说明。\\n\\n以下是原文：\\n原始内容","category":"plan","confidence":0.9,"target_time":"2025-01-28T14:00:00","location":"会议室A","participants":"张三,李四"}}"""


async def extract_memory_from_message(
    content: str,
    role: str = "user",
) -> Optional[ExtractedMemory]:
    """Extract memory information from a message using LLM.

    Args:
        content: Message content to analyze
        role: Message role ('user' or 'assistant')

    Returns:
        ExtractedMemory if extraction successful, None otherwise
    """
    # Load config from database
    settings = chat_db.get_all_settings()

    api_base = settings.get("llm.api_base", "https://api.openai.com/v1")
    api_key = settings.get("llm.api_key", "")
    model = settings.get("llm.model", "gpt-4o-mini")

    if not api_key:
        return None

    # Build prompt with current date for relative time conversion
    current_date = datetime.now().strftime("%Y-%m-%d")
    prompt = EXTRACT_PROMPT_TEMPLATE.format(
        role="用户" if role == "user" else "AI助手",
        content=content,
        current_date=current_date,
    )

    # Call LLM API
    api_url = f"{api_base.rstrip('/')}/chat/completions"

    request_body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 256,
        "temperature": 0.3,  # Lower temperature for more consistent extraction
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                api_url,
                json=request_body,
                headers=headers
            )

            if response.status_code != 200:
                return None

            result = response.json()
            response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Parse JSON response
            extracted = json.loads(response_text.strip())

            return ExtractedMemory(
                key=extracted.get("key", ""),
                value=extracted.get("value", content),
                category=extracted.get("category", "fact"),
                confidence=float(extracted.get("confidence", 0.5)),
                target_time=extracted.get("target_time"),
                location=extracted.get("location"),
                participants=extracted.get("participants"),
            )

    except (json.JSONDecodeError, KeyError, ValueError, httpx.TimeoutException):
        return None
    except Exception:
        return None


def get_default_extraction(content: str, role: str = "user") -> ExtractedMemory:
    """Get default extraction values when LLM extraction fails.

    Args:
        content: Message content
        role: Message role

    Returns:
        ExtractedMemory with default values
    """
    key = "用户输入" if role == "user" else "AI回复"
    return ExtractedMemory(
        key=key,
        value=content,
        category="fact",
        confidence=0.5,
    )
