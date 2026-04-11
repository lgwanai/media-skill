# State: Media Skill — Multi-Model Voice Cloning Expansion

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-11)

**Core value:** Users can clone any voice from a short audio sample and generate natural-sounding speech with emotion control, choosing from multiple TTS models.
**Current focus:** Phase 5 — Emotion Control for All Models

## Phase Status

| Phase | Status | Plans | Progress |
|-------|--------|-------|----------|
| 1 | ✓ Complete | 3/3 | 100% |
| 2 | ✓ Complete | 3/3 | 100% |
| 3 | ✓ Complete | 2/2 | 100% |
| 4 | ✓ Complete | - | 100% |
| 5 | ○ Not started | 0/0 | 0% |

## Accumulated Context

### Codebase Assessment
- Brownfield project with existing IndexTTS-2 and Qwen3-TTS support
- Modular Python scripts in `scripts/` directory
- Configuration centralized in `config.txt`
- Voice clones stored in `data/voices/NAME/` with `meta.json` and `ref_audio.wav`
- Emotion control via text tags parsed into `emo_vector`
- Current TTS engine selection via `TTS_ENGINE` config (indextts or qwen3-tts)
- **Phase 2 added**: LongCat-AudioDiT and OmniVoice engine implementations
- **4 TTS engines now available**: indextts, qwen3-tts, longcat-audiodit, omnivoice
- **Phase 4 added**: Multi-model clone support with `compatible_models` array in meta.json
- **Phase 4 added**: Cache invalidation on reference audio change

### Roadmap Evolution
- Project initialized with 5 phases to add LongCat-AudioDiT and OmniVoice support
- Research complete for both new models (02-RESEARCH.md created)
- Phase 1 complete: Pluggable TTS engine architecture
- Phase 2 complete: LongCat-AudioDiT and OmniVoice engine implementations
- Phase 3 complete: Configuration for 4 engines
- Phase 4 complete: Multi-model voice clone persistence with cache invalidation

## Active Decisions

| Decision | Status | Notes |
|----------|--------|-------|
| Pluggable engine architecture | Complete | ABC + 4 engine implementations + factory pattern |
| Per-model feature serialization | Complete | IndexTTS extracts .pt features; others use zero-shot |
| Emotion mapping layer | Complete | EmotionParser + per-engine integration |
| Local-only for new engines | Complete | LongCat and OmniVoice are local-only (no API mode) |
| Multi-model clone support | Complete | `--models` flag + `compatible_models` array |
| Cache invalidation | Complete | MD5 hash comparison for reference audio |

---
*Last updated: 2026-04-11 after completing Phase 4*
