---
phase: 01-refactor-tts-engine-architecture
plan: 03
type: execute
wave: 3
depends_on:
  - 01-refactor-tts-engine-architecture-02
files_modified:
  - scripts/tts_engines/factory.py
  - scripts/tts_engines/__init__.py
  - scripts/dubbing.py
autonomous: true
requirements:
  - CODE-01
  - CODE-03
  - CODE-04
  - PERF-03

must_haves:
  truths:
    - "create_engine(config) returns correct engine based on TTS_ENGINE config value"
    - "scripts/dubbing.py uses engine factory instead of inline if/else engine selection"
    - "Existing CLI commands (clone, dub) work without any changes to command-line interface"
    - "Invalid TTS_ENGINE config value produces clear error message"
  artifacts:
    - path: "scripts/tts_engines/factory.py"
      provides: "Engine factory function"
      exports: ["create_engine"]
    - path: "scripts/dubbing.py"
      provides: "Refactored dubbing script using engine architecture"
      contains: "from scripts.tts_engines import create_engine"
  key_links:
    - from: "scripts/dubbing.py"
      to: "scripts/tts_engines/factory.py"
      via: "create_engine() call"
      pattern: "create_engine\\(config\\)"
    - from: "scripts/tts_engines/__init__.py"
      to: "scripts/tts_engines/factory.py"
      via: "lazy import of create_engine"
      pattern: "from .factory import create_engine"
---

<objective>
Create the engine factory function and refactor dubbing.py to use the new pluggable architecture, completing the refactoring while preserving full backward compatibility.

Purpose: Routes engine selection via factory (CODE-01), removes monolithic if/else chains from dubbing.py (CODE-03), and ensures existing functionality is preserved (CODE-04, PERF-03).
Output: factory.py and refactored dubbing.py
</objective>

<execution_context>
@/Users/wuliang/.config/opencode/get-shit-done/workflows/execute-plan.md
@/Users/wuliang/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/01-refactor-tts-engine-architecture/01-refactor-tts-engine-architecture-01-SUMMARY.md
@.planning/phases/01-refactor-tts-engine-architecture/01-refactor-tts-engine-architecture-02-SUMMARY.md
@scripts/dubbing.py — file to refactor (keep CLI, text analysis, SRT parsing, audio merging)
@scripts/tts_engines/base.py — TTSEngine interface
@scripts/tts_engines/indextts_engine.py — IndexTTS engine implementation
@scripts/tts_engines/qwen3tts_engine.py — Qwen3-TTS engine implementation
</context>

<tasks>

<task type="auto">
  <name>Create engine factory function</name>
  <files>scripts/tts_engines/factory.py</files>
  <action>
    Create scripts/tts_engines/factory.py with:

    1. **create_engine(config: dict) -> TTSEngine:**
       - Reads TTS_ENGINE from config (default: "indextts")
       - Supported values: "indextts", "qwen3-tts"
       - Returns appropriate engine instance:
         - "indextts" → IndexTTSEngine(config)
         - "qwen3-tts" → Qwen3TTSEngine(config)
       - Raises ValueError with message: "Unsupported TTS engine: '{engine}'. Supported: indextts, qwen3-tts"

    2. **get_supported_engines() -> list[str]:**
       - Returns ["indextts", "qwen3-tts"]
       - Used for config validation and CLI help text

    3. **is_valid_engine(engine: str) -> bool:**
       - Returns True if engine is in supported list

    Update scripts/tts_engines/__init__.py:
    - Replace the lazy import __getattr__ with direct import: `from .factory import create_engine, get_supported_engines, is_valid_engine`
    - Update __all__ to include the new exports

    Do NOT modify dubbing.py in this task.
  </action>
  <verify>
    python -c "
    from scripts.tts_engines import create_engine, get_supported_engines, is_valid_engine
    engines = get_supported_engines()
    assert 'indextts' in engines
    assert 'qwen3-tts' in engines
    assert is_valid_engine('indextts')
    assert not is_valid_engine('invalid')
    print('Factory imports OK')
    "
    python -c "
    from scripts.tts_engines import create_engine
    try:
        create_engine({'TTS_ENGINE': 'invalid'})
        assert False, 'Should have raised ValueError'
    except ValueError as e:
        assert 'Unsupported TTS engine' in str(e)
        print('Error handling OK')
    "
  </verify>
  <done>create_engine() returns correct engine instance based on TTS_ENGINE config. Invalid engine names raise ValueError with helpful message. get_supported_engines() and is_valid_engine() work correctly.</done>
</task>

<task type="auto">
  <name>Refactor dubbing.py to use engine architecture</name>
  <files>scripts/dubbing.py</files>
  <action>
    Refactor scripts/dubbing.py to use the new pluggable architecture. Key changes:

    1. **Add imports at top:**
       ```python
       from scripts.tts_engines import create_engine, EmotionParser
       ```

    2. **Remove engine-specific functions (moved to engine classes):**
       - DELETE: `get_local_tts_model()` — replaced by IndexTTSEngine.load_model()
       - DELETE: `synthesize_speech_local()` — replaced by IndexTTSEngine._synthesize_local()
       - DELETE: `get_qwen3tts_model()` — replaced by Qwen3TTSEngine.load_model()
       - DELETE: `synthesize_speech_qwen3tts()` — replaced by Qwen3TTSEngine.synthesize()
       - DELETE: Global variables: `_local_tts_model`, `_tts_model_lock`, `_tts_infer_lock`, `qwen_tts_model_cache`
       - DELETE: `threading` import (no longer needed at module level)

    3. **Refactor synthesize_speech() (lines 956-1050):**
       Replace the entire function body with:
       ```python
       def synthesize_speech(api_key, text, voice_id, output_path, mode="api", model=None, tts_params=None, engine="indextts", config=None):
           if not config:
               config = load_config()
           # Override mode in config for this call
           if engine == "qwen3-tts":
               config["QWEN3TTS_MODE"] = mode
               if model:
                   config["QWEN3TTS_MODEL_NAME"] = model
               if api_key:
                   config["QWEN3TTS_API_KEY"] = api_key
           else:
               config["INDEXTTS_MODE"] = mode
               if model:
                   config["INDEXTTS_MODEL_NAME"] = model
               if api_key:
                   config["INDEXTTS_API_KEY"] = api_key

           tts_engine = create_engine(config)
           return tts_engine.synthesize(text, voice_id, output_path, tts_params)
       ```

    4. **Refactor clone_voice() (lines 433-538):**
       Replace engine-specific branches with:
       ```python
       # In clone_voice(), after saving ref_audio and building meta dict:
       tts_engine = create_engine(config)
       return tts_engine.clone_voice(ref_audio_path, text, voice_name)
       ```
       Keep the directory setup, audio conversion, and meta.json saving logic that's before the engine-specific branches. Remove the indextts-specific and qwen3-tts-specific branches.

    5. **KEEP unchanged:**
       - `split_text_into_paragraphs_and_sentences()`
       - `synthesize_worker()`
       - `dub_text()`
       - `analyze_text_for_tts_params()`
       - `parse_time()`, `parse_srt()`
       - `auto_transcribe_audio()`
       - `get_voices_dir()`, `get_saved_voices()`
       - `migrate_old_voices_json()`
       - `dub_subtitle()`
       - `main()` and all CLI argument parsing
       - All print statements and user-facing messages

    6. **In main() function:** Keep the engine detection logic but simplify:
       ```python
       engine = config.get("TTS_ENGINE", "indextts").strip().lower()
       # Validate engine
       from scripts.tts_engines import is_valid_engine
       if not is_valid_engine(engine):
           print(f"错误: 不支持的 TTS 引擎: {engine}。支持的引擎: {', '.join(get_supported_engines())}")
           sys.exit(1)
       ```

    The refactored dubbing.py should be significantly shorter (~400-500 lines vs ~1200 lines) while maintaining identical CLI behavior.
  </action>
  <verify>
    python -c "import scripts.dubbing; print('Module import OK')"
    python scripts/dubbing.py --help 2>&1 | grep -q "clone" && echo "clone subcommand OK" || echo "FAIL"
    python scripts/dubbing.py --help 2>&1 | grep -q "dub" && echo "dub subcommand OK" || echo "FAIL"
  </verify>
  <done>dubbing.py uses create_engine() for all TTS operations. CLI interface unchanged (clone and dub subcommands work). Engine-specific code removed from dubbing.py. File is significantly shorter. All existing functionality preserved.</done>
</task>

</tasks>

<verification>
- factory.py exists with create_engine, get_supported_engines, is_valid_engine
- __init__.py exports all factory functions
- dubbing.py imports from scripts.tts_engines (no engine-specific functions remain)
- `python scripts/dubbing.py --help` shows clone and dub subcommands
- Engine factory returns correct engine for "indextts" and "qwen3-tts"
- Invalid engine name raises ValueError with helpful message
- dubbing.py line count reduced from ~1200 to ~400-500 lines
- No behavior changes: same CLI arguments, same output format, same error messages
</verification>

<success_criteria>
- Engine factory correctly routes TTS_ENGINE config to appropriate engine class
- dubbing.py is refactored to use engine architecture without behavior changes
- CLI interface is 100% backward compatible (same commands, same arguments)
- Engine-specific code is fully isolated in engine modules (no if/else chains in dubbing.py)
- Multi-threaded synthesis works through engine locks
- Invalid engine config produces clear error message
</success_criteria>

<output>
After completion, create `.planning/phases/01-refactor-tts-engine-architecture/01-refactor-tts-engine-architecture-03-SUMMARY.md`
</output>
