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
        self._max_new_tokens = int(config.get("QWEN3ASR_MAX_NEW_TOKENS", 256))
    
    @property
    def name(self) -> str:
        return "qwen3-asr"
    
    @property
    def supports_streaming(self) -> bool:
        return self._mode == "local" and self._backend == "vllm"
    
    @property
    def supports_timestamps(self) -> bool:
        return True

    def _resolve_device_and_dtype(self) -> tuple[str, torch.dtype]:
        configured_device = self.config.get("QWEN3ASR_DEVICE", "cuda:0").strip()

        if configured_device.startswith("cuda"):
            if torch.cuda.is_available():
                return configured_device, torch.bfloat16
            if torch.backends.mps.is_available():
                return "mps", torch.float16
            return "cpu", torch.float32

        if configured_device == "mps":
            if torch.backends.mps.is_available():
                return "mps", torch.float16
            if torch.cuda.is_available():
                return "cuda:0", torch.bfloat16
            return "cpu", torch.float32

        if configured_device == "cpu":
            return "cpu", torch.float32

        if torch.cuda.is_available():
            return "cuda:0", torch.bfloat16
        if torch.backends.mps.is_available():
            return "mps", torch.float16
        return "cpu", torch.float32
    
    def load_model(self) -> None:
        """Load Qwen3-ASR model with ForcedAligner."""
        if self._model is not None:
            return
        
        if self._mode == "api":
            return

        # Monkey patch check_model_inputs if needed (fix for transformers compatibility)
        try:
            from transformers.utils.generic import check_model_inputs
            import transformers.utils.generic as generic_utils
            
            # If check_model_inputs is the one causing TypeError when called as @check_model_inputs()
            # we can try to wrap it or replace it in the module before qwen_asr imports it.
            original_check = check_model_inputs
            
            def patched_check(*args, **kwargs):
                if len(args) == 1 and callable(args[0]):
                    return original_check(args[0])
                return original_check

            generic_utils.check_model_inputs = patched_check
        except Exception:
            pass

        # Fix for transformers 5.x compatibility: Qwen3ASRConfig missing thinker_config attribute
        try:
            from qwen_asr.core.transformers_backend.configuration_qwen3_asr import Qwen3ASRConfig
            
            # Patch get_text_config to handle missing thinker_config
            if hasattr(Qwen3ASRConfig, "get_text_config"):
                original_get_text_config = Qwen3ASRConfig.get_text_config
                def patched_get_text_config(self, *args, **kwargs):
                    try:
                        return original_get_text_config(self, *args, **kwargs)
                    except AttributeError:
                        # Fallback for transformers 5.x validation
                        return self
                Qwen3ASRConfig.get_text_config = patched_get_text_config
        except Exception:
            pass

        # Fix for transformers 5.x compatibility: Qwen3ASRThinkerConfig missing pad_token_id
        try:
            from qwen_asr.core.transformers_backend.configuration_qwen3_asr import Qwen3ASRThinkerConfig
            original_thinker_init = Qwen3ASRThinkerConfig.__init__
            def patched_thinker_init(self, *args, **kwargs):
                original_thinker_init(self, *args, **kwargs)
                if not hasattr(self, "pad_token_id"):
                    self.pad_token_id = None
            Qwen3ASRThinkerConfig.__init__ = patched_thinker_init
        except Exception:
            pass

        # Fix for transformers 5.x compatibility: KeyError 'default' in ROPE_INIT_FUNCTIONS
        try:
            from qwen_asr.core.transformers_backend import modeling_qwen3_asr as modeling_module
            import torch
            if hasattr(modeling_module, "ROPE_INIT_FUNCTIONS"):
                if "default" not in modeling_module.ROPE_INIT_FUNCTIONS:
                    def default_rope_init(config, device):
                        # Simple rotary embedding without scaling as fallback for 'default'
                        dim = getattr(config, "hidden_size", 4096) // getattr(config, "num_attention_heads", 32)
                        base = getattr(config, "rope_theta", 10000.0)
                        inv_freq = 1.0 / (base ** (torch.arange(0, dim, 2).float().to(device) / dim))
                        return inv_freq, 1.0
                    modeling_module.ROPE_INIT_FUNCTIONS["default"] = default_rope_init
        except Exception:
            pass

        model_name = self.config.get("QWEN3ASR_MODEL", "Qwen/Qwen3-ASR-1.7B")
        aligner_name = self.config.get("QWEN3ASR_ALIGNER_MODEL", "Qwen/Qwen3-ForcedAligner-0.6B")
        device, dtype = self._resolve_device_and_dtype()

        from qwen_asr import Qwen3ASRModel
        
        if self._backend == "vllm":
            self._model = Qwen3ASRModel.LLM(
                model=model_name,
                gpu_memory_utilization=0.7,
                max_new_tokens=self._max_new_tokens,
                forced_aligner=aligner_name,
                forced_aligner_kwargs=dict(
                    dtype=dtype,
                    device_map=device,
                ),
            )
        else:
            self._model = Qwen3ASRModel.from_pretrained(
                model_name,
                dtype=dtype,
                device_map=device,
                max_new_tokens=self._max_new_tokens,
                forced_aligner=aligner_name,
                forced_aligner_kwargs=dict(
                    dtype=dtype,
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
                    speaker=None,
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
