"""ECS Schema Module

Pydantic models for Externalized Cognitive Step form schema system.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
import uuid


class ECSFieldType(str, Enum):
    """Supported ECS form field types."""
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


class ECSDisplayType(str, Enum):
    """Supported ECS display component types."""
    TABLE = "table"
    ASCII = "ascii"


class ECSActionStyle(str, Enum):
    """Action button styles."""
    PRIMARY = "primary"
    DEFAULT = "default"
    SECONDARY = "secondary"
    DANGER = "danger"


class ECSAction(str, Enum):
    """User actions for ECS requests."""
    APPROVE = "approve"
    EDIT = "edit"
    REJECT = "reject"


class ECSOption(BaseModel):
    """Option for select/radio/checkbox fields."""
    value: str
    label: str


class ECSField(BaseModel):
    """ECS form field definition."""
    name: str
    type: ECSFieldType
    label: str
    required: bool = False
    placeholder: Optional[str] = None
    default: Optional[Any] = None
    options: Optional[List[ECSOption]] = None
    # For number/slider
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None


class ECSActionButton(BaseModel):
    """Action button configuration."""
    label: str
    style: ECSActionStyle = ECSActionStyle.DEFAULT


class ECSActions(BaseModel):
    """ECS action buttons configuration."""
    approve: ECSActionButton = ECSActionButton(label="确认", style=ECSActionStyle.PRIMARY)
    edit: ECSActionButton = ECSActionButton(label="修改后提交", style=ECSActionStyle.DEFAULT)
    reject: ECSActionButton = ECSActionButton(label="跳过", style=ECSActionStyle.SECONDARY)


class ECSContext(BaseModel):
    """Context information for ECS request."""
    intent: Optional[str] = None
    memory_category: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


class ECSTableData(BaseModel):
    """Data for table display component."""
    headers: List[str]
    rows: List[List[str]]
    alignment: Optional[List[str]] = None  # "left" | "center" | "right"
    caption: Optional[str] = None


class ECSAsciiData(BaseModel):
    """Data for ASCII art display component."""
    content: str
    title: Optional[str] = None


class ECSDisplayField(BaseModel):
    """Display field for visual display request."""
    type: ECSDisplayType
    data: Dict[str, Any]  # Will be parsed based on type


class ECSDisplayRequest(BaseModel):
    """ECS visual display request schema."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "visual_display"
    title: str
    description: Optional[str] = None
    displays: List[ECSDisplayField]
    dismiss_label: str = "关闭"
    created_at: datetime = Field(default_factory=datetime.now)
    ttl_seconds: int = 300


class ECSRequest(BaseModel):
    """ECS form request schema."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "form"
    title: str
    description: Optional[str] = None
    fields: List[ECSField]
    actions: ECSActions = Field(default_factory=ECSActions)
    context: Optional[ECSContext] = None
    created_at: datetime = Field(default_factory=datetime.now)
    ttl_seconds: int = 300  # 5 minutes default


class ECSResponseData(BaseModel):
    """User response to ECS request."""
    request_id: str
    session_id: str
    action: ECSAction
    data: Optional[Dict[str, Any]] = None


class ECSContinuationData(BaseModel):
    """Data for ECS continuation to pass to LLM."""
    request_title: str
    action: str  # approve | reject
    form_data: Optional[Dict[str, Any]] = None
    field_labels: Dict[str, str] = {}  # field_name -> label mapping


class ECSResponseResult(BaseModel):
    """Result of processing ECS response."""
    success: bool
    next_action: str = "continue"  # continue | complete
    message: Optional[str] = None
    error: Optional[str] = None
    continuation_data: Optional[ECSContinuationData] = None


def parse_ecs_request_from_dict(data: Dict[str, Any]) -> Optional[Union[ECSRequest, ECSDisplayRequest]]:
    """Parse ECS request from a dictionary (e.g., from LLM JSON output).

    Args:
        data: Dictionary containing ecs_request data

    Returns:
        ECSRequest or ECSDisplayRequest if valid, None otherwise
    """
    try:
        # Handle nested ecs_request field
        ecs_data = data.get("ecs_request", data)

        # Check if it's a visual_display type
        if ecs_data.get("type") == "visual_display":
            return _parse_display_request(ecs_data)

        # Validate required fields for form type
        if "title" not in ecs_data or "fields" not in ecs_data:
            return None

        # Parse fields
        fields = []
        for field_data in ecs_data.get("fields", []):
            # Parse options if present and not None
            options = None
            if field_data.get("options"):
                options = [ECSOption(**opt) for opt in field_data["options"]]

            field = ECSField(
                name=field_data["name"],
                type=ECSFieldType(field_data["type"]),
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
        actions = ECSActions()
        if "actions" in ecs_data:
            actions_data = ecs_data["actions"]
            if "approve" in actions_data:
                actions.approve = ECSActionButton(**actions_data["approve"])
            if "edit" in actions_data:
                actions.edit = ECSActionButton(**actions_data["edit"])
            if "reject" in actions_data:
                actions.reject = ECSActionButton(**actions_data["reject"])

        # Parse context if present and not None
        context = None
        if ecs_data.get("context"):
            context = ECSContext(**ecs_data["context"])

        return ECSRequest(
            id=ecs_data.get("id", str(uuid.uuid4())),
            type=ecs_data.get("type", "form"),
            title=ecs_data["title"],
            description=ecs_data.get("description"),
            fields=fields,
            actions=actions,
            context=context,
            ttl_seconds=ecs_data.get("ttl_seconds", 300),
        )
    except Exception:
        return None


def _parse_display_request(ecs_data: Dict[str, Any]) -> Optional[ECSDisplayRequest]:
    """Parse visual display request from dictionary.

    Args:
        ecs_data: Dictionary containing visual_display ecs_request data

    Returns:
        ECSDisplayRequest if valid, None otherwise
    """
    try:
        # Validate required fields
        if "title" not in ecs_data or "displays" not in ecs_data:
            return None

        # Parse display fields
        displays = []
        for display_data in ecs_data.get("displays", []):
            display_type = display_data.get("type")
            if display_type not in [t.value for t in ECSDisplayType]:
                continue

            display_field = ECSDisplayField(
                type=ECSDisplayType(display_type),
                data=display_data.get("data", {}),
            )
            displays.append(display_field)

        if not displays:
            return None

        return ECSDisplayRequest(
            id=ecs_data.get("id", str(uuid.uuid4())),
            type="visual_display",
            title=ecs_data["title"],
            description=ecs_data.get("description"),
            displays=displays,
            dismiss_label=ecs_data.get("dismiss_label", "关闭"),
            ttl_seconds=ecs_data.get("ttl_seconds", 300),
        )
    except Exception:
        return None


def create_plan_ecs_request(
    title: str = "",
    description: str = "",
    target_datetime: str = "",
) -> ECSRequest:
    """Create a ECS request for collecting plan/reminder details.

    Args:
        title: Pre-filled plan title (from LLM extraction)
        description: Pre-filled description
        target_datetime: Pre-filled target datetime (ISO format)

    Returns:
        ECSRequest configured for plan collection
    """
    return ECSRequest(
        title="创建计划提醒",
        description="请确认或修改以下计划信息，系统将在指定时间提醒您。",
        fields=[
            ECSField(
                name="title",
                type=ECSFieldType.TEXT,
                label="计划标题",
                required=True,
                placeholder="例如：开会、提交报告",
                default=title,
            ),
            ECSField(
                name="description",
                type=ECSFieldType.TEXTAREA,
                label="详细描述",
                required=False,
                placeholder="可选，添加更多细节",
                default=description,
            ),
            ECSField(
                name="target_datetime",
                type=ECSFieldType.DATETIME,
                label="目标时间",
                required=True,
                default=target_datetime,
            ),
            ECSField(
                name="reminder_offset",
                type=ECSFieldType.SELECT,
                label="提前提醒",
                required=True,
                default="10",
                options=[
                    ECSOption(value="0", label="准时提醒"),
                    ECSOption(value="5", label="提前5分钟"),
                    ECSOption(value="10", label="提前10分钟"),
                    ECSOption(value="30", label="提前30分钟"),
                    ECSOption(value="60", label="提前1小时"),
                ],
            ),
            ECSField(
                name="repeat_type",
                type=ECSFieldType.SELECT,
                label="重复",
                required=True,
                default="none",
                options=[
                    ECSOption(value="none", label="不重复"),
                    ECSOption(value="daily", label="每天"),
                    ECSOption(value="weekly", label="每周"),
                    ECSOption(value="monthly", label="每月"),
                ],
            ),
        ],
        actions=ECSActions(
            approve=ECSActionButton(label="创建提醒", style=ECSActionStyle.PRIMARY),
            edit=ECSActionButton(label="修改后创建", style=ECSActionStyle.DEFAULT),
            reject=ECSActionButton(label="取消", style=ECSActionStyle.SECONDARY),
        ),
        context=ECSContext(
            intent="collect_plan",
            memory_category="plan",
        ),
    )
