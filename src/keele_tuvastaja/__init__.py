"""Eesti keele tuvastaja avalik Python API."""

from .detector import Detection, Verdict, detect, is_estonian, warm_up

__all__ = ["Detection", "Verdict", "detect", "is_estonian", "warm_up"]
