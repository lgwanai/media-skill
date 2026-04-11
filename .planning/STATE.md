# State: Media Skill — Multi-Model Voice Cloning Expansion

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-11)

**Core value:** Users can clone any voice from a short audio sample and generate natural-sounding speech with emotion control, choosing from multiple TTS models.
**Current focus:** Phase 1 — Refactor TTS engine architecture for pluggable models

## Phase Status

| Phase | Status | Plans | Progress |
|-------|--------|-------|----------|
| 1 | ○ Not started | 0/0 | 0% |
| 2 | ○ Not started | 0/0 | 0% |
| 3 | ○ Not started | 0/0 | 0% |
| 4 | ○ Not started | 0/0 | 0% |
| 5 | ○ Not started | 0/0 | 0% |

## Accumulated Context

### Codebase Assessment
- Brownfield project with existing IndexTTS-2 and Qwen3-TTS support
- Modular Python scripts in `scripts/` directory
- Configuration centralized in `config.txt`
- Voice clones stored in `data/voices/NAME/` with `meta.json` and `ref_audio.wav`
- Emotion control via text tags parsed into `emo_vector`
- Current TTS engine selection via `TTS_ENGINE` config (indextts or qwen3-tts)

### Roadmap Evolution
- Project initialized with 5 phases to add LongCat-AudioDiT and OmniVoice support
- Research pending for both new models (LongCat-AudioDiT, OmniVoice)

## Active Decisions

| Decision | Status | Notes |
|----------|--------|-------|
| Pluggable engine architecture | Pending | Abstract base class for all TTS engines |
| Per-model feature serialization | Pending | Store features in model-specific formats |
| Emotion mapping layer | Pending | Unified interface → model-specific translation |

---
*Last updated: 2026-04-11 after project initialization*
