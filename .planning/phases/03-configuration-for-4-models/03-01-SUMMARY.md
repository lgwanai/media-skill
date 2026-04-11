# SUMMARY: 03-01 Update config.txt

**Status:** Complete
**Plan:** `.planning/phases/03-configuration-for-4-models/03-01-PLAN.md`
**Executed:** 2026-04-11

---

## What Was Built

Updated `config.txt` with LongCat-AudioDiT and OmniVoice configuration sections, following the existing pattern from IndexTTS and Qwen3-TTS.

### Changes Made

1. **TTS_ENGINE comment** updated to list all 4 engines:
   - `indextts, qwen3-tts, longcat-audiodit, omnivoice`

2. **LongCat-AudioDiT section** added:
   - `LONGCAT_MODEL_NAME = meituan-longcat/LongCat-AudioDiT-1B`
   - `LONGCAT_STEPS = 16`
   - `LONGCAT_CFG_STRENGTH = 4.0`
   - Note: Local-only, no API mode

3. **OmniVoice section** added:
   - `OMNIVOICE_MODEL_NAME = k2-fsa/OmniVoice`
   - `OMNIVOICE_NUM_STEP = 32`
   - `OMNIVOICE_GUIDANCE_SCALE = 2.0`
   - Note: Local-only, 600+ languages

---

## Verification

```
✓ LONGCAT_MODEL_NAME present
✓ LONGCAT_STEPS present
✓ LONGCAT_CFG_STRENGTH present
✓ OMNIVOICE_MODEL_NAME present
✓ OMNIVOICE_NUM_STEP present
✓ OMNIVOICE_GUIDANCE_SCALE present
✓ TTS_ENGINE comment lists all 4 engines
```

---

## Note

`config.txt` is in `.gitignore` (contains sensitive API keys). Changes are local only.

---

## Requirements Addressed

- **CONFIG-01**: LongCat-AudioDiT config section ✓
- **CONFIG-02**: OmniVoice config section ✓
- **MODEL-03**: TTS_ENGINE lists all 4 options ✓
