---
phase: 06-voice-control-methods-instruct-based-and-tag-based-synthesis-control
plan: 03
subsystem: tts-engines
tags: [tts, instruct, warning, emotion-tags, base-class]

# Dependency graph
requires:
  - phase: 06-01
    provides: "OmniVoice engine with instruct support"
provides:
  - "Warning mechanism for unsupported instruct usage across all non-OmniVoice engines"
  - "Default supports_instruct=False in TTSEngine base class"
  - "Consistent instruct parameter in synthesize() signature for all engines"
affects: ["future engine additions", "user-facing TTS API"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Default capability flags in ABC with per-engine overrides"
    - "Consistent warning helper pattern for unsupported features"

key-files:
  created: []
  modified:
    - scripts/tts_engines/base.py
    - scripts/tts_engines/indextts_engine.py
    - scripts/tts_engines/qwen3tts_engine.py
    - scripts/tts_engines/longcat_audiodit_engine.py

key-decisions:
  - "Changed supports_instruct from @abstractmethod to default property returning False"
  - "Warning helper placed in base class for consistent messaging across engines"

patterns-established:
  - "ABC provides default capability flags; only engines with actual support override to True"
  - "Engines call _warn_unsupported_instruct() when optional parameters are ignored"

requirements-completed: ["CTRL-04"]

# Metrics
duration: 5min
completed: 2026-04-11
---

# Phase 06 Plan 03: Warning Mechanism for Unsupported Instruct Usage

**Warning mechanism for instruct parameter on non-OmniVoice engines with default capability flags in TTSEngine base class**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-11T10:30:00Z
- **Completed:** 2026-04-11T10:35:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Added `_warn_unsupported_instruct()` helper to TTSEngine base class for consistent warning messages
- Changed `supports_instruct` from abstract property to default implementation returning False
- Updated IndexTTS, Qwen3-TTS, and LongCat-AudioDiT engines to accept `instruct` parameter and log warning when provided
- Verified tag handling consistency: IndexTTS parses emotion tags, Qwen3-TTS and LongCat strip all brackets

## Task Commits

Each task was committed atomically:

1. **Task 1: Add warning helper to TTSEngine base class** - `696b857` (feat)
2. **Task 2: Update IndexTTS, Qwen3-TTS, LongCat engines with warning** - `4cad996` (feat)
3. **Task 3: Verify tag handling consistency** - verification only, no code changes

## Files Created/Modified

- `scripts/tts_engines/base.py` - Added `_warn_unsupported_instruct()` helper, changed `supports_instruct` to default False
- `scripts/tts_engines/indextts_engine.py` - Added `instruct` param to synthesize(), warns when provided
- `scripts/tts_engines/qwen3tts_engine.py` - Added `instruct` param to synthesize(), warns when provided
- `scripts/tts_engines/longcat_audiodit_engine.py` - Added `instruct` param to synthesize(), warns when provided

## Decisions Made

None - followed plan as specified.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

All non-OmniVoice engines now clearly indicate `supports_instruct=False` and warn users when instruct is provided. Tag handling is consistent per engine capabilities. Ready for next phase.

---
*Phase: 06-voice-control-methods-instruct-based-and-tag-based-synthesis-control*
*Completed: 2026-04-11*
