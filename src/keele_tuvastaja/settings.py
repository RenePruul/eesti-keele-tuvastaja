"""API seadistus keskkonnamuutujatest."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} peab olema positiivne täisarv") from exc
    if value < 1:
        raise RuntimeError(f"{name} peab olema positiivne täisarv")
    return value


def _positive_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} peab olema positiivne arv") from exc
    if value <= 0:
        raise RuntimeError(f"{name} peab olema positiivne arv")
    return value


@dataclass(frozen=True)
class Settings:
    max_text_length: int = 10_000
    max_request_bytes: int = 20_000
    request_timeout_seconds: float = 5.0

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            max_text_length=_positive_int("KEELETUVASTAJA_MAX_TEXT_LENGTH", 10_000),
            max_request_bytes=_positive_int("KEELETUVASTAJA_MAX_REQUEST_BYTES", 20_000),
            request_timeout_seconds=_positive_float(
                "KEELETUVASTAJA_REQUEST_TIMEOUT_SECONDS", 5.0
            ),
        )
