"""Qwen3-TTS engine implementation for the pluggable TTS architecture."""

import json
import os
import threading

import numpy as np
from pydub import AudioSegment

from .base import EmotionParser, TTSEngine


class Qwen3TTSEngine(TTSEngine):
    """Qwen3-TTS engine supporting local and API (DashScope) modes.

    Supports local Qwen3-TTS model inference and DashScope API mode.
    Thread-safe with separate locks for model loading and inference.
    Includes full audio post-processing: silence truncation, DC offset
    removal, soft clipping, int16 PCM conversion.
    """

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._model = None
        self._model_lock = threading.Lock()
        self._infer_lock = threading.Lock()

    # ------------------------------------------------------------------
    # TTSEngine interface
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "qwen3-tts"

    @property
    def supports_emotion(self) -> bool:
        return False

    def load_model(self) -> None:
        """Load the Qwen3-TTS local model.

        Uses bfloat16 for GPU, float32 for CPU. Skips in API mode.
        """
        mode = self.config.get("QWEN3TTS_MODE", "api").strip().lower()
        if mode != "local":
            return

        with self._model_lock:
            if self._model is not None:
                return

            model_path = self.config.get(
                "QWEN3TTS_MODEL_NAME", "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
            )
            print(f"正在加载 Qwen3-TTS 模型 ({model_path})...")
            try:
                from qwen_tts import Qwen3TTSModel
                import torch

                device = (
                    "cuda:0"
                    if torch.cuda.is_available()
                    else (
                        "mps"
                        if torch.backends.mps.is_available()
                        else "cpu"
                    )
                )
                self._model = Qwen3TTSModel.from_pretrained(
                    model_path,
                    device_map=device,
                    dtype=torch.bfloat16 if device != "cpu" else torch.float32,
                )
                print("Qwen3-TTS 模型加载成功！")
            except Exception as e:
                print(f"加载 Qwen3-TTS 模型失败: {e}")
                self._model = None

    def clone_voice(
        self, ref_audio: str, text: str, voice_name: str
    ) -> str:
        """Clone a voice from reference audio.

        Qwen3-TTS supports zero-shot inference, no feature extraction needed.
        """
        voices_dir = self._get_voices_dir()
        voice_path = os.path.join(voices_dir, voice_name)
        os.makedirs(voice_path, exist_ok=True)

        ref_audio_path = os.path.join(voice_path, "ref_audio.wav")
        try:
            audio = AudioSegment.from_file(ref_audio)
            audio.export(ref_audio_path, format="wav")
        except Exception as e:
            print(f"音频转换失败，尝试直接拷贝: {e}")
            import shutil

            shutil.copy2(ref_audio, ref_audio_path)

        return "qwen:" + ref_audio_path

    def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: str,
        tts_params: dict | None = None,
        instruct: str | None = None,
    ) -> bool:
        """Synthesize speech using Qwen3-TTS."""
        if instruct:
            self._warn_unsupported_instruct("Qwen3-TTS")

        _, clean_text = EmotionParser.parse_emotion_tags(text)

        if not clean_text.strip():
            print("文本为空，跳过 Qwen3-TTS 合成")
            return False

        mode = self.config.get("QWEN3TTS_MODE", "api").strip().lower()

        if mode == "local":
            return self._synthesize_local(
                clean_text, voice_id, output_path, tts_params
            )
        else:
            return self._synthesize_api(
                clean_text, voice_id, output_path, tts_params
            )

    def get_emotion_params(self, text: str) -> tuple[dict, str]:
        """Parse emotion tags and return params for Qwen3-TTS.

        Qwen3-TTS doesn't use emo_vector, but we still strip tags.
        """
        _, clean_text = EmotionParser.parse_emotion_tags(text)
        return {}, clean_text

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _synthesize_local(
        self,
        text: str,
        voice_id: str,
        output_path: str,
        tts_params: dict | None,
    ) -> bool:
        """Local Qwen3-TTS synthesis with full audio post-processing."""
        self.load_model()
        if self._model is None:
            return False

        # Resolve ref_audio and ref_text from voice_id
        ref_audio = None
        ref_text = None
        if voice_id.startswith("qwen:"):
            ref_audio = voice_id[5:]
            voices_dir = self._get_voices_dir()
            for vname in os.listdir(voices_dir):
                vpath = os.path.join(voices_dir, vname)
                meta_path = os.path.join(vpath, "meta.json")
                if os.path.exists(meta_path):
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    if meta.get("local_audio") == ref_audio:
                        ref_text = meta.get("text")
                        break

        try:
            import soundfile as sf

            with self._infer_lock:
                if ref_audio and ref_text:
                    wavs, sr = self._model.generate_voice_clone(
                        text=text,
                        language="Chinese",
                        ref_audio=ref_audio,
                        ref_text=ref_text,
                    )
                else:
                    wavs, sr = self._model.generate_custom_voice(
                        text=text,
                        language="Chinese",
                    )

            audio_data = wavs[0]
            if len(audio_data.shape) > 1:
                audio_data = audio_data.flatten()

            # NaN/Inf check
            if np.any(np.isnan(audio_data)):
                audio_data = np.nan_to_num(audio_data, nan=0.0)
            if np.any(np.isinf(audio_data)):
                audio_data = np.nan_to_num(audio_data, posinf=1.0, neginf=-1.0)

            # Silence truncation (800ms threshold)
            try:
                window_size = int(sr * 0.05)
                energy = np.array(
                    [
                        np.mean(np.abs(audio_data[i : i + window_size]))
                        for i in range(0, len(audio_data), window_size)
                    ]
                )

                silence_threshold = 0.005
                min_silence_windows = 16  # 16 * 50ms = 800ms

                continuous_silence = 0
                cut_window = -1

                for i in range(len(energy)):
                    if energy[i] <= silence_threshold:
                        continuous_silence += 1
                    else:
                        if continuous_silence >= min_silence_windows:
                            cut_window = i - continuous_silence
                            break
                        continuous_silence = 0

                if cut_window == -1 and continuous_silence >= min_silence_windows:
                    cut_window = len(energy) - continuous_silence

                if cut_window != -1:
                    end_sample = min(len(audio_data), (cut_window + 2) * window_size)
                    print(
                        f"检测到末尾破音或冗长静音！"
                        f"原长 {len(audio_data)/sr:.2f}s，"
                        f"截断为 {end_sample/sr:.2f}s"
                    )
                    audio_data = audio_data[:end_sample]

                    fade_samples = int(sr * 0.05)
                    if len(audio_data) > fade_samples:
                        fade_curve = np.linspace(1.0, 0.0, fade_samples)
                        audio_data[-fade_samples:] = audio_data[-fade_samples:] * fade_curve
            except Exception as trunc_err:
                print(f"音频截断处理失败: {trunc_err}")

            # DC offset removal
            dc_offset = audio_data.mean()
            if abs(dc_offset) > 0.001:
                audio_data = audio_data - dc_offset

            # Soft clipping via tanh
            if audio_data.dtype in [np.float32, np.float64]:
                if audio_data.max() > 0.95 or audio_data.min() < -0.95:
                    scale_factor = 2.0
                    audio_data = np.tanh(audio_data * scale_factor) * 0.95
                else:
                    audio_data = audio_data * 0.98

            # int16 PCM conversion
            if audio_data.dtype in [np.float32, np.float64]:
                audio_data = np.clip(audio_data, -1.0, 1.0)
                audio_data = (audio_data * 32767).astype(np.int16)
            elif audio_data.dtype != np.int16:
                audio_data = audio_data.astype(np.int16)

            # Save via soundfile, fallback to pydub
            try:
                sf.write(output_path, audio_data, sr, subtype="PCM_16")
            except Exception as sf_error:
                print(f"soundfile保存失败，回退到pydub: {sf_error}")
                audio_segment = AudioSegment(
                    data=audio_data.tobytes(),
                    sample_width=2,
                    frame_rate=sr,
                    channels=1,
                )
                if len(audio_segment) > 20:
                    audio_segment = audio_segment.fade_out(10)
                audio_segment.export(output_path, format="wav")
                return True

            # Apply fade-out via pydub
            try:
                audio_segment = AudioSegment.from_wav(output_path)
                if len(audio_segment) > 20:
                    audio_segment = audio_segment.fade_out(10)
                audio_segment.export(output_path, format="wav")
            except Exception as fade_error:
                print(f"淡出处理失败，但音频已保存: {fade_error}")

            return True
        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"Qwen3-TTS (Local) 语音合成失败: {e}")
            return False

    def _synthesize_api(
        self,
        text: str,
        voice_id: str,
        output_path: str,
        tts_params: dict | None,
    ) -> bool:
        """API mode synthesis via DashScope MultiModalConversation."""
        try:
            import dashscope

            api_key = self.config.get("QWEN3TTS_API_KEY", "")
            dashscope.api_key = api_key

            base_url = self.config.get("QWEN3TTS_URL", "")
            if base_url:
                dashscope.base_http_api_url = base_url

            model = self.config.get("QWEN3TTS_MODEL_NAME", "qwen3-tts")

            # Resolve ref_audio and ref_text
            ref_audio = None
            ref_text = None
            if voice_id.startswith("qwen:"):
                ref_audio = voice_id[5:]
                voices_dir = self._get_voices_dir()
                for vname in os.listdir(voices_dir):
                    vpath = os.path.join(voices_dir, vname)
                    meta_path = os.path.join(vpath, "meta.json")
                    if os.path.exists(meta_path):
                        with open(meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                        if meta.get("local_audio") == ref_audio:
                            ref_text = meta.get("text")
                            break

            messages = []
            if ref_audio and ref_text:
                ref_audio_uri = (
                    f"file://{ref_audio}"
                    if not ref_audio.startswith(("http", "file://"))
                    else ref_audio
                )
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"audio": ref_audio_uri},
                            {
                                "text": f"<|ref_audio|>\n<|text|>{ref_text}\n<|gen_text|>{text}"
                            },
                        ],
                    }
                ]
            else:
                messages = [
                    {
                        "role": "user",
                        "content": [{"text": f"<|gen_text|>{text}"}],
                    }
                ]

            response = dashscope.MultiModalConversation.call(
                model=model if model != "qwen3-tts" else "qwen3-tts-flash",
                messages=messages,
                language_type="Chinese",
            )

            if response.status_code == 200:
                if (
                    hasattr(response, "output")
                    and hasattr(response.output, "audio")
                    and response.output.audio is not None
                ):
                    audio_data = (
                        response.output.audio.data
                        if hasattr(response.output.audio, "data")
                        else response.output.audio
                    )
                    with open(output_path, "wb") as f:
                        f.write(audio_data)
                    return True

            print(f"Qwen3-TTS (API) 失败: {response}")
            return False
        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"Qwen3-TTS (API) 调用异常: {e}")
            return False

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _get_voices_dir() -> str:
        """Get the voices directory path."""
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        voices_dir = os.path.join(base_dir, "data", "voices")
        os.makedirs(voices_dir, exist_ok=True)
        return voices_dir
