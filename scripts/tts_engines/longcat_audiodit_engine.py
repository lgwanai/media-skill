"""LongCat-AudioDiT TTS engine implementation.

Local-only zero-shot voice cloning using diffusion-based TTS.
No emotion control support - strips emotion tags from text.
"""

import os
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

    @property
    def supports_emotion(self) -> bool:
        return False

    def load_model(self) -> None:
        if self._model is not None:
            return
            
        with self._model_lock:
            if self._model is not None:
                return
                
            try:
                import sys
                sys.path.insert(0, os.path.join(os.path.expanduser("~/.models"), "LongCat-AudioDiT"))
                from audiodit import AudioDiTModel
                from transformers import AutoTokenizer
                import torch
                
                device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
                dtype = torch.bfloat16 if device == "cuda" else torch.float32
                
                model_name = self.config.get("LONGCAT_MODEL_NAME", "meituan-longcat/LongCat-AudioDiT-1B")
                print(f"正在加载 LongCat-AudioDiT 本地模型 ({model_name}) 到 {device}...")
                
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
        if os.path.abspath(ref_audio) != os.path.abspath(ref_audio_path):
            shutil.copy2(ref_audio, ref_audio_path)
        
        return f"longcat:{ref_audio_path}"
    
    def synthesize(self, text: str, voice_id: str, output_path: str, tts_params: dict | None = None, instruct: str | None = None) -> bool:
        if instruct:
            self._warn_unsupported_instruct("LongCat-AudioDiT")

        params, clean_text = self.get_emotion_params(text)
        
        self.load_model()
        
        with self._infer_lock:
            import torch
            import librosa
            import soundfile as sf
            import os
            import json
            import numpy as np
            import re
            
            def normalize_text(t):
                t = t.lower()
                t = re.sub(r'["“”‘’]', ' ', t)
                t = re.sub(r'\s+', ' ', t)
                return t

            def approx_duration_from_text(t, max_duration=30.0):
                EN_DUR_PER_CHAR = 0.082
                ZH_DUR_PER_CHAR = 0.21
                t = re.sub(r"\s+", "", t)
                num_zh = num_en = num_other = 0
                for c in t:
                    if "\u4e00" <= c <= "\u9fff":
                        num_zh += 1
                    elif c.isalpha():
                        num_en += 1
                    else:
                        num_other += 1
                dur = num_zh * ZH_DUR_PER_CHAR + num_en * EN_DUR_PER_CHAR + num_other * 0.1
                return min(max(dur, 1.0), max_duration)
            
            steps = int(tts_params.get("steps", self.config.get("LONGCAT_STEPS", 16)) if tts_params else self.config.get("LONGCAT_STEPS", 16))
            cfg_strength = float(tts_params.get("cfg_strength", self.config.get("LONGCAT_CFG_STRENGTH", 4.0)) if tts_params else self.config.get("LONGCAT_CFG_STRENGTH", 4.0))
            
            if voice_id and voice_id.startswith("longcat:"):
                ref_audio_path = voice_id[8:]
            elif voice_id:
                ref_audio_path = voice_id
            else:
                ref_audio_path = None
                
            prompt_text = ""
            if ref_audio_path:
                meta_path = os.path.join(os.path.dirname(ref_audio_path), "meta.json")
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                            prompt_text = meta.get("text", "")
                    except Exception:
                        pass
                        
            text_norm = normalize_text(clean_text)
            if prompt_text:
                prompt_text_norm = normalize_text(prompt_text)
                full_text = f"{prompt_text_norm} {text_norm}"
            else:
                full_text = text_norm
            
            inputs = self._tokenizer([full_text], padding="longest", return_tensors="pt")
            inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
            
            prompt_audio = None
            prompt_dur = 0
            sr = self._model.config.sampling_rate
            full_hop = self._model.config.latent_hop
            max_duration_frames = int(self._model.config.max_wav_duration * sr // full_hop)
            
            if ref_audio_path and os.path.exists(ref_audio_path):
                import torch.nn.functional as F
                audio, _ = librosa.load(ref_audio_path, sr=sr, mono=True)
                # Pad according to LongCat's inference logic
                off = 3
                wav = torch.from_numpy(audio).unsqueeze(0).to(self._model.device)
                if wav.shape[-1] % full_hop != 0:
                    wav = F.pad(wav, (0, full_hop - wav.shape[-1] % full_hop))
                wav = F.pad(wav, (0, full_hop * off))
                prompt_audio = wav
                _, prompt_dur = self._model.encode_prompt_audio(prompt_audio)
                
            prompt_time = prompt_dur * full_hop / sr
            dur_sec = approx_duration_from_text(text_norm, max_duration=self._model.config.max_wav_duration - prompt_time)
            
            if prompt_text:
                approx_pd = approx_duration_from_text(prompt_text_norm, max_duration=self._model.config.max_wav_duration)
                ratio = np.clip(prompt_time / approx_pd, 1.0, 1.5) if approx_pd > 0 else 1.0
                dur_sec = dur_sec * ratio
                
            duration = int(dur_sec * sr // full_hop)
            duration = min(duration + prompt_dur, max_duration_frames)
            
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
            sf.write(output_path, waveform, sr)
            
            return True
    
    def get_emotion_params(self, text: str) -> tuple[dict, str]:
        tags, clean_text = EmotionParser.parse_emotion_tags(text)
        return {}, clean_text
