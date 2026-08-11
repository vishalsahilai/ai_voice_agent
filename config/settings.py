from functools import lru_cache
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    #  Server 
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    #  LLM (Gemini) 
    GEMINI_API_KEY1: str = ""
    GEMINI_API_KEY2: str = ""
    GEMINI_API_KEY3: str = ""
    GEMINI_API_KEY4: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"

    @property
    def GEMINI_API_KEYS(self) -> List[str]:
        """Ordered rotation pool — empty/unset slots are dropped automatically."""
        keys = [self.GEMINI_API_KEY1, self.GEMINI_API_KEY2, self.GEMINI_API_KEY3, self.GEMINI_API_KEY4]
        return [k for k in keys if k.strip()]

    #  STT (Whisper, local/open-source) 
    WHISPER_MODEL_SIZE: str = "Systran/faster-distil-whisper-medium.en"  # tiny | base | small | medium | large
    WHISPER_DEVICE: str = "cpu"  # cpu | cuda

    #  TTS (ElevenLabs) 
    ELEVENLABS_API_KEYS1: str = ""
    ELEVENLABS_VOICE_ID1: str = ""
    ELEVENLABS_API_KEYS2: str = ""
    ELEVENLABS_VOICE_ID2: str = ""
    ELEVENLABS_API_KEYS3: str = ""
    ELEVENLABS_VOICE_ID3: str = ""
    ELEVENLABS_API_KEYS4: str = ""
    ELEVENLABS_VOICE_ID4: str = ""
    ELEVENLABS_API_KEYS5: str = ""
    ELEVENLABS_VOICE_ID5: str = ""
    ELEVENLABS_API_KEYS6: str = ""
    ELEVENLABS_VOICE_ID6: str = ""
    ELEVENLABS_API_KEYS7: str = ""
    ELEVENLABS_VOICE_ID7: str = ""
    ELEVENLABS_API_KEYS8: str = ""
    ELEVENLABS_VOICE_ID8: str = ""
    ELEVENLABS_MODEL_ID: str = "eleven_flash_v2_5"

    @property
    def ELEVENLABS_ACCOUNT_POOL(self) -> List[dict]:
        """
        Returns list of {api_key, voice_id} pairs.
        Key and voice rotate TOGETHER — a cloned voice only exists
        on the account it was cloned on.
        """
        pool = []
        for i in range(1, 6):
            key = getattr(self, f"ELEVENLABS_API_KEY{i}", "")
            voice = getattr(self, f"ELEVENLABS_VOICE_ID{i}", "")
            if key and voice:
                pool.append({"api_key": key, "voice_id": voice})
        return pool
 
    #  Audio 
    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_CHUNK_MS: int = 30  
    SILENCE_THRESHOLD_MS: int = 700  


    # Pinecone (RAG vector store)
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "voice-agent"
    PINECONE_CLOUD: str = "aws"
    PINECONE_REGION: str = "us-east-1"

    # HuggingFace (embeddings)
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    RAG_TOP_K: int = 3
    HF_TOKEN: Optional[str] = Field(default=None)

    # Memory (MongoDB)
    MONGODB_URI: str = ""
    MONGODB_DB_NAME: str = "ai_voice_agent"
    SESSION_EXPIRY_HOURS: int = 2
    MEMORY_RAW_TURNS_LIMIT: int = 6
    MEMORY_SUMMARIZE_AFTER: int = 10

    # Phase 6 — Emotion Detection
    EMOTION_DETECTION_ENABLED: bool = True
    EMOTION_CONFIDENCE_THRESHOLD: float = 0.60
    EMOTION_LOG_RESULTS: bool = True


@lru_cache
def get_settings() -> Settings:
    """Settings are read from env once and cached — call get_settings() anywhere you need config."""
    return Settings()


settings = get_settings()