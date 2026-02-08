"""ImageNode and MemoryExtractionNode for image processing workflow.

ImageNode: Handles Vision API calls for OCR text extraction
MemoryExtractionNode: Extracts memory from OCR text and generates ECS forms
"""

import logging
import uuid
from typing import Dict, Any

from core.state import GraphState, ECSRequest

logger = logging.getLogger(f"workflow.{__name__}")


class ImageNode:
    """
    Node responsible for processing images via Vision API.
    Extracts text from images using OCR.
    """

    async def compute(self, state: GraphState) -> Dict[str, Any]:
        """
        Process image and extract text using Vision API.

        Args:
            state: Current graph state with image data

        Returns:
            State updates including extracted text and OCR result event
        """
        from image_analyzer import analyze_image_text, has_text_content

        images = state.semantic_input.images
        if not images:
            logger.warning("[ImageNode] No images in state")
            return {
                "response": "未提供图片",
                "ocr_result": None,
            }

        # Get the first image (base64 encoded)
        image_data = images[0]

        try:
            # Call Vision API for OCR
            extracted_text = await analyze_image_text(image_data)

            # Format OCR result message
            ocr_message = f"📷 图片文本识别结果：\n\n{extracted_text}"

            # Check if there's valid text content
            has_content = has_text_content(extracted_text)

            if not has_content:
                ocr_message += "\n\n图片中未识别到可保存的文本内容。"

            # Update semantic input with extracted text
            updated_input = state.semantic_input.model_copy()
            updated_input.text = extracted_text

            logger.info(f"[ImageNode] OCR extracted {len(extracted_text)} chars, has_content={has_content}")

            return {
                "semantic_input": updated_input,
                "response": ocr_message,
                "ocr_result": {
                    "text": extracted_text,
                    "has_content": has_content,
                },
            }

        except Exception as e:
            logger.error(f"[ImageNode] Vision API failed: {e}")
            return {
                "response": f"图片分析失败: {str(e)}",
                "ocr_result": None,
            }


class MemoryExtractionNode:
    """
    Node responsible for extracting memory from OCR text.
    Generates ECS forms for user confirmation.
    """

    async def compute(self, state: GraphState) -> Dict[str, Any]:
        """
        Extract memory from OCR text and generate ECS form.

        Args:
            state: Current graph state with OCR result

        Returns:
            State updates including ECS request for memory confirmation
        """
        from memory_extractor import extract_memory_from_message

        # Check if we should extract memory
        image_action = state.semantic_input.image_action
        if image_action != "analyze_for_memory":
            logger.info("[MemoryExtractionNode] Action is not analyze_for_memory, skipping")
            return {}

        # Get OCR text
        ocr_text = state.semantic_input.text
        if not ocr_text:
            logger.info("[MemoryExtractionNode] No OCR text to extract memory from")
            return {
                "response": "\n\n未能从文本中提取出适合保存的记忆信息。",
            }

        try:
            # Extract memory from OCR text
            memory_result = await extract_memory_from_message(
                content=ocr_text,
                role="user",
                source="image",
            )

            if not memory_result or memory_result.confidence < 0.3:
                logger.info(f"[MemoryExtractionNode] Low confidence or no result: {memory_result}")
                return {
                    "response": "\n\n未能从文本中提取出适合保存的记忆信息。",
                }

            # Generate ECS form for memory confirmation
            ecs_request = self._create_memory_ecs_request(memory_result)

            logger.info(f"[MemoryExtractionNode] Created ECS request for memory: {memory_result.key}")

            return {
                "ecs_request": ECSRequest(
                    type="confirmation",
                    message=ecs_request["title"],
                    options=[],
                    context_data={
                        "ecs_id": ecs_request["id"],
                        "memory_category": memory_result.category,
                    },
                ),
                "status": "suspended",
                "ecs_full_request": ecs_request,
            }

        except Exception as e:
            logger.error(f"[MemoryExtractionNode] Memory extraction failed: {e}")
            return {
                "response": f"\n\n记忆提取失败: {str(e)}",
            }

    def _create_memory_ecs_request(self, memory_result) -> Dict[str, Any]:
        """Create ECS request dict for memory confirmation."""
        from ecs_schema import (
            ECSField,
            ECSFieldType,
            ECSOption,
        )

        ecs_id = str(uuid.uuid4())

        # Base fields
        fields = [
            {
                "name": "key",
                "type": "text",
                "label": "记忆名称",
                "required": True,
                "placeholder": "例如：会议笔记、书籍摘录、周五聚餐",
                "default": memory_result.key,
            },
            {
                "name": "value",
                "type": "textarea",
                "label": "记忆内容",
                "required": True,
                "placeholder": "提取的文本内容",
                "default": memory_result.value,
            },
            {
                "name": "category",
                "type": "select",
                "label": "类别",
                "required": True,
                "default": memory_result.category,
                "options": [
                    {"value": "preference", "label": "偏好"},
                    {"value": "fact", "label": "事实"},
                    {"value": "pattern", "label": "模式"},
                    {"value": "plan", "label": "计划"},
                ],
            },
        ]

        # Add plan-specific fields if category is plan
        if memory_result.category == "plan":
            fields.extend([
                {
                    "name": "target_time",
                    "type": "text",
                    "label": "目标时间",
                    "required": True,
                    "placeholder": "例如：2025-01-28T14:00:00",
                    "default": getattr(memory_result, "target_time", "") or "",
                },
                {
                    "name": "location",
                    "type": "text",
                    "label": "地点",
                    "required": False,
                    "placeholder": "例如：会议室A、星巴克",
                    "default": getattr(memory_result, "location", "") or "",
                },
                {
                    "name": "participants",
                    "type": "text",
                    "label": "参与者",
                    "required": False,
                    "placeholder": "例如：张三,李四",
                    "default": getattr(memory_result, "participants", "") or "",
                },
            ])

        # Determine title based on category
        if memory_result.category == "plan":
            title = "保存计划到日程"
            description = "AI 从图片中识别到计划安排，请确认是否保存到日程。"
            ecs_type = "image_plan_confirm"
        else:
            title = "保存图片内容到长期记忆"
            description = "AI 从图片中提取了以下信息，请确认是否保存。"
            ecs_type = "image_memory_confirm"

        return {
            "id": ecs_id,
            "type": ecs_type,
            "title": title,
            "description": description,
            "fields": fields,
            "actions": {
                "approve": {"label": "保存", "style": "primary"},
                "edit": {"label": "编辑", "style": "default"},
                "reject": {"label": "跳过", "style": "secondary"},
            },
            "context": {
                "intent": "collect_plan" if memory_result.category == "plan" else "collect_preference",
                "memory_category": memory_result.category,
            },
        }
