# Research: Phase 7 — ASR底层支持Qwen3-ASR方案

**Phase:** 7
**Created:** 2026-04-12
**Research Type:** Standard (Level 2)

---

## Executive Summary

Phase 7 aims to add Qwen3-ASR as an alternative ASR backend to the existing FunASR implementation. The key innovation is the **dual-model architecture**: Qwen3-ASR for speech-to-text (low latency) + Qwen3-ForcedAligner for character-level millisecond timestamps (high precision).

**Key Finding:** Qwen3-ASR offers superior Chinese recognition, singing/BGM handling, and 67-77% better timestamp precision compared to FunASR, making it an excellent addition for the media processing use case.

---

## 1. Qwen3-ASR Overview

### 1.1 Model Family

| Model | Parameters | Use Case | Mode |
|-------|------------|----------|------|
| Qwen3-ASR-1.7B | ~2B | Best quality, offline & streaming | Local |
| Qwen3-ASR-0.6B | ~0.9B | Faster, lower VRAM | Local |
| Qwen3-ForcedAligner-0.6B | ~0.9B | Word/character-level timestamps | Local |
| Qwen3-ASR-Flash | N/A | Real-time API | DashScope API |
| Qwen3-ASR-Flash-Filetrans | N/A | Long audio transcription | DashScope API |

### 1.2 Supported Languages

- **30 languages**: Chinese, English, Cantonese, Arabic, German, French, Spanish, Portuguese, Indonesian, Italian, Korean, Russian, Japanese, Thai, Vietnamese, Turkish, Dutch, Polish, Swedish, Norwegian, Danish, Finnish, Greek, Hebrew, Hindi, Bengali, Tamil, Telugu, Marathi, Urdu
- **22 Chinese dialects**: Wu, Min, Hakka, Xiang, Gan, Jin, Hui, Pinghua, etc.

### 1.3 Key Features

1. **All-in-one model**: Single model supports both streaming and offline transcription
2. **Noise robustness**: Excellent performance in noisy environments (far-field, BGM)
3. **Singing voice recognition**: SOTA performance on music/singing transcription
4. **Context biasing**: Support for 10K token context hints (hotwords, domain terms)
5. **Streaming support**: Real-time transcription via vLLM backend

---

## 2. Qwen3-ForcedAligner Overview

### 2.1 Purpose

The ForcedAligner provides **character-level millisecond timestamps** by aligning text transcripts with audio. It's essential for:
- Precise subtitle timing
- Video editing synchronization
- Speaker diarization alignment

### 2.2 Performance Comparison

| Model | Avg Alignment Error (ms) |
|-------|--------------------------|
| Qwen3-ForcedAligner | **42.9** |
| WhisperX | 133.2 |
| NFA | 129.8 |
| Monotonic-Aligner | Higher |

**67-77% reduction** in alignment error compared to alternatives.

### 2.3 Supported Languages (11)

Chinese, English, Cantonese, French, German, Italian, Japanese, Korean, Portuguese, Russian, Spanish

### 2.4 Usage Pattern

```python
from qwen_asr import Qwen3ForcedAligner

aligner = Qwen3ForcedAligner.from_pretrained(
    "Qwen/Qwen3-ForcedAligner-0.6B",
    dtype=torch.bfloat16,
    device_map="cuda:0",
)

results = aligner.align(
    audio="path/to/audio.wav",
    text="transcript text here",
    language="Chinese",
)

# Each result has: text, start_time, end_time
for item in results[0]:
    print(f"'{item.text}': {item.start_time}s -> {item.end_time}s")
```

---

## 3. Integration Architecture

### 3.1 Dual-Model Pipeline

```
Audio Input
    │
    ▼
┌─────────────────────┐
│   Qwen3-ASR-1.7B    │  ← Speech-to-text (low latency)
│   (Transcribe)      │
└─────────────────────┘
    │
    ├─── Transcribed text
    │
    ▼
┌─────────────────────┐
│ Qwen3-ForcedAligner │  ← Timestamp alignment (high precision)
│   (Align)           │
└─────────────────────┘
    │
    ▼
Output: text + character-level timestamps
```

### 3.2 Recommended Engine Architecture

Following the TTSEngine pattern from Phase 1-6:

```python
# scripts/asr_engines/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class TranscriptionResult:
    language: str
    text: str
    timestamps: Optional[List[dict]] = None  # [{text, start_time, end_time}, ...]
    file_md5: Optional[str] = None

@dataclass
class TimestampItem:
    text: str
    start_time: float  # seconds
    end_time: float    # seconds

class ASREngine(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Engine identifier (funasr, qwen3-asr)"""
        pass
    
    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether engine supports real-time streaming"""
        pass
    
    @abstractmethod
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        context: str = "",
        return_timestamps: bool = True,
    ) -> TranscriptionResult:
        """Transcribe audio file"""
        pass
    
    @abstractmethod
    def load_model(self):
        """Lazy load model"""
        pass
```

### 3.3 Engine Factory Pattern

```python
# scripts/asr_engines/factory.py
from .base import ASREngine
from .fun_asr_engine import FunASREngine
from .qwen3_asr_engine import Qwen3ASREngine

def get_asr_engine(engine_name: str = None, config: dict = None) -> ASREngine:
    """Get ASR engine instance by name"""
    if engine_name is None:
        engine_name = config.get("ASR_ENGINE", "funasr")
    
    if engine_name == "funasr":
        return FunASREngine(config)
    elif engine_name == "qwen3-asr":
        return Qwen3ASREngine(config)
    else:
        raise ValueError(f"Unknown ASR engine: {engine_name}")
```

---

## 4. Configuration Design

### 4.1 Config Template (config.example.txt)

```ini
# ---------------------------------------------------------
# 7. ASR Configuration
# ---------------------------------------------------------
# ASR_ENGINE can be: funasr, qwen3-asr
# 
# Engine comparison:
# - funasr: Proven stability, sentence-level timestamps, good for clean audio
# - qwen3-asr: SOTA Chinese/multilingual, character-level timestamps, excellent for noisy/BGM audio
ASR_ENGINE = funasr

# 7.1 FunASR Configuration (existing, unchanged)
FUNASR_PARAFORMER_MODEL = iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch
FUNASR_VAD_MODEL = damo/speech_fsmn_vad_zh-cn-16k-common-pytorch
FUNASR_PUNC_MODEL = damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch
FUNASR_SPK_MODEL = iic/speech_eres2net_sv_zh-cn_16k-common

# 7.2 Qwen3-ASR Configuration
# QWEN3ASR_MODE can be: local or api
QWEN3ASR_MODE = local

# Local mode settings
QWEN3ASR_MODEL = Qwen/Qwen3-ASR-1.7B
QWEN3ASR_ALIGNER_MODEL = Qwen/Qwen3-ForcedAligner-0.6B
QWEN3ASR_DEVICE = cuda:0
QWEN3ASR_BACKEND = transformers  # or vllm for faster inference
QWEN3ASR_MAX_NEW_TOKENS = 256

# API mode settings (DashScope)
QWEN3ASR_API_KEY = your_dashscope_api_key_here
QWEN3ASR_API_URL = https://dashscope.aliyuncs.com/api/v1
# For international: https://dashscope-intl.aliyuncs.com/api/v1
```

### 4.2 Config Loading (utils.py)

```python
def load_config(config_path="config.txt"):
    # ... existing code ...
    
    # ASR defaults
    if "ASR_ENGINE" not in config:
        config["ASR_ENGINE"] = "funasr"
    if "QWEN3ASR_MODE" not in config:
        config["QWEN3ASR_MODE"] = "local"
    if "QWEN3ASR_BACKEND" not in config:
        config["QWEN3ASR_BACKEND"] = "transformers"
    
    return config
```

---

## 5. Implementation Details

### 5.1 Qwen3ASREngine Class

```python
# scripts/asr_engines/qwen3_asr_engine.py
import torch
from typing import Optional, List
from .base import ASREngine, TranscriptionResult, TimestampItem

class Qwen3ASREngine(ASREngine):
    def __init__(self, config: dict):
        self.config = config
        self._model = None
        self._mode = config.get("QWEN3ASR_MODE", "local")
    
    @property
    def name(self) -> str:
        return "qwen3-asr"
    
    @property
    def supports_streaming(self) -> bool:
        return self._mode == "local"  # Only local mode supports streaming
    
    def load_model(self):
        if self._model is not None:
            return
        
        if self._mode == "local":
            import torch
            from qwen_asr import Qwen3ASRModel
            
            backend = self.config.get("QWEN3ASR_BACKEND", "transformers")
            model_name = self.config.get("QWEN3ASR_MODEL", "Qwen/Qwen3-ASR-1.7B")
            aligner_name = self.config.get("QWEN3ASR_ALIGNER_MODEL", "Qwen/Qwen3-ForcedAligner-0.6B")
            device = self.config.get("QWEN3ASR_DEVICE", "cuda:0")
            
            if backend == "vllm":
                self._model = Qwen3ASRModel.LLM(
                    model=model_name,
                    gpu_memory_utilization=0.7,
                    max_new_tokens=int(self.config.get("QWEN3ASR_MAX_NEW_TOKENS", 256)),
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
                    max_new_tokens=int(self.config.get("QWEN3ASR_MAX_NEW_TOKENS", 256)),
                    forced_aligner=aligner_name,
                    forced_aligner_kwargs=dict(
                        dtype=torch.bfloat16,
                        device_map=device,
                    ),
                )
        else:
            # API mode - no model to load
            pass
    
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        context: str = "",
        return_timestamps: bool = True,
    ) -> TranscriptionResult:
        self.load_model()
        
        if self._mode == "local":
            return self._transcribe_local(audio_path, language, context, return_timestamps)
        else:
            return self._transcribe_api(audio_path, language, context, return_timestamps)
    
    def _transcribe_local(self, audio_path, language, context, return_timestamps):
        results = self._model.transcribe(
            audio=audio_path,
            language=language,
            context=context,
            return_time_stamps=return_timestamps,
        )
        
        result = results[0]
        timestamps = None
        
        if return_timestamps and result.time_stamps:
            timestamps = [
                {"text": ts.text, "start_time": ts.start_time, "end_time": ts.end_time}
                for ts in result.time_stamps
            ]
        
        return TranscriptionResult(
            language=result.language,
            text=result.text,
            timestamps=timestamps,
        )
    
    def _transcribe_api(self, audio_path, language, context, return_timestamps):
        # DashScope API implementation
        import dashscope
        from dashscope.audio.asr import Transcription
        
        dashscope.api_key = self.config.get("QWEN3ASR_API_KEY")
        
        # API call logic...
        pass
```

### 5.2 FunASREngine Adapter

Wrap existing FunASR code into the ASREngine interface:

```python
# scripts/asr_engines/fun_asr_engine.py
from .base import ASREngine, TranscriptionResult

class FunASREngine(ASREngine):
    """Adapter for existing FunASR implementation"""
    
    @property
    def name(self) -> str:
        return "funasr"
    
    @property
    def supports_streaming(self) -> bool:
        return False  # FunASR streaming requires separate model
    
    def transcribe(self, audio_path, language=None, context="", return_timestamps=True):
        # Call existing transcribe.py logic
        # Convert to TranscriptionResult format
        pass
```

---

## 6. transcribe.py Refactoring

### 6.1 Current Structure

Currently `transcribe.py` is monolithic with:
- Audio extraction (ffmpeg)
- FunASR model loading
- Transcription logic
- SRT/TXT generation
- MD5 caching

### 6.2 Proposed Refactoring

```python
# scripts/transcribe.py (refactored)
from utils import load_config, get_file_md5, get_unified_output_dir, setup_env
from asr_engines.factory import get_asr_engine

def transcribe(media_path, output_dir=None):
    config = load_config()
    setup_env()
    
    # Get engine from factory
    engine = get_asr_engine(config=config)
    engine.load_model()
    
    # Prepare audio (extract if video)
    audio_path = prepare_audio(media_path, config)
    
    # Transcribe
    result = engine.transcribe(
        audio_path=audio_path,
        return_timestamps=True,
    )
    
    # Generate outputs (SRT, TXT, JSON)
    generate_outputs(result, output_dir)
    
    return result
```

---

## 7. Dependencies

### 7.1 New Dependencies

```
# requirements.txt addition
qwen-asr>=0.1.0  # Core Qwen3-ASR package

# Optional for vLLM backend
# vllm>=0.6.0  # Uncomment if using vLLM backend

# API mode
# dashscope>=1.25.6  # Uncomment if using DashScope API
```

### 7.2 VRAM Requirements

| Model | VRAM Required |
|-------|---------------|
| Qwen3-ASR-1.7B + ForcedAligner | ~5-6 GB |
| Qwen3-ASR-0.6B + ForcedAligner | ~3-4 GB |
| API mode | 0 GB (cloud) |

---

## 8. Comparison: FunASR vs Qwen3-ASR

| Feature | FunASR (Paraformer) | Qwen3-ASR |
|---------|---------------------|-----------|
| **Languages** | 31 + 7 dialects | 52 (30 + 22 dialects) |
| **Singing/BGM** | Poor | Excellent (SOTA) |
| **Timestamp precision** | Sentence-level | Character-level (42.9ms error) |
| **Streaming** | Yes (separate model) | Yes (unified model) |
| **Context biasing** | No | Yes (10K tokens) |
| **API mode** | No | Yes (DashScope) |
| **Open source** | Yes (MIT) | Yes (Apache 2.0) |
| **Chinese accuracy** | Good | Best (SOTA) |
| **Noise robustness** | Good | Excellent |
| **Speaker diarization** | Yes (built-in) | No (external tool needed) |

### 8.1 Use Case Recommendations

- **Use FunASR when:**
  - Speaker diarization is critical
  - Clean audio, standard speech
  - Lower GPU resources

- **Use Qwen3-ASR when:**
  - Chinese/multilingual content
  - Noisy environment, BGM, singing
  - Precise character-level timestamps needed
  - Streaming transcription required

---

## 9. Common Pitfalls

1. **VRAM OOM**: Use Qwen3-ASR-0.6B for lower VRAM, or API mode
2. **No timestamps without aligner**: Must load ForcedAligner for timestamps
3. **Streaming no timestamps**: Streaming mode doesn't use ForcedAligner
4. **Long audio (>5min)**: ForcedAligner has 5-minute limit, need chunking
5. **API rate limits**: DashScope has 20 req/s limit
6. **Language detection**: Set `language=None` for auto-detection, or specify for better accuracy

---

## 10. Implementation Phases

Based on research findings, recommend splitting into:

1. **Phase 7.1**: ASR engine abstraction layer
   - Create ASREngine base class
   - Create FunASREngine adapter
   - Create engine factory

2. **Phase 7.2**: Qwen3-ASR local implementation
   - Qwen3ASREngine class
   - Configuration support
   - Timestamp handling

3. **Phase 7.3**: Integration & testing
   - Refactor transcribe.py
   - Update config.example.txt
   - End-to-end testing

---

## 11. References

- GitHub: https://github.com/QwenLM/Qwen3-ASR
- Paper: https://arxiv.org/pdf/2601.21337
- DashScope API: https://www.alibabacloud.com/help/en/model-studio/qwen-asr-api-reference
- HuggingFace: https://huggingface.co/Qwen/Qwen3-ASR-1.7B

---

*Research completed: 2026-04-12*
