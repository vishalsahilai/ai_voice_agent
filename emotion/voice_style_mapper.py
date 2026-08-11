from dataclasses import dataclass
from typing import Dict
 
from emotion.emotion_detector import EmotionLabel, EmotionResult
 
@dataclass
class VoiceStyle:
    """
    ElevenLabs voice generation parameters.
    All values are floats in their documented ranges.
    """
    stability: float        
    similarity_boost: float  
    style: float           
    speed: float           

# Emotion → Voice Style mapping table
# Tuned for a professional-but-warm personal AI voice
_NEUTRAL_STYLE = VoiceStyle(
    stability=0.75,
    similarity_boost=0.75,
    style=0.10,
    speed=1.00,
)
 
_EMOTION_MAP: Dict[EmotionLabel, VoiceStyle] = {
    "neutral": _NEUTRAL_STYLE,
 
    "happy": VoiceStyle(
        stability=0.65,
        similarity_boost=0.80,
        style=0.35,
        speed=1.05,
    ),
 
    "excited": VoiceStyle(
        stability=0.55,
        similarity_boost=0.75,
        style=0.50,
        speed=1.15,
    ),
 
    "sad": VoiceStyle(
        stability=0.85,
        similarity_boost=0.80,
        style=0.05,
        speed=0.88,
    ),
 
    "angry": VoiceStyle(
        stability=0.60,
        similarity_boost=0.70,
        style=0.20,
        speed=1.08,
    ),
 
    "frustrated": VoiceStyle(
        stability=0.65,
        similarity_boost=0.75,
        style=0.15,
        speed=1.05,
    ),
 
    "confused": VoiceStyle(
        stability=0.80,
        similarity_boost=0.80,
        style=0.08,
        speed=0.93,
    ),
}

 
class VoiceStyleMapper:
    """
    Maps an EmotionResult → VoiceStyle, blending toward neutral
    when confidence is low.
 
    Usage:
        mapper = VoiceStyleMapper()
        style  = mapper.map(emotion_result)
        # VoiceStyle(stability=0.65, similarity_boost=0.80, style=0.35, speed=1.05)
    """

    CONFIDENCE_THRESHOLD: float = 0.60

    def map(self, result: EmotionResult) -> VoiceStyle:
        """
        Returns a VoiceStyle for the given EmotionResult.
        Blends toward neutral if confidence < CONFIDENCE_THRESHOLD.
        """
        target = _EMOTION_MAP.get(result.emotion, _NEUTRAL_STYLE)
 
        if result.confidence >= self.CONFIDENCE_THRESHOLD:
            return target

        blend_factor = result.confidence / self.CONFIDENCE_THRESHOLD 
        return self._blend(target, _NEUTRAL_STYLE, blend_factor)

    def map_by_label(self, emotion: EmotionLabel, confidence: float = 1.0) -> VoiceStyle:
        """
        Convenience method — map directly by label without an EmotionResult object.
        """
        from emotion.emotion_detector import EmotionResult as _ER
        return self.map(_ER(emotion=emotion, confidence=confidence, reasoning=""))

    # Internal helpers
    @staticmethod
    def _blend(a: VoiceStyle, b: VoiceStyle, t: float) -> VoiceStyle:
        """
        Linear interpolation between style `a` (t=1.0) and style `b` (t=0.0).
        """
        def lerp(x: float, y: float) -> float:
            return x * t + y * (1.0 - t)
 
        return VoiceStyle(
            stability=round(lerp(a.stability, b.stability), 3),
            similarity_boost=round(lerp(a.similarity_boost, b.similarity_boost), 3),
            style=round(lerp(a.style, b.style), 3),
            speed=round(lerp(a.speed, b.speed), 3),
        )
 