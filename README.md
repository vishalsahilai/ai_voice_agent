# 🎙️ AI Voice Agent

A real-time voice assistant that acts as Vishal Sahil's personal AI representative. Users open a browser, click Start Call, speak naturally, and the AI responds with voice — understanding context, remembering the conversation, pulling from a knowledge base to give accurate answers, and adapting its voice tone to match the user's emotional state.

---

## What It Does

- Listens to your voice in real time via the browser mic
- Detects when you start and stop speaking (VAD)
- Transcribes what you said (Whisper, runs locally)
- Thinks using Gemini LLM with full conversation context
- Pulls relevant facts from your knowledge base (RAG via Pinecone)
- Remembers the conversation across turns using MongoDB summaries
- Detects your emotional tone and adjusts voice style accordingly (Phase 6)
- Replies in a natural voice (ElevenLabs TTS)
- Handles barge-in: if you start talking while the agent is speaking, it stops immediately

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Uvicorn |
| Real-time channel | FastAPI WebSocket |
| Voice Activity Detection | webrtcvad |
| Speech-to-Text | faster-whisper (Systran/faster-distil-whisper-medium.en) |
| LLM | Google Gemini (gemini-3.1-flash-lite) |
| Text-to-Speech | ElevenLabs (with 3-account key rotation) |
| RAG Vector Store | Pinecone (serverless) |
| Embeddings | HuggingFace sentence-transformers (all-MiniLM-L6-v2, local) |
| Memory | MongoDB + Motor (async) |
| Emotion Detection | Gemini (structured JSON classification) |
| Frontend | HTML/CSS/JS (temporary — React widget planned) |

---

## File Structure

```
ai_voice_agent/
├── main.py                        # Entry point — python main.py
├── app.py                         # FastAPI app, router wiring, serves frontend/
├── requirements.txt
├── .env                           # Your secrets (copy from .env.example)
│
├── config/
│   └── settings.py                # All config loaded from .env
│
├── call/
│   ├── call_state_machine.py      # LISTENING / THINKING / SPEAKING + interrupt()
│   └── session_manager.py         # One Session per active connection
│
├── audio/
│   ├── vad.py                     # Voice Activity Detection
│   ├── audio_buffer.py            # FrameBuffer + UtteranceBuffer
│   └── stt_whisper.py             # Local Whisper transcription
│
├── llm/
│   ├── gemini_service.py          # Gemini calls + 4-key rotation
│   └── prompt_builder.py          # System instruction + content formatting
│
├── rag/
│   ├── embeddings.py              # HuggingFace local embeddings
│   ├── vector_store.py            # Pinecone upsert + query
│   ├── ingest.py                  # One-time doc ingestion pipeline
│   └── retriever.py               # Query-time chunk retrieval
│
├── memory/
│   ├── memory_manager.py          # MongoDB CRUD (sessions, summaries)
│   ├── summarizer.py              # Background turn summarization via Gemini
│   └── context_builder.py         # Assembles summaries + history + RAG for Gemini
│
├── emotion/
│   ├── __init__.py
│   ├── emotion_detector.py        # Detects user emotion via Gemini (Phase 6)
│   └── voice_style_mapper.py      # Maps emotion → ElevenLabs voice settings (Phase 6)
│
├── tts/
│   └── voice_manager.py           # ElevenLabs TTS + account rotation + emotion style
│
├── api/
│   ├── health_routes.py           # GET /health
│   └── websocket_routes.py        # WS /ws/call — full pipeline orchestration
│
├── knowledge_base/
│   └── Vishal_Sahil_Knowledge_Document.pdf   # Source document for RAG
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js                     # Mic capture → PCM → WebSocket → audio playback
│
└── utils/
    └── logger.py
```

---

## How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up your .env (see Environment Variables section below)

# 3. Pre-download Whisper model (only needed once)
python -c "from faster_whisper import WhisperModel; WhisperModel('Systran/faster-distil-whisper-medium.en', device='cpu', compute_type='int8')"

# 4. Ingest your knowledge base into Pinecone (only needed once, or when docs change)
python -m rag.ingest

# 5. Start the server
python main.py

# 6. Open http://localhost:8000 in your browser
# Click Start Call, allow mic access, and talk
```

---

## Environment Variables

```bash
# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Gemini (LLM) — up to 4 keys for rotation across Google projects
GEMINI_API_KEY1=
GEMINI_API_KEY2=
GEMINI_API_KEY3=
GEMINI_API_KEY4=
GEMINI_MODEL=gemini-3.1-flash-lite

# Whisper (STT) — runs locally, no key needed
WHISPER_MODEL_SIZE=Systran/faster-distil-whisper-medium.en
WHISPER_DEVICE=cpu

# ElevenLabs (TTS) — key AND voice ID paired per account
# Cloned voices only exist on the account they were created on,
# so each account needs its own voice ID. Rotation moves both together.
ELEVENLABS_API_KEY1=
ELEVENLABS_VOICE_ID1=
ELEVENLABS_API_KEY2=
ELEVENLABS_VOICE_ID2=
ELEVENLABS_API_KEY3=
ELEVENLABS_VOICE_ID3=
ELEVENLABS_MODEL_ID=eleven_turbo_v2

# Pinecone (RAG vector store)
PINECONE_API_KEY=
PINECONE_INDEX_NAME=voice-agent
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1

# HuggingFace embeddings (local, no key required)
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
RAG_TOP_K=3

# MongoDB (Memory)
MONGODB_URI=
MONGODB_DB_NAME=ai_voice_agent
SESSION_EXPIRY_HOURS=2
MEMORY_RAW_TURNS_LIMIT=6

# Emotion Detection (Phase 6)
EMOTION_DETECTION_ENABLED=True
EMOTION_CONFIDENCE_THRESHOLD=0.60
EMOTION_LOG_RESULTS=True
```

---

## How the Full Pipeline Works (Per Turn)

Every time you finish speaking, this is what happens:

```
1.  VAD detects silence → speech_ended fires
2.  UtteranceBuffer hands buffered PCM audio to Whisper
3.  Whisper transcribes → "Hello, my name is Vishal"
4.  MongoDB: increment message count for this session
5.  Pinecone: embed the query, retrieve top 3 relevant chunks from knowledge base
6.  context_builder.py assembles what Gemini sees:
        - Message 1: just the current message
        - Message 2: first raw exchange + current message
        - Message 3+: MongoDB summaries + recent turns + RAG chunks + current message
7.  Gemini generates a reply (short, spoken-language, no markdown)
8.  Emotion detector classifies user's emotional tone → VoiceStyle  ← Phase 6
9.  Both turns saved to in-RAM conversation_history
10. Background task: summarizer.py compresses the exchange into JSON, saves to MongoDB
11. ElevenLabs synthesizes reply with emotion-matched voice settings  ← Phase 6
12. Transcript + reply text + audio bytes sent back down the WebSocket
13. Browser plays the audio, shows transcript in the log
```

---

## Emotion → Voice Style Mapping (Phase 6)

| Emotion | Stability | Similarity | Style | Speed |
|---|---|---|---|---|
| neutral | 0.75 | 0.75 | 0.10 | 1.00 |
| happy | 0.65 | 0.80 | 0.35 | 1.05 |
| excited | 0.55 | 0.75 | 0.50 | 1.15 |
| sad | 0.85 | 0.80 | 0.05 | 0.88 |
| angry | 0.60 | 0.70 | 0.20 | 1.08 |
| frustrated | 0.65 | 0.75 | 0.15 | 1.05 |
| confused | 0.80 | 0.80 | 0.08 | 0.93 |

If Gemini confidence is below `EMOTION_CONFIDENCE_THRESHOLD` (default 0.60), the style blends toward neutral proportionally.

---

## Phase-by-Phase Build History

### Phase 1 — Backend Skeleton ✅
**Goal:** A FastAPI server that starts, accepts WebSocket connections, and tracks session state cleanly. No AI logic yet.

**What was built:**
- `main.py`, `app.py`, FastAPI app with CORS
- `config/settings.py` — all secrets loaded from `.env`, including key rotation pools (GEMINI_API_KEY1-4, ELEVENLABS paired key+voice slots)
- `call/call_state_machine.py` — LISTENING → THINKING → SPEAKING state machine with `interrupt()` for barge-in
- `call/session_manager.py` — one Session object per active WebSocket connection
- `api/health_routes.py` — GET /health
- `api/websocket_routes.py` — accepts connection, echoes audio acks (no STT yet)
- `utils/logger.py`

**Tested:** server boots, `/health` returns 200, WebSocket connects and disconnects cleanly.

---

### Phase 2 — Voice Loop Working ✅
**Goal:** Talk into the browser and hear a voice reply. No real AI — the reply is just an echo — but the full audio pipeline runs end to end.

**What was built:**
- `audio/vad.py` — webrtcvad wrapper, fires `speech_started`/`speech_ended` events
- `audio/audio_buffer.py` — `FrameBuffer` slices arbitrary browser chunks into fixed 30ms VAD frames; `UtteranceBuffer` accumulates a full utterance
- `audio/stt_whisper.py` — faster-whisper (local, no API key), lazy-loads model on first use
- `tts/voice_manager.py` — ElevenLabs TTS with automatic key+voice rotation across 3 accounts
- `frontend/index.html`, `style.css`, `app.js` — browser mic capture → 16kHz PCM → WebSocket → plays reply audio back
- `call/session_manager.py` updated — each Session now owns its own VAD + buffers
- `api/websocket_routes.py` updated — orchestrates VAD → STT → dummy reply → TTS, with barge-in handling
- `app.py` updated — serves `frontend/` as static files at `/`

**Key decisions made:**
- Used `faster-whisper` not `openai-whisper` — openai-whisper has broken packaging on current pip/uv
- ElevenLabs free tier blocks Voice Library / default voices via API — only cloned voices work on free tier. Each account's cloned voice only exists on that account, so key and voice ID are paired per account
- `setuptools<81` pin required because webrtcvad internally imports `pkg_resources` which setuptools 81+ dropped

**Tested:** server runs, browser page loads, VAD correctly detects speech start/end, Whisper transcribes, ElevenLabs synthesizes and returns audio.

---

### Phase 3 — Real Gemini Brain ✅
**Goal:** Replace the echo reply with real Gemini responses, with conversation context across turns.

**What was built:**
- `llm/gemini_service.py` — Gemini API calls using `google-genai` SDK (not `google-generativeai` which is deprecated), with 4-key rotation
- `llm/prompt_builder.py` — formats `session.conversation_history` + new user turn into `List[types.Content]`; system instruction tells Gemini to reply like a voice (short, no markdown, no lists)
- `call/session_manager.py` updated — `conversation_history` field added
- `api/websocket_routes.py` updated — STT → Gemini → both turns appended to history → TTS

**Key decisions:**
- `google-genai` SDK: `from google import genai`, `genai.Client(api_key=...)`, `client.models.generate_content(...)`
- Gemini `APIError` has `.code` attribute (not `.status_code` like ElevenLabs) for quota detection

**Tested:** full conversation with follow-up context confirmed Gemini correctly uses conversation history.

---

### Phase 4 — RAG with Pinecone ✅
**Goal:** Give the agent access to a knowledge base so it can answer questions about Vishal accurately.

**What was built:**
- `rag/embeddings.py` — local HuggingFace `sentence-transformers` (all-MiniLM-L6-v2, 384-dim), lazy-loaded
- `rag/vector_store.py` — Pinecone serverless, auto-creates index on first use, `upsert_chunks()` and `query()`
- `rag/ingest.py` — reads `knowledge_base/*.txt`, `*.md`, `*.pdf`, chunks with overlap, embeds in batch, upserts. Deterministic chunk IDs so re-running doesn't duplicate
- `rag/retriever.py` — embeds the user query at call time, queries Pinecone for top-K relevant chunks
- `websocket_routes.py` updated — retrieval step added between STT and Gemini

**Tested:** agent correctly answers questions from PDF knowledge base.

---

### Phase 5 — Memory with MongoDB ✅
**Goal:** Long conversations no longer blow up the token budget. The agent remembers across turns.

**What was built:**
- `memory/memory_manager.py` — MongoDB CRUD: sessions, summaries, message count, 2-hour session expiry
- `memory/summarizer.py` — after every turn (message 3+), fires background `asyncio.create_task()` that calls Gemini to compress the exchange into structured JSON `{user_intent, bot_response, context}` and saves to MongoDB. Never blocks the WebSocket handler
- `memory/context_builder.py` — assembles what Gemini sees each turn (message 1 = direct, message 2 = raw exchange, message 3+ = summaries + recent + RAG)
- `gemini_service.py` updated — added `generate_reply_from_contents(contents)` method
- Barge-in improved — server sends `{"type": "stop_audio"}` to browser; browser immediately stops audio playback

**Token savings:** ~86% fewer tokens per request on long conversations.

**MongoDB document structure:**
```json
{
  "session_id": "abc-123",
  "summaries": [
    {
      "user_intent": "what the user was asking",
      "bot_response": "what the bot replied",
      "context": "key facts to remember"
    }
  ],
  "message_count": 4,
  "last_active": "2026-08-11T06:00:00Z"
}
```

**Tested:** summaries correctly saved to MongoDB, injected into context from message 3 onwards.

---

### Phase 6 — Emotion Detection + Adaptive Voice ✅
**Goal:** The agent detects the user's emotional tone and responds with a matching voice style.

**What was built:**
- `emotion/emotion_detector.py` — calls Gemini with a one-shot classification prompt, returns structured `EmotionResult(emotion, confidence, reasoning)`. Falls back to neutral on any error
- `emotion/voice_style_mapper.py` — maps emotion → `VoiceStyle(stability, similarity_boost, style, speed)`. Blends toward neutral when Gemini confidence is below threshold
- `tts/voice_manager.py` updated — `synthesize(text, voice_style=None)` accepts optional Phase 6 style; falls back to neutral defaults if None. Uses `VoiceSettings` object (correct ElevenLabs SDK format)
- `api/websocket_routes.py` updated — emotion detection step added between Gemini reply and TTS synthesis
- `config/settings.py` updated — `EMOTION_DETECTION_ENABLED`, `EMOTION_CONFIDENCE_THRESHOLD`, `EMOTION_LOG_RESULTS` settings added

**How it works:**
```
User speaks → Whisper transcribes
        ↓
Gemini generates reply
        ↓
Emotion detector classifies user text → {emotion, confidence, reasoning}
        ↓
VoiceStyleMapper maps emotion → {stability, similarity_boost, style, speed}
        ↓
ElevenLabs synthesizes reply with emotion-matched voice settings ✅
```

**Tested:** emotion correctly detected and logged per turn, voice style applied to ElevenLabs synthesis.

---

### Phase 7 — Production Hardening ⏳ (Planned)
**Goal:** Make this ready to deploy beyond localhost.

**What will be built:**
- `tests/` — unit tests for VAD, state machine, LLM service, memory, WebSocket pipeline
- Rate limiting — prevent abuse on the WebSocket endpoint
- Structured logging / error monitoring
- `Dockerfile` + `docker-compose.yml`
- Environment-specific config (dev / staging / prod)
- Latency profiling — measure where time is spent (VAD → STT → Gemini → TTS) and optimize
- React voice widget for portfolio website deployment
- Telegram/WhatsApp integration

---

## Key Architectural Decisions

**Why faster-whisper instead of openai-whisper?**
openai-whisper's `setup.py` calls `pkg_resources` at build time without declaring it as a build dependency — broken on current pip/uv. faster-whisper is a CTranslate2 reimplementation of the same models: faster on CPU, lower memory, installs cleanly.

**Why distil-whisper-medium instead of base?**
`base` model frequently mishears proper nouns (e.g. "Vishal Sahil" → "visual style") and non-native accents. `distil-whisper-medium` is 394MB, runs on CPU, and has significantly better accuracy — same underlying model as Whisper medium but 6x faster via knowledge distillation.

**Why is ElevenLabs key+voice paired per account?**
ElevenLabs free tier blocks Voice Library and default voices via API (402 error). The workaround is to clone your own voice on each account. A cloned voice only exists on the account it was created on — so rotating to account 2's key while still trying to use account 1's voice ID would fail. Key and voice ID rotate together as a pair.

**Why is Gemini key rotation only on 401/403/429?**
Rotating on any error would burn through all keys when there's a bug unrelated to quota — a bad request would silently try all 4 keys and fail confusingly. Only errors that specifically mean "this key is out of quota or unauthorized" trigger rotation.

**Why background summarization?**
Summarization is itself a Gemini API call. If it ran synchronously it would add 1-2 seconds of latency to every turn. Running it as `asyncio.create_task()` means the user gets their reply instantly and summarization happens in parallel.

**Why sentence-transformers over OpenAI/Gemini embeddings?**
Local, free, no API call at query time (which is on the hot path — every user turn triggers retrieval). all-MiniLM-L6-v2 is fast enough on CPU that it doesn't add noticeable latency.

**Why emotion detection uses Gemini not a local model?**
Emotion detection runs on the reply text after Gemini has already replied — it's off the critical path and runs concurrently with TTS synthesis. Gemini's structured JSON output is reliable and requires no additional model to download or run locally.

---

## Known Issues

| Issue | Impact | Fix |
|---|---|---|
| MongoDB datetime timezone warning | Minor, doesn't break anything | Add `tzinfo` check in `get_session()` |
| HuggingFace unauthenticated warning | Cosmetic only | Set `HF_TOKEN` in `.env` |
| Whisper picks up background noise | Sometimes transcribes silence | VAD `aggressiveness=3` + browser `noiseSuppression=true` helps |
| webrtcvad + setuptools<81 | Install-time only | Already pinned in `requirements.txt` |

---

## GitHub

```
https://github.com/vishalsahilai/ai_voice_agent
```