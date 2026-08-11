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
 