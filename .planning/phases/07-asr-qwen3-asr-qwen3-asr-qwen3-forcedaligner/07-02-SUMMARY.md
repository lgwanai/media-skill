---
phase: 07-asr-qwen3-asr-qwen3-asr-qwen3-forcedaligner
plan: 02
status: complete
completed: 2026-04-12
---

# Summary: FunASR Engine Adapter

## What Was Built

FunASREngine adapter wrapping existing FunASR transcription logic into the ASREngine interface.

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `scripts/asr_engines/funasr_engine.py` | 175 | FunASREngine class with Paraformer + VAD + PUNC + SPK pipeline |

## Key Decisions

1. **ERes2Net registration**: Preserved ERes2NetAugWrapper for FunASR 1.x compatibility
2. **VAD parameters**: Maintained original settings (max_single_segment_time=15000, max_end_silence_time=400)
3. **Timestamp conversion**: Converted milliseconds to seconds in TranscriptionResult
4. **Speaker labels**: Included speaker labels in text output for backward compatibility

## Verification

- FunASREngine inherits from ASREngine
- All abstract methods implemented
- Audio preprocessing works for video files
- TranscriptionResult format matches base class

## Self-Check

✓ PASSED