# Requirements: Media Skill — Multi-Model Voice Cloning Expansion

**Defined:** 2026-04-11
**Core Value:** Users can clone any voice from a short audio sample and generate natural-sounding speech with emotion control, choosing from multiple TTS models to balance quality, speed, and resource constraints.

## v1 Requirements

### Model Integration

- [ ] **MODEL-01**: System supports LongCat-AudioDiT as a TTS engine for voice cloning and synthesis
- [ ] **MODEL-02**: System supports OmniVoice (k2-fsa/OmniVoice) as a TTS engine for voice cloning and synthesis
- [ ] **MODEL-03**: All 4 models (IndexTTS-2, Qwen3-TTS, LongCat-AudioDiT, OmniVoice) can be selected via configuration

### Configuration

- [ ] **CONFIG-01**: config.txt includes configuration sections for LongCat-AudioDiT (mode, URL, API key, model name)
- [ ] **CONFIG-02**: config.txt includes configuration sections for OmniVoice (mode, URL, API key, model name)
- [ ] **CONFIG-03**: TTS_ENGINE config accepts all 4 model identifiers as valid values
- [ ] **CONFIG-04**: config.example.txt updated with all 4 model configuration templates

### Voice Cloning & Persistence

- [ ] **CLONE-01**: Cloned voice samples are saved to `data/voices/NAME/` with model-compatible metadata
- [ ] **CLONE-02**: Each voice clone records which models it is compatible with in meta.json
- [ ] **CLONE-03**: Voice features are serialized and cached per compatible model (e.g., .pt for IndexTTS, model-specific format for others)
- [ ] **CLONE-04**: Clone command supports specifying target model(s) for feature extraction

### Emotion Control

- [ ] **EMO-01**: Emotion tags in text (e.g., `[高兴:0.9]`) are parsed and mapped to each model's emotion/prosody API
- [ ] **EMO-02**: LongCat-AudioDiT supports emotion-controlled synthesis
- [ ] **EMO-03**: OmniVoice supports emotion-controlled synthesis
- [ ] **EMO-04**: Emotion tag stripping from output text works for all models

### Code Quality & Architecture

- [ ] **CODE-01**: TTS engines use a common abstract base class/interface for pluggable architecture
- [ ] **CODE-02**: Each model implements the same interface: `clone_voice()`, `synthesize()`, `get_emotion_params()`
- [ ] **CODE-03**: Engine-specific code is isolated in separate modules (no monolithic if/else chains)
- [ ] **CODE-04**: Existing IndexTTS-2 and Qwen3-TTS functionality is preserved (backward compatible)

### Performance

- [ ] **PERF-01**: Cached voice features are reused without re-extraction on subsequent synthesis
- [ ] **PERF-02**: Feature cache is invalidated when reference audio changes
- [ ] **PERF-03**: Multi-threaded synthesis works with all 4 models

## v2 Requirements

### Model Management

- **MODEL-04**: Runtime model switching without restart
- **MODEL-05**: Model quality benchmarking and automatic recommendation based on input characteristics

### Advanced Emotion

- **EMO-05**: Fine-grained emotion mixing (multiple emotions with weights)
- **EMO-06**: Automatic emotion detection from source audio for clone matching

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time streaming TTS | Batch processing sufficient for current video dubbing workflow |
| Modifying existing IndexTTS-2/Qwen3-TTS core behavior | Only extend, don't break existing functionality |
| Training custom models from scratch | Focus on inference/integration, not training |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
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
| EMO-01 | Phase 5 | Pending |
| EMO-02 | Phase 5 | Pending |
| EMO-03 | Phase 5 | Pending |
| EMO-04 | Phase 5 | Pending |
| CODE-01 | Phase 1 | Pending |
| CODE-02 | Phase 1 | Pending |
| CODE-03 | Phase 1 | Pending |
| CODE-04 | Phase 1 | Pending |
| PERF-01 | Phase 4 | Pending |
| PERF-02 | Phase 4 | Pending |
| PERF-03 | Phase 1 | Pending |

**Coverage:**
- v1 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-11*
*Last updated: 2026-04-11 after initial definition*
