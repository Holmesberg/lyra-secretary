"use client";
/**
 * Lyra assistant chat dialog — operator-only conversational surface.
 *
 * Architecture:
 *  - Conversation state lives in component-local React state. No DB
 *    persistence — closing the modal wipes the thread by design (privacy
 *    + simplicity for v1).
 *  - Message turns: user types → POST /v1/jarvis/ask → render answer +
 *    tool-call chips inline + confirmation chips for any queued writes.
 *  - Confirmation chip → POST /v1/jarvis/confirm with confirmed=true|false
 *    → backend executes (or rejects) and returns a follow-up answer turn.
 *
 * Visual tone matches the Neural Noir grammar of /pulse:
 *  - terminal-panel chrome, hairline-signal borders
 *  - cyan accents for read tools, ember accents for queued writes
 *  - tactile micro-animations only on send + on confirmation flip
 */
import { useEffect, useRef, useState } from "react";
import {
  jarvisAsk,
  jarvisConfirm,
  type JarvisHistoryMessage,
  type JarvisPendingConfirmation,
  type JarvisToolCallExecuted,
} from "@/lib/jarvis";

type Turn = {
  id: string;
  role: "user" | "assistant" | "system_status";
  content: string;
  toolCalls?: JarvisToolCallExecuted[];
  pending?: JarvisPendingConfirmation[];
};

interface Props {
  open: boolean;
  onClose: () => void;
}

function uid(): string {
  return Math.random().toString(36).slice(2, 10);
}

export function JarvisChatModal({ open, onClose }: Props) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<JarvisHistoryMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [turns]);

  async function send(message: string) {
    if (!message.trim() || busy) return;
    setBusy(true);
    setTurns((prev) => [
      ...prev,
      { id: uid(), role: "user", content: message },
    ]);
    setInput("");
    try {
      const res = await jarvisAsk(message, history);
      setHistory(res.history);
      setTurns((prev) => [
        ...prev,
        {
          id: uid(),
          role: "assistant",
          content: res.answer || (res.error ?? ""),
          toolCalls: res.tool_calls_executed,
          pending: res.pending_confirmations,
        },
      ]);
    } catch (e: unknown) {
      const msg =
        e instanceof Error
          ? e.message
          : typeof e === "string"
            ? e
            : "Lyra request failed";
      setTurns((prev) => [
        ...prev,
        { id: uid(), role: "system_status", content: msg },
      ]);
    } finally {
      setBusy(false);
    }
  }

  async function handleConfirm(
    pending: JarvisPendingConfirmation,
    confirmed: boolean,
  ) {
    if (busy) return;
    setBusy(true);
    setTurns((prev) => [
      ...prev,
      {
        id: uid(),
        role: "system_status",
        content: confirmed
          ? `Confirmed → ${pending.preview}`
          : `Cancelled → ${pending.preview}`,
      },
    ]);
    try {
      const res = await jarvisConfirm(pending, history, confirmed);
      setHistory(res.history);
      setTurns((prev) => [
        ...prev,
        {
          id: uid(),
          role: "assistant",
          content: res.answer || (res.error ?? ""),
          toolCalls: res.tool_calls_executed,
          pending: res.pending_confirmations,
        },
      ]);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Confirmation failed";
      setTurns((prev) => [
        ...prev,
        { id: uid(), role: "system_status", content: msg },
      ]);
    } finally {
      setBusy(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-end bg-void/70 p-4 backdrop-blur-sm sm:items-center sm:justify-center"
      onClick={onClose}
    >
      <div
        className="terminal-panel flex h-[640px] w-full max-w-[560px] flex-col overflow-hidden rounded-md border border-hairline-signal/40 bg-void-2/95 shadow-[0_0_40px_rgba(0,229,255,0.08)]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-hairline-signal/30 bg-void/40 px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="status-dot bg-signal shadow-[0_0_8px_rgba(0,229,255,0.6)]" />
            <span className="font-mono text-sm tracking-widest text-signal">
              Lyra
            </span>
            <span className="font-mono text-[10px] uppercase tracking-widest text-dust-deep">
              · operator console
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="font-mono text-xs text-dust transition-colors hover:text-parchment"
            aria-label="Close Lyra"
          >
            ESC ✕
          </button>
        </div>

        {/* Conversation */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-4 py-4 text-sm"
        >
          {turns.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center text-center text-dust-deep">
              <div className="font-mono text-xs uppercase tracking-widest text-signal/60">
                /// boot sequence complete
              </div>
              <div className="mt-2 max-w-[320px] text-xs text-dust">
                Ask anything about your tasks, deadlines, focus minutes, or
                tell me to create something. Try:{" "}
                <span className="italic text-signal/80">
                  "what's overdue?"
                </span>{" "}
                or{" "}
                <span className="italic text-signal/80">
                  "create a 30 min study block at 3pm for Lab 8"
                </span>
                .
              </div>
            </div>
          )}
          <div className="flex flex-col gap-4">
            {turns.map((t) => (
              <TurnView
                key={t.id}
                turn={t}
                disabled={busy}
                onConfirm={handleConfirm}
              />
            ))}
            {busy && (
              <div className="text-xs italic text-dust-deep">
                Lyra is thinking…
              </div>
            )}
          </div>
        </div>

        {/* Composer */}
        <div className="border-t border-hairline-signal/30 bg-void/40 px-3 py-3">
          <div className="flex items-end gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={2}
              placeholder="Ask Lyra… (Enter to send, Shift+Enter for newline)"
              className="flex-1 resize-none rounded-sm border border-hairline-signal/30 bg-void-2/60 px-3 py-2 font-mono text-xs text-parchment placeholder:text-dust-deep focus:border-signal/60 focus:outline-none"
              disabled={busy}
            />
            <button
              type="button"
              onClick={() => send(input)}
              disabled={busy || !input.trim()}
              className="rounded-sm border border-signal/40 bg-signal/10 px-3 py-2 font-mono text-[11px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/20 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function TurnView({
  turn,
  disabled,
  onConfirm,
}: {
  turn: Turn;
  disabled: boolean;
  onConfirm: (p: JarvisPendingConfirmation, confirmed: boolean) => void;
}) {
  if (turn.role === "system_status") {
    return (
      <div className="font-mono text-[10px] uppercase tracking-widest text-dust-deep">
        // {turn.content}
      </div>
    );
  }
  if (turn.role === "user") {
    return (
      <div className="ml-auto max-w-[80%] rounded-sm border border-hairline-signal/30 bg-void-2/60 px-3 py-2 text-parchment">
        {turn.content}
      </div>
    );
  }
  return (
    <div className="max-w-[90%]">
      <div className="font-mono text-[10px] uppercase tracking-widest text-signal/70">
        Lyra
      </div>
      <div className="mt-1 whitespace-pre-wrap text-parchment">
        {turn.content}
      </div>
      {turn.toolCalls && turn.toolCalls.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {turn.toolCalls.map((tc) => (
            <span
              key={tc.tool_call_id}
              className="rounded-sm border border-signal/30 bg-signal/5 px-2 py-0.5 font-mono text-[10px] text-signal/80"
              title={tc.result_summary}
            >
              🔧 {tc.name}
            </span>
          ))}
        </div>
      )}
      {turn.pending && turn.pending.length > 0 && (
        <div className="mt-3 flex flex-col gap-2">
          {turn.pending.map((p) => (
            <div
              key={p.tool_call_id}
              className="alert-bar-ember rounded-sm border border-ember/40 bg-ember/5 px-3 py-2 text-xs"
            >
              <div className="text-ember">
                Lyra wants to:{" "}
                <span className="font-mono">{p.preview}</span>
              </div>
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => onConfirm(p, true)}
                  className="rounded-sm border border-signal/40 bg-signal/10 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-signal transition-colors hover:bg-signal/20 disabled:opacity-40"
                >
                  Confirm
                </button>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => onConfirm(p, false)}
                  className="rounded-sm border border-hairline-signal/40 bg-void-2/60 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-dust transition-colors hover:bg-void-2 disabled:opacity-40"
                >
                  Cancel
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
