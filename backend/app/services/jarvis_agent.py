"""JARVIS agent loop — ties NIM ↔ tools ↔ pending-confirmation queue.

Operator-only (2026-04-30). Sits between the FastAPI endpoint and the
NIM client. The endpoint hands off (user_id, user_message, history) and
gets back a response object the chat UI can render directly.

Loop semantics:
  1. Build system prompt (Lyra context + clock + tool list)
  2. Send messages + tools to NIM
  3. If NIM returns final content (no tool calls) → return as the answer
  4. If NIM returns READ tool calls → execute immediately, append results,
     loop with the new conversation state
  5. If NIM returns WRITE tool calls → DO NOT execute. Append a stubbed
     "queued for confirmation" tool result so NIM can describe the action,
     then return — UI surfaces the confirmation chip
  6. Hard cap at MAX_ITERATIONS=5 (defends against runaway loops)

Confirmation flow:
  - /v1/jarvis/ask returns pending_confirmations: PendingAction[]
  - User clicks Confirm → /v1/jarvis/confirm executes the write tool +
    re-enters the loop with the real result so NIM can finalize the
    response ("Done — created 'Lab 8' for 3pm")
  - User clicks Cancel → /v1/jarvis/confirm marks status='rejected' +
    returns a short cancel acknowledgement (no NIM round-trip needed)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services import jarvis_tools, nvidia_nim_client
from app.services.nvidia_nim_client import NimConfigError, NimError, NimUnavailable
from app.utils.time_utils import now_utc

logger = logging.getLogger(__name__)


MAX_ITERATIONS = 8


def _build_system_prompt(user_timezone: str) -> str:
    """The Lyra context block + tool-use instructions."""
    return (
        "You are Lyra, the in-app assistant for the Lyra Secretary product. "
        "Lyra is a measurement-backed task scheduler that records planned vs "
        "executed time per task. The user is the operator (the developer who "
        "built Lyra), so they understand the system deeply and prefer terse, "
        "direct answers without filler. When you refer to yourself, say "
        "'Lyra' — never 'JARVIS' or 'the assistant'.\n\n"
        f"Current UTC time: {now_utc().isoformat()}.\n"
        f"User timezone: {user_timezone} (interpret natural-language times in this zone).\n\n"
        "When to use tools (be deliberate, not eager):\n"
        "- Greetings, chitchat, meta questions ('hi', 'what can you do?', "
        "'how does this work?'), and questions about Lyra-the-product itself "
        "→ answer directly with NO tool calls. A warm one-line intro + an "
        "offer to help is the right shape.\n"
        "- Specific factual questions about ONE dimension ('what's overdue?', "
        "'how much focus time today?', 'what am I working on?') → call "
        "exactly ONE targeted tool and respond.\n"
        "- Analytical / pattern / trend / 'how am I doing' / 'what's "
        "obvious' / 'what's subtle' / comparison questions → call "
        "get_pattern_summary ONCE. It returns totals, by-category "
        "bias_factor, by-time-of-day deltas, readiness signal, skip rate, "
        "overdue count, and outliers in a single response. Do NOT chain "
        "individual tools when get_pattern_summary covers it.\n"
        "- DISCOVERY questions ('what patterns do you see in my data', "
        "'discover something', 'what's surprising', 'what do you notice', "
        "'what's hidden in my behavior') → call analyze_behavioral_signature "
        "ONCE for the deep fingerprint (pause-reason distribution, recovery "
        "latency, hesitation chain, schedule volatility, context-switch "
        "graph, snooze chains, reflection engagement). Then OPTIONALLY drill "
        "into specific signals via query_dark_columns (whitelisted only). "
        "Then propose 1-3 specific hypotheses via propose_pattern_hypothesis "
        "— each MUST have a falsifier, a generality_tag (operator-only vs "
        "potentially-general), and a valence_class (friction / flow / "
        "scope_creep / under_plan / neutral). Use generality_tag honestly: "
        "most operator patterns are 'operator-only' (topology-specific "
        "traits like introspection appetite); only behavioral primitives "
        "(transition friction, recovery latency, abandonment topology) "
        "are 'potentially-general'. NEVER call get_pattern_summary AND "
        "analyze_behavioral_signature in the same turn — they overlap.\n"
        "- After tool results, synthesize a real READ — don't just echo "
        "the headline number. For 'obvious patterns' name the largest "
        "effect (top category, biggest overrun, highest skip rate). For "
        "'subtle patterns' name a non-headline signal the user might miss: "
        "a category with bias_factor >> 1.3 (systematic overrun), a time-"
        "of-day bucket with avg_delta_min much worse than others, a "
        "readiness inversion (sharp sessions overrunning MORE than drained "
        "ones — the manifesto's VT-22 signal), or an outlier title.\n"
        "- Never call the same tool twice in one turn. If you already "
        "have data from a tool this turn, work with what you have.\n\n"
        "Discovery integrity rules:\n"
        "- Confidence scales with sample size. A pattern with n=12 is "
        "'tentative'; n>=30 is 'confirmed'; n<5 is 'cold_start' — say so "
        "explicitly when you describe a hypothesis.\n"
        "- Cite specific numbers from tool output. NEVER fabricate numbers.\n"
        "- ASK the operator if a pattern matches their lived experience "
        "before treating it as validated. Operator validation is the only "
        "ground truth pre-cohort.\n"
        "- A pattern without a falsifier is not a hypothesis — it's a "
        "narrative. Always state what would kill the pattern.\n"
        "- Discovery layer ≠ inference layer. You PROPOSE; rule-based "
        "math VALIDATES and ships. Don't promise the operator that "
        "users will see your hypothesis surfaced — promotion to user-"
        "facing requires (a) operator validation, (b) re-derivability "
        "in rule-based code, (c) generality_tag = 'potentially-general'.\n"
        "- ANTI-HALLUCINATION RULE (HARD): every tool result includes a "
        "'coverage' field with `covered_signal_categories` and "
        "`NOT_covered_dont_speculate_about_these`. If the operator asks "
        "about something in NOT_covered (onboarding fingerprint, modal "
        "dwell, integration-connect patterns, archetype-survey timings, "
        "demographic data, etc.), you MUST say explicitly: 'I don't have "
        "that signal in my tool output — I can only speak to the "
        "categories in covered_signal_categories.' Do NOT invent patterns "
        "from data you don't have. A confident-sounding fabrication is "
        "WORSE than honest 'I can't answer that with current tools' — "
        "it erodes the trust substrate the entire Phase 2 soak depends "
        "on. The operator caught this on 2026-05-02 (chat about "
        "onboarding integration-connect order, which the tool does NOT "
        "surface). Don't repeat it.\n\n"
        "Write tools (create_task, start_focus_session, mark_deadline_done, "
        "sync_moodle_now) are GATED — they queue for user confirmation. When "
        "the system tells you a write is queued, summarize the proposed "
        "action in one sentence and stop. Do not chain more writes.\n\n"
        "Other rules:\n"
        "- Never invent task IDs or deadline IDs. Only use IDs the read tools "
        "returned in this conversation.\n"
        "- Be concise. The chat UI is small; one short paragraph max unless "
        "the user explicitly asks for detail."
    )


def _truncate_history(messages: list[dict], max_pairs: int = 8) -> list[dict]:
    """Keep the system prompt + the last N user/assistant pairs.

    NIM free tier has a context window way bigger than we need; this is
    a defense against pathological "type a 50k-char prompt" abuse and
    keeps response latency stable.
    """
    if len(messages) <= 1 + max_pairs * 2:
        return messages
    system = [m for m in messages if m["role"] == "system"][:1]
    others = [m for m in messages if m["role"] != "system"]
    return system + others[-(max_pairs * 2) :]


def _extract_tool_calls(message: dict) -> list[dict]:
    """Pull tool_calls out of a NIM assistant message. Empty list if none."""
    tcs = message.get("tool_calls") or []
    out = []
    for tc in tcs:
        fn = tc.get("function") or {}
        name = fn.get("name")
        if not name:
            continue
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {}
        out.append({"id": tc.get("id"), "name": name, "args": args})
    return out


def run_agent(
    db: Session,
    user_id: int,
    user_timezone: str,
    user_message: str,
    history: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Single agent invocation. Returns the chat-UI response object.

    Args:
      db: SQLAlchemy session (auto-scoped via ContextVar).
      user_id: Operator's user_id (from auth).
      user_timezone: For natural-language time interpretation.
      user_message: The fresh user turn.
      history: Prior {role, content[, tool_calls/tool_call_id]} messages
        from the chat thread (excluding the system prompt). The agent
        prepends a fresh system prompt each call (cheap + keeps clock fresh).

    Returns:
      {
        "answer": str,                       # final assistant text
        "tool_calls_executed": list[dict],   # read-tool history for UI chips
        "pending_confirmations": list[dict], # write tools awaiting user
        "history": list[dict],               # updated message log for next turn
        "model": str,                        # NIM model used
        "error": str | None,                 # set when NIM was unreachable
      }
    """
    if not nvidia_nim_client.is_configured():
        return _error_response(
            "JARVIS is offline — NVIDIA_NIM_API_KEY not configured.",
            history=history or [],
        )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _build_system_prompt(user_timezone)},
    ]
    messages.extend(history or [])
    messages.append({"role": "user", "content": user_message})
    messages = _truncate_history(messages)

    tools = jarvis_tools.all_tools()
    executed: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []

    for iteration in range(MAX_ITERATIONS):
        try:
            response = nvidia_nim_client.chat_completion(
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.2,
                max_tokens=900,
            )
        except NimUnavailable as e:
            logger.info("JARVIS: NIM unavailable: %s", e)
            return _error_response(
                f"JARVIS is offline — {e}", history=history or []
            )
        except NimConfigError as e:
            logger.warning("JARVIS: NIM config error: %s", e)
            return _error_response(
                f"JARVIS misconfigured — {e}", history=history or []
            )
        except NimError as e:
            logger.exception("JARVIS: unexpected NIM error")
            return _error_response(f"JARVIS unexpected error: {e}", history=history or [])

        choice = (response.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        # Echo the assistant message into the running thread so the
        # next loop iteration carries the tool_calls + content.
        messages.append({
            "role": "assistant",
            "content": message.get("content"),
            "tool_calls": message.get("tool_calls") or None,
        })

        tool_calls = _extract_tool_calls(message)
        if not tool_calls:
            # Plain text answer → done.
            answer = (message.get("content") or "").strip()
            return {
                "answer": answer,
                "tool_calls_executed": executed,
                "pending_confirmations": pending,
                "history": [m for m in messages if m["role"] != "system"],
                "model": response.get("model") or settings.NVIDIA_NIM_MODEL,
                "error": None,
            }

        # Dispatch each tool call. Reads run immediately; writes queue.
        for tc in tool_calls:
            name = tc["name"]
            args = tc["args"]
            tc_id = tc["id"]

            if jarvis_tools.is_write_tool(name):
                pending.append({
                    "tool_call_id": tc_id,
                    "name": name,
                    "args": args,
                    "preview": _preview_write(name, args),
                })
                # Log the queued state. confirmed_at stays NULL until /confirm.
                jarvis_tools.write_invocation(
                    db, user_id, name, args, {"queued": True},
                    status="pending_confirmation",
                )
                # Stub result so NIM understands what happened.
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": json.dumps({
                        "queued_for_user_confirmation": True,
                        "name": name,
                        "args": args,
                    }),
                })
            else:
                result = jarvis_tools.execute_read_tool(db, user_id, name, args)
                executed.append({
                    "tool_call_id": tc_id,
                    "name": name,
                    "args": args,
                    "result_summary": jarvis_tools._summarize_result(result),
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": json.dumps(result),
                })

        # If we queued any writes, NIM should now produce a one-sentence
        # summary of what's queued. We continue the loop so it can do that
        # turn, but we cap iterations to prevent runaway chains.
        if pending and not any(
            tc for tc in tool_calls if not jarvis_tools.is_write_tool(tc["name"])
        ):
            # Pure-write turn — let NIM produce the confirmation summary
            # on the next iteration, then exit.
            pass

    # Hit the iteration cap. Return whatever we have with a soft notice.
    return {
        "answer": (
            "Hit my reasoning iteration cap. Try asking the question again "
            "or breaking it into smaller pieces."
        ),
        "tool_calls_executed": executed,
        "pending_confirmations": pending,
        "history": [m for m in messages if m["role"] != "system"],
        "model": settings.NVIDIA_NIM_MODEL,
        "error": "max_iterations_exceeded",
    }


def _preview_write(name: str, args: dict) -> str:
    """One-line human description of a queued write action for the chip."""
    if name == "create_task":
        return (
            f"Create task '{args.get('title', '?')}' at {args.get('when_iso', '?')} "
            f"for {args.get('duration_minutes', '?')} min"
        )
    if name == "start_focus_session":
        return f"Start a focus session on task {args.get('task_id', '?')[:8]}"
    if name == "mark_deadline_done":
        return f"Mark deadline {args.get('deadline_id', '?')[:8]} as completed"
    if name == "sync_moodle_now":
        return "Trigger an immediate Moodle resync"
    return f"{name}({args})"


def _error_response(message: str, history: list[dict]) -> dict[str, Any]:
    return {
        "answer": message,
        "tool_calls_executed": [],
        "pending_confirmations": [],
        "history": history,
        "model": settings.NVIDIA_NIM_MODEL,
        "error": message,
    }
