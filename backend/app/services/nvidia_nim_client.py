"""NVIDIA NIM client — OpenAI-compatible wrapper over build.nvidia.com.

Surfaces one method used across the LyraOS LLM stack:
  - chat_completion()         — single-shot, returns full response dict

Trust class boundary:
  - Hosted NIM remains optional and degrades to Ollama on transient failure
  - Privacy: every call sends user task content to NVIDIA. Mom + sister +
    students stay on the Ollama-only enrichment path unless explicitly enabled
    through the parser enrichment path
  - Default model switched 2026-05-09 to moonshotai/kimi-k2.6 with
    chat_template_kwargs.thinking enabled by default. Structured parser calls
    disable thinking explicitly to preserve JSON.

Graceful-degradation contract (matches the existing Ollama contract in
llm_parser.py so callers can swap with a feature flag):
  - 5xx / timeout / connection error → raises NimUnavailable
    Caller falls back to Ollama or marks llm_parse_status='unavailable'
  - 4xx (auth, malformed body, model not found) → raises NimConfigError
    Caller logs + surfaces; this is a developer error, not a runtime hiccup
  - 429 (rate limit) → raises NimUnavailable (transient — back off + retry
    on the next worker cycle, don't crash parser enrichment)

Why httpx over the openai SDK:
  - httpx already in requirements.txt; openai SDK would add tiktoken + other
    deps for behavior we don't need (only using chat-completions, no
    embeddings/audio/files API surface)
  - The OpenAI-compat endpoint shape is stable + small enough to call directly
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class NimError(Exception):
    """Base class for NIM client errors."""


class NimUnavailable(NimError):
    """Transient failure — caller should fall back or retry later.

    Includes: connection refused, timeout, 5xx server errors, 429 rate limit.
    """


class NimConfigError(NimError):
    """Permanent failure — bad API key, unknown model, malformed request.

    Caller should log + surface to operator; retrying won't help.
    """


# Stable hosted-parser model defaults. Operator can override per env var without
# touching code.
DEFAULT_MODEL = "moonshotai/kimi-k2.6"
DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"


def is_configured() -> bool:
    """True iff NVIDIA_NIM_API_KEY is set and looks plausible.

    Cheap predicate — call before each LLM operation to decide whether
    to attempt NIM (fall back to Ollama otherwise). NIM keys are prefixed
    `nvapi-` per the developer-program docs; a non-empty value that
    starts with that prefix passes the cheap check, the actual auth
    happens on the first request.
    """
    key = getattr(settings, "NVIDIA_NIM_API_KEY", "") or ""
    return bool(key) and key.startswith("nvapi-")


def _build_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.NVIDIA_NIM_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _effective_chat_template_kwargs(
    override: Optional[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Return NVIDIA chat_template_kwargs for this request.

    Kimi K2.6 uses {"thinking": true} to enable its reasoning mode. The default
    is controlled by env, but callers that need strict structured output can
    pass an explicit override such as {"thinking": false}.
    """
    if override is not None:
        return override
    if getattr(settings, "NVIDIA_NIM_ENABLE_THINKING", False):
        return {"thinking": True}
    return None


def _classify_http_error(status_code: int, body_text: str) -> NimError:
    """Map HTTP status to the right exception class for the contract."""
    if status_code in (401, 403):
        return NimConfigError(f"NIM auth rejected ({status_code}): {body_text[:200]}")
    if status_code == 404:
        return NimConfigError(
            f"NIM model not found ({status_code}). Check NVIDIA_NIM_MODEL: {body_text[:200]}"
        )
    if status_code == 429:
        # Rate limit — caller should back off + retry; NOT a config error.
        return NimUnavailable(f"NIM rate-limited ({status_code}): {body_text[:200]}")
    if 400 <= status_code < 500:
        return NimConfigError(f"NIM 4xx ({status_code}): {body_text[:200]}")
    return NimUnavailable(f"NIM 5xx ({status_code}): {body_text[:200]}")


def chat_completion(
    messages: list[dict[str, Any]],
    model: Optional[str] = None,
    tools: Optional[list[dict[str, Any]]] = None,
    tool_choice: str | dict[str, Any] = "auto",
    temperature: float = 0.2,
    max_tokens: int = 1024,
    response_format: Optional[dict[str, Any]] = None,
    chat_template_kwargs: Optional[dict[str, Any]] = None,
    timeout_seconds: Optional[int] = None,
) -> dict[str, Any]:
    """Single-shot chat completion. Returns the parsed JSON response dict.

    The shape matches OpenAI's chat-completions response. Parser enrichment
    reads choices[0].message.content.

    Raises NimUnavailable on 5xx/timeout/connection (fallback path).
    Raises NimConfigError on 4xx (developer/operator action needed).
    """
    if not is_configured():
        raise NimConfigError("NVIDIA_NIM_API_KEY not set or invalid format")

    model = model or settings.NVIDIA_NIM_MODEL
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice
    if response_format:
        payload["response_format"] = response_format
    template_kwargs = _effective_chat_template_kwargs(chat_template_kwargs)
    if template_kwargs:
        payload["chat_template_kwargs"] = template_kwargs

    url = f"{settings.NVIDIA_NIM_BASE_URL.rstrip('/')}/chat/completions"
    timeout = timeout_seconds or settings.NVIDIA_NIM_TIMEOUT_SECONDS

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, headers=_build_headers(), json=payload)
    except httpx.TimeoutException as e:
        raise NimUnavailable(f"NIM timeout after {timeout}s: {e}") from e
    except httpx.ConnectError as e:
        raise NimUnavailable(f"NIM connection failed: {e}") from e
    except httpx.HTTPError as e:
        raise NimUnavailable(f"NIM HTTP error: {e}") from e

    if response.status_code != 200:
        raise _classify_http_error(response.status_code, response.text)

    try:
        return response.json()
    except json.JSONDecodeError as e:
        raise NimUnavailable(f"NIM returned non-JSON body: {e}") from e


def health_check() -> dict[str, Any]:
    """Cheap probe for operator NIM diagnostics.

    Returns:
      {"available": bool, "model": str, "reason": str|None}

    Sends a 1-token chat completion. The remaining health callers are
    operator-gated diagnostics; user-facing parser enrichment falls back
    without needing this probe.
    """
    if not is_configured():
        return {
            "available": False,
            "model": settings.NVIDIA_NIM_MODEL,
            "reason": "NVIDIA_NIM_API_KEY not set",
        }
    try:
        chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=16,
            temperature=0.0,
        )
        return {
            "available": True,
            "model": settings.NVIDIA_NIM_MODEL,
            "reason": None,
        }
    except NimError as e:
        return {
            "available": False,
            "model": settings.NVIDIA_NIM_MODEL,
            "reason": str(e),
        }
