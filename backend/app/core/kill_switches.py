"""Pre-scale containment switches for high-risk inference paths."""
from __future__ import annotations

from app.core.config import settings


READ_ONLY_PRESSURE_MODE = "read_only_pressure"


def lyra_safe_mode() -> str:
    return (settings.LYRA_SAFE_MODE or "").strip().lower()


def read_only_pressure_mode_enabled() -> bool:
    return lyra_safe_mode() == READ_ONLY_PRESSURE_MODE


def baseet_pressure_input_enabled() -> bool:
    return bool(settings.LYRA_BASEET_PRESSURE_INPUT_ENABLED)


def provider_progress_signals_enabled() -> bool:
    if read_only_pressure_mode_enabled():
        return False
    return bool(settings.LYRA_PROVIDER_PROGRESS_SIGNALS_ENABLED)


def recovery_nudges_enabled() -> bool:
    if read_only_pressure_mode_enabled():
        return False
    return bool(settings.LYRA_RECOVERY_NUDGES_ENABLED)
