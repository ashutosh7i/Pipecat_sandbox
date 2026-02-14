import type { SandboxMode } from "../hooks/useSandboxState";
import type { SandboxStateActions } from "../hooks/useSandboxState";

interface ModeSelectorProps
  extends Pick<
    SandboxStateActions,
    | "setMode"
    | "setSttProvider"
    | "setLlmProvider"
    | "setTtsProvider"
    | "setS2sProvider"
  > {
  mode: SandboxMode;
  sttProvider: string;
  llmProvider: string;
  ttsProvider: string;
  s2sProvider: string;
}

const STT_OPTIONS = [
  { value: "deepgram", label: "Deepgram (nova-3-general)" },
  { value: "soniox", label: "Soniox (stt-rt-v4)" },
];
const LLM_OPTIONS = [
  { value: "openai", label: "OpenAI (gpt-4.1)" },
  { value: "gemini", label: "Gemini (gemini-2.0-flash)" },
  { value: "grok", label: "Grok (grok-3-beta)" },
];
const TTS_OPTIONS = [{ value: "cartesia", label: "Cartesia (sonic-3)" }];
const S2S_OPTIONS = [
  {
    value: "openai_realtime",
    label: "OpenAI Realtime (gpt-4o-realtime-preview)",
  },
  {
    value: "gemini_live",
    label: "Gemini Live (gemini-2.5-flash-native-audio)",
  },
];

export function ModeSelector({
  mode,
  sttProvider,
  llmProvider,
  ttsProvider,
  s2sProvider,
  setMode,
  setSttProvider,
  setLlmProvider,
  setTtsProvider,
  setS2sProvider,
}: ModeSelectorProps) {
  const isThreeTier = mode === "three_tier";

  return (
    <div className="mode-selector">
      <h3>Mode & Models</h3>
      <div>
        <label htmlFor="mode">Mode</label>
        <select
          id="mode"
          value={mode}
          onChange={(e) => setMode(e.target.value as SandboxMode)}
        >
          <option value="three_tier">3-tier (STT + LLM + TTS)</option>
          <option value="s2s">Speech-to-Speech</option>
        </select>
      </div>
      {isThreeTier ? (
        <>
          <div>
            <label htmlFor="stt-provider">STT Provider</label>
            <select
              id="stt-provider"
              value={sttProvider}
              onChange={(e) => setSttProvider(e.target.value)}
            >
              {STT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="llm-provider">LLM Provider</label>
            <select
              id="llm-provider"
              value={llmProvider}
              onChange={(e) => setLlmProvider(e.target.value)}
            >
              {LLM_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="tts-provider">TTS Provider</label>
            <select
              id="tts-provider"
              value={ttsProvider}
              onChange={(e) => setTtsProvider(e.target.value)}
            >
              {TTS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </>
      ) : (
        <div>
          <label htmlFor="s2s-provider">S2S Provider</label>
          <select
            id="s2s-provider"
            value={s2sProvider}
            onChange={(e) => setS2sProvider(e.target.value)}
          >
            {S2S_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
}
