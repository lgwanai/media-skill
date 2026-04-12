# Media Skill - 你的全能 AI 视频创作与分析助手 🎬

## 📖 简介
**Media Skill** 是一款专为内容创作者打造的“全能型 AI 视频工作站”。我们深度融合了当前最先进的多模态大模型与语音技术，旨在帮你从繁琐、机械的视频后期工作中彻底解放出来。

无论你是播客主理人、短视频博主、还是教育培训从业者，Media Skill 都能帮你实现**一键出字幕**、**自动剔除废话**、**智能提取高光时刻**，甚至**克隆你的声音**来自动生成配音。把机械的剪辑交给 AI，把创造力留给自己。

---

## 🎯 谁最需要它？(核心使用场景)

- 🎙️ **播客/访谈创作者**：几个小时的录音，一键生成精确到毫秒的字幕，还能自动区分是谁在说话。
- 📱 **口播视频/Vlog 博主**：录制时经常卡壳、说“额”、“啊”、重复说错？AI 会自动帮你把这些“废话”和无声的尴尬等待全部剪掉，输出极其流畅的成片。
- 👩‍🏫 **知识分享/教程讲师**：讲课时多余的解释会被自动剪掉，但 AI 能“看懂”画面，你在演示操作软件时的静音画面会被智能保留，绝不误删。
- ✂️ **长视频素材提炼**：面对几个小时的会议或直播回放，只需输入一句话（比如：“提取关于人工智能的讨论”），AI 就能自动把相关片段全部剪辑成一个精粹合集。
- 🗣️ **不想录音的创作者**：只需要提供一段你的录音，AI 就能完美克隆你的音色。后续只需输入文字，就能生成完全是你本人声音的配音，甚至连情绪都能自动匹配。

---

## ✨ 核心魔法 (五大绝技)

### 1. 📝 毫秒级极速字幕生成
丢掉昂贵的字幕软件！我们提供了专业级的语音识别能力，不仅能输出极其精准的字幕文本，还能精确到毫秒级的时间戳，并自动分离不同的说话人。

### 2. ✂️ 零误差的智能“净”剪辑
传统的粗暴剪辑容易导致画面跳跃，而我们独创了“多级混合智能剪辑架构”。AI 会像人类剪辑师一样去理解你说的每一句话，精准找出“废话”并将其无缝剔除，保证最终视频画质 100% 完美且音画绝对同步。

### 3. 👀 懂画面的“非语言”保留
很多剪辑软件只会死板地删掉所有无声片段，导致重要的动作展示被误删。我们的 AI 长了一双“眼睛”，能看懂画面里你是不是在操作鼠标或展示物品，如果有价值，哪怕没有声音也会被完美保留。

### 4. 🔍 “大海捞针”式主题提取
不用再拖动进度条苦苦寻找素材了。告诉 AI 你想要什么主题，它会通读所有内容，精准定位并提取所有相关片段，还会贴心地帮你保留上下文，确保剪出来的合集语义连贯。

### 5. 🎙️ 专属声音克隆与智能配音 (支持四引擎)
在本地建立你自己的"专属音色库"。只需几秒钟的样本，即可克隆你的声音。在后续配音时，支持**智能拆分超长文本**并**多线程极速并发生成**。AI 还会根据你输入的文本情境，自动调整语速和情绪。
**全新升级四引擎支持**：
- **IndexTTS-2**：高情感表现力，支持精确情绪控制标签
- **Qwen3-TTS**：极速且高音色还原度
- **LongCat-AudioDiT**：本地扩散模型，零样本克隆
- **OmniVoice**：支持 600+ 语言，独有的 Voice Design 功能

所有引擎均支持 API 和本地模式（部分引擎仅支持本地），可在 `config.txt` 中一键切换。

### 6. 🌐 智能翻译与硬核字幕烧录
不仅能一键提取精准字幕，还支持大模型智能翻译！AI 会先理解你的专业领域，进行非生硬的翻译，自动过滤“呃”、“啊”等语气词。
最新升级了**多线程 OpenCV 硬核字幕烧录**技术，彻底告别复杂的 FFmpeg 滤镜报错。生成的字幕会自动识别横竖屏，配备美观的“白底黑字圆角”背景，智能拆分长句（且绝不截断英文单词），字体大小自适应，排版极度舒适。

### 7. 🌟 金句高光自动提取
无需人工逐字审核，AI 自动读懂全部内容，圈选出包含“金句”、“鲜明观点”或“实用技能”的高光片段。最棒的是，提取出的每一个片段都会自动走一遍“智能精剪”，输出干干净净的纯干货短视频。

### 8. 🚀 “一条龙”全自动短视频流水线
将【高光提取】+【智能精剪】+【翻译字幕】完美串联。只要扔进去一个长视频，AI 自动帮你把最精彩的部分切出来、去掉废话、配好双语字幕，直接输出多个可以直接发布到 TikTok/抖音 的完美短视频！

### 9. 🗣️ 同音色全自动视频翻译 (黑科技)
想把你的中文视频发到海外，又不想失去你原有的声音魅力？系统会自动提取你原视频中的纯净语音作为样本克隆音色，随后自动翻译字幕，并用“你的声音”念出外语，最后将新语音严格对齐原视频的时间轴并烧录双语/外文字幕。真正实现**“画质无损 + 你的音色 + 外语配音 + 外语字幕”**的一键出海。

### 10. 📊 多模态爆款视频深度解构
不仅仅是创作工具，更是你的“内容策略分析师”。输入一个爆款视频，系统会自动将其压缩上传，利用最先进的多模态大模型（如 Omini），从视觉流、听觉流和文本流三个维度同步拆解。它能一针见血地分析“前3秒钩子”、“声画字协同效应”，并**带有批判性地**评估视频的真实潜力，最终输出一份结构化的专业 Markdown 分析报告。

### 11. 🧠 智能专业词库纠错
受够了语音模型把专业名词（如“Omini”）识别成“欧米米”？系统内置了极其硬核的词库映射功能（`data/hotwords.yaml`）。它不仅仅是“搜索替换”这么简单，更会在底层**动态重新对齐毫秒级的时间戳矩阵**，保证替换后的视频毫秒级精准裁剪分毫不差！

---

## 🚀 快速开始

### 1. 环境准备
- **Python 3.8 ~ 3.11** (⚠️ 注意：如果想使用本地声音克隆功能，由于底层依赖 `numba`，Python 版本最高不能超过 3.11。如果在高版本 Python 如 3.12+ 运行，建议使用 API 模式)
- 安装 **FFmpeg** (必须安装并配置到系统环境变量中)

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置密钥与参数

安装完毕后，你需要为系统配置 AI 大模型和云存储的密钥。

**对于命令行 / 普通用户：**
复制示例配置文件并编辑：
```bash
cp config.example.txt config.txt
```
打开 `config.txt` 填入你的配置信息。

**对于 OpenClaw / Claude Code Agent 用户：**
作为 Skill 被 Agent 调用时，由于通常无法直接看到隐藏的配置文件，你只需**复制下方完整的配置模板**，在本地文本编辑器中填好你的私密信息，然后直接粘贴给你的 Agent（如 OpenClaw 或 Claude Code），并告诉它：
> *"请根据以下内容，帮我更新 Media Skill 的 `config.txt` 配置文件。"*

<details>
<summary>点击展开：config.txt 完整配置模板 (供复制)</summary>

```ini
# ---------------------------------------------------------
# 1. 基础配置
# ---------------------------------------------------------
# 模型存放目录，用于存放 FunASR 等本地下载的模型，默认存放于 models/ 目录
MODEL_DIR = models/

# ---------------------------------------------------------
# 2. 纯文本语义分析大模型配置 (Step 2)
# 用于第二步：通过纯文本判断并剔除明显的废话、结巴、重复
# ---------------------------------------------------------
# 大模型 API 接口地址（兼容 OpenAI 格式）
TEXT_LLM_URL = https://api.deepseek.com/v1
# 你的大模型 API Key
TEXT_LLM_API_KEY = your_text_llm_api_key_here
# 使用的大模型名称（如 deepseek-chat, gpt-4o, qwen-plus 等）
TEXT_LLM_MODEL_NAME = deepseek-chat

# ---------------------------------------------------------
# 3. 多模态大模型配置 (Step 3 & 爆款分析)
# 用于精细剔除局部瑕疵，以及多模态爆款视频深度解构
# ---------------------------------------------------------
# 多模态大模型 API 接口地址（兼容 OpenAI 格式，推荐小米 Omini）
OMINI_URL = https://api.xiaomimimo.com/v1
# 你的多模态大模型 API Key
OMINI_API_KEY = your_omini_api_key_here
# 使用的多模态大模型名称
OMINI_MODEL_NAME = mimo-v2-omni

# ---------------------------------------------------------
# 4. 腾讯云 COS 配置 (对象存储)
# 用于将本地切片或完整视频上传至云端，以获取公网 URL 供多模态大模型读取
# ---------------------------------------------------------
# 腾讯云 API 密钥 ID
COS_SECRET_ID = your_cos_secret_id_here
# 腾讯云 API 密钥 Key
COS_SECRET_KEY = your_cos_secret_key_here
# 存储桶所在地域（如 ap-beijing）
COS_REGION = ap-beijing
# 存储桶名称（格式为 BucketName-APPID）
COS_BUCKET_NAME = your_bucket_name_here

# ---------------------------------------------------------
# 5. TTS 四引擎配置 (用于 TTS 配音与声音克隆)
# ---------------------------------------------------------
# TTS_ENGINE 可选: indextts, qwen3-tts, longcat-audiodit, omnivoice
TTS_ENGINE = indextts

# IndexTTS-2 配置 (支持精确情绪控制)
INDEXTTS_MODE = local
INDEXTTS_URL = https://api.siliconflow.cn/v1/audio/speech
INDEXTTS_API_KEY = your_indextts_api_key_here
INDEXTTS_MODEL_NAME = IndexTeam/IndexTTS-2

# Qwen3-TTS 配置
QWEN3TTS_MODE = local
QWEN3TTS_URL = wss://dashscope.aliyuncs.com/api-ws/v1/inference
QWEN3TTS_API_KEY = your_qwen3tts_api_key_here
QWEN3TTS_MODEL_NAME = qwen3-tts

# LongCat-AudioDiT 配置 (仅本地模式)
LONGCAT_MODE = local
LONGCAT_MODEL_DIR = models/LongCat-AudioDiT-1B

# OmniVoice 配置 (支持 Voice Design 和非语言标签，仅本地模式)
OMNIVOICE_MODE = local
OMNIVOICE_MODEL_DIR = models/OmniVoice

# 配音基准情绪参数（当没有特殊说明或大模型未调整时使用的默认值）
TTS_DEFAULT_TEMPERATURE = 0.65
TTS_DEFAULT_TOP_K = 40
TTS_DEFAULT_TOP_P = 0.8
TTS_DEFAULT_MAX_TEXT_TOKENS = 130

# ---------------------------------------------------------
# 6. ASR 配置
# ---------------------------------------------------------
# ASR_ENGINE 可选: funasr, qwen3-asr
ASR_ENGINE = qwen3-asr

# FunASR 配置（用于 diarization 补充）
FUNASR_PARAFORMER_MODEL = iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch
FUNASR_VAD_MODEL = damo/speech_fsmn_vad_zh-cn-16k-common-pytorch
FUNASR_PUNC_MODEL = damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch
FUNASR_SPK_MODEL = iic/speech_eres2net_sv_zh-cn_16k-common

# Qwen3-ASR 配置
QWEN3ASR_MODE = local
QWEN3ASR_MODEL = Qwen/Qwen3-ASR-1.7B
QWEN3ASR_ALIGNER_MODEL = Qwen/Qwen3-ForcedAligner-0.6B
QWEN3ASR_DEVICE = cuda:0
QWEN3ASR_BACKEND = transformers
QWEN3ASR_MAX_NEW_TOKENS = 256
QWEN3ASR_ENABLE_DIARIZATION = true
QWEN3ASR_MAX_SPEAKERS = 4
```
</details>

### 4. 尽情创作吧！

#### 🎬 魔法 A: 一键出字幕
```bash
python scripts/transcribe.py <你的视频或音频文件.mp4>
```
*完成后，你会在 `output/<文件名_MD5>/` 文件夹里找到生成好的 `transcription.json`、SRT 字幕和纯文本稿。系统会自动根据文件 MD5 进行缓存，重复运行秒级跳过！*

**当前字幕输出规则：**
- `transcription.srt`：输出**标准 SRT 格式**，可直接导入剪映、Premiere、Final Cut 等视频编辑软件。
- `transcription.json`：
  - `sentence_info`：按**语义完整句**聚合后的字幕片段，适合剪辑与上屏。
  - `char_level_info`：保留**字级毫秒时间戳**，适合做精细对齐、后处理或二次分析。
- 当检测到**多人发言**时，会自动在字幕文本中加入 `SPEAKER_00` / `SPEAKER_01` 等发言人标识；单人发言时默认输出纯文本字幕。

**Qwen3-ASR 多人发言说明：**
- `Qwen3-ASR` 负责高质量识别与毫秒级对齐。
- 当前工程中的说话人分离采用**融合方案**：`Qwen3-ASR` 产出文本与时间戳，`FunASR` 产出 diarization 结果，再自动回填 `SPEAKER_00 / 01` 标签。
- 这不会生成每位说话人的独立音轨，但会输出“**谁在什么时间说了哪句话**”。

#### ✂️ 魔法 B: 全自动智能剪辑 (去除废话)
*请先执行上面的魔法 A 生成字幕，然后再执行剪辑：*
```bash
python scripts/clip_video.py output/<文件名_MD5>/transcription.json <待剪辑的视频.mp4>
```
*喝杯咖啡，一个纯净、流畅的成片就会出现在对应的 `output/<文件名_MD5>/<视频名>_clipped.mp4`。*

#### 🔍 魔法 C: 根据主题提取视频
```bash
python scripts/extract_by_theme.py <你的长视频.mp4> "<你想提取的主题，例如：聊聊苹果手机的优缺点>"
```

#### 🗣️ 魔法 D: 克隆你的专属声音
把你的一段清晰录音交给 AI，给它起个名字：
```bash
# 克隆到所有支持的引擎（推荐）
python scripts/dubbing.py clone --audio <你的参考录音.mp3> --name "我的专属音色"

# 仅克隆到指定引擎
python scripts/dubbing.py clone --audio <你的参考录音.mp3> --name "我的专属音色" --models "omnivoice,indextts"
```

#### 🎙️ 魔法 E: 用你的声音自动配音 (支持多线程极速生成与多种控制方式)
> ⚠️ **提示**：配音可能比较耗时，如果您是通过 Agent（如 Claude Code/OpenClaw）调用，建议将其放到后台执行，防止超时卡死。
> - **Mac/Linux 环境**：首次运行前执行 `chmod +x scripts/async_run.sh`，调用时使用 `sh scripts/async_run.sh python ...`。
> - **Windows 环境**：调用时使用 `scripts\async_run.bat python ...`。

---

## 🎛️ 音色控制方式大全

Media Skill 支持四种音色控制方式，让你精准控制 AI 的声音表现：

### 方式一：精确情绪控制标签 (IndexTTS-2 专属)

支持格式：`[情绪名:强度值]`。例如：`[高兴:1.2]`, `[惊讶:0.8]`, `[悲伤:1.0]`。

支持的情绪类型：`高兴`, `愤怒`, `悲伤`, `恐惧`, `反感`, `低落`, `惊讶`, `自然`。强度值范围推荐 `0.0 - 1.5`。

```bash
sh scripts/async_run.sh python scripts/dubbing.py dub --text "[惊讶:1.2]哎哟喂！这效果太惊人了！" --voice "我的音色"
```

### 方式二：Voice Design 自然语言描述 (OmniVoice / Qwen3-TTS)

通过自然语言描述你想要的声音特征，无需参考音频即可设计音色！

**支持的引擎**：
- **OmniVoice**：支持性别、年龄、音调、口音等属性组合
- **Qwen3-TTS**：支持自然语言描述情感语气（需使用 VoiceDesign 模型）

**OmniVoice 支持的属性**：
- **性别**：`male`, `female`
- **年龄**：`child`, `young`, `middle-aged`, `elderly`
- **音调**：`very low pitch`, `low pitch`, `high pitch`, `very high pitch`
- **风格**：`whisper`
- **英语口音**：`American accent`, `British accent`, `Australian accent` 等
- **中文方言**：`四川话`, `陕西话`, `粤语` 等

**属性可自由组合，用逗号分隔**：

```bash
# OmniVoice: 使用 --instruct 参数进行 Voice Design
sh scripts/async_run.sh python scripts/dubbing.py dub \
  --text "Hello, this is a demonstration of voice design." \
  --instruct "female, low pitch, british accent, professional" \
  --engine omnivoice

# OmniVoice: 中文方言示例
sh scripts/async_run.sh python scripts/dubbing.py dub \
  --text "大家好，今天给大家带来一个好消息。" \
  --instruct "female, 四川话" \
  --engine omnivoice

# Qwen3-TTS: Voice Design (需本地模式 + VoiceDesign 模型)
sh scripts/async_run.sh python scripts/dubbing.py dub \
  --text "哥哥，你回来啦~" \
  --instruct "体现撒娇稚嫩的萝莉女声" \
  --engine qwen3-tts

# Qwen3-TTS: 使用预设音色 + 情感指令
sh scripts/async_run.sh python scripts/dubbing.py dub \
  --text "这简直太过分了！" \
  --voice "Vivian" \
  --instruct "用特别愤怒的语气说" \
  --engine qwen3-tts
```

**Qwen3-TTS 预设音色**：Vivian, Serena, Uncle_Fu, Dylan, Eric, Ryan, Aiden, Ono_Anna, Sohee

### 方式三：非语言声音标签 (OmniVoice 专属)

在文本中插入标签，让 AI 发出笑声、叹气、疑问等非语言声音：

**支持的标签**：
| 标签 | 效果 |
|------|------|
| `[laughter]` | 笑声 |
| `[sigh]` | 叹气 |
| `[confirmation-en]` | 英语肯定语气 |
| `[question-en]` | 英语疑问语气 |
| `[question-ah]` | "啊" 疑问语气 |
| `[question-oh]` | "哦" 疑问语气 |
| `[question-ei]` | "诶" 疑问语气 |
| `[question-yi]` | "咦" 疑问语气 |
| `[surprise-ah]` | "啊" 惊讶语气 |
| `[surprise-oh]` | "哦" 惊讶语气 |
| `[surprise-wa]` | "哇" 惊讶语气 |
| `[surprise-yo]` | "哟" 惊讶语气 |
| `[dissatisfaction-hnn]` | 不满语气 |

```bash
sh scripts/async_run.sh python scripts/dubbing.py dub \
  --text "[laughter] You really got me! I didn't see that coming at all. [sigh] But seriously, that was impressive." \
  --engine omnivoice
```

### 方式四：发音纠正 (OmniVoice 专属)

精确控制特定汉字或单词的发音，解决多音字、专有名词等问题。

#### 中文发音纠正：拼音+声调

使用带声调数字的拼音覆盖默认发音：

```bash
# "折" 字有 zhē (折腾) 和 zhé (打折) 两个读音
sh scripts/async_run.sh python scripts/dubbing.py dub \
  --text "这批货物打ZHE2出售后他严重SHE2本了，再也经不起ZHE1腾了。" \
  --engine omnivoice

# 解释：
# ZHE2 = zhé (打折的折)
# SHE2 = shé (折本的折)  
# ZHE1 = zhē (折腾的折)
```

**拼音声调规则**：
- 声调 1 = 阴平 (ā) → 如 MA1 = 妈
- 声调 2 = 阳平 (á) → 如 MA2 = 麻
- 声调 3 = 上声 (ǎ) → 如 MA3 = 马
- 声调 4 = 去声 (à) → 如 MA4 = 骂
- 声调 5 = 轻声 → 如 MA5 = 吗

#### 英语发音纠正：CMU 发音词典

使用 CMU 发音词典格式（大写，置于方括号内）覆盖默认发音：

```bash
# "bass" 有两个读音：/beɪs/ (低音) 和 /bæs/ (鲈鱼)
sh scripts/async_run.sh python scripts/dubbing.py dub \
  --text "He plays the [B EY1 S] guitar while catching a [B AE1 S] fish." \
  --engine omnivoice

# [B EY1 S] = /beɪs/ (低音乐器)
# [B AE1 S] = /bæs/ (鲈鱼)
```

**CMU 发音符号速查**：
| 符号 | IPA | 示例 |
|------|-----|------|
| `AA` | /ɑ/ | b**o**ttle |
| `AE` | /æ/ | c**a**t |
| `AH` | /ʌ/ | c**u**t |
| `AO` | /ɔ/ | d**o**g |
| `AW` | /aʊ/ | h**ow** |
| `AY` | /aɪ/ | l**i**ke |
| `EH` | /ɛ/ | b**e**d |
| `ER` | /ɜr/ | b**ir**d |
| `EY` | /eɪ/ | s**ay** |
| `IH` | /ɪ/ | b**i**t |
| `IY` | /i/ | s**ee** |
| `OW` | /oʊ/ | g**o** |
| `OY` | /ɔɪ/ | b**oy** |
| `UH` | /ʊ/ | b**oo**k |
| `UW` | /u/ | t**oo** |

数字后缀表示重音：`1` = 主重音，`2` = 次重音，`0` = 无重音

---

## 📁 音色配置文件格式

为每个音色创建配置文件，实现默认参数管理：

**文件位置**：`data/voices/<音色名称>/config.md`

**配置格式**：
```markdown
---
name: "专业播音员"
engine: omnivoice
created: 2026-04-11
---

# Voice Configuration: 专业播音员

## Instruct

female, low pitch, british accent, professional tone

## Compatible Engines

- **omnivoice**: Full support (instruct + tags)
- **indextts**: Clone from reference audio, emotion tags supported
- **qwen3-tts**: Clone from reference audio only
- **longcat-audiodit**: Clone from reference audio only

## Notes

This voice works best with English narration.
```

使用配置文件时，只需指定音色名称：
```bash
sh scripts/async_run.sh python scripts/dubbing.py dub \
  --text "Your text here" \
  --voice "专业播音员"
# 系统会自动加载 config.md 中的 engine 和 instruct 设置
```

---

## 📊 四引擎对比

| 特性 | IndexTTS-2 | Qwen3-TTS | LongCat-AudioDiT | OmniVoice |
|------|-----------|-----------|------------------|-----------|
| **情绪控制** | ✅ 精确标签 + 文本指令 | ❌ | ❌ | ❌ |
| **Voice Design** | ❌ | ✅ 自然语言 (VoiceDesign 模型) | ❌ | ✅ 自然语言 |
| **预设音色** | ❌ | ✅ 9种精品音色 | ❌ | ❌ |
| **非语言标签** | ❌ | ❌ | ❌ | ✅ 13种标签 |
| **发音纠正** | ❌ | ❌ | ❌ | ✅ 拼音+CMU |
| **流式输出** | ✅ `stream_return=True` | ✅ 97ms 极低延迟 | ❌ | ❌ |
| **API 模式** | ✅ | ✅ | ❌ | ❌ |
| **本地模式** | ✅ | ✅ | ✅ | ✅ |
| **语言支持** | 中文为主 | 10种语言 | 中英文 | 600+ 语言 |

---

## 💡 使用示例汇总

```bash
# 1. 情绪控制 (IndexTTS-2)
python scripts/dubbing.py dub --text "[高兴:1.2]今天真是太棒了！" --voice "我的音色" --engine indextts

# 2. Voice Design (OmniVoice) - 无需克隆，直接设计
python scripts/dubbing.py dub --text "Welcome to our show!" --instruct "male, deep voice, American accent" --engine omnivoice

# 3. 非语言标签 (OmniVoice)
python scripts/dubbing.py dub --text "[laughter] What a surprise! [sigh] I never expected this." --engine omnivoice

# 4. 发音纠正 (OmniVoice) - 中文拼音
python scripts/dubbing.py dub --text "这批货物打ZHE2出售后他严重SHE2本了。" --engine omnivoice

# 5. 发音纠正 (OmniVoice) - 英语 CMU
python scripts/dubbing.py dub --text "He plays the [B EY1 S] guitar while catching a [B AE1 S] fish." --engine omnivoice

# 6. 使用配置文件
python scripts/dubbing.py dub --text "Your content here" --voice "专业播音员"

# 7. 字幕配音
python scripts/dubbing.py dub --srt subtitle.srt --voice "我的音色" --out output.mp3
```

*AI 会自动询问你想使用哪个克隆好的音色。对于长文本，程序会在 `output/` 目录下生成 `dubbing_status.json`，支持 Agent 或第三方应用异步查询生成进度。*

#### 🌐 魔法 F: 智能配字幕与大模型翻译
直接给视频配上排版精美的硬字幕（自动识别横竖屏、智能拆分、白底黑字圆角），还能翻译：
```bash
# 生成原语言排版字幕 (默认输出到 output/<文件名_MD5>/<原名>_subtitled.mp4)
python scripts/subtitle.py <你的视频.mp4>

# 翻译为英文并生成字幕（自动识别领域、过滤语气词）
python scripts/subtitle.py <你的视频.mp4> --lang "English"
```

#### 🌟 魔法 G: 自动提取精彩片段 (自带精剪)
自动找出金句、观点，并把这些高光时刻剪成干净的短视频：
```bash
python scripts/highlight.py <你的长视频.mp4>
```

#### 🚀 魔法 H: 终极连招 (提取 -> 精剪 -> 翻译字幕)
一条龙服务，直接输出可以直接发抖音/TikTok的视频：
```bash
python scripts/combine.py <你的长视频.mp4> --lang "English"
```

#### 🌍 魔法 I: 同音色视频翻译 (一键出海)
保持原视频画质和**你的专属音色**，自动翻译并生成全新外语配音及字幕对齐的视频：
```bash
python scripts/translate_video.py <你的中文视频.mp4> --lang "English"
```
*完成后，会在 `output/<文件名_MD5>/` 中得到一个用你本人的声音说英语并带好英语字幕的完美视频。*

#### 🧠 魔法 J: 自动应用专业词库纠错
在运行上述转录或剪辑命令前，只需在 `data/hotwords.yaml` 中配置你的专有名词（如 `Omini: ["欧米米", "o米你"]`），系统会在转录时自动纠错并无缝对齐时间戳。

#### 📊 魔法 K: 爆款视频深度解构
输入一段别人的爆款视频（或你自己的视频），让多模态 AI 从视、听、文三个维度批判性拆解它的爆款逻辑与硬伤：
```bash
python scripts/analyze_video.py <待分析视频.mp4>
```
*系统会自动将其压缩为 540p 节省 Token，并输出一份极其专业的 Markdown 深度分析报告。*

#### 📽️ 魔法 L: PPT 翻页视频生成
输入一系列场景的“图片+文字”，系统会自动将文字进行 AI 配音，并与图片合并生成每一段带字幕的视频，最后无缝拼接为一个完整的 PPT 讲解视频。
```bash
# 准备一个 scenes.json，格式为 [{"image_url": "...", "text": "第一段文字"}, ...]
python scripts/ppt_video.py --scenes scenes.json --voice default
```
*完成后，会在 `output/` 中得到 `ppt_final_video.mp4`，包含全部配音、画面和精美字幕。*

---

## ❓ 常见问题 (FAQ)

**Q: 运行声音克隆或配音时提示“未找到 indextts”或下载失败？**
A: 请确保已经正确安装了语音底层的运行环境：
```bash
git clone https://github.com/index-tts/index-tts.git
cd index-tts
pip install -r requirements.txt
pip install -e .
pip install torchcodec
```
如果你在国内网络下载模型较慢，系统已经默认配置了国内镜像，通常可以顺畅下载。

**Q: 剪辑时遇到 Omini API 报 `402 Payment Required` 错误怎么办？**
A: 这是因为视觉大模型的免费额度用完了。别担心，系统非常聪明，会自动降级到“纯文本语义过滤模式”，依然能帮你准确删掉大量的废话和语气词，工作绝不中断！

**Q: 我的 API 密钥等隐私信息安全吗？**
A: 绝对安全。配置文件 `config.txt` 已经被屏蔽，不会被上传到网络。所有的数据处理也都在你授权的范围内进行。

**Q: 遇到模块导入错误 `cannot import name 'CosS3Client'`？**
A: 请检查你的 Python 环境，卸载旧版的云存储包，并确保安装的是官方推荐的 `cos-python-sdk-v5`。
