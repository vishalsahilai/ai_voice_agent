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
 