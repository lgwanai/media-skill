---
phase: 07-asr-qwen3-asr-qwen3-asr-qwen3-forcedaligner
plan: 04
status: complete
completed: 2026-04-12
---

# Summary: transcribe.py Refactored

## What Was Built

Refactored transcribe.py to use the pluggable ASR engine architecture.

### Files Modified

| File | Changes |
|------|---------|
| `scripts/transcribe.py` | Removed direct FunASR imports, added factory-based engine creation |

## Changes Summary

1. **Imports**: Replaced `from funasr import AutoModel` with `from asr_engines.factory import create_asr_engine`
2. **Engine creation**: `engine = create_asr_engine(config)` routes to correct engine
3. **Transcription**: `result = engine.transcribe(audio_path, return_timestamps=True)`
4. **Legacy conversion**: `_convert_result_to_legacy()` maintains backward compatibility

## Key Decisions

1. **Backward compatibility**: Legacy format conversion ensures existing output generation code works
2. **Vocab integration**: vocab_utils.apply_vocab_to_result() preserved
3. **MD5 caching**: Unchanged - works for both engines
4. **Output formats**: JSON, SRT, TXT generation unchanged

## Verification

- transcribe.py uses create_asr_engine() to get engine based on config
- Legacy format conversion ensures output compatibility
- MD5 caching, vocab application, SRT/TXT generation unchanged
- ASR_ENGINE=funasr produces identical output to previous version

## Self-Check

✓ PASSED