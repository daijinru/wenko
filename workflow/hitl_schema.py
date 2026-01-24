"""HITL Schema Module

Pydantic models for Human-in-the-Loop form schema system.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
import uuid


class HITLFieldType(str, Enum):
    """Supported HITL form field types."""
    TEXT = "text"
    TEXTAREA = "textarea"
    SELECT = "select"
    MULTISELECT = "multiselect"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    NUMBER = "number"
    SLIDER = "slider"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"


class HITLActionStyle(str, Enum):
    """Action button styles."""
    PRIMARY = "primary"
    DEFAULT = "default"
    SECONDARY = "secondary"
    DANGER = "danger"


class HITLAction(str, Enum):
    """User actions for HITL requests."""
    APPROVE = "approve"
    EDIT = "edit"
    REJECT = "reject"


class HITLOption(BaseModel):
    """Option for select/radio/checkbox fields."""
    value: str
    label: str


class HITLField(BaseModel):
    """HITL form field definition."""
    name: str
    type: HITLFieldType
    label: str
    required: bool = False
    placeholder: Optional[str] = None
    default: Optional[Any] = None
    options: Optional[List[HITLOption]] = None
    # For number/slider
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None


class HITLActionButton(BaseModel):
    """Action button configuration."""
    label: str
    style: HITLActionStyle = HITLActionStyle.DEFAULT


class HITLActions(BaseModel):
    """HITL action buttons configuration."""
    approve: HITLActionButton = HITLActionButton(label="确认", style=HITLActionStyle.PRIMARY)
    edit: HITLActionButton = HITLActionButton(label="修改后提交", style=HITLActionStyle.DEFAULT)
    reject: HITLActionButton = HITLActionButton(label="跳过", style=HITLActionStyle.SECONDARY)


class HITLContext(BaseModel):
    """Context information for HITL request."""
    intent: Optional[str] = None
    memory_category: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


class HITLRequest(BaseModel):
    """HITL form request schema."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "form"
    title: str
    description: Optional[str] = None
    fields: List[HITLField]
    actions: HITLActions = Field(default_factory=HITLActions)
    context: Optional[HITLContext] = None
    created_at: datetime = Field(default_factory=datetime.now)
    ttl_seconds: int = 300  # 5 minutes default


class HITLResponseData(BaseModel):
    """User response to HITL request."""
    request_id: str
    session_id: str
    action: HITLAction
    data: Optional[Dict[str, Any]] = None


class HITLContinuationData(BaseModel):
    """Data for HITL continuation to pass to LLM."""
    request_title: str
    action: str  # approve | reject
    form_data: Optional[Dict[str, Any]] = None
    field_labels: Dict[str, str] = {}  # field_name -> label mapping


class HITLResponseResult(BaseModel):
    """Result of processing HITL response."""
    success: bool
    next_action: str = "continue"  # continue | complete
    message: Optional[str] = None
    error: Optional[str] = None
    continuation_data: Optional[HITLContinuationData] = None


def parse_hitl_request_from_dict(data: Dict[str, Any]) -> Optional[HITLRequest]:
    """Parse HITL request from a dictionary (e.g., from LLM JSON output).

    Args:
        data: Dictionary containing hitl_request data

    Returns:
        HITLRequest if valid, None otherwise
    """
    try:
        # Handle nested hitl_request field
        hitl_data = data.get("hitl_request", data)

        # Validate required fields
        if "title" not in hitl_data or "fields" not in hitl_data:
            return None

        # Parse fields
        fields = []
        for field_data in hitl_data.get("fields", []):
            # Parse options if present
            options = None
            if "options" in field_data:
                options = [HITLOption(**opt) for opt in field_data["options"]]

            field = HITLField(
                name=field_data["name"],
                type=HITLFieldType(field_data["type"]),
                label=field_data["label"],
                required=field_data.get("required", False),
                placeholder=field_data.get("placeholder"),
                default=field_data.get("default"),
                options=options,
                min=field_data.get("min"),
                max=field_data.get("max"),
                step=field_data.get("step"),
            )
            fields.append(field)

        # Parse actions if present
        actions = HITLActions()
        if "actions" in hitl_data:
            actions_data = hitl_data["actions"]
            if "approve" in actions_data:
                actions.approve = HITLActionButton(**actions_data["approve"])
            if "edit" in actions_data:
                actions.edit = HITLActionButton(**actions_data["edit"])
            if "reject" in actions_data:
                actions.reject = HITLActionButton(**actions_data["reject"])

        # Parse context if present
        context = None
        if "context" in hitl_data:
            context = HITLContext(**hitl_data["context"])

        return HITLRequest(
            id=hitl_data.get("id", str(uuid.uuid4())),
            type=hitl_data.get("type", "form"),
            title=hitl_data["title"],
            description=hitl_data.get("description"),
            fields=fields,
            actions=actions,
            context=context,
            ttl_seconds=hitl_data.get("ttl_seconds", 300),
        )
    except Exception:
        return None


def create_plan_hitl_request(
    title: str = "",
    description: str = "",
    target_datetime: str = "",
) -> HITLRequest:
    """Create a HITL request for collecting plan/reminder details.

    Args:
        title: Pre-filled plan title (from LLM extraction)
        description: Pre-filled description
        target_datetime: Pre-filled target datetime (ISO format)

    Returns:
        HITLRequest configured for plan collection
    """
    return HITLRequest(
        title="创建计划提醒",
        description="请确认或修改以下计划信息，系统将在指定时间提醒您。",
        fields=[
            HITLField(
                name="title",
                type=HITLFieldType.TEXT,
                label="计划标题",
                required=True,
                placeholder="例如：开会、提交报告",
                default=title,
            ),
            HITLField(
                name="description",
                type=HITLFieldType.TEXTAREA,
                label="详细描述",
                required=False,
                placeholder="可选，添加更多细节",
                default=description,
            ),
            HITLField(
                name="target_datetime",
                type=HITLFieldType.DATETIME,
                label="目标时间",
                required=True,
                default=target_datetime,
            ),
            HITLField(
                name="reminder_offset",
                type=HITLFieldType.SELECT,
                label="提前提醒",
                required=True,
                default="10",
                options=[
                    HITLOption(value="0", label="准时提醒"),
                    HITLOption(value="5", label="提前5分钟"),
                    HITLOption(value="10", label="提前10分钟"),
                    HITLOption(value="30", label="提前30分钟"),
                    HITLOption(value="60", label="提前1小时"),
                ],
            ),
            HITLField(
                name="repeat_type",
                type=HITLFieldType.SELECT,
                label="重复",
                required=True,
                default="none",
                options=[
                    HITLOption(value="none", label="不重复"),
                    HITLOption(value="daily", label="每天"),
                    HITLOption(value="weekly", label="每周"),
                    HITLOption(value="monthly", label="每月"),
                ],
            ),
        ],
        actions=HITLActions(
            approve=HITLActionButton(label="创建提醒", style=HITLActionStyle.PRIMARY),
            edit=HITLActionButton(label="修改后创建", style=HITLActionStyle.DEFAULT),
            reject=HITLActionButton(label="取消", style=HITLActionStyle.SECONDARY),
        ),
        context=HITLContext(
            intent="collect_plan",
            memory_category="plan",
        ),
    )
