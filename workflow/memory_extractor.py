"""Memory Extractor Module

Provides smart memory extraction from messages using LLM.
Extracts key, value, category, and confidence from message content.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx

import chat_db

logger = logging.getLogger(__name__)
from chat_processor import DISABLE_THINKING_PROMPT_SUFFIX


def _is_deep_thinking_enabled() -> bool:
    """检查是否启用深度思考模式"""
    value = chat_db.get_setting("llm.deep_thinking_enabled")
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)


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

内容来源: {source}
消息角色: {role}
消息内容: {content}

请提取以下信息并以 JSON 格式返回：
1. key: 记忆的键名（简洁的摘要，3-15个中文字，如"编程语言偏好"、"用户姓名"、"周五团队聚餐"、"月会通知"）
2. value: 记忆的值，格式为：
   先写核心要点摘要（1-3句话）
   然后空一行
   最后附上"以下是原文："并换行后附上原始内容
3. category: 类别，必须是以下之一：
   - preference: 用户偏好、观点、看法、价值观（包含"我认为"、"我觉得"、"我相信"、"在我看来"等）
   - fact: 客观事实、个人信息、经历、发现（姓名、职业、地点、学到的东西等）
   - pattern: 行为模式（沟通风格、使用习惯、思维方式）
   - plan: 计划、安排、预约、日程（会议、聚餐、约会、活动、提醒事项、通知等包含时间的安排）
4. confidence: 置信度（0.0-1.0，表示该信息值得保存的确定性）

如果 category 是 plan，还需要额外提取：
5. target_time: 计划的目标时间（ISO 8601格式，如"2025-01-28T14:00:00"）。如果只有日期没有时间，默认为当天09:00。如果是相对时间（如"明天"、"下周一"），请转换为具体日期（当前日期参考：{current_date}）
6. location: 地点（如果有的话）
7. participants: 参与者（如果有的话，用逗号分隔多人）

【重要提取规则】
- 包含具体时间和事件的内容（会议通知、聚餐邀请、约会安排、月会通知等）应使用 plan 类别，confidence >= 0.7
- 来自图片的会议通知、日程表、工作安排等内容非常值得保存，confidence >= 0.7
- 计划类信息的 key 应该简洁描述事件，如"周五团队聚餐"、"项目评审会议"、"月会"
- 个人观点、看法、深度思考非常值得保存，使用 preference 类别
- 用户的发现、洞见、结论也值得保存，根据内容选择 preference 或 fact
- 只有简单的问候、确认、无实质内容的消息才返回 confidence < 0.3
- key 应该是描述性的标签，不是消息原文
- value 必须包含摘要和原文两部分

只返回 JSON，不要其他文字。对于非 plan 类别：
{{"key":"提取的键名","value":"核心要点摘要。\\n\\n以下是原文：\\n原始内容","category":"类别","confidence":0.9}}

对于 plan 类别：
{{"key":"事件名称","value":"事件摘要说明。\\n\\n以下是原文：\\n原始内容","category":"plan","confidence":0.9,"target_time":"2025-01-28T14:00:00","location":"会议室A","participants":"张三,李四"}}"""


async def extract_memory_from_message(
    content: str,
    role: str = "user",
    source: str = "text",
) -> Optional[ExtractedMemory]:
    """Extract memory information from a message using LLM.

    Args:
        content: Message content to analyze
        role: Message role ('user' or 'assistant')
        source: Content source ('text' for chat messages, 'image' for OCR extracted text)

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
    source_desc = "图片OCR识别" if source == "image" else "用户输入"
    prompt = EXTRACT_PROMPT_TEMPLATE.format(
        source=source_desc,
        role="用户" if role == "user" else "AI助手",
        content=content,
        current_date=current_date,
    )

    # 应用深度思考开关逻辑
    deep_thinking_enabled = _is_deep_thinking_enabled()

    # 深度思考关闭时追加提示词
    if not deep_thinking_enabled:
        prompt += DISABLE_THINKING_PROMPT_SUFFIX

    # Call LLM API
    api_url = f"{api_base.rstrip('/')}/chat/completions"
    if deep_thinking_enabled:
        temperature = 0.5  # 深度思考时使用较高温度
    else:
        temperature = 0.3  # 关闭时使用较低温度

    request_body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,  # Increased to avoid truncation
        "temperature": temperature,
    }

    # 根据深度思考状态添加额外参数
    if deep_thinking_enabled:
        request_body["reasoning_effort"] = "high"
    else:
        request_body["reasoning_effort"] = "low"

    logger.info(f"[MemoryExtractor] deep_thinking_enabled={deep_thinking_enabled}, temperature={temperature}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                api_url,
                json=request_body,
                headers=headers
            )

            if response.status_code != 200:
                logger.info(f"[MemoryExtractor] API error: status={response.status_code}")
                return None

            result = response.json()
            response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.info(f"[MemoryExtractor] LLM response: {response_text[:500]}")

            # Parse JSON response - strip markdown code block if present
            json_text = response_text.strip()
            if json_text.startswith("```"):
                # Remove ```json or ``` prefix and ``` suffix
                lines = json_text.split("\n")
                # Find start (skip first line with ```)
                start_idx = 1 if lines[0].startswith("```") else 0
                # Find end (skip last line with ```)
                end_idx = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
                json_text = "\n".join(lines[start_idx:end_idx])

            extracted = json.loads(json_text.strip())
            logger.info(f"[MemoryExtractor] Extracted: key={extracted.get('key')}, category={extracted.get('category')}, confidence={extracted.get('confidence')}")

            return ExtractedMemory(
                key=extracted.get("key", ""),
                value=extracted.get("value", content),
                category=extracted.get("category", "fact"),
                confidence=float(extracted.get("confidence", 0.5)),
                target_time=extracted.get("target_time"),
                location=extracted.get("location"),
                participants=extracted.get("participants"),
            )

    except (json.JSONDecodeError, KeyError, ValueError, httpx.TimeoutException) as e:
        logger.info(f"[MemoryExtractor] Parse error: {type(e).__name__}: {e}")
        return None
    except Exception as e:
        logger.info(f"[MemoryExtractor] Unexpected error: {type(e).__name__}: {e}")
        return None


def get_default_extraction(content: str, role: str = "user", source: str = "text") -> ExtractedMemory:
    """Get default extraction values when LLM extraction fails.

    Args:
        content: Message content
        role: Message role
        source: Content source ('text' or 'image')

    Returns:
        ExtractedMemory with default values
    """
    if source == "image":
        key = "图片内容"
    elif role == "user":
        key = "用户输入"
    else:
        key = "AI回复"
    return ExtractedMemory(
        key=key,
        value=content,
        category="fact",
        confidence=0.5,
    )
