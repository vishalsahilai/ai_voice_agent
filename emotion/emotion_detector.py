import json
import logging
from dataclasses import dataclass
from typing import Literal
 
from llm.gemini_service import GeminiService
 
logger = logging.getLogger(__name__)

EmotionLabel = Literal[
    "happy",
    "sad",
    "angry",
    "confused",
    "excited",
    "frustrated",
    "neutral",
]
 
VALID_EMOTIONS: set[str] = {
    "happy",
    "sad",
    "angry",
    "confused",
    "excited",
    "frustrated",
    "neutral",
}

@dataclass
class EmotionResult:
    emotion: EmotionLabel
    confidence: float  # 0.0 – 1.0
    reasoning: str     # short explanation (for logging / debug)
 
 
_SYSTEM_PROMPT = """\
You are an emotion classifier. Analyze the user's message and return ONLY a JSON object.
 
Classify the emotion into exactly one of these labels:
- happy       (positive, pleased, grateful)
- excited     (enthusiastic, eager, high energy)
- sad         (down, disappointed, melancholic)
- angry       (annoyed, aggressive, hostile)
- frustrated  (stuck, exasperated, impatient)
- confused    (uncertain, lost, asking for clarification)
- neutral     (calm, informational, no strong emotion)
 
Return ONLY this JSON — no markdown, no explanation, no extra text:
{
  "emotion": "<label>",
  "confidence": <0.0 to 1.0>,
  "reasoning": "<one short sentence>"
}
"""
class EmotionDetector:
    """
    Detects emotion from transcribed user text.
 
    Usage:
        detector = EmotionDetector(gemini_service)
        result = detector.detect("I'm so confused about this!")
        # EmotionResult(emotion='confused', confidence=0.92, reasoning='...')
    """
 
    def __init__(self, gemini_service: GeminiService) -> None:
        self._gemini = gemini_service
 
    def detect(self, user_text: str) -> EmotionResult:
        """
        Synchronous detection — call via asyncio.to_thread() from async code.
 
        Falls back to 'neutral' on any error so the pipeline never crashes.
        """
        if not user_text or not user_text.strip():
            return EmotionResult(emotion="neutral", confidence=1.0, reasoning="Empty input.")
 
        try:
            raw = self._call_gemini(user_text.strip())
            return self._parse(raw)
        except Exception as exc:
            logger.warning("EmotionDetector: detection failed — %s", exc)
            return EmotionResult(emotion="neutral", confidence=1.0, reasoning="Detection error.")
 