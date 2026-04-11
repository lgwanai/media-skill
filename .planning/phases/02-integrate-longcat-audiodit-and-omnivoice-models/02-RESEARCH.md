# RESEARCH: Phase 2 - Integrate LongCat-AudioDiT and OmniVoice Models

**Researched:** 2026-04-11
**Goal:** Implement `LongCatAudioDiTEngine` and `OmniVoiceEngine` classes implementing `TTSEngine` interface

---

## 1. LongCat-AudioDiT

### Overview
- **GitHub:** https://github.com/meituan-longcat/LongCat-AudioDiT
- **HuggingFace:** https://huggingface.co/meituan-longcat/LongCat-AudioDiT-1B
- **License:** MIT
- **Architecture:** Diffusion-based TTS operating directly in waveform latent space (no mel-spectrogram)
- **Sample Rate:** 24kHz
- **Models:** 1B (lightweight) and 3.5B (high quality)

### Key Features
- Zero-shot voice cloning (3-15 seconds reference audio recommended)
- State-of-the-art performance on Seed benchmark (0.818 SIM on Seed-ZH)
- Adaptive Projection Guidance (APG) for better voice cloning

### Python API

```python
import audiodit  # auto-registers with transformers
from audiodit import AudioDiTModel
from transformers import AutoTokenizer
import torch
import librosa
import soundfile as sf

# Load model
model = AudioDiTModel.from_pretrained("meituan-longcat/LongCat-AudioDiT-1B").to("cuda")
tokenizer = AutoTokenizer.from_pretrained(model.config.text_encoder_model)

# Zero-shot TTS (no voice cloning)
inputs = tokenizer(["今天晴暖转阴雨"], padding="longest", return_tensors="pt")
output = model(
    input_ids=inputs.input_ids,
    attention_mask=inputs.attention_mask,
    duration=62,  # latent frames
    steps=16,
    cfg_strength=4.0,
    guidance_method="cfg",  # or "apg"
)
sf.write("output.wav", output.waveform.squeeze().cpu().numpy(), 24000)

# Voice cloning (with prompt audio)
audio, _ = librosa.load("reference.wav", sr=24000, mono=True)
inputs = tokenizer(["要合成的文本"], padding="longest", return_tensors="pt")
output = model(
    input_ids=inputs.input_ids,
    attention_mask=inputs.attention_mask,
    prompt_audio=torch.from_numpy(audio).unsqueeze(0).to("cuda"),
    duration=62,
    steps=16,
    cfg_strength=4.0,
    guidance_method="apg",  # Use APG for voice cloning
)
```

### CLI Usage

```bash
# TTS
python inference.py --text "今天晴暖转阴雨" --output_audio output.wav --model_dir meituan-longcat/LongCat-AudioDiT-1B

# Voice cloning
python inference.py \
    --text "要合成的文本" \
    --prompt_text "参考音频对应的文本" \
    --prompt_audio reference.wav \
    --output_audio output.wav \
    --model_dir meituan-longcat/LongCat-AudioDiT-1B \
    --guidance_method apg
```

### Generation Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `duration` | int | ~ | Latent frames (approximate audio duration) |
| `steps` | int | 16 | ODE Euler steps (4-64, higher = better quality) |
| `cfg_strength` | float | 4.0 | Guidance strength (0-10) |
| `guidance_method` | str | "cfg" | "cfg" for TTS, "apg" for voice cloning |

### Dependencies

```bash
pip install transformers torch librosa soundfile
# Model auto-downloads from HuggingFace on first use
```

### Emotion Control
- **NOT SUPPORTED**: No explicit emotion control API found in the model
- The model focuses on voice timbre cloning, not prosody/emotion modulation
- **Implementation approach:** Strip emotion tags from text (like Qwen3-TTS)

### Voice Cloning Flow
1. Load reference audio (3-15 seconds, 24kHz)
2. Provide transcript of reference audio (`prompt_text`) for better quality
3. Use `guidance_method="apg"` for best cloning results
4. No feature extraction needed - pure zero-shot inference

---

## 2. OmniVoice

### Overview
- **GitHub:** https://github.com/k2-fsa/OmniVoice
- **HuggingFace:** https://huggingface.co/k2-fsa/OmniVoice
- **License:** Apache 2.0
- **Architecture:** Diffusion language model-style architecture
- **Sample Rate:** 24kHz
- **Languages:** 600+ languages supported

### Key Features
- Zero-shot voice cloning
- Massive multilingual support (600+ languages)
- Fast inference: RTF as low as 0.025 (40x faster than real-time)
- Voice design and auto-voice modes (not needed for this phase)

### Python API

```python
from omnivoice import OmniVoice
import torch
import torchaudio

# Load model
model = OmniVoice.from_pretrained(
    "k2-fsa/OmniVoice",
    device_map="cuda:0",
    dtype=torch.float16
)

# Voice cloning
audio, sr = torchaudio.load("reference.wav")
if sr != 24000:
    resampler = torchaudio.transforms.Resample(sr, 24000)
    audio = resampler(audio)

audios = model.generate(
    text="This is a test for text to speech.",
    language="Chinese",  # or specific language code
    ref_audio="reference.wav",
    ref_text="Transcription of the reference audio.",
    num_step=32,
    guidance_scale=2.0,
)

torchaudio.save("output.wav", audios[0].unsqueeze(0), 24000)
```

### CLI Usage

```bash
# Voice cloning (ref_text can be omitted - Whisper auto-transcribes)
omnivoice-infer \
    --model k2-fsa/OmniVoice \
    --text "This is a test for text to speech." \
    --ref_audio reference.wav \
    --ref_text "Transcription of reference audio." \
    --output output.wav
```

### Generation Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `num_step` | int | 32 | Iterative unmasking steps (higher = better quality) |
| `guidance_scale` | float | 2.0 | Classifier-free guidance scale |
| `duration` | float | None | Fixed output duration in seconds |
| `speed` | float | None | Speed factor (>1.0 = faster, <1.0 = slower) |
| `t_shift` | float | 0.1 | Time-step shift for noise schedule |
| `denoise` | bool | True | Produce cleaner audio |
| `language` | str | auto | Language name or code |

### Dependencies

```bash
pip install omnivoice
# Or from source:
pip install git+https://github.com/k2-fsa/OmniVoice.git
# Requires: torch, torchaudio
```

### Emotion Control
- **NOT SUPPORTED**: No explicit emotion control API found
- The model focuses on voice timbre and language support
- **Implementation approach:** Strip emotion tags from text (like Qwen3-TTS)

### Voice Cloning Flow
1. Load reference audio (any duration, will be preprocessed)
2. Optionally provide `ref_text` (transcript) - if omitted, Whisper auto-transcribes
3. Specify `language` for better quality
4. No feature extraction needed - pure zero-shot inference

---

## 3. Comparison with Existing Engines

| Feature | IndexTTS-2 | Qwen3-TTS | LongCat-AudioDiT | OmniVoice |
|---------|-----------|-----------|------------------|-----------|
| Voice cloning | Zero-shot + feature extraction | Zero-shot only | Zero-shot only | Zero-shot only |
| Emotion control | emo_vector | None | None | None |
| Feature caching | .pt files | None | None | None |
| API mode | SiliconFlow | DashScope | **None** | **None** |
| Local mode | Yes | Yes | Yes | Yes |
| License | Custom | Custom | MIT | Apache 2.0 |
| Languages | Chinese | Chinese | Chinese | 600+ |

### Key Differences

1. **No API Mode**: Both LongCat-AudioDiT and OmniVoice are local-only models. No cloud API available.
2. **Zero-shot Only**: Unlike IndexTTS, no feature extraction/caching. Pure zero-shot inference.
3. **No Emotion Control**: Neither model supports explicit emotion parameters.
4. **Transcript Required**: LongCat-AudioDiT benefits from `prompt_text` (transcript of reference audio). OmniVoice can auto-transcribe with Whisper if `ref_text` is omitted.

---

## 4. Implementation Approach

### LongCatAudioDiTEngine

```python
class LongCatAudioDiTEngine(TTSEngine):
    @property
    def name(self) -> str:
        return "longcat-audiodit"
    
    def load_model(self) -> None:
        # Local mode only - load AudioDiTModel from HuggingFace
        # Config: LONGCAT_MODEL_NAME (default: meituan-longcat/LongCat-AudioDiT-1B)
    
    def clone_voice(self, ref_audio: str, text: str, voice_name: str) -> str:
        # Save ref_audio to data/voices/{voice_name}/ref_audio.wav
        # Save transcript to meta.json
        # Return "longcat:{ref_audio_path}"
    
    def synthesize(self, text: str, voice_id: str, output_path: str, tts_params: dict | None) -> bool:
        # Strip emotion tags (not supported)
        # Load model if not loaded
        # Tokenize text
        # Call model with prompt_audio and prompt_text
        # Use guidance_method="apg" for voice cloning
        # Save output to output_path
    
    def get_emotion_params(self, text: str) -> tuple[dict, str]:
        # Strip emotion tags, return empty params (not supported)
        return {}, clean_text
```

### OmniVoiceEngine

```python
class OmniVoiceEngine(TTSEngine):
    @property
    def name(self) -> str:
        return "omnivoice"
    
    def load_model(self) -> None:
        # Local mode only - load OmniVoice from HuggingFace
        # Config: OMNIVOICE_MODEL_NAME (default: k2-fsa/OmniVoice)
    
    def clone_voice(self, ref_audio: str, text: str, voice_name: str) -> str:
        # Save ref_audio to data/voices/{voice_name}/ref_audio.wav
        # Save transcript to meta.json
        # Return "omnivoice:{ref_audio_path}"
    
    def synthesize(self, text: str, voice_id: str, output_path: str, tts_params: dict | None) -> bool:
        # Strip emotion tags (not supported)
        # Load model if not loaded
        # Resolve ref_audio and ref_text from voice_id
        # Call model.generate() with ref_audio, ref_text
        # Save output to output_path
    
    def get_emotion_params(self, text: str) -> tuple[dict, str]:
        # Strip emotion tags, return empty params (not supported)
        return {}, clean_text
```

---

## 5. Configuration Schema

```ini
# LongCat-AudioDiT Configuration
LONGCAT_MODEL_NAME = meituan-longcat/LongCat-AudioDiT-1B
LONGCAT_STEPS = 16
LONGCAT_CFG_STRENGTH = 4.0

# OmniVoice Configuration
OMNIVOICE_MODEL_NAME = k2-fsa/OmniVoice
OMNIVOICE_NUM_STEP = 32
OMNIVOICE_GUIDANCE_SCALE = 2.0
```

---

## 6. Dependencies to Add

### LongCat-AudioDiT
```bash
pip install transformers librosa soundfile
# Model downloads from HuggingFace: meituan-longcat/LongCat-AudioDiT-1B (~4GB)
```

### OmniVoice
```bash
pip install omnivoice
# Or: pip install git+https://github.com/k2-fsa/OmniVoice.git
# Model downloads from HuggingFace: k2-fsa/OmniVoice
```

---

## 7. Gotchas & Common Pitfalls

### LongCat-AudioDiT
1. **Reference audio transcript required**: While optional, `prompt_text` significantly improves voice cloning quality. Always provide transcript.
2. **Sample rate must be 24kHz**: Load audio with `librosa.load(path, sr=24000)`
3. **Use APG for cloning**: Set `guidance_method="apg"` for best voice cloning results
4. **Duration estimation**: The `duration` parameter is in latent frames, not seconds. Rough guide: ~1 frame ≈ 0.024 seconds

### OmniVoice
1. **Auto-transcription**: If `ref_text` is omitted, Whisper auto-transcribes. This is slower but convenient.
2. **Language specification**: Provide `language` parameter for better quality
3. **Device compatibility**: Supports CUDA, MPS (Apple Silicon), and CPU
4. **Batch inference**: Supports multi-GPU batch inference for production workloads

---

## 8. Summary

| Aspect | LongCat-AudioDiT | OmniVoice |
|--------|------------------|-----------|
| API Mode | ❌ None | ❌ None |
| Local Mode | ✅ Yes | ✅ Yes |
| Voice Cloning | ✅ Zero-shot | ✅ Zero-shot |
| Emotion Control | ❌ None | ❌ None |
| Transcript Needed | ✅ Recommended | ⚡ Optional (auto-transcribe) |
| Language Support | Chinese | 600+ languages |
| Model Size | 1B / 3.5B | ~1B |
| Sample Rate | 24kHz | 24kHz |

**Recommendation:**
- Both engines are local-only (no API mode needed)
- Both strip emotion tags (like Qwen3-TTS)
- LongCat benefits from reference transcript
- OmniVoice has broader language support and can auto-transcribe

---

## RESEARCH COMPLETE

**Status:** Ready for planning
**Next:** Spawn gsd-planner with research context
