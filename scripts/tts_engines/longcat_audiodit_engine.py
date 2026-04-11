"""LongCat-AudioDiT TTS engine implementation.

Local-only zero-shot voice cloning using diffusion-based TTS.
No emotion control support - strips emotion tags from text.
"""

import json
import os
import sys
import threading

from .base import EmotionParser, TTSEngine


class LongCatAudioDiTEngine(TTSEngine):
    """LongCat-AudioDiT engine for zero-shot voice cloning.
    
    Local-only TTS engine using diffusion-based synthesis.
    Supports zero-shot voice cloning with reference audio.
    No emotion control - strips emotion tags from text.
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        self._model = None
        self._model_lock = threading.Lock()
        self._infer_lock = threading.Lock()
        self._tokenizer = None
    
    @property
    def name(self) -> str:
        return "longcat-audiodit"
    
    def load_model(self) -> None:
        with self._model_lock:
            if self._model is not None:
                return
            
            try:
                import torch
                from transformers import AutoTokenizer
                
                model_name = self.config.get("LONGCAT_MODEL_NAME", "meituan-longcat/LongCat-AudioDiT-1B")
                
                from audiodit import AudioDiTModel
                device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
                dtype = torch.float16 if device == "cuda" else torch.float32
                
                self._model = AudioDiTModel.from_pretrained(model_name).to(device=device, dtype=dtype)
                self._tokenizer = AutoTokenizer.from_pretrained(self._model.config.text_encoder_model)
                
            except ImportError as e:
                raise ImportError(
                    f"LongCat-AudioDiT dependencies not installed. "
                    f"Run: pip install transformers librosa soundfile\n"
                    f"See: https://github.com/meituan-longcat/LongCat-AudioDiT\n"
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
        
        meta = {
            "name": voice_name,
            "text": text,
            "engine": "longcat-audiodit",
            "local_audio": ref_audio_path,
            "mode": "local"
        }
        
        with open(os.path.join(voice_dir, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        
        return f"longcat:{ref_audio_path}"
    
    def synthesize(self, text: str, voice_id: str, output_path: str, tts_params: dict | None = None) -> bool:
        params, clean_text = self.get_emotion_params(text)
        
        self.load_model()
        
        with self._infer_lock:
            import torch
            import librosa
            import soundfile as sf
            import os
            
            steps = tts_params.get("steps", self.config.get("LONGCAT_STEPS", 16)) if tts_params else self.config.get("LONGCAT_STEPS", 16)
            cfg_strength = tts_params.get("cfg_strength", self.config.get("LONGCAT_CFG_STRENGTH", 4.0)) if tts_params else self.config.get("LONGCAT_CFG_STRENGTH", 4.0)
            
            inputs = self._tokenizer([clean_text], padding="longest", return_tensors="pt")
            inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
            
            duration = max(16, int(len(clean_text) * 2.5))
            
            if voice_id and voice_id.startswith("longcat:"):
                ref_audio_path = voice_id[8:]
            elif voice_id:
                ref_audio_path = voice_id
            else:
                ref_audio_path = None
            
            prompt_audio = None
            if ref_audio_path and os.path.exists(ref_audio_path):
                audio, sr = librosa.load(ref_audio_path, sr=24000, mono=True)
                prompt_audio = torch.from_numpy(audio).unsqueeze(0).to(self._model.device)
            
            with torch.no_grad():
                output = self._model(
                    input_ids=inputs["input_ids"],
                    attention_mask=inputs["attention_mask"],
                    prompt_audio=prompt_audio,
                    duration=duration,
                    steps=steps,
                    cfg_strength=cfg_strength,
                    guidance_method="apg" if prompt_audio is not None else "cfg",
                )
            
            waveform = output.waveform.squeeze().cpu().numpy()
            
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
            sf.write(output_path, waveform, 24000)
            
            return True
    
    def get_emotion_params(self, text: str) -> tuple[dict, str]:
        tags, clean_text = EmotionParser.parse_emotion_tags(text)
        return {}, clean_text
