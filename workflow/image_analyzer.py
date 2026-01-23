"""Image Analyzer Module

Provides image text extraction using Vision LLM API.
Extracts text content from images (screenshots, notes, documents, etc.)
for conversion to long-term memory.
"""

import base64
import json
import os
import re
from typing import Optional

import httpx


# Vision analysis prompt
VISION_PROMPT = """请识别并提取图片中的所有文本内容。

要求：
1. 如果是截图、笔记、文档或名片，请完整提取所有可见文本
2. 保持原有的格式和换行
3. 如果图片中没有文本内容，请回复"无文本内容"
4. 只输出提取的文本，不要添加额外的解释或描述

请直接输出识别到的文本："""


def load_vision_config() -> dict:
    """Load vision configuration from chat_config.json.

    Returns:
        Configuration dict with api_base, api_key, and vision_model.

    Raises:
        FileNotFoundError: If config file doesn't exist.
    """
    config_path = os.path.join(os.path.dirname(__file__), "chat_config.json")

    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"配置文件不存在: {config_path}。请复制 chat_config.example.json 为 chat_config.json 并填写 API Key。"
        )

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    return {
        "api_base": config.get("api_base", "https://api.openai.com/v1"),
        "api_key": config.get("api_key", ""),
        "vision_model": config.get("vision_model", config.get("model", "gpt-4o-mini")),
    }


def parse_image_data(image_data: str) -> tuple[str, str]:
    """Parse image data URL or raw base64.

    Args:
        image_data: Either a data URL (data:image/png;base64,...) or raw base64 string.

    Returns:
        Tuple of (media_type, base64_data).
    """
    if image_data.startswith("data:"):
        # Parse data URL format: data:image/png;base64,iVBORw0...
        match = re.match(r"data:(image/[^;]+);base64,(.+)", image_data)
        if match:
            return match.group(1), match.group(2)
        # Fallback if format is slightly different
        parts = image_data.split(",", 1)
        if len(parts) == 2:
            media_match = re.search(r"image/[^;]+", parts[0])
            media_type = media_match.group(0) if media_match else "image/png"
            return media_type, parts[1]

    # Assume raw base64 data with PNG as default
    return "image/png", image_data


async def analyze_image_text(image_data: str) -> str:
    """Analyze image and extract text content using Vision LLM.

    Args:
        image_data: Base64 encoded image data (can be data URL or raw base64).

    Returns:
        Extracted text content from the image.

    Raises:
        ValueError: If image data is invalid or analysis fails.
    """
    config = load_vision_config()

    if not config["api_key"]:
        raise ValueError("API Key 未配置")

    media_type, base64_data = parse_image_data(image_data)

    # Validate base64 data
    try:
        decoded = base64.b64decode(base64_data)
        if len(decoded) > 4 * 1024 * 1024:  # 4MB limit
            raise ValueError("图片大小超过 4MB 限制")
    except Exception as e:
        if "图片大小" in str(e):
            raise
        raise ValueError(f"无效的图片数据: {e}")

    # Build OpenAI Vision API request
    api_url = f"{config['api_base'].rstrip('/')}/chat/completions"

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": VISION_PROMPT},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{base64_data}",
                        "detail": "high",  # Use high detail for better text recognition
                    },
                },
            ],
        }
    ]

    request_body = {
        "model": config["vision_model"],
        "messages": messages,
        "max_tokens": 2048,
        "temperature": 0.1,  # Low temperature for more accurate extraction
    }

    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(api_url, json=request_body, headers=headers)

            if response.status_code != 200:
                error_text = response.text
                raise ValueError(f"Vision API 请求失败: {response.status_code} - {error_text}")

            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            if not content:
                return "无文本内容"

            return content.strip()

    except httpx.TimeoutException:
        raise ValueError("Vision API 请求超时，请稍后重试")
    except httpx.ConnectError:
        raise ValueError("无法连接到 Vision API 服务器")
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"图片分析失败: {str(e)}")


def has_text_content(extracted_text: str) -> bool:
    """Check if extracted text contains meaningful content.

    Args:
        extracted_text: Text extracted from image.

    Returns:
        True if text has meaningful content, False otherwise.
    """
    if not extracted_text:
        return False

    # Check for common "no text" responses
    no_text_patterns = [
        "无文本内容",
        "没有文本",
        "图片中没有",
        "无法识别",
        "no text",
        "cannot identify",
    ]

    text_lower = extracted_text.lower()
    for pattern in no_text_patterns:
        if pattern.lower() in text_lower:
            return False

    # Check if there's substantial content (at least some characters)
    clean_text = re.sub(r"\s+", "", extracted_text)
    return len(clean_text) >= 2
