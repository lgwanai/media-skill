"""Pluggable TTS engine architecture supporting IndexTTS-2, Qwen3-TTS, and future models."""

from .base import EmotionParser, TTSEngine

__all__ = ["TTSEngine", "EmotionParser"]


def __getattr__(name: str):
    if name == "create_engine":
        from .factory import create_engine

        return create_engine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
