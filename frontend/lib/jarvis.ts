/**
 * JARVIS chat client — wraps the three /v1/jarvis/* endpoints.
 *
 * Operator-only; non-operator users get a 403 from the backend and the
 * UI never renders the floating button. The fetch helper still respects
 * that gate (treats 403 as "not entitled" rather than retrying).
 */
import { api } from "@/lib/api";

export type JarvisHistoryMessage = {
  role: "system" | "user" | "assistant" | "tool";
  content: string | null;
  tool_calls?: unknown;
  tool_call_id?: string;
};

export type JarvisToolCallExecuted = {
  tool_call_id: string;
  name: string;
  args: Record<string, unknown>;
  result_summary: string;
};

export type JarvisPendingConfirmation = {
  tool_call_id: string;
  name: string;
  args: Record<string, unknown>;
  preview: string;
};

export type JarvisAskResponse = {
  answer: string;
  tool_calls_executed: JarvisToolCallExecuted[];
  pending_confirmations: JarvisPendingConfirmation[];
  history: JarvisHistoryMessage[];
  model: string;
  error: string | null;
};

export type JarvisHealth = {
  available: boolean;
  model: string;
  reason: string | null;
};

export async function jarvisAsk(
  message: string,
  history: JarvisHistoryMessage[],
): Promise<JarvisAskResponse> {
  return api<JarvisAskResponse>("/v1/jarvis/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });
}

export async function jarvisConfirm(
  pending: JarvisPendingConfirmation,
  history: JarvisHistoryMessage[],
  confirmed: boolean,
): Promise<JarvisAskResponse> {
  return api<JarvisAskResponse>("/v1/jarvis/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      tool_call_id: pending.tool_call_id,
      name: pending.name,
      args: pending.args,
      history,
      confirmed,
    }),
  });
}

export async function jarvisHealth(): Promise<JarvisHealth> {
  return api<JarvisHealth>("/v1/jarvis/health");
}
