"""Eesti keele tuvastaja avalik Python API."""

__version__ = "0.3.1"

from .detector import Detection, Verdict, detect, is_estonian

__all__ = ["Detection", "Verdict", "detect", "is_estonian"]
