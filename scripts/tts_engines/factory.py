"""Engine factory for pluggable TTS architecture."""
from typing import TYPE_CHECKING

from scripts.tts_engines.base import TTSEngine

if TYPE_CHECKING:
    from scripts.tts_engines.indextts_engine import IndexTTSEngine
    from scripts.tts_engines.qwen3tts_engine import Qwen3TTSEngine

SUPPORTED_ENGINES = ["indextts", "qwen3-tts"]


def create_engine(config: dict) -> TTSEngine:
    """Create TTS engine instance based on config.
    
    Args:
        config: Configuration dict with TTS_ENGINE key.
        
    Returns:
        TTSEngine instance for the configured engine.
        
    Raises:
        ValueError: If TTS_ENGINE is not a supported value.
    """
    engine = config.get("TTS_ENGINE", "indextts").strip().lower()
    
    if engine == "indextts":
        from scripts.tts_engines.indextts_engine import IndexTTSEngine
        return IndexTTSEngine(config)
    elif engine == "qwen3-tts":
        from scripts.tts_engines.qwen3tts_engine import Qwen3TTSEngine
        return Qwen3TTSEngine(config)
    else:
        raise ValueError(f"Unsupported TTS engine: '{engine}'. Supported: {', '.join(SUPPORTED_ENGINES)}")


def get_supported_engines() -> list[str]:
    """Return list of supported engine names."""
    return list(SUPPORTED_ENGINES)


def is_valid_engine(engine: str) -> bool:
    """Check if engine name is supported."""
    return engine.strip().lower() in SUPPORTED_ENGINES
