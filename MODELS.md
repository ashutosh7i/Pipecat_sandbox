# Models Reference

Exact model and voice names used in the Pipecat sandbox, based on `backend/bot.py` and Pipecat documentation.

---

## 3-Tier Mode (STT + LLM + TTS)

### Speech-to-Text (STT)

| Provider | Model | Source |
|----------|-------|--------|
| **Deepgram** | `nova-3-general` | Pipecat default (`DeepgramSTTService`), `bot.py` line 117 |
| **Soniox** | `stt-rt-v4` | Pipecat/Soniox default (`SonioxSTTService`), `bot.py` line 116 |

---

### Large Language Models (LLM)

| Provider | Model | Source |
|----------|-------|--------|
| **OpenAI** | `gpt-4.1` | Pipecat default (`OpenAILLMService`), `bot.py` line 135 |
| **Gemini** | `gemini-2.0-flash` | Explicit in `bot.py` line 128 |
| **Grok** | `grok-3-beta` | Pipecat default (`GrokLLMService`), `bot.py` line 133 |

---

### Text-to-Speech (TTS)

| Provider | Model | Voice | Source |
|----------|-------|-------|--------|
| **Cartesia** | `sonic-3` | `79a125e8-cd45-4c13-8a67-188112f4dd22` | Model: Pipecat default. Voice ID: explicit in `bot.py` line 145 |

---

## S2S Mode (Speech-to-Speech / Realtime)

### OpenAI Realtime

| Component | Model / Voice | Source |
|-----------|---------------|--------|
| **Realtime LLM** | `gpt-4o-realtime-preview` | `bot.py` line 247 |
| **Input transcription** | `gpt-4o-transcribe` | `bot.py` line 236 |
| **Output voice** | `alloy` | `bot.py` line 239 |
| **Output speed** | `1.0` | `bot.py` line 239 |

---

### Gemini Live

| Component | Model / Voice | Source |
|-----------|---------------|--------|
| **Live model** | `models/gemini-2.0-flash-exp` | `bot.py` line 291 |
| **Voice** | `Charon` | `bot.py` line 292 |

---

## Summary Table

| Mode | Service | Provider | Exact Model / Voice |
|------|---------|----------|---------------------|
| 3-tier | STT | Deepgram | `nova-3-general` |
| 3-tier | STT | Soniox | `stt-rt-v4` |
| 3-tier | LLM | OpenAI | `gpt-4.1` |
| 3-tier | LLM | Gemini | `gemini-2.0-flash` |
| 3-tier | LLM | Grok | `grok-3-beta` |
| 3-tier | TTS | Cartesia | Model: `sonic-3`, Voice: `79a125e8-cd45-4c13-8a67-188112f4dd22` |
| S2S | Realtime | OpenAI | LLM: `gpt-4o-realtime-preview`, Transcription: `gpt-4o-transcribe`, Voice: `alloy` |
| S2S | Realtime | Gemini | Model: `models/gemini-2.0-flash-exp`, Voice: `Charon` |

---

## Notes

- **Pipecat defaults**: Where no model is set in `bot.py`, Pipecat’s default for that service is used.
- **OpenAI Realtime**: Single multimodal model; transcription and voice are configured in `SessionProperties`.
- **Cartesia voice**: `79a125e8-cd45-4c13-8a67-188112f4dd22` is a Cartesia voice UUID; names are in the [Cartesia Voice Library](https://play.cartesia.ai/).
- **Gemini model path**: Gemini Live uses the full path `models/gemini-2.0-flash-exp` per the [Gemini Live API](https://ai.google.dev/gemini-api/docs).
