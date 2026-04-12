# State: Media Skill — Multi-Model Voice Cloning Expansion

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-11)

**Core value:** Users can clone any voice from a short audio sample and generate natural-sounding speech with emotion control, choosing from multiple TTS models.
**Current focus:** Phase 7 complete — ASR底层支持Qwen3-ASR方案

## Phase Status

| Phase | Status | Plans | Progress |
|-------|--------|-------|----------|
| 1 | ✓ Complete | 3/3 | 100% |
| 2 | ✓ Complete | 3/3 | 100% |
| 3 | ✓ Complete | 2/2 | 100% |
| 4 | ✓ Complete | - | 100% |
| 5 | ✓ Complete | - | 100% |
| 6 | ✓ Complete | 4/4 | 100% |
| 7 | ✓ Complete | 4/4 | 100% |

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
- **Phase 7 added**: Pluggable ASR architecture with FunASR and Qwen3-ASR support

### Roadmap Evolution
- Project initialized with 5 phases to add LongCat-AudioDiT and OmniVoice support
- Research complete for both new models (02-RESEARCH.md created)
- Phase 1 complete: Pluggable TTS engine architecture
- Phase 2 complete: LongCat-AudioDiT and OmniVoice engine implementations
- Phase 3 complete: Configuration for 4 engines
- Phase 4 complete: Multi-model voice clone persistence with cache invalidation
- Phase 5 complete: Emotion control already implemented via EmotionParser (IndexTTS-only)
- Phase 6 added: Voice control methods (instruct-based and tag-based synthesis control)
- Phase 7 complete: ASR底层支持Qwen3-ASR方案（双模型协同架构：Qwen3-ASR + ForcedAligner）

## Active Decisions

| Decision | Status | Notes |
|----------|--------|-------|
| Pluggable engine architecture | Complete | ABC + 4 engine implementations + factory pattern |
| Per-model feature serialization | Complete | IndexTTS extracts .pt features; others use zero-shot |
| Emotion mapping layer | Complete | EmotionParser + per-engine integration |
| Local-only for new engines | Complete | LongCat and OmniVoice are local-only (no API mode) |
| Multi-model clone support | Complete | `--models` flag + `compatible_models` array |
| Cache invalidation | Complete | MD5 hash comparison for reference audio |
| Instruct parameter optional | Complete | `instruct: str | None` for backward compatibility |
| supports_instruct property | Complete | Default False in base class, OmniVoice overrides to True |
| Instruct warning mechanism | Complete | _warn_unsupported_instruct() in base, all non-OmniVoice warn |
| CLI --instruct integration | Complete | dub command accepts --instruct, passed through to engines |
| Voice config loader | Complete | load_voice_config() for markdown config files |
| Pluggable ASR architecture | Complete | ASREngine ABC + FunASR + Qwen3-ASR implementations |
| ASR engine switching | Complete | ASR_ENGINE config (funasr/qwen3-asr) |

---
*Last updated: 2026-04-12 after completing Phase 7*
