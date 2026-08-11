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
    confidence: float 
    reasoning: str    
 
 
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

   # Internal helpers
    def _call_gemini(self, text: str) -> str:
        """
        Calls Gemini with a short classify prompt.
        Reuses GeminiService's key rotation under the hood.
        """
        prompt_message = f"User message: \"{text}\""

        from google.genai import types  # type: ignore
 
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part(text=_SYSTEM_PROMPT),
                    types.Part(text=prompt_message),
                ],
            )
        ]
 
        return self._gemini.generate_reply_from_contents(contents)
 
    def _parse(self, raw: str) -> EmotionResult:
        """
        Safely parses Gemini's JSON response.
        Falls back to neutral on any parse error.
        """
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.splitlines()
                cleaned = "\n".join(
                    line for line in lines
                    if not line.startswith("```")
                ).strip()
 
            data = json.loads(cleaned)
 
            emotion = str(data.get("emotion", "neutral")).lower()
            if emotion not in VALID_EMOTIONS:
                logger.warning("EmotionDetector: unknown emotion '%s', defaulting to neutral", emotion)
                emotion = "neutral"
 
            confidence = float(data.get("confidence", 0.8))
            confidence = max(0.0, min(1.0, confidence))
 
            reasoning = str(data.get("reasoning", ""))
 
            return EmotionResult(
                emotion=emotion,  
                confidence=confidence,
                reasoning=reasoning,
            )
 
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            logger.warning("EmotionDetector: parse error — %s | raw=%r", exc, raw)
            return EmotionResult(emotion="neutral", confidence=1.0, reasoning="Parse error.")
 