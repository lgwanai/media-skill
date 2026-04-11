---
phase: 06-voice-control-methods-instruct-based-and-tag-based-synthesis-control
plan: 01
subsystem: tts-engine-interface
tags: [tts, voice-control, instruct, abstract-base-class, markdown-config]

# Dependency graph
requires: []
provides:
  - "TTSEngine base class with instruct parameter support"
  - "supports_instruct property for engine capability detection"
  - "Documented markdown voice config file format"
affects: [engine-implementations, voice-profiles]

# Tech tracking
tech-stack:
  added: []
  patterns: [abstract-method-signature-extension, capability-detection-property]

key-files:
  created: [docs/voice-config-format.md]
  modified: [scripts/tts_engines/base.py]

key-decisions:
  - "Made instruct parameter optional (str | None) to maintain backward compatibility"
  - "Added supports_instruct abstract property for runtime capability detection"
  - "Documented warning behavior for unsupported engines in config format spec"

patterns-established:
  - "Optional parameter extension: New parameters added with None default to avoid breaking existing implementations"
  - "Capability detection: Abstract properties (supports_emotion, supports_instruct) for feature flagging"

requirements-completed: [CTRL-02]

# Metrics
duration: 3min
completed: 2026-04-11
---

# Phase 06 Plan 01: Voice Control Interface Definition Summary

**TTSEngine base class extended with instruct parameter and supports_instruct property; markdown voice config format documented with compatibility matrix**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-11T15:21:20Z
- **Completed:** 2026-04-11T15:24:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Updated TTSEngine.synthesize() abstract method signature with optional `instruct` parameter
- Added `supports_instruct` abstract property for engine capability detection
- Created comprehensive markdown voice config format specification in docs/voice-config-format.md

## Task Commits

Each task was committed atomically:

1. **Task 1: Add instruct parameter to TTSEngine.synthesize()** - `58be937` (feat)
2. **Task 2: Define markdown voice config file format** - `9f1f54c` (feat)

## Files Created/Modified
- `scripts/tts_engines/base.py` - Added instruct parameter to synthesize() and supports_instruct property
- `docs/voice-config-format.md` - Complete voice config format specification with examples

## Decisions Made
- Made `instruct` parameter optional (`str | None`) to maintain backward compatibility with existing engine implementations
- Added `supports_instruct` as an abstract property (not a method) for consistency with existing `supports_emotion` pattern
- Documented warning behavior for unsupported engines to ensure users understand fallback behavior

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Base class interface ready for engine implementations to add instruct support
- OmniVoice engine should implement supports_instruct returning True
- Other engines (indextts, qwen3-tts, longcat-audiodit) should implement supports_instruct returning False
- Voice profiles can now be created using the documented config.md format

---
*Phase: 06-voice-control-methods-instruct-based-and-tag-based-synthesis-control*
*Completed: 2026-04-11*
