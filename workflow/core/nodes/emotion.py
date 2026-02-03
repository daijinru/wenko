from typing import Dict, Any
from workflow.core.state import GraphState, EmotionalContext
from workflow.emotion_detector import extract_emotion_from_text, EmotionResult

class EmotionNode:
    """
    Node responsible for inferring user emotion from input.
    """

    async def compute(self, state: GraphState) -> Dict[str, Any]:
        """
        Analyze input and update emotional context.
        """
        text = state.semantic_input.text
        if not text:
            return {}

        # 1. Heuristic Detection (Fast)
        result: EmotionResult = extract_emotion_from_text(text)

        # 2. (Optional) LLM-based detection could go here
        # if confidence is low, or if configured to use better model.

        # 3. Determine modulation instruction based on emotion
        modulation = self._get_modulation_instruction(result.primary)

        # 4. Update state
        emotional_context = EmotionalContext(
            current_emotion=result.primary,
            valence=self._get_valence(result.category), # Approximation
            arousal=result.confidence, # Using confidence as proxy for intensity for now
            modulation_instruction=modulation
        )

        return {"emotional_context": emotional_context}

    def _get_modulation_instruction(self, emotion: str) -> str:
        """Get system prompt instruction for the given emotion."""
        instructions = {
            "happy": "User is happy. Maintain a positive and energetic tone.",
            "sad": "User is sad. Be supportive, gentle, and empathetic.",
            "anxious": "User is anxious. Be calm, reassuring, and clear.",
            "frustrated": "User is frustrated. Be concise, apologetic if needed, and solution-oriented.",
            "confused": "User is confused. Explain things clearly and simply, step by step.",
            "neutral": "Maintain a helpful and professional tone."
        }
        return instructions.get(emotion, instructions["neutral"])

    def _get_valence(self, category: str) -> float:
        if category == "positive":
            return 0.5
        elif category == "negative":
            return -0.5
        return 0.0
