# Research: Voice Control Methods for TTS Engines

**Created:** 2026-04-11
**Phase:** 6 - Voice control methods: instruct-based and tag-based synthesis control

## Summary

This research investigates voice control methods across all 4 supported TTS engines:
- **Instruct-based control**: Natural language descriptions (e.g., "female, low pitch, british accent")
- **Tag-based control**: Inline markers (e.g., `[laughter]`, `[sigh]`)

## Findings by Engine

### 1. OmniVoice ✅ FULL SUPPORT

**Instruct-based control**: YES
```python
audio = model.generate(
    text="Hello, this is a test of zero-shot voice design.",
    instruct="female, low pitch, british accent",
)
```

**Supported instruct attributes:**
- **gender**: male, female
- **age**: child to elderly
- **pitch**: very low to very high
- **style**: whisper
- **English accent**: American, British, etc.
- **Chinese dialect**: 四川话, 陕西话, etc.

**Attributes are comma-separated and freely combinable.**

**Tag-based control**: YES
```python
audio = model.generate(text="[laughter] You really got me. I didn't see that coming at all.")
```

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

**Pronunciation control**: YES
- **Chinese**: Pinyin with tone numbers (1-5)
  - Example: `这批货物打ZHE2出售后他严重SHE2本了`
  - Explanation: ZHE2 = zhé (sell at discount), SHE2 = shé (lose money)
- **English**: CMU pronunciation dictionary in brackets
  - Example: `He plays the [B EY1 S] guitar while catching a [B AE1 S] fish.`
  - Explanation: [B EY1 S] = /beɪs/ (bass instrument), [B AE1 S] = /bæs/ (fish)- **Tone numbers**:
  - 1 = primary stress,  - 2 = secondary stress
  - 0 = no stress

**Tags should be passed RAW to the engine - no parsing/interception needed.**

---

### 2. LongCat-AudioDiT ❌ NO SUPPORT

**Instruct-based control**: NO - Not mentioned in official documentation

**Tag-based control**: NO - Not mentioned in official documentation

**Voice control method**: Zero-shot voice cloning via `prompt_audio` + `prompt_text` only

```python
# Voice cloning only
output = model(
    input_ids=inputs.input_ids,
    attention_mask=inputs.attention_mask,
    prompt_audio=prompt_wav,  # Reference audio
    duration=138,
    steps=16,
    cfg_strength=4.0,
    guidance_method="apg",  # or "cfg"
)
```

**Parameters:**
- `steps`: Diffusion steps (16 for fast, 32 for quality)
- `cfg_strength`: Classifier-free guidance strength (default 4.0)
- `guidance_method`: "cfg" or "apg" (adaptive projection guidance)

---

### 3. IndexTTS-2 ⏳ RESEARCHING

**Current known support:**
- ✅ Emotion control via `emo_vector` (8-element array)
- ✅ Emotion tags in text: `[情绪:强度]` format
  - Supported emotions: 高兴, 愤怒, 悲伤, 恐惧, 反感, 低落, 惊讶, 自然
- ❓ Instruct-based control: Under investigation
- ❓ Tag-based control: Under investigation

**Emotion vector format:**
```python
# Emotion mapping to 8-element vector
emo_vector = [0.0] * 8  # [高兴, 愤怒, 悲伤, 恐惧, 反感, 低落, 惊讶, 自然]
emo_vector[0] = 1.2  # Set "高兴" (happy) with intensity 1.2
```

---

### 4. Qwen3-TTS ⏳ RESEARCHING

**Current known support:**
- ❌ No emotion control (no emo_vector support)
- ❓ Instruct-based control: Under investigation
- ❓ Tag-based control: Under investigation

**Voice control method**: Zero-shot voice cloning via `ref_audio` + `ref_text`

---

## Implementation Recommendations

### Voice Config File Format (Markdown)

```markdown
---
name: "professional-narrator"
engine: omnivoice
created: 2026-04-11
---

# Voice Configuration

## Instruct (Voice Design)
female, low pitch, british accent, professional

## Compatible Engines
- omnivoice (instruct + tags)
- indextts (emotion tags only)
- qwen3-tts (cloning only)
- longcat-audiodit (cloning only)

## Notes
This voice works best with English narration. 
For OmniVoice, use instruct for voice design.
For other engines, clone from reference audio.
```

### Code Changes Required

1. **DO NOT intercept/parse tags** - Pass them raw to engines
2. **Add `instruct` parameter** to `synthesize()` method
3. **Add warning mechanism** when engine doesn't support provided instruct/tags

```python
# synthesize() signature change
def synthesize(
    self,
    text: str,
    voice_id: str,
    output_path: str,
    tts_params: dict | None = None,
    instruct: str | None = None,  # NEW: Voice design instruction
) -> bool:
    ...
```

### Engine Support Matrix

| Engine | Instruct | Tags | Emotion Vector | Notes |
|--------|----------|------|----------------|-------|
| OmniVoice | ✅ | ✅ (13 tags) | ❌ | Full support |
| LongCat-AudioDiT | ❌ | ❌ | ❌ | Clone only |
| IndexTTS-2 | ❓ | ❓ | ✅ | Emotion via vector |
| Qwen3-TTS | ❓ | ❓ | ❌ | Clone only |

---

## References

- OmniVoice: https://github.com/k2-fsa/OmniVoice
- LongCat-AudioDiT: https://github.com/meituan-longcat/LongCat-AudioDiT
- IndexTTS-2: https://github.com/index-tts/index-tts
- Qwen3-TTS: https://github.com/QwenLM/Qwen3-TTS
