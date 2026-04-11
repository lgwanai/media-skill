---
phase: 01-refactor-tts-engine-architecture
plan: 01
subsystem: infra
tags: [abc, abstract-base-class, python, emotion-parsing, refactoring]

# Dependency graph
requires: []
provides:
  - TTSEngine abstract base class with 4 abstract methods + name property
  - EmotionParser utility for [情绪:强度] tag parsing
  - scripts/tts_engines/ package structure ready for engine implementations
affects:
  - 01-refactor-tts-engine-architecture-02 (IndexTTSEngine implementation)
  - 01-refactor-tts-engine-architecture-03 (Engine factory)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - ABC-based interface contract for pluggable engines
    - Lazy import via __getattr__ for forward references
    - Compiled regex patterns for emotion tag parsing

key-files:
  created:
    - scripts/tts_engines/base.py
    - scripts/tts_engines/__init__.py
  modified: []

key-decisions:
  - "EmotionParser uses last-valid-tag semantics for emotion_to_vector, matching original dubbing.py behavior"
  - "Module-level docstring removed from base.py to avoid redundancy with __init__.py package docstring"

patterns-established:
  - "ABC with @abstractmethod for engine contract enforcement"
  - "Classmethod utility pattern for stateless parsers"
  - "Compiled regex constants for reuse across method calls"

requirements-completed:
  - CODE-01
  - CODE-02

# Metrics
duration: 3min
completed: 2026-04-11
---

# Phase 01 Plan 01: TTSEngine Abstract Base Class and EmotionParser Summary

**TTSEngine ABC with 4 abstract methods (load_model, clone_voice, synthesize, get_emotion_params) and EmotionParser utility extracting emotion tag logic from dubbing.py**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-11T00:00:00Z
- **Completed:** 2026-04-11T00:03:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created TTSEngine abstract base class enforcing interface contract via ABC
- Extracted emotion parsing logic from dubbing.py into reusable EmotionParser utility
- Established scripts/tts_engines/ package with proper exports and lazy import pattern

## Task Commits

Each task was committed atomically:

1. **Task 1: Create TTSEngine abstract base class** - `e3e3d73` (feat)
2. **Task 2: Create tts_engines package init** - `3f0df8b` (feat)

## Files Created/Modified

- `scripts/tts_engines/base.py` - TTSEngine ABC and EmotionParser utility class
- `scripts/tts_engines/__init__.py` - Package init with exports and lazy import for create_engine

## Decisions Made

- EmotionParser.emotion_to_vector() uses last-valid-tag semantics (matching original dubbing.py behavior where only the final emotion tag sets the emo_vector)
- Removed redundant module-level docstring from base.py since __init__.py provides the package docstring

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- scripts/tts_engines/ package structure established and verified
- TTSEngine interface contract ready for IndexTTSEngine and Qwen3TTSEngine implementations (Plan 02)
- Lazy import for create_engine set up, ready for factory implementation (Plan 03)

---
*Phase: 01-refactor-tts-engine-architecture*
*Completed: 2026-04-11*
