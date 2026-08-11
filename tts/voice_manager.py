from typing import List, Optional

from elevenlabs import ElevenLabs, VoiceSettings
from elevenlabs.core.api_error import ApiError

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class AllElevenLabsKeysExhausted(Exception):
    """Raised when every account in the rotation pool has failed with a quota/auth error."""
    pass


class ElevenLabsVoiceManager:
    DEFAULT_STABILITY: float = 0.75
    DEFAULT_SIMILARITY_BOOST: float = 0.75
    DEFAULT_STYLE: float = 0.10
    DEFAULT_SPEED: float = 1.00

    def __init__(self, account_pool: List[dict] = None, model_id: str = None):
        self.account_pool = account_pool if account_pool is not None else settings.ELEVENLABS_ACCOUNT_POOL
        self.model_id = model_id or settings.ELEVENLABS_MODEL_ID

        if not self.account_pool:
            logger.warning(
                "No complete ElevenLabs account (key + voice ID) configured — "
                "TTS will fail until .env is filled in"
            )

        self._current_index = 0
        self._client = self._build_client() if self.account_pool else None

    def _current_account(self) -> dict:
        return self.account_pool[self._current_index]

    def _build_client(self) -> ElevenLabs:
        return ElevenLabs(api_key=self._current_account()["api_key"])

    def _rotate_to_next_account(self) -> bool:
        """Move to the next {key, voice_id} pair. Returns False if we've already tried them all."""
        if self._current_index + 1 >= len(self.account_pool):
            return False
        self._current_index += 1
        logger.warning(
            f"ElevenLabs account {self._current_index} exhausted/unauthorized — "
            f"rotating to account {self._current_index + 1} of {len(self.account_pool)}"
        )
        self._client = self._build_client()
        return True

    @staticmethod
    def _is_quota_or_auth_error(exc: Exception) -> bool:
        status = getattr(exc, "status_code", None)
        return status in (401, 403, 429)

    def synthesize(self, text: str, voice_style=None) -> bytes:
        """
        Convert text to speech, returns raw audio bytes (mp3).

        Args:
            text:        The text to speak.
            voice_style: Optional Phase 6 VoiceStyle from emotion detection.
                         Falls back to neutral defaults if None.

        Rotates through the account pool on quota/auth failures.
        Raises AllElevenLabsKeysExhausted if every account is out.
        """
        if not self._client:
            raise RuntimeError("ElevenLabsVoiceManager has no accounts configured")

        if not text or not text.strip():
            logger.warning("VoiceManager: empty text received, skipping.")
            return b""

        if voice_style is not None:
            stability        = voice_style.stability
            similarity_boost = voice_style.similarity_boost
            style            = voice_style.style
            speed            = voice_style.speed
        else:
            stability        = self.DEFAULT_STABILITY
            similarity_boost = self.DEFAULT_SIMILARITY_BOOST
            style            = self.DEFAULT_STYLE
            speed            = self.DEFAULT_SPEED

        accounts_tried = 0
        while accounts_tried < len(self.account_pool):
            try:
                audio_stream = self._client.text_to_speech.convert(
                    voice_id=self._current_account()["voice_id"],
                    model_id=self.model_id,
                    text=text,
                    voice_settings=VoiceSettings(
                        stability=stability,
                        similarity_boost=similarity_boost,
                        style=style,
                        speed=speed,
                    ),
                )
                return b"".join(audio_stream)

            except ApiError as e:
                accounts_tried += 1
                if self._is_quota_or_auth_error(e) and self._rotate_to_next_account():
                    continue
                if accounts_tried >= len(self.account_pool):
                    break
                raise

        raise AllElevenLabsKeysExhausted(
            f"All {len(self.account_pool)} ElevenLabs accounts failed with quota/auth errors"
        )

voice_manager = ElevenLabsVoiceManager()