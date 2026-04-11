# Voice Configuration File Format

This document specifies the markdown voice configuration file format used by Media Skill to define and manage voice profiles across multiple TTS engines.

## File Location

Voice configuration files follow this naming convention:

```
data/voices/{voice_name}/config.md
```

Each voice profile resides in its own directory under `data/voices/`, with the configuration stored in `config.md`.

## File Structure

The format consists of two parts:

### 1. YAML Frontmatter

Metadata about the voice profile:

```yaml
---
name: "professional-narrator"
engine: omnivoice
created: 2026-04-11
---
```

**Fields:**
- `name`: Unique identifier for the voice profile
- `engine`: Primary TTS engine this voice was designed for (e.g., `omnivoice`, `indextts`, `qwen3-tts`, `longcat-audiodit`)
- `created`: Date the voice profile was created (ISO 8601 format: YYYY-MM-DD)

### 2. Markdown Body

Human-readable configuration sections:

```markdown
# Voice Configuration: Professional Narrator

## Instruct

female, low pitch, british accent, professional tone

## Compatible Engines

- **omnivoice**: Full support (instruct + tags)
- **indextts**: Clone from reference audio, emotion tags supported
- **qwen3-tts**: Clone from reference audio only
- **longcat-audiodit**: Clone from reference audio only

## Notes

This voice works best with English narration. For OmniVoice, use the instruct field for voice design. For other engines, clone from a reference audio sample.

## Example Tags (OmniVoice only)

[laughter] - Laughter sound
[sigh] - Sigh sound
[confirmation-en] - English confirmation tone
```

## Sections Explained

### Instruct

The `## Instruct` section contains natural language voice design instructions. This is **only supported by OmniVoice**.

**Example:**
```
female, low pitch, british accent, professional tone
```

**Supported attributes (OmniVoice):**
- **gender**: male, female
- **age**: child to elderly
- **pitch**: very low to very high
- **style**: whisper
- **English accent**: American, British, etc.
- **Chinese dialect**: 四川话, 陕西话, etc.

Attributes are comma-separated and freely combinable.

**Behavior with unsupported engines:** When `instruct` is provided to engines other than OmniVoice, the parameter is **ignored** and a warning is issued. These engines fall back to zero-shot voice cloning using reference audio.

### Compatible Engines

Lists all TTS engines that can use this voice profile, with notes on what features are supported:

- **omnivoice**: Full support for instruct-based voice design and tag-based emotion control
- **indextts**: Supports emotion tags (`[情绪:强度]` format) converted to emo_vector; requires reference audio for cloning
- **qwen3-tts**: Zero-shot cloning only; no emotion or instruct support
- **longcat-audiodit**: Zero-shot cloning only; no emotion or instruct support

### Notes

Free-form section for usage guidelines, best practices, or special considerations for this voice profile.

### Example Tags (OmniVoice only)

Documents available tags for tag-based control. Tags are **passed raw to the engine**—no parsing or interception is performed by Media Skill.

**Supported tags (13 total):**

| Tag | Description |
|-----|-------------|
| `[laughter]` | Laughter sound |
| `[sigh]` | Sigh sound |
| `[confirmation-en]` | English confirmation |
| `[question-en]` | English question tone |
| `[question-ah]` | "Ah" question tone |
| `[question-oh]` | "Oh" question tone |
| `[question-ei]` | "Ei" question tone |
| `[question-yi]` | "Yi" question tone |
| `[surprise-ah]` | "Ah" surprise tone |
| `[surprise-oh]` | "Oh" surprise tone |
| `[surprise-wa]` | "Wa" surprise tone |
| `[surprise-yo]` | "Yo" surprise tone |
| `[dissatisfaction-hnn]` | Dissatisfaction sound |

## How Instruct Is Used

The `instruct` field from the config is passed to the `synthesize()` method's `instruct` parameter:

```python
engine.synthesize(
    text="Hello world",
    voice_id="professional-narrator",
    output_path="output.wav",
    instruct="female, low pitch, british accent"  # From config.md ## Instruct section
)
```

**Engine behavior:**
- **OmniVoice**: Uses the instruct for voice design (zero-shot voice creation from text description)
- **Other engines**: Ignores the instruct parameter and issues a warning; falls back to reference audio cloning

## How Tags Work

Tags (e.g., `[laughter]`, `[sigh]`) are **passed raw to the engine**. Media Skill does not parse, intercept, or strip these tags before passing them to `synthesize()`.

**Important:** 
- Tags are embedded directly in the `text` parameter
- The engine is responsible for interpreting and rendering tags
- Only OmniVoice currently supports tag-based control
- Other engines will either ignore tags or may produce unexpected output

## Warning Behavior

When `instruct` is provided to an engine that doesn't support it:

1. The engine logs a warning message: `"Warning: {engine_name} does not support instruct-based voice design. Ignoring instruct parameter."`
2. The engine falls back to its default voice cloning behavior using reference audio
3. Synthesis continues normally (no error is raised)

This ensures backward compatibility while alerting users that their voice design instructions are not being applied.

## Complete Example

```markdown
---
name: "british-narrator"
engine: omnivoice
created: 2026-04-11
---

# Voice Configuration: British Narrator

## Instruct

female, low pitch, british accent, professional tone, slow pace

## Compatible Engines

- **omnivoice**: Full support (instruct + tags)
- **indextts**: Clone from reference audio, emotion tags supported
- **qwen3-tts**: Clone from reference audio only
- **longcat-audiodit**: Clone from reference audio only

## Notes

Optimized for documentary narration. Works best with formal English content. For non-OmniVoice engines, provide a 10-second reference audio sample for best cloning results.

## Example Tags (OmniVoice only)

[laughter] - Use for humorous segments
[sigh] - Use for reflective moments
[confirmation-en] - Use for affirmative statements
```
