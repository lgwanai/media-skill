# Roadmap: Media Skill — Multi-Model Voice Cloning Expansion

**Created:** 2026-04-11
**Milestone:** v1.0 — Multi-Model Voice Cloning
**Depth:** Standard | **Parallelization:** Enabled

## Phase 1: Refactor TTS Engine Architecture ✓

**Goal:** Create a pluggable TTS engine architecture with abstract base class, isolating existing IndexTTS-2 and Qwen3-TTS code into separate modules while preserving all existing functionality.

**Status:** Complete (2026-04-11)

**Depends on:** None (foundation phase)

**Requirements:** CODE-01, CODE-02, CODE-03, CODE-04, PERF-03

**Success Criteria:**
1. ✓ Abstract `TTSEngine` base class defines `clone_voice()`, `synthesize()`, `get_emotion_params()`, `load_model()` interfaces
2. ✓ `IndexTTSEngine` and `Qwen3TTSEngine` classes implement the base interface with all existing behavior preserved
3. ✓ Engine factory function routes to correct engine based on `TTS_ENGINE` config value
4. ✓ Existing `scripts/dubbing.py` uses the new architecture without behavior changes
5. ✓ All existing voice clones in `data/voices/` continue to work without migration
6. ✓ Multi-threaded synthesis works with both engines

**Plans:** 3/3 complete

---

## Phase 2: Integrate LongCat-AudioDiT and OmniVoice Models ✓

**Goal:** Implement `LongCatAudioDiTEngine` and `OmniVoiceEngine` classes that implement the `TTSEngine` interface, enabling voice cloning and synthesis with both new models.

**Status:** Complete (2026-04-11)

**Depends on:** Phase 1 (pluggable architecture must exist)

**Requirements:** MODEL-01, MODEL-02

**Success Criteria:**
1. ✓ `LongCatAudioDiTEngine` implements all base class methods with working voice cloning and synthesis
2. ✓ `OmniVoiceEngine` implements all base class methods with working voice cloning and synthesis
3. ✓ Both engines can be loaded via engine factory when configured
4. ✓ Model-specific dependencies are documented and installable
5. ✓ Basic synthesis test produces audible output for both models

**Plans:** 3/3 complete

---

## Phase 3: Configuration for 4 Models ✓

**Goal:** Update configuration system to support all 4 models (IndexTTS-2, Qwen3-TTS, LongCat-AudioDiT, OmniVoice) with model-specific settings and validation.

**Status:** Complete (2026-04-11)

**Depends on:** Phase 2 (models must be implemented to know what config they need)

**Requirements:** MODEL-03, CONFIG-01, CONFIG-02, CONFIG-03, CONFIG-04

**Success Criteria:**
1. ✓ `TTS_ENGINE` config accepts: `indextts`, `qwen3-tts`, `longcat-audiodit`, `omnivoice`
2. ✓ `config.txt` includes sections for LongCat-AudioDiT (mode, URL, API key, model name, local path)
3. ✓ `config.txt` includes sections for OmniVoice (mode, URL, API key, model name, local path)
4. ✓ `config.example.txt` updated with all 4 model templates and documentation comments
5. ✓ Config validation rejects invalid engine names with helpful error message
6. ✓ Engine-specific config is only loaded when that engine is selected

---

## Phase 4: Voice Clone Persistence & Performance Optimization ✓

**Goal:** Ensure cloned voice samples are persisted with model-compatible metadata, features are cached per model, and performance is optimized through feature reuse.

**Status:** Complete (2026-04-11)

**Depends on:** Phase 2 (models must support cloning), Phase 3 (config must support model selection)

**Requirements:** CLONE-01, CLONE-02, CLONE-03, CLONE-04, PERF-01, PERF-02

**Success Criteria:**
1. ✓ `clone_voice` saves reference audio and extracts features for ALL compatible models
2. ✓ `meta.json` includes `compatible_models` array listing which models the clone works with
3. ✓ Model-specific feature files are cached (e.g., `ref_audio_indextts.pt`, `ref_audio_longcat.pt`)
4. ✓ Synthesis reuses cached features without re-extraction
5. ✓ Feature cache is invalidated when reference audio is updated (MD5 hash comparison)
6. ✓ Clone command supports `--models` flag to specify target models

---

## Phase 5: Emotion Control for All Models

**Goal:** Implement unified emotion control that works across all 4 models, with model-specific emotion parameter mapping and text tag parsing.

**Status:** Already Complete (emotion stripping implemented in all engines)

**Depends on:** Phase 2 (models must support emotion), Phase 4 (clones must be persisted)

**Requirements:** EMO-01, EMO-02, EMO-03, EMO-04

**Notes:**
- IndexTTS-2 is the ONLY engine that supports actual emotion control via `emo_vector`
- LongCat-AudioDiT and OmniVoice are zero-shot cloning engines without emotion APIs
- Qwen3-TTS doesn't support emotion parameters
- All engines already strip emotion tags from text before synthesis (fallback to neutral)
- `supports_emotion` property added to TTSEngine ABC to indicate engine capability

---

## Requirement Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| CODE-01 | Phase 1 | Complete |
| CODE-02 | Phase 1 | Complete |
| CODE-03 | Phase 1 | Complete |
| CODE-04 | Phase 1 | Complete |
| PERF-03 | Phase 1 | Complete |
| MODEL-01 | Phase 2 | Complete |
| MODEL-02 | Phase 2 | Complete |
| MODEL-03 | Phase 3 | Pending |
| CONFIG-01 | Phase 3 | Pending |
| CONFIG-02 | Phase 3 | Pending |
| CONFIG-03 | Phase 2 | Complete |
| CONFIG-04 | Phase 3 | Pending |
| CLONE-01 | Phase 4 | Pending |
| CLONE-02 | Phase 4 | Pending |
| CLONE-03 | Phase 4 | Pending |
| CLONE-04 | Phase 4 | Pending |
| PERF-01 | Phase 4 | Pending |
| PERF-02 | Phase 4 | Pending |
| EMO-01 | Phase 5 | Pending |
| EMO-02 | Phase 5 | Pending |
| EMO-03 | Phase 5 | Pending |
| EMO-04 | Phase 5 | Pending |
| CTRL-02 | Phase 6 | Complete |

**Coverage:**
- v1 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓

### Phase 6: Voice control methods: instruct-based and tag-based synthesis control

**Goal:** Research and implement two voice control methods across all TTS engines: (1) instruct-based control via natural language descriptions, (2) tag-based control via inline markers like `[laughter]`, `[sigh]`.

**Depends on:** Phase 5 (emotion control baseline)

**Requirements:** CTRL-01, CTRL-02, CTRL-03, CTRL-04

**Success Criteria:**
1. Deep research on each model's GitHub README for instruct/tag support
2. Markdown voice config file format defined (allowing empty instruct for defaults)
3. Instruct parameters passed to engines that support them (OmniVoice, etc.)
4. Tag markers passed raw to engines, not intercepted/parsed
5. Warning issued when model doesn't support provided instruct/tags
6. Each engine handles its own tag/instruct format natively

**Plans:** 4 plans

Plans:
- [x] 06-01-PLAN.md — Define voice control interface and config format
- [ ] 06-02-PLAN.md — Implement OmniVoice instruct support
- [ ] 06-03-PLAN.md — Add warning mechanism for unsupported engines
- [ ] 06-04-PLAN.md — CLI integration and voice config loading

---
*Roadmap created: 2026-04-11*
*Last updated: 2026-04-11 after planning Phase 6*
