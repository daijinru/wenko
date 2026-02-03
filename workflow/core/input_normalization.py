from typing import List, Dict, Any, Optional
import logging
from workflow.core.state import SemanticInput
from workflow.intent_recognizer import IntentRecognizer, IntentResult

logger = logging.getLogger(__name__)

class InputNormalizer:
    """
    Component responsible for converting raw inputs into structured SemanticInput.
    """

    def __init__(self, intent_recognizer: Optional[IntentRecognizer] = None):
        self.intent_recognizer = intent_recognizer

    async def normalize(
        self,
        text: str,
        images: List[str] = None,
        files: List[str] = None,
        raw_event: Dict[str, Any] = None,
        llm_client: Any = None,
        api_base: str = None,
        api_key: str = None,
        model: str = None
    ) -> SemanticInput:
        """
        Normalize raw input into SemanticInput.

        Args:
            text: Primary text content
            images: List of image paths/references
            files: List of file paths
            raw_event: Original event data
            llm_client: Client for intent recognition (if needed)
            api_base: API base for intent recognition
            api_key: API key for intent recognition
            model: Model for intent recognition

        Returns:
            SemanticInput object
        """
        images = images or []
        files = files or []
        raw_event = raw_event or {}

        intent_str = None

        # Try to recognize intent if recognizer is available and text is present
        if self.intent_recognizer and text:
            try:
                # We assume intent_recognizer is configured or we pass params
                intent_result: IntentResult = await self.intent_recognizer.recognize(
                    message=text,
                    api_base=api_base,
                    api_key=api_key,
                    model=model
                )

                if intent_result and intent_result.intent_type:
                    intent_str = intent_result.intent_type
            except Exception as e:
                logger.error(f"Failed to recognize intent: {e}")

        return SemanticInput(
            text=text,
            images=images,
            files=files,
            intent=intent_str,
            raw_event=raw_event
        )
