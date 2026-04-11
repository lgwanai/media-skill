---
phase: 01-refactor-tts-engine-architecture
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - scripts/tts_engines/__init__.py
  - scripts/tts_engines/base.py
autonomous: true
requirements:
  - CODE-01
  - CODE-02

must_haves:
  truths:
    - "TTSEngine abstract base class can be imported from scripts.tts_engines"
    - "TTSEngine defines clone_voice(), synthesize(), get_emotion_params(), load_model() as abstract methods"
    - "EmotionParser utility parses [情绪:强度] tags into unified dict format"
  artifacts:
    - path: "scripts/tts_engines/__init__.py"
      provides: "Package init with TTSEngine and EmotionParser exports"
      exports: ["TTSEngine", "EmotionParser"]
    - path: "scripts/tts_engines/base.py"
      provides: "Abstract TTSEngine base class and EmotionParser utility"
      contains: "class TTSEngine(ABC)"
  key_links:
    - from: "scripts/tts_engines/base.py"
      to: "scripts/tts_engines/__init__.py"
      via: "import and re-export"
      pattern: "from .base import TTSEngine"
---

<objective>
Create the TTSEngine abstract base class and EmotionParser utility, establishing the common interface that all TTS engines will implement.

Purpose: Provides the contract (CODE-01, CODE-02) that IndexTTSEngine and Qwen3TTSEngine will implement in the next plan.
Output: scripts/tts_engines/ package with base.py and __init__.py
</objective>

<execution_context>
@/Users/wuliang/.config/opencode/get-shit-done/workflows/execute-plan.md
@/Users/wuliang/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@scripts/dubbing.py — extract emotion parsing logic (lines 966-1000) and understand current interface patterns
@scripts/utils.py — load_config() pattern for reference
</context>

<tasks>

<task type="auto">
  <name>Create TTSEngine abstract base class</name>
  <files>scripts/tts_engines/base.py</files>
  <action>
    Create scripts/tts_engines/base.py with:

    1. **TTSEngine abstract base class** (inherits ABC):
       - `__init__(self, config: dict)` — accepts config dict from load_config()
       - `load_model(self) -> None` — abstract, loads the TTS model (local or API setup)
       - `clone_voice(self, ref_audio: str, text: str, voice_name: str) -> str` — abstract, returns voice identifier string (format: "engine:reference")
       - `synthesize(self, text: str, voice_id: str, output_path: str, tts_params: dict | None = None) -> bool` — abstract, returns success boolean
       - `get_emotion_params(self, text: str) -> tuple[dict, str]` — abstract, parses emotion tags from text, returns (params_dict, cleaned_text)
       - `name(self) -> str` — property returning engine name (e.g., "indextts", "qwen3-tts")

    2. **EmotionParser utility class** (extracted from dubbing.py lines 966-984):
       - Class method `parse_emotion_tags(text: str) -> tuple[list[dict], str]` — parses [情绪:强度] tags, returns (parsed_tags, cleaned_text)
       - Class method `emotion_to_vector(tags: list[dict]) -> list[float] | None` — converts parsed tags to IndexTTS-style 8-element emo_vector
       - Supported emotions: ["高兴", "愤怒", "悲伤", "恐惧", "反感", "低落", "惊讶", "自然"]
       - Also strips all bracket content from text: [], 【】, <>, (), （）

    3. **Type hints** on all method signatures per project coding style.
    4. **Docstrings** on all public methods explaining parameters and return values.

    Do NOT implement any engine-specific logic — this is purely the interface contract.
    Do NOT import indextts, qwen_tts, or any model-specific libraries.
  </action>
  <verify>
    python -c "from scripts.tts_engines.base import TTSEngine, EmotionParser; print('Import OK')"
    python -c "from scripts.tts_engines.base import TTSEngine; import inspect; methods = [m for m in dir(TTSEngine) if not m.startswith('_')]; print(methods); assert 'clone_voice' in methods; assert 'synthesize' in methods; assert 'get_emotion_params' in methods; assert 'load_model' in methods; print('Interface OK')"
  </verify>
  <done>TTSEngine is an abstract class with 4 abstract methods (load_model, clone_voice, synthesize, get_emotion_params) and name property. EmotionParser can parse [情绪:强度] tags and strip all bracket content from text.</done>
</task>

<task type="auto">
  <name>Create tts_engines package init</name>
  <files>scripts/tts_engines/__init__.py</files>
  <action>
    Create scripts/tts_engines/__init__.py that:
    1. Imports TTSEngine and EmotionParser from .base
    2. Exports them at package level: __all__ = ["TTSEngine", "EmotionParser"]
    3. Imports engine_factory function (will be added by Plan 03, use try/except for now to avoid import error)
    4. Add docstring: "Pluggable TTS engine architecture supporting IndexTTS-2, Qwen3-TTS, and future models."

    For engine_factory import, use lazy import pattern:
    ```python
    def __getattr__(name):
        if name == "create_engine":
            from .factory import create_engine
            return create_engine
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    ```
  </action>
  <verify>
    python -c "from scripts.tts_engines import TTSEngine, EmotionParser; print('Package imports OK')"
  </verify>
  <done>scripts/tts_engines/ is a valid Python package exporting TTSEngine and EmotionParser. Lazy import for create_engine is set up for Plan 03.</done>
</task>

</tasks>

<verification>
- Both files exist and are syntactically valid Python
- TTSEngine cannot be instantiated directly (ABC enforcement)
- EmotionParser.parse_emotion_tags("[高兴:1.2]你好[惊讶:0.8]世界") returns ([{"type": "emotion", "name": "高兴", "intensity": 1.2}, {"type": "emotion", "name": "惊讶", "intensity": 0.8}], "你好世界")
- Package can be imported: from scripts.tts_engines import TTSEngine, EmotionParser
</verification>

<success_criteria>
- TTSEngine abstract base class defines all 4 required abstract methods + name property
- EmotionParser extracts emotion parsing logic from dubbing.py into reusable utility
- Package structure established at scripts/tts_engines/ ready for engine implementations
- No engine-specific imports in base.py or __init__.py
</success_criteria>

<output>
After completion, create `.planning/phases/01-refactor-tts-engine-architecture/01-refactor-tts-engine-architecture-01-SUMMARY.md`
</output>
