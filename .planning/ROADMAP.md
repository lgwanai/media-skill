# Roadmap: Media Skill — Multi-Model Voice Cloning Expansion

**Created:** 2026-04-11
**Milestone:** v1.0 — Multi-Model Voice Cloning
**Depth:** Standard | **Parallelization:** Enabled

## Phase 1: Refactor TTS Engine Architecture

**Goal:** Create a pluggable TTS engine architecture with abstract base class, isolating existing IndexTTS-2 and Qwen3-TTS code into separate modules while preserving all existing functionality.

**Depends on:** None (foundation phase)

**Requirements:** CODE-01, CODE-02, CODE-03, CODE-04, PERF-03

**Success Criteria:**
1. Abstract `TTSEngine` base class defines `clone_voice()`, `synthesize()`, `get_emotion_params()`, `load_model()` interfaces
2. `IndexTTSEngine` and `Qwen3TTSEngine` classes implement the base interface with all existing behavior preserved
3. Engine factory function routes to correct engine based on `TTS_ENGINE` config value
4. Existing `scripts/dubbing.py` uses the new architecture without behavior changes
5. All existing voice clones in `data/voices/` continue to work without migration
6. Multi-threaded synthesis works with both engines

**Plans:** 3 plans

Plans:
- [ ] 01-refactor-tts-engine-architecture-01-PLAN.md — Create TTSEngine abstract base class and EmotionParser utility
- [ ] 01-refactor-tts-engine-architecture-02-PLAN.md — Extract IndexTTS-2 and Qwen3-TTS into separate engine classes
- [ ] 01-refactor-tts-engine-architecture-03-PLAN.md — Create engine factory and refactor dubbing.py

---

## Phase 2: Integrate LongCat-AudioDiT and OmniVoice Models

**Goal:** Implement `LongCatAudioDiTEngine` and `OmniVoiceEngine` classes that implement the `TTSEngine` interface, enabling voice cloning and synthesis with both new models.

**Depends on:** Phase 1 (pluggable architecture must exist)

**Requirements:** MODEL-01, MODEL-02

**Success Criteria:**
1. `LongCatAudioDiTEngine` implements all base class methods with working voice cloning and synthesis
2. `OmniVoiceEngine` implements all base class methods with working voice cloning and synthesis
3. Both engines can be loaded via engine factory when configured
4. Model-specific dependencies are documented and installable
5. Basic synthesis test produces audible output for both models

**Plans:**
- [ ] Research LongCat-AudioDiT API and create `scripts/tts_engines/longcat_audiodit_engine.py`
- [ ] Research OmniVoice API and create `scripts/tts_engines/omnivoice_engine.py`
- [ ] Add model loading logic with proper error handling and fallback messages
- [ ] Implement voice cloning flow for both models (reference audio → model-specific features)
- [ ] Implement synthesis flow for both models (text + voice → audio output)
- [ ] Test both models with sample audio and text

---

## Phase 3: Configuration for 4 Models

**Goal:** Update configuration system to support all 4 models (IndexTTS-2, Qwen3-TTS, LongCat-AudioDiT, OmniVoice) with model-specific settings and validation.

**Depends on:** Phase 2 (models must be implemented to know what config they need)

**Requirements:** MODEL-03, CONFIG-01, CONFIG-02, CONFIG-03, CONFIG-04

**Success Criteria:**
1. `TTS_ENGINE` config accepts: `indextts`, `qwen3-tts`, `longcat-audiodit`, `omnivoice`
2. `config.txt` includes sections for LongCat-AudioDiT (mode, URL, API key, model name, local path)
3. `config.txt` includes sections for OmniVoice (mode, URL, API key, model name, local path)
4. `config.example.txt` updated with all 4 model templates and documentation comments
5. Config validation rejects invalid engine names with helpful error message
6. Engine-specific config is only loaded when that engine is selected

**Plans:**
- [ ] Update `config.txt` with LongCat-AudioDiT and OmniVoice sections
- [ ] Update `config.example.txt` with complete 4-model template
- [ ] Update config parser to validate `TTS_ENGINE` against allowed values
- [ ] Update engine factory to load model-specific config
- [ ] Add config documentation comments explaining each model's requirements

---

## Phase 4: Voice Clone Persistence & Performance Optimization

**Goal:** Ensure cloned voice samples are persisted with model-compatible metadata, features are cached per model, and performance is optimized through feature reuse.

**Depends on:** Phase 2 (models must support cloning), Phase 3 (config must support model selection)

**Requirements:** CLONE-01, CLONE-02, CLONE-03, CLONE-04, PERF-01, PERF-02

**Success Criteria:**
1. `clone_voice` saves reference audio and extracts features for ALL compatible models
2. `meta.json` includes `compatible_models` array listing which models the clone works with
3. Model-specific feature files are cached (e.g., `ref_audio_indextts.pt`, `ref_audio_longcat.pt`)
4. Synthesis reuses cached features without re-extraction
5. Feature cache is invalidated when reference audio is updated
6. Clone command supports `--models` flag to specify target models

**Plans:**
- [ ] Update `clone_voice` to extract and cache features for all compatible models
- [ ] Update `meta.json` schema to include `compatible_models` array
- [ ] Implement feature cache lookup in each engine's `synthesize` method
- [ ] Add cache invalidation logic (check reference audio modification time)
- [ ] Add `--models` flag to clone command for targeted feature extraction
- [ ] Test clone → synthesize round-trip with feature caching for all 4 models

---

## Phase 5: Emotion Control for All Models

**Goal:** Implement unified emotion control that works across all 4 models, with model-specific emotion parameter mapping and text tag parsing.

**Depends on:** Phase 2 (models must support emotion), Phase 4 (clones must be persisted)

**Requirements:** EMO-01, EMO-02, EMO-03, EMO-04

**Success Criteria:**
1. Emotion tags `[情绪:强度]` in text are parsed into unified emotion representation
2. Each engine maps unified emotion to model-specific parameters (emo_vector, style tokens, etc.)
3. LongCat-AudioDiT supports emotion-controlled synthesis
4. OmniVoice supports emotion-controlled synthesis
5. Emotion tags are stripped from output text before synthesis for all models
6. Fallback to neutral emotion when model doesn't support a specific emotion

**Plans:**
- [ ] Create `EmotionParser` utility to parse text tags into unified emotion dict
- [ ] Add `get_emotion_params(emotion_dict)` to each engine with model-specific mapping
- [ ] Implement emotion mapping for LongCat-AudioDiT (research model's emotion API)
- [ ] Implement emotion mapping for OmniVoice (research model's emotion API)
- [ ] Update IndexTTS-2 and Qwen3-TTS engines to use unified emotion parser
- [ ] Test emotion-controlled synthesis with all 4 models using sample text with emotion tags

---

## Requirement Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| CODE-01 | Phase 1 | Pending |
| CODE-02 | Phase 1 | Pending |
| CODE-03 | Phase 1 | Pending |
| CODE-04 | Phase 1 | Pending |
| PERF-03 | Phase 1 | Pending |
| MODEL-01 | Phase 2 | Pending |
| MODEL-02 | Phase 2 | Pending |
| MODEL-03 | Phase 3 | Pending |
| CONFIG-01 | Phase 3 | Pending |
| CONFIG-02 | Phase 3 | Pending |
| CONFIG-03 | Phase 3 | Pending |
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

**Coverage:**
- v1 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓

---
*Roadmap created: 2026-04-11*
*Last updated: 2026-04-11 after initialization*
