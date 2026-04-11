import re
from abc import ABC, abstractmethod


class TTSEngine(ABC):
    """Abstract base class for pluggable TTS engines.

    All TTS engine implementations (IndexTTS, Qwen3-TTS, etc.) must inherit
    from this class and implement the four abstract methods plus the name property.

    Attributes:
        config: Configuration dictionary loaded from config.txt via load_config().
    """

    def __init__(self, config: dict) -> None:
        """Initialize the TTS engine with configuration.

        Args:
            config: Configuration dictionary from load_config(), containing
                    engine-specific settings like API keys, model names, etc.
        """
        self.config = config

    @property
    @abstractmethod
    def supports_emotion(self) -> bool:
        """Return True if this engine supports emotion control via emo_vector."""
        ...

    @property
    @abstractmethod
    def supports_instruct(self) -> bool:
        """Return True if this engine supports instruct-based voice design."""
        ...

    @abstractmethod
    def load_model(self) -> None:
        """Load the TTS model (local model weights or API client setup).

        Must be implemented by each engine to handle its own initialization,
        such as downloading model weights, establishing API connections,
        or warming up inference pipelines.
        """
        ...

    @abstractmethod
    def clone_voice(
        self, ref_audio: str, text: str, voice_name: str
    ) -> str:
        """Clone a voice from a reference audio sample.

        Args:
            ref_audio: Path to the reference audio file for voice cloning.
            text: Text spoken in the reference audio (used by some engines).
            voice_name: Human-readable name to assign to the cloned voice.

        Returns:
            A voice identifier string (format: "engine:reference") that can
            be passed to synthesize() for voice selection.
        """
        ...

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: str,
        tts_params: dict | None = None,
        instruct: str | None = None,
    ) -> bool:
        """Synthesize speech from text using the specified voice.

        Args:
            text: The text content to synthesize.
            voice_id: Voice identifier returned by clone_voice().
            output_path: File path where the generated audio will be saved.
            tts_params: Optional engine-specific parameters (e.g., temperature,
                       top_k, emo_vector for emotion control).
            instruct: Optional voice design instruction (e.g., "female, low pitch,
                     british accent"). Only supported by OmniVoice; other engines
                     will ignore this parameter and issue a warning.

        Returns:
            True if synthesis succeeded and audio was written to output_path,
            False otherwise.
        """
        ...

    @abstractmethod
    def get_emotion_params(self, text: str) -> tuple[dict, str]:
        """Parse emotion tags from text and return emotion parameters.

        Extracts [情绪:强度] tags from the input text, converts them to
        engine-appropriate emotion parameters, and returns the cleaned text
        with all tags removed.

        Args:
            text: Input text potentially containing emotion tags like
                  "[高兴:1.2]" or "[惊讶:0.8]".

        Returns:
            A tuple of (params_dict, cleaned_text) where params_dict contains
            emotion-related parameters (e.g., emo_vector) for the TTS engine,
            and cleaned_text has all bracket content stripped out.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the engine's unique name identifier.

        Examples: "indextts", "qwen3-tts"
        """
        ...


class EmotionParser:
    """Utility class for parsing emotion tags from TTS input text.

    Supports the [情绪:强度] tag format, e.g., [高兴:1.2], [惊讶:0.8].
    Also strips all bracket-style content from text to prevent tags from
    being spoken aloud during synthesis.

    Supported emotions: 高兴, 愤怒, 悲伤, 恐惧, 反感, 低落, 惊讶, 自然
    """

    SUPPORTED_EMOTIONS = [
        "高兴",
        "愤怒",
        "悲伤",
        "恐惧",
        "反感",
        "低落",
        "惊讶",
        "自然",
    ]

    _EMOTION_TAG_RE = re.compile(r"\[([^\]:]+):([\d.]+)\]")
    _BRACKET_PATTERNS = [
        re.compile(r"\[.*?\]"),
        re.compile(r"【.*?】"),
        re.compile(r"<.*?>"),
        re.compile(r"\(.*?\)"),
        re.compile(r"（.*?）"),
    ]

    @classmethod
    def parse_emotion_tags(cls, text: str) -> tuple[list[dict], str]:
        """Parse [情绪:强度] emotion tags from text.

        Scans the input text for emotion tags in the format [name:intensity],
        validates them against the supported emotion list, and returns both
        the parsed tags and the cleaned text with all bracket content removed.

        Args:
            text: Input text potentially containing emotion tags.

        Returns:
            A tuple of (parsed_tags, cleaned_text) where:
            - parsed_tags: List of dicts with keys "type", "name", "intensity"
                          for each valid emotion tag found.
            - cleaned_text: Original text with all bracket content stripped.
        """
        matches = cls._EMOTION_TAG_RE.finditer(text)
        parsed_tags: list[dict] = []

        for match in matches:
            emo_name = match.group(1)
            if emo_name in cls.SUPPORTED_EMOTIONS:
                try:
                    emo_intensity = float(match.group(2))
                    parsed_tags.append(
                        {
                            "type": "emotion",
                            "name": emo_name,
                            "intensity": emo_intensity,
                        }
                    )
                except ValueError:
                    pass

        cleaned_text = text
        for pattern in cls._BRACKET_PATTERNS:
            cleaned_text = pattern.sub("", cleaned_text)
        cleaned_text = cleaned_text.strip()

        return parsed_tags, cleaned_text

    @classmethod
    def emotion_to_vector(cls, tags: list[dict]) -> list[float] | None:
        """Convert parsed emotion tags to an IndexTTS-style 8-element emo_vector.

        Creates a sparse vector where only the emotion matching the tag has
        a non-zero intensity value. Returns None if no valid tags are provided.

        Args:
            tags: List of parsed emotion tag dicts from parse_emotion_tags().
                  Each dict should have "name" and "intensity" keys.

        Returns:
            An 8-element list of floats representing the emotion vector,
            or None if no valid emotion tags were found.
        """
        if not tags:
            return None

        # Use the last valid emotion tag (matching original behavior)
        last_valid_tag = None
        for tag in tags:
            if tag.get("name") in cls.SUPPORTED_EMOTIONS:
                last_valid_tag = tag

        if last_valid_tag is None:
            return None

        emo_vector = [0.0] * 8
        emo_name = last_valid_tag["name"]
        emo_intensity = last_valid_tag["intensity"]
        emo_index = cls.SUPPORTED_EMOTIONS.index(emo_name)
        emo_vector[emo_index] = emo_intensity

        return emo_vector
