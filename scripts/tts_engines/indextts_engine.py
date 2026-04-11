"""IndexTTS-2 engine implementation for the pluggable TTS architecture."""

import json
import os
import sys
import threading

import requests
from pydub import AudioSegment

from .base import EmotionParser, TTSEngine


class IndexTTSEngine(TTSEngine):
    """IndexTTS-2 engine supporting local and API modes.

    Supports both local IndexTTS-2 model inference and SiliconFlow API mode.
    Thread-safe with separate locks for model loading and inference.
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
        return "indextts"

    def load_model(self) -> None:
        """Load the IndexTTS-2 local model.

        Downloads model via modelscope if not cached. Tries v2 interface
        first, falls back to v1. Skips loading in API mode.
        """
        mode = self.config.get("INDEXTTS_MODE", "api").strip().lower()
        if mode != "local":
            return

        with self._model_lock:
            if self._model is not None:
                return

            try:
                from modelscope import snapshot_download
            except ImportError:
                print("缺少 modelscope 库，请执行: pip install modelscope")
                sys.exit(1)

            print("正在检查/下载 IndexTTS 本地模型 (首次运行可能需要一些时间)...")
            model_base = self.config.get("MODEL_DIR")
            os.makedirs(model_base, exist_ok=True)

            model_dir = snapshot_download(
                "IndexTeam/IndexTTS-2", cache_dir=model_base
            )

            try:
                import indextts
            except ImportError:
                print("错误: 未找到 indextts。请先安装 IndexTTS 运行环境。")
                print("安装参考:")
                print("  git clone https://github.com/index-tts/index-tts.git")
                print("  cd index-tts")
                print("  pip install -r requirements.txt")
                print("  pip install -e .")
                sys.exit(1)

            try:
                import torch

                device = "cuda:0" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"

            try:
                from indextts.infer_v2 import IndexTTS2

                self._model = IndexTTS2(
                    cfg_path=os.path.join(model_dir, "config.yaml"),
                    model_dir=model_dir,
                    device=device,
                )
            except ImportError:
                try:
                    from indextts.infer import IndexTTS

                    self._model = IndexTTS(
                        model_dir=model_dir,
                        cfg_path=os.path.join(model_dir, "config.yaml"),
                    )
                except Exception as e:
                    print(f"本地模型加载失败: {e}")
                    sys.exit(1)

    def clone_voice(
        self, ref_audio: str, text: str, voice_name: str
    ) -> str:
        """Clone a voice from reference audio.

        For local mode: saves audio, extracts and persists .pt feature file.
        For API mode: uploads to SiliconFlow and gets voice URI.
        """
        from scripts.utils import load_config

        config = self.config
        if not text:
            # Auto-transcribe if text not provided
            from scripts.dubbing import auto_transcribe_audio

            text = auto_transcribe_audio(ref_audio, config)
            if not text:
                print("自动识别文本为空，无法进行克隆。")
                sys.exit(1)

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

        mode = config.get("INDEXTTS_MODE", "api").strip().lower()
        model_name = config.get("INDEXTTS_MODEL_NAME", "IndexTeam/IndexTTS-2")

        meta = {
            "name": voice_name,
            "text": text,
            "mode": mode,
            "engine": "indextts",
            "local_audio": ref_audio_path,
        }

        if mode == "local":
            with open(os.path.join(voice_path, "meta.json"), "w", encoding="utf-8") as vf:
                json.dump(meta, vf, ensure_ascii=False, indent=2)

            print(f"音色已保存到本地样本库目录 {voice_path} (本地模式)")

            # Extract and persist voice features
            print("正在提取并持久化音色特征，以提升后续生成速度...")
            try:
                self.load_model()
                dummy_wav = ref_audio_path + ".dummy.wav"
                try:
                    self._model.infer(ref_audio_path, text[:2], output_path=dummy_wav)
                except Exception:
                    pass
                if os.path.exists(dummy_wav):
                    os.remove(dummy_wav)
                print(f"音色特征提取完成，已持久化到: {ref_audio_path}.pt")
            except Exception as e:
                print(f"持久化音色特征时出错 (不影响使用，但下次会重新提取): {e}")

            return "local:" + ref_audio_path

        # API mode
        api_key = config.get("INDEXTTS_API_KEY", "")
        url = config.get(
            "INDEXTTS_URL", "https://api.siliconflow.cn/v1/audio/speech"
        ).replace("/audio/speech", "/uploads/audio/voice")
        headers = {"Authorization": f"Bearer {api_key}"}
        with open(ref_audio_path, "rb") as f:
            files = {"file": f}
            data = {"model": model_name, "customName": voice_name, "text": text}
            response = requests.post(url, headers=headers, files=files, data=data)

        if response.status_code == 200:
            result = response.json()
            voice_uri = result.get("uri")
            print(f"声音克隆成功！音色 ID (URI): {voice_uri}")

            meta["uri"] = voice_uri
            with open(os.path.join(voice_path, "meta.json"), "w", encoding="utf-8") as vf:
                json.dump(meta, vf, ensure_ascii=False, indent=2)
            print(f"音色已保存到本地样本库目录 {voice_path}")
            return "api:" + voice_uri
        else:
            print(f"克隆失败: {response.status_code} {response.text}")
            sys.exit(1)

    def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: str,
        tts_params: dict | None = None,
    ) -> bool:
        """Synthesize speech using IndexTTS-2."""
        if tts_params is None:
            tts_params = {}
        else:
            tts_params = tts_params.copy()

        # Parse emotion tags
        parsed_tags, clean_text = EmotionParser.parse_emotion_tags(text)
        emo_vector = EmotionParser.emotion_to_vector(parsed_tags)
        if emo_vector:
            tts_params["emo_vector"] = emo_vector

        # Strip residual bracket content
        clean_text = EmotionParser._BRACKET_PATTERNS[0].sub("", clean_text)
        clean_text = clean_text.strip()

        mode = self.config.get("INDEXTTS_MODE", "api").strip().lower()

        if mode == "local":
            return self._synthesize_local(clean_text, voice_id, output_path, tts_params)
        else:
            return self._synthesize_api(
                clean_text, voice_id, output_path, tts_params
            )

    def get_emotion_params(self, text: str) -> tuple[dict, str]:
        """Parse emotion tags and return params for IndexTTS."""
        parsed_tags, clean_text = EmotionParser.parse_emotion_tags(text)
        emo_vector = EmotionParser.emotion_to_vector(parsed_tags)
        params: dict = {}
        if emo_vector:
            params["emo_vector"] = emo_vector
        return params, clean_text

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _synthesize_local(
        self,
        text: str,
        voice_id: str,
        output_path: str,
        tts_params: dict,
    ) -> bool:
        """Local IndexTTS synthesis with thread-safe inference."""
        if tts_params is None:
            tts_params = {}

        local_audio_path = (
            voice_id.replace("local:", "")
            if voice_id.startswith("local:")
            else voice_id
        )

        if local_audio_path.startswith("IndexTeam/IndexTTS-2:"):
            print(
                "提示: 默认音色需要依赖真实的参考音频。"
                "请使用 clone 功能先克隆一个音色。"
            )
            return False

        if not os.path.exists(local_audio_path):
            print(f"本地参考音频不存在: {local_audio_path}")
            return False

        self.load_model()

        temp_wav_path = output_path + ".temp.wav"

        with self._infer_lock:
            try:
                infer_kwargs = {
                    "spk_audio_prompt": local_audio_path,
                    "text": text,
                    "output_path": temp_wav_path,
                }
                for k, v in tts_params.items():
                    infer_kwargs[k] = v

                self._model.infer(**infer_kwargs)

                if os.path.exists(temp_wav_path):
                    if output_path.lower().endswith(".mp3"):
                        audio = AudioSegment.from_wav(temp_wav_path)
                        audio.export(output_path, format="mp3")
                    else:
                        import shutil

                        shutil.move(temp_wav_path, output_path)

                    if os.path.exists(temp_wav_path):
                        os.remove(temp_wav_path)
                return True
            except TypeError:
                try:
                    # v1 fallback
                    self._model.infer(
                        local_audio_path, text, output_path=temp_wav_path
                    )

                    if os.path.exists(temp_wav_path):
                        if output_path.lower().endswith(".mp3"):
                            audio = AudioSegment.from_wav(temp_wav_path)
                            audio.export(output_path, format="mp3")
                        else:
                            import shutil

                            shutil.move(temp_wav_path, output_path)

                        if os.path.exists(temp_wav_path):
                            os.remove(temp_wav_path)
                    return True
                except Exception as e:
                    import traceback

                    traceback.print_exc()
                    print(f"本地合成失败 (v1): {e}")
                    return False
            except Exception as e:
                import traceback

                traceback.print_exc()
                print(f"本地合成失败 (v2): {e}")
                return False

    def _synthesize_api(
        self,
        text: str,
        voice_id: str,
        output_path: str,
        tts_params: dict,
    ) -> bool:
        """API mode synthesis via SiliconFlow."""
        api_key = self.config.get("INDEXTTS_API_KEY", "")
        model = self.config.get("INDEXTTS_MODEL_NAME", "IndexTeam/IndexTTS-2")
        url = self.config.get(
            "INDEXTTS_URL", "https://api.siliconflow.cn/v1/audio/speech"
        )
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": model,
            "input": text,
            "voice": voice_id,
            "response_format": "mp3",
            "sample_rate": 32000,
            "stream": False,
            "speed": 1.0,
            "gain": 0.0,
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            return True
        else:
            print(f"语音合成失败: {response.status_code} {response.text}")
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
