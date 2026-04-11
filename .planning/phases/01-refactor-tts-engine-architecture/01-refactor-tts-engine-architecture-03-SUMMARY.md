---
phase: 01
plan: 03
subsystem: tts-engines
tags: [factory-pattern, pluggable-architecture, lazy-imports, dubbing-refactor]
dependency:
  requires: []
  provides: [engine-factory, engine-validation, dubbing-refactor]
  affects: [dubbing-py]
tech-stack:
  added: []
  patterns: [factory-method, lazy-imports, type-checking-imports, strategy-pattern]
key-files:
  created:
    - scripts/tts_engines/factory.py
  modified:
    - scripts/tts_engines/__init__.py
    - scripts/tts_engines/factory.py
    - scripts/dubbing.py
decisions:
  - Used lazy imports inside create_engine() to avoid circular imports
  - Removed __getattr__ pattern from __init__.py in favor of direct imports
  - Kept TYPE_CHECKING imports for IDE autocomplete support
  - Changed tts_engines imports from `scripts.tts_engines.*` to `tts_engines.*` to support both script and module execution modes
  - Removed 402 lines of engine-specific code from dubbing.py, replaced with 69 lines of factory-based delegation
metrics:
  duration: ~2min
  completed: "2026-04-11T12:00:00Z"
  tasks: 3
  commits: 3
---

# Phase 01 Plan 03: Create Engine Factory + Refactor dubbing.py

**One-liner:** Factory module with `create_engine()`, `get_supported_engines()`, and `is_valid_engine()` for pluggable TTS architecture, plus full refactor of dubbing.py to use the factory pattern, removing all engine-specific if/else chains.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Create factory.py | `bf57b67` | `scripts/tts_engines/factory.py` |
| 2 | Update __init__.py | `3d7427b` | `scripts/tts_engines/__init__.py` |
| 3 | Refactor dubbing.py to use factory | `1245490` | `scripts/dubbing.py`, `scripts/tts_engines/__init__.py`, `scripts/tts_engines/factory.py` |

## Task 3: Refactor dubbing.py Details

### What was deleted from dubbing.py (402 lines removed):
- `get_local_tts_model()` — replaced by `IndexTTSEngine.load_model()`
- `synthesize_speech_local()` — replaced by `IndexTTSEngine._synthesize_local()`
- `get_qwen3tts_model()` — replaced by `Qwen3TTSEngine.load_model()`
- `synthesize_speech_qwen3tts()` — replaced by `Qwen3TTSEngine.synthesize()`
- Global variables: `_local_tts_model`, `_tts_model_lock`, `_tts_infer_lock`, `qwen_tts_model_cache`
- `threading` import (no longer needed at module level)
- All engine-specific if/else branches in `clone_voice()` and `synthesize_speech()`

### What was refactored:
- `synthesize_speech()` — replaced engine branches with `create_engine(config).synthesize()`
- `clone_voice()` — replaced engine branches with `create_engine(config).clone_voice()`
- `main()` engine validation — replaced with `is_valid_engine()` + `get_supported_engines()`
- Import paths in `tts_engines/__init__.py` and `factory.py` changed from `scripts.tts_engines.*` to `tts_engines.*` for dual-mode compatibility

### What was preserved (unchanged):
- All CLI commands, arguments, help text
- All user-facing print messages
- All non-TTS functions: `split_text_into_paragraphs_and_sentences()`, `synthesize_worker()`, `dub_text()`, `analyze_text_for_tts_params()`, `parse_time()`, `parse_srt()`, `auto_transcribe_audio()`, `get_voices_dir()`, `get_saved_voices()`, `migrate_old_voices_json()`, `dub_subtitle()`, `main()`

## Verification

- Factory imports OK: `create_engine`, `get_supported_engines`, `is_valid_engine` all importable
- Engine validation OK: `is_valid_engine('indextts')` returns True, `is_valid_engine('invalid')` returns False
- Error handling OK: `create_engine({'TTS_ENGINE': 'invalid'})` raises ValueError with "Unsupported TTS engine" message
- Module import OK: `python -c "import scripts.dubbing; print('Module import OK')"` passes
- CLI clone subcommand OK: `python scripts/dubbing.py --help` shows "clone"
- CLI dub subcommand OK: `python scripts/dubbing.py --help` shows "dub"
- Net lines removed: 402 deleted, 69 added = -333 lines

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed import path compatibility for dual execution modes**
- **Found during:** Task 3 verification
- **Issue:** `tts_engines/__init__.py` and `factory.py` used `scripts.tts_engines.*` absolute imports, which fail when running `python scripts/dubbing.py` directly (since `scripts/` is added to sys.path but `scripts` package isn't on the path)
- **Fix:** Changed all imports in `__init__.py` and `factory.py` from `scripts.tts_engines.*` to `tts_engines.*` to work in both modes
- **Files modified:** `scripts/tts_engines/__init__.py`, `scripts/tts_engines/factory.py`
- **Commit:** `1245490`

## Self-Check: PASSED
