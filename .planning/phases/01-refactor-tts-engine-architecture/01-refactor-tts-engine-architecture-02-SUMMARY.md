---
phase: 01-refactor-tts-engine-architecture
plan: 02
subsystem: infra
tags: [indextts, qwen3-tts, abc, python, thread-safety, audio-processing]

# Dependency graph
requires:
  - phase: 01-refactor-tts-engine-architecture-01
    provides: TTSEngine abstract base class and EmotionParser utility
provides:
  - IndexTTSEngine class with local and API mode support
  - Qwen3TTSEngine class with local and API mode support
  - Both engines implement TTSEngine interface with identical method signatures
  - Thread-safe synthesis with per-engine model and inference locks
  - Full audio post-processing pipeline preserved (silence truncation, DC offset, soft clipping)
affects:
  - 01-refactor-tts-engine-architecture-03 (Engine factory will wire these engines)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Per-engine thread safety with separate _model_lock and _infer_lock
    - Self-contained engine modules (no imports from dubbing.py)
    - Audio post-processing pipeline: silence detection/truncation, DC offset removal, soft clipping via tanh, int16 PCM conversion
    - Zero-shot voice cloning for Qwen3-TTS (no feature extraction needed)
    - Feature extraction and persistence for IndexTTS (dummy inference to trigger .pt save)

key-files:
  created:
    - scripts/tts_engines/indextts_engine.py
    - scripts/tts_engines/qwen3tts_engine.py
  modified: []

key-decisions:
  - "clone_voice requires text parameter (no auto-transcribe) to keep engines self-contained"
  - "Qwen3-TTS get_emotion_params returns empty dict (no emo_vector support) but still strips tags"
  - "IndexTTSEngine uses EmotionParser directly for emotion-to-vector conversion in synthesize"

patterns-established:
  - "Engine classes inherit TTSEngine ABC and implement all 4 abstract methods + name property"
  - "Lazy model loading via load_model() with thread-safe singleton pattern"
  - "Voice ID format: 'engine:identifier' (local:path, api:uri, qwen:path)"

requirements-completed:
  - CODE-02
  - CODE-03
  - CODE-04
  - PERF-03

# Metrics
duration: 5min
completed: 2026-04-11
---

# Phase 01 Plan 02: IndexTTSEngine and Qwen3TTSEngine Extraction Summary

**Extracted IndexTTS-2 and Qwen3-TTS logic from dubbing.py into separate TTSEngine implementations with thread-safe local/API modes, full audio post-processing, and zero dubbing.py dependencies**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-11T00:05:00Z
- **Completed:** 2026-04-11T00:10:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created IndexTTSEngine with local model loading (modelscope, v2/v1 fallback) and API mode (SiliconFlow)
- Created Qwen3TTSEngine with local model loading (Qwen3TTSModel) and API mode (DashScope MultiModalConversation)
- Both engines implement the full TTSEngine interface: load_model, clone_voice, synthesize, get_emotion_params, name
- Preserved all existing audio post-processing: silence truncation (800ms), DC offset removal, soft clipping, int16 PCM
- Thread-safe: each engine has independent _model_lock and _infer_lock
- Engines are fully self-contained with no imports from dubbing.py

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract IndexTTS-2 engine implementation** - `1ad9477` (feat)
2. **Task 2: Extract Qwen3-TTS engine implementation** - `325066d` (feat)

**Deviation fix: Remove dubbing.py import** - `aebdc0b` (fix)

## Files Created/Modified

- `scripts/tts_engines/indextts_engine.py` - IndexTTSEngine: local/API mode, emotion parsing, voice cloning with feature extraction
- `scripts/tts_engines/qwen3tts_engine.py` - Qwen3TTSEngine: local/API mode, full audio post-processing pipeline, zero-shot cloning

## Decisions Made

- clone_voice requires text parameter (raises ValueError if missing) instead of auto-transcribing, to keep engines self-contained with no dubbing.py imports
- Qwen3-TTS get_emotion_params returns empty params dict (Qwen3 doesn't use emo_vector) but still strips emotion tags from text
- IndexTTSEngine integrates EmotionParser directly in synthesize() to convert emotion tags to emo_vector before inference

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Removed dubbing.py auto_transcribe_audio dependency**
- **Found during:** Task 1 (IndexTTSEngine clone_voice implementation)
- **Issue:** Initial implementation imported auto_transcribe_audio from scripts.dubbing, violating the self-contained engine requirement (plan verification: "Engine files do NOT import from dubbing.py")
- **Fix:** Replaced auto-transcribe call with ValueError when text is not provided, requiring caller to supply transcribed text
- **Files modified:** scripts/tts_engines/indextts_engine.py
- **Verification:** AST analysis confirms no dubbing.py imports in either engine file; both engines import and instantiate correctly
- **Committed in:** `aebdc0b` (fix commit after task commits)

---

**Total deviations:** 1 auto-fixed (1 missing critical for self-containment)
**Impact on plan:** Essential for meeting the plan's self-containment requirement. No behavior change for callers who provide text (which is the normal case).

## Issues Encountered

None beyond the planned deviation above.

## User Setup Required

None - no external service configuration required. Engines use existing config.txt keys (INDEXTTS_*, QWEN3TTS_*).

## Next Phase Readiness

- Both engine implementations complete and verified
- Ready for Plan 03: Engine factory (create_engine function) to wire engines together
- dubbing.py still contains original logic (not yet modified) - will be updated in Plan 03 to use the factory

---
*Phase: 01-refactor-tts-engine-architecture*
*Completed: 2026-04-11*

## Self-Check: PASSED

- All created files verified: indextts_engine.py, qwen3tts_engine.py, SUMMARY.md
- All commits verified: 1ad9477, 325066d, aebdc0b, 60180d2
