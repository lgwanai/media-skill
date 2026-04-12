"""ASR engine factory for pluggable architecture."""
from typing import TYPE_CHECKING

from asr_engines.base import ASREngine

if TYPE_CHECKING:
    from asr_engines.funasr_engine import FunASREngine
    from asr_engines.qwen3_asr_engine import Qwen3ASREngine

SUPPORTED_ASR_ENGINES = ["funasr", "qwen3-asr"]


def create_asr_engine(config: dict) -> ASREngine:
    """Create ASR engine instance based on config.
    
    Args:
        config: Configuration dict with ASR_ENGINE key.
        
    Returns:
        ASREngine instance for the configured engine.
        
    Raises:
        ValueError: If ASR_ENGINE is not supported.
    """
    engine = config.get("ASR_ENGINE", "funasr").strip().lower()
    
    if engine == "funasr":
        from asr_engines.funasr_engine import FunASREngine
        return FunASREngine(config)
    elif engine == "qwen3-asr":
        from asr_engines.qwen3_asr_engine import Qwen3ASREngine
        return Qwen3ASREngine(config)
    else:
        raise ValueError(f"Unsupported ASR engine: '{engine}'. Supported: {', '.join(SUPPORTED_ASR_ENGINES)}")


def get_supported_asr_engines() -> list[str]:
    """Return list of supported ASR engine names."""
    return list(SUPPORTED_ASR_ENGINES)


def is_valid_asr_engine(engine: str) -> bool:
    """Check if ASR engine name is supported."""
    return engine.strip().lower() in SUPPORTED_ASR_ENGINES
