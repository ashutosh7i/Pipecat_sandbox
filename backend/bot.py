"""Pipecat bot for sandbox: 3-tier (STT+LLM+TTS) and S2S (OpenAI Realtime) pipelines."""

import os
from typing import Any

from dotenv import load_dotenv
from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.frameworks.rtvi import (
    RTVIFunctionCallReportLevel,
    RTVIObserverParams,
)
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.turns.user_start import TranscriptionUserTurnStartStrategy, VADUserTurnStartStrategy
from pipecat.turns.user_stop import TurnAnalyzerUserTurnStopStrategy
from pipecat.turns.user_turn_strategies import ExternalUserTurnStrategies, UserTurnStrategies
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

from config import MODE_S2S, MODE_THREE_TIER

load_dotenv(override=True)


def _build_system_message(config: dict[str, Any]) -> str:
    """Combine system_prompt and activity_prompt into system message.
    Activity prompt is emphasized so the LLM follows it strictly."""
    system_prompt = config.get("system_prompt", "").strip()
    activity_prompt = config.get("activity_prompt", "").strip()

    if not system_prompt and not activity_prompt:
        return (
            "You are a friendly voice assistant for kids. Keep responses short, clear, and age-appropriate. "
            "You have access to tools: show_picture(url) to display an image, and show_text(text) to display text."
        )

    parts = []
    if system_prompt:
        parts.append(system_prompt)

    if activity_prompt:
        parts.append(
            "ACTIVITY INSTRUCTIONS (you MUST follow these strictly):\n"
            f"{activity_prompt}\n"
            "Always adhere to the activity instructions above in every response."
        )

    base = (
        "You have access to tools: show_picture(url) to display an image to the user, "
        "and show_text(text) to display text to the user. Call these when appropriate."
    )
    parts.append(base)
    return "\n\n".join(parts)


async def _show_picture(params: Any) -> None:
    """Mock show_picture tool - returns dummy result. Client sees tool call via RTVI."""
    args = params.arguments if hasattr(params, "arguments") else {}
    logger.info(f"[Tool] show_picture called with args: {args}")
    await params.result_callback({"status": "displayed", "url": args.get("url", "")})


async def _show_text(params: Any) -> None:
    """Mock show_text tool - returns dummy result. Client sees tool call via RTVI."""
    args = params.arguments if hasattr(params, "arguments") else {}
    logger.info(f"[Tool] show_text called with args: {args}")
    await params.result_callback({"status": "displayed", "text": args.get("text", "")})


def _create_tools_schema() -> ToolsSchema:
    """Create tools schema for show_picture and show_text."""
    show_picture_schema = FunctionSchema(
        name="show_picture",
        description="Display an image to the user. Use when you want to show a picture.",
        properties={
            "url": {"type": "string", "description": "URL of the image to display"},
        },
        required=["url"],
    )
    show_text_schema = FunctionSchema(
        name="show_text",
        description="Display text to the user. Use when you want to show text for the user to read.",
        properties={
            "text": {"type": "string", "description": "The text to display"},
        },
        required=["text"],
    )
    return ToolsSchema(standard_tools=[show_picture_schema, show_text_schema])


INITIAL_GREETING_PROMPT = (
    "You are about to start a voice conversation. Greet the user warmly and introduce yourself first. "
    "Do not wait for the user to speak - you must speak first. Follow all activity instructions in your system prompt."
)


def _create_stt(config: dict[str, Any]):
    """Create STT service based on config."""
    provider = config.get("stt_provider", "deepgram")
    if provider == "soniox":
        from pipecat.services.soniox.stt import SonioxSTTService

        return SonioxSTTService(api_key=os.getenv("SONIOX_API_KEY"))
    return DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))


def _create_llm(config: dict[str, Any], tools: ToolsSchema):
    """Create LLM service based on config."""
    provider = config.get("llm_provider", "openai")
    if provider == "gemini":
        from pipecat.services.google.llm import GoogleLLMService

        llm = GoogleLLMService(
            api_key=os.getenv("GOOGLE_API_KEY"),
            model="gemini-2.0-flash",
        )
    elif provider == "grok":
        from pipecat.services.grok.llm import GrokLLMService

        llm = GrokLLMService(api_key=os.getenv("XAI_API_KEY"))
    else:
        llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"))
    llm.register_function("show_picture", _show_picture)
    llm.register_function("show_text", _show_text)
    return llm


def _create_tts(config: dict[str, Any]):
    """Create TTS service based on config."""
    return CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id="79a125e8-cd45-4c13-8a67-188112f4dd22",
    )


async def _run_bot_three_tier(
    transport: SmallWebRTCTransport,
    system_message: str,
    tools: ToolsSchema,
    config: dict[str, Any],
) -> Pipeline:
    """Run 3-tier pipeline: STT + LLM + TTS."""
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": INITIAL_GREETING_PROMPT},
    ]
    context = LLMContext(messages=messages, tools=tools)
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(),
            user_turn_strategies=UserTurnStrategies(
                start=[
                    VADUserTurnStartStrategy(),
                    TranscriptionUserTurnStartStrategy(use_interim=True),
                ],
                stop=[
                    TurnAnalyzerUserTurnStopStrategy(
                        turn_analyzer=LocalSmartTurnAnalyzerV3()
                    ),
                ],
            ),
            user_turn_stop_timeout=8.0,  # Allow longer pauses for kids
        ),
    )

    stt = _create_stt(config)
    llm = _create_llm(config, tools)
    tts = _create_tts(config)

    return Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )


async def _run_bot_s2s(
    transport: SmallWebRTCTransport,
    system_message: str,
    tools: ToolsSchema,
    config: dict[str, Any],
) -> Pipeline:
    """Run S2S pipeline: OpenAI Realtime or Gemini Live."""
    provider = config.get("s2s_provider", "openai_realtime")
    if provider == "gemini_live":
        return await _run_bot_s2s_gemini(transport, system_message, tools, config)
    return await _run_bot_s2s_openai(transport, system_message, tools, config)


async def _run_bot_s2s_openai(
    transport: SmallWebRTCTransport,
    system_message: str,
    tools: ToolsSchema,
    config: dict[str, Any],
) -> Pipeline:
    """Run S2S pipeline using OpenAI Realtime."""
    try:
        from pipecat.services.openai.realtime.llm import OpenAIRealtimeLLMService
        from pipecat.services.openai.realtime.events import (
            AudioConfiguration,
            AudioInput,
            AudioOutput,
            InputAudioTranscription,
            SemanticTurnDetection,
            SessionProperties,
        )
    except ImportError as e:
        logger.error(f"OpenAI Realtime not available: {e}. Fallback to 3-tier.")
        return await _run_bot_three_tier(transport, system_message, tools, config)

    session_properties = SessionProperties(
        instructions=system_message,
        audio=AudioConfiguration(
            input=AudioInput(
                transcription=InputAudioTranscription(model="gpt-4o-transcribe"),
                turn_detection=SemanticTurnDetection(eagerness="medium"),
            ),
            output=AudioOutput(voice="alloy", speed=1.0),
        ),
        tools=tools,
        max_output_tokens=4096,
    )

    llm = OpenAIRealtimeLLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o-realtime-preview",
        session_properties=session_properties,
    )
    llm.register_function("show_picture", _show_picture)
    llm.register_function("show_text", _show_text)

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": INITIAL_GREETING_PROMPT},
    ]
    context = LLMContext(messages=messages, tools=tools)
    context_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            user_turn_strategies=ExternalUserTurnStrategies(),
        ),
    )

    return Pipeline(
        [
            transport.input(),
            context_aggregator.user(),
            llm,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )


async def _run_bot_s2s_gemini(
    transport: SmallWebRTCTransport,
    system_message: str,
    tools: ToolsSchema,
    config: dict[str, Any],
) -> Pipeline:
    """Run S2S pipeline using Gemini Live (per Pipecat docs and official example)."""
    try:
        from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService
    except ImportError as e:
        logger.error(f"Gemini Live not available: {e}. Install: pip install pipecat-ai[google] google-genai")
        return await _run_bot_s2s_openai(transport, system_message, tools, config)

    # Docs: https://docs.pipecat.ai/server/services/s2s/gemini-live
    # Default model for native audio: gemini-2.5-flash-native-audio-preview-12-2025
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY not set. Gemini Live requires it.")
        return await _run_bot_s2s_openai(transport, system_message, tools, config)

    llm = GeminiLiveLLMService(
        api_key=api_key,
        model="models/gemini-2.5-flash-native-audio-preview-12-2025",
        voice_id="Charon",
        system_instruction=system_message,
        tools=tools,
    )
    llm.register_function("show_picture", _show_picture)
    llm.register_function("show_text", _show_text)

    # Align with official example: context + user/assistant aggregators with VAD for phrase alignment
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": INITIAL_GREETING_PROMPT},
    ]
    context = LLMContext(messages=messages, tools=tools)
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.5)),
        ),
    )

    return Pipeline(
        [
            transport.input(),
            user_aggregator,
            llm,
            transport.output(),
            assistant_aggregator,
        ]
    )


async def run_bot(webrtc_connection: Any, config: dict[str, Any]) -> None:
    """
    Run the Pipecat bot. Supports:
    - three_tier: STT + LLM + TTS
    - s2s: OpenAI Realtime (speech-to-speech)
    """
    mode = config.get("mode", MODE_THREE_TIER)
    # S2S: use 4 chunks (40ms) for smoother playback; 3-tier: use 2 (20ms) for faster interruptions
    audio_chunks = 4 if mode == MODE_S2S else 2
    transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_out_10ms_chunks=audio_chunks,
        ),
    )

    system_message = _build_system_message(config)
    tools = _create_tools_schema()

    if mode == MODE_S2S:
        pipeline = await _run_bot_s2s(transport, system_message, tools, config)
    else:
        pipeline = await _run_bot_three_tier(transport, system_message, tools, config)

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        rtvi_observer_params=RTVIObserverParams(
            function_call_report_level={"*": RTVIFunctionCallReportLevel.FULL},
        ),
        idle_timeout_secs=300,  # 5 min production timeout
    )

    @task.event_handler("on_pipeline_started")
    async def on_pipeline_started(t, frame):
        """Queue LLMRunFrame when pipeline is ready - ensures bot speaks first reliably."""
        logger.info("Pipeline started - queueing initial greeting")
        await t.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_connected")
    async def on_client_connected(tr, client):
        logger.info("Client connected")

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(tr, client):
        logger.info("Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)
