import { useCallback, useState } from "react";

export interface TokenUsage {
  processor: string;
  model?: string;
  promptTokens?: number;
  completionTokens?: number;
  totalTokens?: number;
  characters?: number;
}

export interface SessionInfoState {
  userTranscript: string;
  botOutput: string;
  tokenUsage: TokenUsage[];
}

export function useSessionInfo() {
  const [userTranscript, setUserTranscript] = useState("");
  const [botOutput, setBotOutput] = useState("");
  const [tokenUsage, setTokenUsage] = useState<TokenUsage[]>([]);

  const addUserTranscript = useCallback((text: string) => {
    setUserTranscript(text);
  }, []);

  const appendBotOutput = useCallback((text: string) => {
    setBotOutput((prev) => prev + text);
  }, []);

  const addTokenUsage = useCallback((usage: TokenUsage) => {
    setTokenUsage((prev) => {
      const existing = prev.findIndex(
        (u) => u.processor === usage.processor && u.model === usage.model
      );
      if (existing >= 0) {
        const next = [...prev];
        const cur = next[existing];
        next[existing] = {
          ...cur,
          promptTokens: (cur.promptTokens ?? 0) + (usage.promptTokens ?? 0),
          completionTokens:
            (cur.completionTokens ?? 0) + (usage.completionTokens ?? 0),
          totalTokens: (cur.totalTokens ?? 0) + (usage.totalTokens ?? 0),
          characters: (cur.characters ?? 0) + (usage.characters ?? 0),
        };
        return next;
      }
      return [...prev, usage];
    });
  }, []);

  const clearSession = useCallback(() => {
    setUserTranscript("");
    setBotOutput("");
    setTokenUsage([]);
  }, []);

  return {
    userTranscript,
    botOutput,
    tokenUsage,
    addUserTranscript,
    appendBotOutput,
    addTokenUsage,
    clearSession,
  };
}
