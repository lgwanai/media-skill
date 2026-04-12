"""ASR engine abstract base class for pluggable speech recognition architecture."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class TimestampItem:
    """Single timestamp segment with text and timing."""
    text: str
    start_time: float  # seconds
    end_time: float    # seconds
    speaker: Optional[str] = None


@dataclass
class TranscriptionResult:
    """Result from ASR transcription."""
    language: str
    text: str
    timestamps: Optional[List[TimestampItem]] = None
    file_md5: Optional[str] = None


class ASREngine(ABC):
    """Abstract base class for pluggable ASR engines.
    
    All ASR implementations (FunASR, Qwen3-ASR) must inherit from this
    class and implement the abstract methods.
    """
    
    def __init__(self, config: dict) -> None:
        """Initialize the ASR engine with configuration.
        
        Args:
            config: Configuration dictionary loaded from config.txt via load_config().
        """
        self.config = config
        self._model = None
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the engine's unique name identifier.
        
        Examples: "funasr", "qwen3-asr"
        """
        ...
    
    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Return True if this engine supports real-time streaming transcription."""
        ...
    
    @property
    @abstractmethod
    def supports_timestamps(self) -> bool:
        """Return True if this engine provides word/character-level timestamps."""
        ...
    
    @abstractmethod
    def load_model(self) -> None:
        """Load the ASR model (lazy loading).
        
        Must be implemented by each engine to handle its own initialization,
        such as downloading model weights, establishing API connections,
        or warming up inference pipelines.
        """
        ...
    
    @abstractmethod
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        context: str = "",
        return_timestamps: bool = True,
    ) -> TranscriptionResult:
        """Transcribe audio file to text with optional timestamps.
        
        Args:
            audio_path: Path to audio file (16kHz mono WAV recommended).
            language: Language hint (None for auto-detect).
            context: Context hint for biasing (up to 10K tokens for Qwen3-ASR).
            return_timestamps: Whether to include word/character-level timestamps.
            
        Returns:
            TranscriptionResult with language, text, and timestamps.
        """
        ...
