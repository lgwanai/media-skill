# SUMMARY: 02-03 Engine Factory Registration

**Status:** Complete
**Plan:** `.planning/phases/02-integrate-longcat-audiodit-and-omnivoice-models/02-03-PLAN.md`
**Executed:** 2026-04-11

---

## What Was Built

Updated engine factory and package exports to register LongCat-AudioDiT and OmniVoice engines.

### Key Artifacts

| Path | Purpose |
|------|---------|
| `scripts/tts_engines/factory.py` | Factory with 4 engine registrations |
| `scripts/tts_engines/__init__.py` | Package exports for both new engines |

### Changes Made

1. **SUPPORTED_ENGINES** updated: `["indextts", "qwen3-tts", "longcat-audiodit", "omnivoice"]`
2. **create_engine()** branches added for both new engines
3. **__init__.py** exports both engine classes
4. **is_valid_engine()** now accepts all 4 engine names

---

## Verification

```
✓ SUPPORTED_ENGINES contains all 4 engine names
✓ is_valid_engine("longcat-audiodit") returns True
✓ is_valid_engine("omnivoice") returns True
✓ Invalid engine names raise ValueError with helpful message
✓ Both engines importable: from tts_engines import LongCatAudioDiTEngine, OmniVoiceEngine
```

---

## Commits

| Hash | Message |
|------|---------|
| `83eea32` | feat(02): add LongCat-AudioDiT and OmniVoice engine implementations |

---

## Requirements Addressed

- **MODEL-01**: LongCat-AudioDiT selectable via TTS_ENGINE config ✓
- **MODEL-02**: OmniVoice selectable via TTS_ENGINE config ✓

---

## Self-Check: PASSED

- [x] Factory updated with new engines
- [x] SUPPORTED_ENGINES list complete
- [x] Both engines import correctly
- [x] Invalid engine handling works
