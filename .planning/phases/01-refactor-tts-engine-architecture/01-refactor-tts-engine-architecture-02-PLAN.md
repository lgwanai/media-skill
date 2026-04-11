---
phase: 01-refactor-tts-engine-architecture
plan: 02
type: execute
wave: 2
depends_on:
  - 01-refactor-tts-engine-architecture-01
files_modified:
  - scripts/tts_engines/indextts_engine.py
  - scripts/tts_engines/qwen3tts_engine.py
autonomous: true
requirements:
  - CODE-02
  - CODE-03
  - CODE-04
  - PERF-03

must_haves:
  truths:
    - "IndexTTSEngine can be instantiated and used independently of Qwen3TTSEngine"
    - "Qwen3TTSEngine can be instantiated and used independently of IndexTTSEngine"
    - "Both engines implement the TTSEngine interface with identical method signatures"
    - "Multi-threaded synthesis is safe (uses proper locking for model loading and inference)"
  artifacts:
    - path: "scripts/tts_engines/indextts_engine.py"
      provides: "IndexTTS-2 engine implementation"
      exports: ["IndexTTSEngine"]
    - path: "scripts/tts_engines/qwen3tts_engine.py"
      provides: "Qwen3-TTS engine implementation"
      exports: ["Qwen3TTSEngine"]
  key_links:
    - from: "scripts/tts_engines/indextts_engine.py"
      to: "scripts/tts_engines/base.py"
      via: "class inheritance"
      pattern: "class IndexTTSEngine\\(TTSEngine\\)"
    - from: "scripts/tts_engines/qwen3tts_engine.py"
      to: "scripts/tts_engines/base.py"
      via: "class inheritance"
      pattern: "class Qwen3TTSEngine\\(TTSEngine\\)"
---

<objective>
Extract IndexTTS-2 and Qwen3-TTS logic from dubbing.py into separate engine classes that implement the TTSEngine interface, preserving all existing functionality.

Purpose: Isolates engine-specific code into separate modules (CODE-03) while preserving backward compatibility (CODE-04) and multi-threading safety (PERF-03).
Output: Two engine files implementing the TTSEngine interface
</objective>

<execution_context>
@/Users/wuliang/.config/opencode/get-shit-done/workflows/execute-plan.md
@/Users/wuliang/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/01-refactor-tts-engine-architecture/01-refactor-tts-engine-architecture-01-PLAN.md
@.planning/phases/01-refactor-tts-engine-architecture/01-refactor-tts-engine-architecture-01-SUMMARY.md
@scripts/dubbing.py — source of all TTS logic to extract (lines 433-1050)
@scripts/tts_engines/base.py — TTSEngine interface to implement
</context>

<tasks>

<task type="auto">
  <name>Extract IndexTTS-2 engine implementation</name>
  <files>scripts/tts_engines/indextts_engine.py</files>
  <action>
    Create scripts/tts_engines/indextts_engine.py with IndexTTSEngine class:

    1. **Class structure:**
       ```python
       class IndexTTSEngine(TTSEngine):
           def __init__(self, config: dict):
               super().__init__(config)
               self._model = None
               self._model_lock = threading.Lock()
               self._infer_lock = threading.Lock()
       ```

    2. **load_model()** — extracted from get_local_tts_model() (dubbing.py lines 826-881):
       - Downloads model via modelscope snapshot_download if needed
       - Tries indextts.infer_v2.IndexTTS2 first, falls back to indextts.infer.IndexTTS
       - Stores model in self._model with thread-safe locking
       - Reads INDEXTTS_MODE from config: "local" loads model, "api" skips model loading
       - Handles missing indextts package with helpful error message

    3. **clone_voice()** — extracted from clone_voice() (dubbing.py lines 433-538, indextts branch):
       - Saves ref_audio to data/voices/NAME/ref_audio.wav
       - For local mode: extracts and persists .pt feature file (trigger dummy inference)
       - For API mode: uploads to siliconflow, gets voice URI
       - Returns "local:ref_audio_path" or "api:voice_uri"
       - Saves meta.json with name, text, mode, engine="indextts", local_audio, uri (if API)

    4. **synthesize()** — extracted from synthesize_speech() indextts branch (dubbing.py lines 956-1050):
       - Uses EmotionParser.parse_emotion_tags() to parse emotion tags from text
       - For local mode: calls synthesize_speech_local() logic with _infer_lock
       - For API mode: POST to INDEXTTS_URL with model, input, voice, response_format
       - Preserves all audio post-processing: fade in/out, DC offset removal, soft clipping
       - Returns True/False

    5. **get_emotion_params()** — uses EmotionParser to parse tags, returns (tts_params, clean_text):
       - Parses [情绪:强度] tags into emo_vector
       - Strips all bracket content from text
       - Returns dict with emo_vector key (if found) and cleaned text

    6. **name property** — returns "indextts"

    7. **Private helper _synthesize_local()** — extracted from synthesize_speech_local() (dubbing.py lines 883-954):
       - Uses _infer_lock for thread safety
       - Handles both v2 and v1 IndexTTS interfaces
       - Applies audio post-processing (librosa load, pydub export)

    Do NOT modify dubbing.py in this task. Only create the new engine file.
    Preserve ALL existing behavior: API endpoints, error handling, audio processing, lock usage.
  </action>
  <verify>
    python -c "from scripts.tts_engines.indextts_engine import IndexTTSEngine; print('Import OK')"
    python -c "
    from scripts.tts_engines.indextts_engine import IndexTTSEngine
    from scripts.tts_engines.base import TTSEngine
    assert issubclass(IndexTTSEngine, TTSEngine), 'Must inherit TTSEngine'
    engine = IndexTTSEngine({'TTS_ENGINE': 'indextts', 'INDEXTTS_MODE': 'api'})
    assert engine.name == 'indextts'
    print('Interface compliance OK')
    "
  </verify>
  <done>IndexTTSEngine implements all TTSEngine abstract methods. Local and API modes work. Emotion parsing integrated. Thread-safe with model and infer locks. No behavior changes from original dubbing.py implementation.</done>
</task>

<task type="auto">
  <name>Extract Qwen3-TTS engine implementation</name>
  <files>scripts/tts_engines/qwen3tts_engine.py</files>
  <action>
    Create scripts/tts_engines/qwen3tts_engine.py with Qwen3TTSEngine class:

    1. **Class structure:**
       ```python
       class Qwen3TTSEngine(TTSEngine):
           def __init__(self, config: dict):
               super().__init__(config)
               self._model = None
               self._model_lock = threading.Lock()
               self._infer_lock = threading.Lock()
       ```

    2. **load_model()** — extracted from get_qwen3tts_model() (dubbing.py lines 550-569):
       - Reads QWEN3TTS_MODE from config: "local" loads model, "api" skips
       - For local: imports qwen_tts.Qwen3TTSModel, loads with torch (cuda/mps/cpu)
       - Uses bfloat16 for GPU, float32 for CPU
       - Stores in self._model with thread-safe locking

    3. **clone_voice()** — extracted from clone_voice() (dubbing.py lines 466-474, qwen3-tts branch):
       - Saves ref_audio to data/voices/NAME/ref_audio.wav
       - Qwen3-TTS supports zero-shot inference, no feature extraction needed
       - Returns "qwen:ref_audio_path"
       - Saves meta.json with name, text, mode, engine="qwen3-tts", local_audio

    4. **synthesize()** — extracted from synthesize_speech_qwen3tts() (dubbing.py lines 571-821):
       - For local mode: uses qwen_model.generate_voice_clone() or generate_custom_voice()
       - For API mode: uses dashscope.MultiModalConversation.call()
       - Preserves ALL audio post-processing:
         - Silence detection and truncation (800ms threshold)
         - Fade out for trailing noise
         - DC offset removal
         - Soft clipping via tanh ([-0.95, 0.95])
         - int16 PCM conversion
         - soundfile save with PCM_16, fallback to pydub
       - Uses _infer_lock for thread safety

    5. **get_emotion_params()** — Qwen3-TTS doesn't use IndexTTS emo_vector:
       - Still uses EmotionParser to strip emotion tags from text
       - Returns empty params dict + cleaned text
       - Tags are parsed but not converted to emo_vector (Qwen3-TTS handles emotion differently)

    6. **name property** — returns "qwen3-tts"

    7. **Private helpers:**
       - _synthesize_local(): local model inference with full audio post-processing
       - _synthesize_api(): dashscope API call with MultiModalConversation

    Do NOT modify dubbing.py in this task. Only create the new engine file.
    Preserve ALL existing behavior including the complex audio post-processing pipeline.
  </action>
  <verify>
    python -c "from scripts.tts_engines.qwen3tts_engine import Qwen3TTSEngine; print('Import OK')"
    python -c "
    from scripts.tts_engines.qwen3tts_engine import Qwen3TTSEngine
    from scripts.tts_engines.base import TTSEngine
    assert issubclass(Qwen3TTSEngine, TTSEngine), 'Must inherit TTSEngine'
    engine = Qwen3TTSEngine({'TTS_ENGINE': 'qwen3-tts', 'QWEN3TTS_MODE': 'api'})
    assert engine.name == 'qwen3-tts'
    print('Interface compliance OK')
    "
  </verify>
  <done>Qwen3TTSEngine implements all TTSEngine abstract methods. Local and API modes work. Full audio post-processing preserved (silence truncation, DC offset, soft clipping). Thread-safe. No behavior changes from original.</done>
</task>

</tasks>

<verification>
- Both engine files exist and are syntactically valid Python
- Both classes inherit from TTSEngine and implement all abstract methods
- Both engines can be instantiated with a config dict
- No circular imports between engine files
- Engine files do NOT import from dubbing.py (all logic is self-contained)
- Thread safety: each engine has its own _model_lock and _infer_lock
- Multi-threaded synthesis is safe (locks protect model loading and inference)
</verification>

<success_criteria>
- IndexTTSEngine and Qwen3TTSEngine both implement TTSEngine interface
- All existing functionality preserved: clone_voice, synthesize (local + API), emotion handling
- Audio post-processing pipelines are identical to original dubbing.py behavior
- Each engine is self-contained (no imports from dubbing.py)
- Thread-safe: proper locking for model loading and inference
- Both engines handle their respective config keys (INDEXTTS_*, QWEN3TTS_*)
</success_criteria>

<output>
After completion, create `.planning/phases/01-refactor-tts-engine-architecture/01-refactor-tts-engine-architecture-02-SUMMARY.md`
</output>
