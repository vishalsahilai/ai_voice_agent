import asyncio
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from audio.stt_whisper import whisper_stt
from call.call_state_machine import CallState
from call.session_manager import Session, session_manager
from config.settings import settings
from elevenlabs.core.api_error import ApiError
from emotion.emotion_detector import EmotionDetector, EmotionResult
from emotion.voice_style_mapper import VoiceStyle, VoiceStyleMapper
from google.genai.errors import APIError as GeminiApiError
from llm.gemini_service import AllGeminiKeysExhausted, gemini_service
from memory.context_builder import build_gemini_context
from memory.memory_manager import memory_manager
from memory.summarizer import summarize_exchange_in_background
from rag.retriever import retriever
from tts.voice_manager import AllElevenLabsKeysExhausted, voice_manager
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


emotion_detector = EmotionDetector(gemini_service)
voice_mapper = VoiceStyleMapper()


async def _detect_emotion_and_map(
    session_id: str,
    user_text: str,
) -> Optional[VoiceStyle]:
    """
    Detects emotion from user_text and maps it to a VoiceStyle.
    Runs in thread pool — never blocks the event loop.
    Returns None if disabled or on any error → VoiceManager uses neutral defaults.
    """
    if not settings.EMOTION_DETECTION_ENABLED:
        return None

    try:
        emotion_result: EmotionResult = await asyncio.to_thread(
            emotion_detector.detect, user_text
        )
        voice_style: VoiceStyle = voice_mapper.map(emotion_result)

        if settings.EMOTION_LOG_RESULTS:
            logger.info(
                f"[{session_id}] Emotion: {emotion_result.emotion} "
                f"(confidence={emotion_result.confidence:.2f}) → "
                f"stability={voice_style.stability:.2f}, "
                f"similarity={voice_style.similarity_boost:.2f}, "
                f"style={voice_style.style:.2f}, "
                f"speed={voice_style.speed:.2f} | {emotion_result.reasoning}"
            )
        return voice_style

    except Exception as e:
        logger.warning(f"[{session_id}] Emotion detection failed, using neutral: {e}")
        return None


async def _handle_speech_started(session: Session, websocket: WebSocket) -> None:
    if session.state_machine.state == CallState.SPEAKING:
        session.state_machine.interrupt()
        session.interrupted = True
        await websocket.send_json({"type": "stop_audio"})
        logger.info(f"[{session.session_id}] barge-in detected — audio interrupted")
    session.utterance_buffer.reset()


async def _handle_speech_ended(session: Session, websocket: WebSocket) -> None:
    audio = session.utterance_buffer.get_audio()
    session.utterance_buffer.reset()

    if not audio:
        return

    session.interrupted = False
    session.state_machine.transition(CallState.THINKING)

    # Step 1: Whisper STT
    text = await asyncio.to_thread(whisper_stt.transcribe, audio)

    if not text:
        session.state_machine.transition(CallState.LISTENING)
        return

    await websocket.send_json({"type": "transcript", "text": text})

    # Step 2: Message count (MongoDB)
    msg_count = await memory_manager.increment_message_count(session.session_id)

    # Step 3: RAG retrieval (Pinecone)
    context = await asyncio.to_thread(retriever.retrieve, text)

    # Step 4: Build Gemini context (summaries + recent + RAG)
    contents = await build_gemini_context(
        session_id=session.session_id,
        conversation_history=session.conversation_history,
        new_user_text=text,
        retrieved_context=context,
        message_count=msg_count,
    )

    # Step 5: Gemini LLM call
    try:
        reply_text = await asyncio.to_thread(
            gemini_service.generate_reply_from_contents, contents
        )
    except AllGeminiKeysExhausted:
        logger.error(f"[{session.session_id}] all Gemini keys exhausted, skipping turn")
        session.state_machine.transition(CallState.LISTENING)
        return
    except GeminiApiError as e:
        logger.error(f"[{session.session_id}] Gemini call failed: {e}")
        session.state_machine.transition(CallState.LISTENING)
        return

    if not reply_text:
        session.state_machine.transition(CallState.LISTENING)
        return

    # Step 6: Detect emotion (Phase 6)
    voice_style = await _detect_emotion_and_map(session.session_id, text)

    # Step 7: Save to in-RAM history
    session.conversation_history.append({"role": "user", "text": text})
    session.conversation_history.append({"role": "model", "text": reply_text})

    # Step 8: Background summarization
    await summarize_exchange_in_background(
        session_id=session.session_id,
        user_text=text,
        bot_text=reply_text,
        message_count=msg_count,
    )

    session.state_machine.transition(CallState.SPEAKING)

    # Step 9: ElevenLabs TTS with emotion voice style (Phase 6)
    try:
        reply_audio = await asyncio.to_thread(
            voice_manager.synthesize, reply_text, voice_style
        )
    except AllElevenLabsKeysExhausted:
        logger.error(f"[{session.session_id}] all ElevenLabs accounts exhausted, skipping TTS")
        session.state_machine.transition(CallState.LISTENING)
        return
    except ApiError as e:
        logger.error(f"[{session.session_id}] ElevenLabs TTS failed: {e}")
        session.state_machine.transition(CallState.LISTENING)
        return

    # Step 10: Send audio to browser
    if session.interrupted:
        logger.info(f"[{session.session_id}] reply discarded — user interrupted during synthesis")
    else:
        await websocket.send_json({"type": "reply_text", "text": reply_text})
        await websocket.send_bytes(reply_audio)

    if session.state_machine.state == CallState.SPEAKING:
        session.state_machine.transition(CallState.LISTENING)


@router.websocket("/ws/call")
async def call_websocket(websocket: WebSocket):
    await websocket.accept()
    session = session_manager.create_session()

    await websocket.send_json({
        "type": "session_started",
        "session_id": session.session_id,
    })

    try:
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                raise WebSocketDisconnect(code=message.get("code", 1000))

            if "bytes" in message and message["bytes"] is not None:
                frames = session.frame_buffer.push(message["bytes"])

                for frame in frames:
                    event = session.vad.process_frame(frame)

                    if event == "speech_started":
                        await _handle_speech_started(session, websocket)
                    elif event == "speech_ended":
                        await _handle_speech_ended(session, websocket)

                    if session.vad.is_speaking:
                        session.utterance_buffer.add(frame)

            elif "text" in message and message["text"] is not None:
                logger.info(f"[{session.session_id}] control message: {message['text']}")

    except WebSocketDisconnect:
        logger.info(f"[{session.session_id}] client disconnected")
    finally:
        session_manager.end_session(session.session_id)