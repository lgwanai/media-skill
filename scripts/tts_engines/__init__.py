"""Pluggable TTS engine architecture supporting IndexTTS-2, Qwen3-TTS, LongCat-AudioDiT, and OmniVoice."""

from tts_engines.base import EmotionParser, TTSEngine
from tts_engines.factory import create_engine, get_supported_engines, is_valid_engine
from tts_engines.longcat_audiodit_engine import LongCatAudioDiTEngine
from tts_engines.omnivoice_engine import OmniVoiceEngine
from tts_engines.voice_config import load_voice_config

__all__ = [
    "TTSEngine",
    "EmotionParser",
    "create_engine",
    "get_supported_engines",
    "is_valid_engine",
    "LongCatAudioDiTEngine",
    "OmniVoiceEngine",
    "load_voice_config",
]
