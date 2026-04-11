"""OmniVoice TTS engine implementation.

Local-only zero-shot voice cloning supporting 600+ languages.
No emotion control support - strips emotion tags from text.
"""

import json
import os
import threading

from .base import EmotionParser, TTSEngine


class OmniVoiceEngine(TTSEngine):
    """OmniVoice engine for multilingual zero-shot voice cloning.
    
    Local-only TTS engine with 600+ language support.
    Supports zero-shot voice cloning with reference audio.
    Can auto-transcribe reference audio using Whisper.
    No emotion control - strips emotion tags from text.
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        self._model = None
        self._model_lock = threading.Lock()
        self._infer_lock = threading.Lock()
    
    @property
    def name(self) -> str:
        return "omnivoice"

    @property
    def supports_emotion(self) -> bool:
        return False

    @property
    def supports_instruct(self) -> bool:
        return True

    def load_model(self) -> None:
        with self._model_lock:
            if self._model is not None:
                return
            
            try:
                import torch
                
                model_name = self.config.get("OMNIVOICE_MODEL_NAME", "k2-fsa/OmniVoice")
                
                device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
                dtype = torch.float16 if device == "cuda" else torch.float32
                
                from omnivoice import OmniVoice
                self._model = OmniVoice.from_pretrained(
                    model_name,
                    device_map=device,
                    dtype=dtype
                )
                
            except ImportError as e:
                raise ImportError(
                    f"OmniVoice dependencies not installed. "
                    f"Run: pip install omnivoice\n"
                    f"See: https://github.com/k2-fsa/OmniVoice\n"
                    f"Error: {e}"
                )
    
    @staticmethod
    def _get_voices_dir() -> str:
        return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "voices")
    
    def clone_voice(self, ref_audio: str, text: str, voice_name: str) -> str:
        voice_dir = os.path.join(self._get_voices_dir(), voice_name)
        os.makedirs(voice_dir, exist_ok=True)
        
        ref_audio_path = os.path.join(voice_dir, "ref_audio.wav")
        
        import shutil
        shutil.copy2(ref_audio, ref_audio_path)
        
        return f"omnivoice:{ref_audio_path}"
    
    def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: str,
        tts_params: dict | None = None,
        instruct: str | None = None,
    ) -> bool:
        # OmniVoice handles ALL tags natively (emotion tags, [laughter], [sigh], etc.)
        # Do NOT strip any brackets - pass text through unchanged
        # OmniVoice will handle the tags itself
        params, clean_text = self.get_emotion_params(text)

        self.load_model()

        with self._infer_lock:
            import torch
            import torchaudio
            import os

            num_step = tts_params.get("num_step", self.config.get("OMNIVOICE_NUM_STEP", 32)) if tts_params else self.config.get("OMNIVOICE_NUM_STEP", 32)
            guidance_scale = tts_params.get("guidance_scale", self.config.get("OMNIVOICE_GUIDANCE_SCALE", 2.0)) if tts_params else self.config.get("OMNIVOICE_GUIDANCE_SCALE", 2.0)

            if voice_id and voice_id.startswith("omnivoice:"):
                ref_audio_path = voice_id[10:]
            elif voice_id:
                ref_audio_path = voice_id
            else:
                ref_audio_path = None

            ref_text = None
            if ref_audio_path and os.path.exists(ref_audio_path):
                voice_dir = os.path.dirname(ref_audio_path)
                meta_path = os.path.join(voice_dir, "meta.json")
                if os.path.exists(meta_path):
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        ref_text = meta.get("text", None)

            language = tts_params.get("language", "Chinese") if tts_params else "Chinese"

            audios = self._model.generate(
                text=clean_text,  # Contains OmniVoice tags like [laughter], [sigh]
                language=language,
                ref_audio=ref_audio_path,
                ref_text=ref_text,
                num_step=num_step,
                guidance_scale=guidance_scale,
                instruct=instruct,
            )

            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
            torchaudio.save(output_path, audios[0].unsqueeze(0).cpu(), 24000)

            return True
    
    def get_emotion_params(self, text: str) -> tuple[dict, str]:
        # OmniVoice handles ALL tags natively (emotion tags, [laughter], [sigh], etc.)
        # Do NOT strip any brackets - pass text through unchanged
        # OmniVoice will handle the tags itself
        return {}, text
