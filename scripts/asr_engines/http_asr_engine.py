"""HTTP-based ASR engine that calls the model-server API."""
import json
import logging
import os
import tempfile
from typing import Optional, List

import requests

from asr_engines.base import ASREngine, TranscriptionResult, TimestampItem

logger = logging.getLogger(__name__)


class HTTPASREngine(ASREngine):
    """ASR engine that calls the model-server HTTP API instead of loading models in-process."""

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.base_url = config.get("MODEL_SERVER_URL", "http://localhost:8100").rstrip("/")
        self.timeout = float(config.get("MODEL_SERVER_TIMEOUT", 600))
        self._engine = config.get("HTTP_ASR_ENGINE", "funasr")

    @property
    def name(self) -> str:
        return "http"

    @property
    def supports_streaming(self) -> bool:
        return False

    @property
    def supports_timestamps(self) -> bool:
        return True

    def load_model(self) -> None:
        pass

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        context: str = "",
        return_timestamps: bool = True,
    ) -> TranscriptionResult:
        if not os.path.exists(audio_path):
            return TranscriptionResult(language="unknown", text="", timestamps=[])

        url = f"{self.base_url}/asr/transcribe/upload"

        with open(audio_path, "rb") as f:
            files = {"file": (os.path.basename(audio_path), f)}
            data = {
                "engine": self._engine,
                "return_timestamps": str(return_timestamps).lower(),
            }
            if language:
                data["language"] = language
            if context:
                data["context"] = context

            try:
                resp = requests.post(url, files=files, data=data, timeout=self.timeout)
                resp.raise_for_status()
                result = resp.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"HTTP ASR request failed: {e}")
                return TranscriptionResult(language="unknown", text="", timestamps=[])

        timestamps: Optional[List[TimestampItem]] = None
        if return_timestamps and result.get("timestamps"):
            timestamps = [
                TimestampItem(
                    text=ts.get("text", ""),
                    start_time=ts.get("start_time", 0),
                    end_time=ts.get("end_time", 0),
                    speaker=ts.get("speaker"),
                )
                for ts in result["timestamps"]
            ]

        return TranscriptionResult(
            language=result.get("language", "unknown"),
            text=result.get("text", ""),
            timestamps=timestamps,
        )
