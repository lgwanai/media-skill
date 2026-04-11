"""Pluggable TTS engine architecture supporting IndexTTS-2, Qwen3-TTS, and future models."""

from tts_engines.base import EmotionParser, TTSEngine
from tts_engines.factory import create_engine, get_supported_engines, is_valid_engine

__all__ = ["TTSEngine", "EmotionParser", "create_engine", "get_supported_engines", "is_valid_engine"]
