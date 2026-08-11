import json
import logging
from dataclasses import dataclass
from typing import Literal
 
from llm.gemini_service import GeminiService
 
logger = logging.getLogger(__name__)