# Media Skill — Multi-Model Voice Cloning Expansion

## What This Is

A modular media AI workspace that handles long-form audio/video workflows end-to-end: transcription (FunASR), intelligent editing, highlight extraction, voice cloning, and auto-dubbing with subtitles. Currently supports IndexTTS-2 and Qwen3-TTS engines. This project expands voice cloning to support **4 models total**: IndexTTS-2, Qwen3-TTS, **LongCat-AudioDiT**, and **OmniVoice** (k2-fsa/OmniVoice).

## Core Value

Users can clone any voice from a short audio sample and generate natural-sounding speech with emotion control, choosing from multiple TTS models to balance quality, speed, and resource constraints.

## Requirements

### Validated

- ✓ Transcription via FunASR (Paraformer + VAD + PUNC + diarization) — existing
- ✓ Voice cloning with IndexTTS-2 (local) — existing
- ✓ Voice cloning with Qwen3-TTS (local/API) — existing
- ✓ Emotion control via emo_vector from text tags — existing
- ✓ End-to-end dubbing pipeline (transcription → TTS → output) — existing
- ✓ Configuration via config.txt — existing

### Active

- [ ] Add LongCat-AudioDiT as a supported TTS/voice cloning model
- [ ] Add OmniVoice (k2-fsa/OmniVoice) as a supported TTS/voice cloning model
- [ ] Unified configuration allowing users to select from 4 models (IndexTTS-2, Qwen3-TTS, LongCat-AudioDiT, OmniVoice)
- [ ] Emotion control support for all 4 models (model-specific emotion parameter mapping)
- [ ] Cloned voice samples must be persisted with metadata tagging compatible models
- [ ] Performance optimization: cache/serialize voice features per compatible model
- [ ] Code quality improvements: clean abstraction layer for pluggable TTS engines

### Out of Scope

- Modifying existing IndexTTS-2 or Qwen3-TTS core behavior — only extend, don't break
- Real-time streaming TTS — batch processing is sufficient for current use case

## Context

- **Existing architecture**: Modular Python scripts in `scripts/` with centralized config in `config.txt`
- **Current engines**: IndexTTS-2 (local via modelscope), Qwen3-TTS (local/API via DashScope)
- **Voice storage**: `data/voices/NAME/` with `meta.json`, `ref_audio.wav`, and optional `.pt` feature files
- **Emotion system**: Text tags like `[高兴:0.9]` parsed into `emo_vector` for IndexTTS-2
- **Dependencies**: funasr, modelscope, torch, torchaudio, pydub, requests
- **New models to integrate**:
  - **LongCat-AudioDiT**: Audio diffusion model for TTS — need to research API/local deployment
  - **OmniVoice**: https://github.com/k2-fsa/OmniVoice/ — k2-fsa voice cloning framework

## Constraints

- **Tech stack**: Python 3.x, PyTorch ecosystem — new models must integrate via Python
- **Configuration**: Must maintain backward compatibility with existing config.txt format
- **Performance**: Cloned samples must be reusable without re-extraction; feature caching required
- **Emotion**: All 4 models must support some form of emotion/prosody control, even if mapping differs

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Pluggable engine architecture via abstract base class | Current code has engine-specific branches; need clean separation for 4+ models | — Pending |
| Per-model feature serialization | Different models need different feature formats; store all compatible features per voice | — Pending |
| Emotion mapping layer | Each model has different emotion parameter APIs; need unified interface → model-specific translation | — Pending |

---
*Last updated: 2026-04-11 after initialization*
