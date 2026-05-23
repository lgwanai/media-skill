"""HTTP-based TTS engine that calls the model-server API."""
import json
import logging
import os
import shutil
from typing import Optional

import requests

from .base import EmotionParser, TTSEngine

logger = logging.getLogger(__name__)


class HTTTSEngine(TTSEngine):
    """TTS engine that calls the model-server HTTP API instead of loading models in-process."""

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.base_url = config.get("MODEL_SERVER_URL", "http://localhost:8100").rstrip("/")
        self.timeout = float(config.get("MODEL_SERVER_TIMEOUT", 600))
        self._engine = config.get("HTTP_TTS_ENGINE", "indextts")

    @property
    def name(self) -> str:
        return "http"

    @property
    def supports_emotion(self) -> bool:
        return True

    @property
    def supports_instruct(self) -> bool:
        return True

    def load_model(self) -> None:
        pass

    @staticmethod
    def _get_voices_dir() -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        voices_dir = os.path.join(base_dir, "data", "voices")
        os.makedirs(voices_dir, exist_ok=True)
        return voices_dir

    def clone_voice(self, ref_audio: str, text: str, voice_name: str) -> str:
        url = f"{self.base_url}/tts/clone"

        data = {
            "ref_audio": ref_audio,
            "voice_name": voice_name,
            "text": text,
            "engine": self._engine,
        }

        try:
            resp = requests.post(url, data=data, timeout=self.timeout)
            resp.raise_for_status()
            result = resp.json()
            return result.get("voice_id", f"http:{voice_name}")
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP TTS clone failed: {e}")
            raise RuntimeError(f"Voice clone failed: {e}")

    def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: str,
        tts_params: Optional[dict] = None,
        instruct: Optional[str] = None,
    ) -> bool:
        params, clean_text = self.get_emotion_params(text)

        if tts_params:
            params = {**params, **tts_params}

        url = f"{self.base_url}/tts/synthesize"

        data = {
            "text": clean_text,
            "voice_id": voice_id,
            "engine": self._engine,
            "tts_params": json.dumps(params),
        }
        if instruct:
            data["instruct"] = instruct

        try:
            resp = requests.post(url, data=data, timeout=self.timeout)
            if resp.status_code != 200:
                logger.error(f"TTS synthesis failed: {resp.status_code} {resp.text}")
                return False

            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP TTS synthesis failed: {e}")
            return False

    def get_emotion_params(self, text: str) -> tuple[dict, str]:
        tags, clean_text = EmotionParser.parse_emotion_tags(text)
        emo_vector = EmotionParser.emotion_to_vector(tags)
        params: dict = {}
        if emo_vector:
            params["emo_vector"] = emo_vector
        return params, clean_text
