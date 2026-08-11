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
 