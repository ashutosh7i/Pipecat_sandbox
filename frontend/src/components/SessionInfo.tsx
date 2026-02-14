import type { TokenUsage } from "../hooks/useSessionInfo";

interface SessionInfoProps {
  userTranscript: string;
  botOutput: string;
  tokenUsage: TokenUsage[];
  mode: "three_tier" | "s2s";
}

function formatTokenUsage(usage: TokenUsage): string {
  const parts: string[] = [];
  if (usage.promptTokens != null || usage.completionTokens != null) {
    parts.push(
      `prompt: ${usage.promptTokens ?? 0}, completion: ${
        usage.completionTokens ?? 0
      }`
    );
  }
  if (usage.totalTokens != null) {
    parts.push(`total: ${usage.totalTokens}`);
  }
  if (usage.characters != null) {
    parts.push(`chars: ${usage.characters}`);
  }
  return parts.join(" | ") || "—";
}

export function SessionInfo({
  userTranscript,
  botOutput,
  tokenUsage,
  mode,
}: SessionInfoProps) {
  const totalPrompt = tokenUsage.reduce((s, u) => s + (u.promptTokens ?? 0), 0);
  const totalCompletion = tokenUsage.reduce(
    (s, u) => s + (u.completionTokens ?? 0),
    0
  );
  const totalChars = tokenUsage.reduce((s, u) => s + (u.characters ?? 0), 0);

  return (
    <div className="session-info">
      <h3>Session Info</h3>
      <div className="session-transcripts">
        <div>
          <label>User (transcribed)</label>
          <div className="session-text">
            {userTranscript || <span className="muted">—</span>}
          </div>
        </div>
        <div>
          <label>Bot (LLM output)</label>
          <div className="session-text">
            {botOutput || <span className="muted">—</span>}
          </div>
        </div>
      </div>
      <div className="session-tokens">
        <label>Token / character usage</label>
        <div className="token-summary">
          {mode === "s2s" ? (
            <span>
              Realtime: prompt {totalPrompt}, completion {totalCompletion}
              {totalChars > 0 ? `, chars ${totalChars}` : ""}
            </span>
          ) : (
            <span>
              STT+LLM+TTS: prompt {totalPrompt}, completion {totalCompletion}
              {totalChars > 0 ? `, TTS chars ${totalChars}` : ""}
            </span>
          )}
        </div>
        {tokenUsage.length > 0 && (
          <ul className="token-detail">
            {tokenUsage.map((u, i) => (
              <li key={i}>
                <strong>{u.processor}</strong>
                {u.model ? ` (${u.model})` : ""}: {formatTokenUsage(u)}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
