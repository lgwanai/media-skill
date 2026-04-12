"""FunASR engine adapter for pluggable ASR architecture."""
import os
import subprocess
import time
from typing import Optional, List

import numpy as np
import torch

from asr_engines.base import ASREngine, TranscriptionResult, TimestampItem
from utils import setup_env


class FunASREngine(ASREngine):
    """FunASR engine adapter wrapping existing FunASR transcription logic.
    
    Uses the Paraformer-large model with VAD, punctuation, and speaker diarization.
    """
    
    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._model = None
        self._eres2net_registered = False
    
    @property
    def name(self) -> str:
        return "funasr"
    
    @property
    def supports_streaming(self) -> bool:
        return False
    
    @property
    def supports_timestamps(self) -> bool:
        return True
    
    def _register_eres2net_model(self) -> None:
        """Register ERes2Net model for FunASR 1.x compatibility."""
        if self._eres2net_registered:
            return
        
        try:
            from funasr.register import tables
            from funasr.models.eres2net.eres2net_aug import ERes2NetAug
            from funasr.models.campplus.utils import extract_feature
            from funasr.utils.load_utils import load_audio_text_image_video
            
            class ERes2NetAugWrapper(ERes2NetAug):
                def __init__(self, **kwargs):
                    super().__init__(
                        m_channels=kwargs.get("m_channels", 64),
                        feat_dim=kwargs.get("feat_dim", 80),
                        embedding_size=kwargs.get("embedding_size", 192),
                        pooling_func=kwargs.get("pooling_func", "TSTP"),
                        two_emb_layer=kwargs.get("two_emb_layer", False),
                    )
                
                def inference(self, data_in, data_lengths=None, key: list = None, tokenizer=None, frontend=None, **kwargs):
                    meta_data = {}
                    time1 = time.perf_counter()
                    audio_sample_list = load_audio_text_image_video(
                        data_in, fs=16000, audio_fs=kwargs.get("fs", 16000), data_type="sound"
                    )
                    time2 = time.perf_counter()
                    meta_data["load_data"] = f"{time2 - time1:0.3f}"
                    speech, speech_lengths, speech_times = extract_feature(audio_sample_list)
                    speech = speech.to(device=kwargs["device"])
                    time3 = time.perf_counter()
                    meta_data["extract_feat"] = f"{time3 - time2:0.3f}"
                    meta_data["batch_data_time"] = np.array(speech_times).sum().item() / 16000.0
                    
                    with torch.no_grad():
                        spk_embedding = self.forward(speech.to(torch.float32))
                    results = [{"spk_embedding": spk_embedding}]
                    return results, meta_data
            
            tables.register("model_classes", "iic/speech_eres2net_sv_zh-cn_16k-common")(ERes2NetAugWrapper)
            self._eres2net_registered = True
        except Exception as e:
            import logging
            logging.warning(f"Failed to register ERes2Net model: {e}")
    
    def load_model(self) -> None:
        """Load FunASR model pipeline (Paraformer + VAD + PUNC + SPK)."""
        if self._model is not None:
            return
        
        setup_env()
        self._register_eres2net_model()
        
        from funasr import AutoModel
        
        asr_model = self.config.get("FUNASR_PARAFORMER_MODEL", "iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch")
        vad_model = self.config.get("FUNASR_VAD_MODEL", "damo/speech_fsmn_vad_zh-cn-16k-common-pytorch")
        punc_model = self.config.get("FUNASR_PUNC_MODEL", "damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch")
        spk_model = self.config.get("FUNASR_SPK_MODEL", "iic/speech_eres2net_sv_zh-cn_16k-common")
        
        self._model = AutoModel(
            model=asr_model,
            model_revision="v2.0.4",
            vad_model=vad_model,
            vad_model_revision="v2.0.4",
            punc_model=punc_model,
            punc_model_revision="v2.0.4",
            spk_model=spk_model,
            spk_model_revision="v1.0.5",
            disable_update=True,
        )
    
    def _prepare_audio(self, media_path: str, output_dir: str) -> str:
        """Convert media file to 16kHz mono WAV for FunASR."""
        if media_path.lower().endswith(".wav"):
            return media_path
        
        audio_path = os.path.join(output_dir, "temp_audio.wav")
        if os.path.exists(audio_path):
            return audio_path
        
        print(f"Extracting audio: {media_path} -> {audio_path}")
        cmd = [
            "ffmpeg", "-y", "-i", media_path,
            "-vn", "-af", "afftdn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            audio_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        return audio_path
    
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        context: str = "",
        return_timestamps: bool = True,
    ) -> TranscriptionResult:
        """Transcribe audio using FunASR pipeline.
        
        Args:
            audio_path: Path to audio file (16kHz mono WAV recommended).
            language: Language hint (not used by FunASR, auto-detected).
            context: Context hint (not used by FunASR).
            return_timestamps: Whether to include timestamps (always True for FunASR).
            
        Returns:
            TranscriptionResult with language, text, and timestamps.
        """
        self.load_model()
        
        res = self._model.generate(
            input=audio_path,
            batch_size_s=60,
            sentence_timestamp=True,
            return_spk_res=True,
            vad_kwargs={
                "max_single_segment_time": 15000,
                "max_end_silence_time": 400,
            }
        )
        
        if not res or len(res) == 0:
            return TranscriptionResult(language="unknown", text="", timestamps=[])
        
        result_data = res[0]
        sentences = result_data.get("sentence_info", [])
        
        text_parts = []
        timestamps: List[TimestampItem] = []
        
        for sent in sentences:
            sent_text = sent.get("text", "").strip()
            spk = sent.get("spk", "Unknown")
            text_parts.append(f"[说话人{spk}]: {sent_text}")
            
            if return_timestamps:
                timestamps.append(TimestampItem(
                    text=sent_text,
                    start_time=sent.get("start", 0) / 1000.0,
                    end_time=sent.get("end", 0) / 1000.0,
                    speaker=spk,
                ))
        
        full_text = "\n".join(text_parts)
        
        return TranscriptionResult(
            language="zh",
            text=full_text,
            timestamps=timestamps if return_timestamps else None,
        )
