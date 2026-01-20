"""Memory Extractor Module

Provides smart memory extraction from messages using LLM.
Extracts key, value, category, and confidence from message content.
"""

import json
import os
from dataclasses import dataclass
from typing import Optional

import httpx


@dataclass
class ExtractedMemory:
    """Extracted memory from message content."""
    key: str
    value: str
    category: str  # preference | fact | pattern
    confidence: float


EXTRACT_PROMPT_TEMPLATE = """分析以下消息内容，提取可以保存为长期记忆的信息。

消息角色: {role}
消息内容: {content}

请提取以下信息并以 JSON 格式返回：
1. key: 记忆的键名（简洁的摘要，3-15个中文字，如"编程语言偏好"、"用户姓名"、"对AI学习的看法"）
2. value: 记忆的值（原文中的关键信息或核心要点摘要）
3. category: 类别，必须是以下之一：
   - preference: 用户偏好、观点、看法、价值观（包含"我认为"、"我觉得"、"我相信"、"在我看来"等）
   - fact: 客观事实、个人信息、经历、发现（姓名、职业、地点、学到的东西等）
   - pattern: 行为模式（沟通风格、使用习惯、思维方式）
4. confidence: 置信度（0.0-1.0，表示该信息值得保存的确定性）

特别注意：
- 个人观点、看法、深度思考非常值得保存，使用 preference 类别
- 用户的发现、洞见、结论也值得保存，根据内容选择 preference 或 fact
- 对于长篇内容，提取核心观点作为 value
- 如果消息内容没有值得保存的信息（如简单的问候、确认），返回 confidence < 0.5
- key 应该是描述性的标签，不是消息原文
- value 应该是具体的信息内容或核心要点

只返回 JSON，不要其他文字：
{{"key":"提取的键名","value":"提取的值","category":"类别","confidence":0.9}}"""


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
    # Load config
    config_path = os.path.join(os.path.dirname(__file__), "chat_config.json")
    if not os.path.exists(config_path):
        return None

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    api_base = config.get("api_base", "https://api.openai.com/v1")
    api_key = config.get("api_key", "")
    model = config.get("model", "gpt-4o-mini")

    if not api_key:
        return None

    # Build prompt
    prompt = EXTRACT_PROMPT_TEMPLATE.format(
        role="用户" if role == "user" else "AI助手",
        content=content,
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
