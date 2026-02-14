import { PipecatClient } from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";

export type OnToolCallRef = {
  current: (name: string, args: Record<string, unknown>) => void;
};

export type SessionCallbacks = {
  onUserTranscript?: (text: string, final: boolean) => void;
  onBotOutput?: (text: string, spoken: boolean) => void;
  onMetrics?: (data: unknown) => void;
};

export type SessionCallbacksRef = {
  current: SessionCallbacks;
};

export function parseMetricsToTokenUsage(
  data: unknown
): import("../hooks/useSessionInfo").TokenUsage[] {
  const usages: import("../hooks/useSessionInfo").TokenUsage[] = [];
  if (!data || typeof data !== "object") return usages;
  const raw = data as Record<string, unknown>;
  const d = (raw.data ?? raw) as Record<string, unknown>;

  const walkArray = (
    arr: unknown[],
    check: (e: Record<string, unknown>) => void
  ) => {
    if (!Array.isArray(arr)) return;
    for (const entry of arr) {
      if (entry && typeof entry === "object")
        check(entry as Record<string, unknown>);
    }
  };

  const addLlm = (e: Record<string, unknown>, val: unknown) => {
    if (!val || typeof val !== "object") return;
    const v = val as Record<string, unknown>;
    if ("prompt_tokens" in v || "completion_tokens" in v) {
      usages.push({
        processor: String(e.processor ?? ""),
        model: e.model != null ? String(e.model) : undefined,
        promptTokens: (v.prompt_tokens as number) ?? 0,
        completionTokens: (v.completion_tokens as number) ?? 0,
        totalTokens:
          (v.total_tokens as number) ??
          ((v.prompt_tokens as number) ?? 0) +
            ((v.completion_tokens as number) ?? 0),
      });
    }
  };

  walkArray((d.processing as unknown[]) ?? [], (e) => {
    addLlm(e, e.value);
  });
  walkArray((d.llm_usage as unknown[]) ?? [], (e) => {
    addLlm(e, e.value ?? e);
  });

  walkArray((d.characters as unknown[]) ?? [], (e) => {
    if (typeof e.value === "number") {
      usages.push({
        processor: String(e.processor ?? ""),
        model: e.model != null ? String(e.model) : undefined,
        characters: e.value,
      });
    }
  });

  return usages;
}

export function createPipecatClient(
  onToolCallRef: OnToolCallRef,
  sessionCallbacksRef?: SessionCallbacksRef
): PipecatClient {
  const transport = new SmallWebRTCTransport({
    iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
  });

  const callbacks: Record<string, (...args: unknown[]) => void> = {
    onLLMFunctionCallInProgress: (data: {
      function_name?: string;
      tool_call_id: string;
      arguments?: Record<string, unknown>;
    }) => {
      if (data.function_name && onToolCallRef.current) {
        onToolCallRef.current(data.function_name, data.arguments ?? {});
      }
    },
  };

  if (sessionCallbacksRef) {
    callbacks.onUserTranscript = (data: unknown) => {
      const d = data as { text?: string; final?: boolean };
      sessionCallbacksRef.current.onUserTranscript?.(
        d?.text ?? "",
        d?.final ?? true
      );
    };
    callbacks.onBotOutput = (data: unknown) => {
      const d = data as { text?: string; spoken?: boolean };
      sessionCallbacksRef.current.onBotOutput?.(
        d?.text ?? "",
        d?.spoken ?? false
      );
    };
    callbacks.onMetrics = (data: unknown) => {
      sessionCallbacksRef.current.onMetrics?.(data);
    };
  }

  const client = new PipecatClient({
    transport,
    enableMic: true,
    enableCam: false,
    callbacks,
  });

  return client;
}
