"""Qwen3-ASR engine implementation with dual-model architecture."""
from typing import Optional, List

import torch

from asr_engines.base import ASREngine, TranscriptionResult, TimestampItem


class Qwen3ASREngine(ASREngine):
    """Qwen3-ASR engine with dual-model architecture.
    
    Uses Qwen3-ASR for speech-to-text and Qwen3-ForcedAligner for
    character-level millisecond timestamps.
    """
    
    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._mode = config.get("QWEN3ASR_MODE", "local")
        self._backend = config.get("QWEN3ASR_BACKEND", "transformers")
    
    @property
    def name(self) -> str:
        return "qwen3-asr"
    
    @property
    def supports_streaming(self) -> bool:
        return self._mode == "local" and self._backend == "vllm"
    
    @property
    def supports_timestamps(self) -> bool:
        return True
    
    def load_model(self) -> None:
        """Load Qwen3-ASR model with ForcedAligner."""
        if self._model is not None:
            return
        
        if self._mode == "api":
            return
        
        model_name = self.config.get("QWEN3ASR_MODEL", "Qwen/Qwen3-ASR-1.7B")
        aligner_name = self.config.get("QWEN3ASR_ALIGNER_MODEL", "Qwen/Qwen3-ForcedAligner-0.6B")
        device = self.config.get("QWEN3ASR_DEVICE", "cuda:0")
        max_new_tokens = int(self.config.get("QWEN3ASR_MAX_NEW_TOKENS", 256))
        
        from qwen_asr import Qwen3ASRModel
        
        if self._backend == "vllm":
            self._model = Qwen3ASRModel.LLM(
                model=model_name,
                gpu_memory_utilization=0.7,
                max_new_tokens=max_new_tokens,
                forced_aligner=aligner_name,
                forced_aligner_kwargs=dict(
                    dtype=torch.bfloat16,
                    device_map=device,
                ),
            )
        else:
            self._model = Qwen3ASRModel.from_pretrained(
                model_name,
                dtype=torch.bfloat16,
                device_map=device,
                max_new_tokens=max_new_tokens,
                forced_aligner=aligner_name,
                forced_aligner_kwargs=dict(
                    dtype=torch.bfloat16,
                    device_map=device,
                ),
            )
    
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        context: str = "",
        return_timestamps: bool = True,
    ) -> TranscriptionResult:
        """Transcribe audio using Qwen3-ASR.
        
        Args:
            audio_path: Path to audio file or URL.
            language: Language hint (None for auto-detect).
            context: Context hint for biasing (up to 10K tokens).
            return_timestamps: Whether to include character-level timestamps.
            
        Returns:
            TranscriptionResult with language, text, and timestamps.
        """
        self.load_model()
        
        if self._mode == "api":
            return self._transcribe_api(audio_path, language, context, return_timestamps)
        
        results = self._model.transcribe(
            audio=audio_path,
            language=language,
            context=context,
            return_time_stamps=return_timestamps,
        )
        
        if not results or len(results) == 0:
            return TranscriptionResult(language="unknown", text="", timestamps=[])
        
        result = results[0]
        
        timestamps: Optional[List[TimestampItem]] = None
        if return_timestamps and result.time_stamps:
            timestamps = [
                TimestampItem(
                    text=ts.text,
                    start_time=ts.start_time,
                    end_time=ts.end_time,
                )
                for ts in result.time_stamps
            ]
        
        return TranscriptionResult(
            language=result.language,
            text=result.text,
            timestamps=timestamps,
        )
    
    def _transcribe_api(
        self,
        audio_path: str,
        language: Optional[str],
        context: str,
        return_timestamps: bool,
    ) -> TranscriptionResult:
        """Transcribe using DashScope API (placeholder for future)."""
        import logging
        logging.warning(
            "Qwen3-ASR API mode not yet implemented. "
            "Set QWEN3ASR_MODE=local for local inference."
        )
        return TranscriptionResult(language="unknown", text="", timestamps=[])
