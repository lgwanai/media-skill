---
name: media-skill
description: 多媒体生成、识别、剪辑一体化处理技能。当用户需要处理超长音视频转写文字、要求输出精确到毫秒级的时间轴（SRT/JSON）、通过多模态识别视频场景意图，或者要求进行自动化的智能视频剪辑（剔除气口、语气词、重复口语等无意义部分，分四步精剪）时，请务必使用此技能。即使他们只提到“音视频提取字幕”或“自动剪掉视频空白”，也要触发本技能。
---

# Media Skill: 多媒体生成、识别与智能剪辑一体化工作流

本技能旨在帮助用户通过一系列自动化、智能化的工作流，对音视频文件进行高精度识别、时间轴提取以及基于语义和多模态理解的智能剪辑。

## 核心能力
1. **高精度音视频转写 (独立功能)**：将音视频转换为文字，附带精确到毫秒级的时间戳。支持一键生成区分说话人的专业级字幕。支持通过 `data/hotwords.yaml` 映射专业术语和自定义词汇，纠正中文同音字识别偏误，同时保证下游剪辑时间戳精准对齐。
2. **多说话人分离 (Speaker Diarization)**：准确标记不同说话人，处理重叠发言，适用于播客、会议访谈等场景。
3. **基于主题的内容提取 (独立功能)**：用户输入主题描述，系统自动进行长视频/音频分析，并基于语义连贯性，智能提取与合并所有相关片段。
4. **视频智能剪辑 (极速 5 步管线)**：自动识别并精准剔除视频中的无声片段、语气词、重复表达及磕巴口误。
5. **爆款视频深度分析 (多模态解构)**：利用 Omini 模型综合声音、画面和文本，深度拆解爆款视频逻辑（黄金三秒、观众画像、情绪转折），并输出客观批判性的 Markdown 评估报告。
6. **声音克隆 (独立功能)**：集成 IndexTTS-2，支持提取个人声音特征并以自定义名称持久化保存至本地样本库（特征持久化为 `.pt`），供后续配音任务极速重复使用。
7. **AI 智能配音 (独立功能)**：基于字幕或长文本全自动生成配音。支持**智能长文本拆分**、**LLM 文本口语化润色**、**异步多线程并发合成**，自动在段落间插入 400ms 停顿，极大提升生成速度与声音自然度。
8. **智能配字幕与翻译 (独立功能)**：一键为视频生成字幕并压制，支持 LLM 语境识别与翻译，自动过滤语气词并排版折行。
9. **自动提取精彩片段 (独立功能)**：基于大模型提取金句、观点或实用技能片段，并结合智能剪辑 4 步法剔除无用废话，输出精华短视频。
10. **联合处理：精彩片段提取+智能剪辑+配字幕**：结合提取与配字幕能力，一键流水线输出带翻译字幕的精剪短视频。
11. **PPT 视频生成 (独立功能)**：将多场景的“图片+文字”组合，全自动配音、合成带字幕的视频段落，并无缝拼接为一个完整的 PPT 翻页讲解视频。

## 系统配置要求
系统依赖外部 `config.txt` 文件进行配置，处理任何任务前，请先确保当前目录下存在 `config.txt` 并读取其内容：
- `MODEL_DIR`: 模型存放目录
- `TEXT_LLM_URL` / `TEXT_LLM_API_KEY`: 文本大模型配置
- `OMINI_URL` / `OMINI_API_KEY` / `MIMO_API_KEY`: Omini 大模型配置
- 腾讯云 COS 配置（用于多模态剪辑的静音切片上传）
- `ENABLE_SILENCE_ANALYSIS`: 是否开启非语言片段智能保留
- `INDEXTTS_MODE`: TTS 运行模式配置 (`api` 为使用 SiliconFlow，`local` 为本地下载模型运行)

## 执行工作流指南

### 1. 环境与依赖检查
在开始处理之前，检查系统是否安装了 `ffmpeg` 并在环境变量中。同时确保 Python 环境已安装 `requirements.txt` 中的依赖。如果缺失，请指导用户或自动通过终端安装。

**对于异步执行脚本的权限与环境要求 (至关重要)**：
由于音视频处理非常耗时，所有的调用都必须通过异步包装脚本在后台执行以防 Agent 挂死。
- **Mac/Linux 环境**：首次运行前，必须确保 `.sh` 脚本有执行权限：`chmod +x scripts/async_run.sh`。调用时使用 `sh scripts/async_run.sh python ...`。
- **Windows 环境**：不支持 `.sh`，必须使用提供的 `.bat` 脚本：调用时使用 `scripts\async_run.bat python ...`。

### 2. 独立功能：毫秒级字幕识别与说话人分离
当用户仅要求“提取字幕”、“识别语音”、“区分说话人”时，请作为独立功能调用以下命令：
**⚠️ 重要提示：长音频/视频识别非常耗时，Agent 调用时请务必使用 `async_run.sh` 脚本，它会自动将任务转入后台执行并立即返回！**
```bash
sh scripts/async_run.sh python scripts/transcribe.py <音视频文件路径>
# 查询状态: cat output/<文件特征目录>/transcribe_status.json
```
**功能特性**：
- 使用 `ffmpeg` 提取音频并重采样至 16kHz。
- 调用 FunASR Pipeline (`FSMN-VAD + Paraformer + CAM++`) 进行高精度识别与说话人分离。
- **输出产物**：在 `output/` 目录下生成包含**毫秒级时间戳和说话人标签**的 SRT 字幕文件 (`transcription.srt`)、TXT 纯文本 (`transcription.txt`)，以及包含详细词级/句级数据的 JSON 文件 (`transcription.json`)。
- **状态查询**：Agent 可异步定期读取 `output/<文件特征目录>/transcribe_status.json` 以获取精确的进度与状态。

### 3. 独立功能：基于主题的长视频/音频片段提取
当用户要求“根据描述提取片段”、“找一下关于xxx的部分”时，请作为独立功能调用以下命令：
**⚠️ 重要提示：涉及视频切片处理非常耗时，Agent 调用时请务必使用 `async_run.sh` 脚本！**
```bash
sh scripts/async_run.sh python scripts/extract_by_theme.py <音视频文件路径> "<主题描述>"
# 查询状态: cat output/<文件特征目录>/extract_status.json
```
**功能特性**：
- 先进行毫秒级转字幕。
- 基于大模型进行带上下文分析：如果片段 2 和 4 与主题相关，为了保证语义连贯，会自动保留 2、3、4。
- **自动分块**：对于长于 10000 字符的字幕，脚本会自动按最大安全长度切块后交给 LLM 处理，并最终进行精准的时间轴合并。
- **输出产物**：提取的最终视频会保存为 `output/theme_extract/theme_final.mp4`。
- **状态查询**：Agent 可异步定期读取 `output/theme_extract/extract_status.json` 跟踪进度。

### 4. 智能视频剪辑（极速 5 步法）
当用户请求“智能剪辑”或“精剪”时，确保先运行过 `transcribe.py`，然后调用：
**⚠️ 重要提示：视频处理可能耗时，Agent 调用时请务必使用 `async_run.sh` 脚本！**
```bash
sh scripts/async_run.sh python scripts/clip_video.py output/<视频名>/transcription.json <待剪辑视频路径.mp4>
# 查询状态: cat output/<文件特征目录>/clip_status.json
```
**状态查询**：Agent 可异步定期读取 `output/<文件特征目录>/clip_status.json` 跟踪进度。
脚本将严格执行以下 5 步策略：

#### 第一步：虚拟硬切片 (Metadata Slicing)
- 直接解析时间戳，在内存中计算各片段（带 300ms 缓冲）的绝对时间轴元数据，不产生实体切片文件。

#### 第二步：LLM 语义分析 (Semantic Analysis)
- 文本大模型结构化分析所有台词，精准识别语气词和废话，提取需剔除的“废话原句”。

#### 第三步：字级时间戳精细匹配 (Precise Trimming)
- 将提取的废话原句与 FunASR 字符级时间戳碰撞，计算出毫秒级的绝对剔除区间。

#### 第四步：非语言片段智能保留 (Silence Analysis)
- (可选，受配置控制) 截取语言片段间的静音画面，压缩上传至 COS，交由视觉大模型判定是否有意义（如鼠标交互、运镜等）。

#### 第五步：终极无损合并 (Final Merge)
- 利用 FFmpeg `filter_complex` 基于前面计算的时间轴，一次性从原视频上进行精准挖空、拼接，输出无损成片。

### 5. 独立功能：爆款视频深度分析（多模态解构）
利用 Omini 模型同时处理视频的声音与画面，深度解构爆款视频的成功要素，包含客观的缺陷评估。
**⚠️ 重要提示：涉及视频上传和多模态大模型分析，耗时较长，Agent 调用时请务必使用 `async_run.sh` 脚本！**
```bash
sh scripts/async_run.sh python scripts/analyze_video.py <待分析的视频路径.mp4>
# 查询状态: cat output/<文件特征目录>/analyze_status.json
```
**功能特性**：
- **Token 消耗优化**：在上传前，脚本会自动将视频压缩至 `540p`，既保留了必要的视觉细节（如鼠标动作、界面切换），又极大降低了分析成本。
- **结构化输出**：分析报告包含“视频拆解”、“观众画像”、“爆款策略”、“同步性分析”以及“批判性评估”，最终以 `.md` 格式保存在统一的 `output/` 目录下。
- **状态查询**：Agent 可异步定期读取 `output/<文件特征目录>/analyze_status.json` 跟踪进度。

### 6. 独立功能：声音克隆
基于 IndexTTS-2 提取用户的独特声纹特征，并要求用户指定名称以保存到本地，构建专属的声音样本库。
```bash
# 克隆音色 (添加 sh scripts/async_run.sh 可直接后台异步执行，防止 Agent 卡死)
sh scripts/async_run.sh python scripts/dubbing.py clone --audio <参考音频.mp3> --name <自定义音色名称>
# 查询状态: cat output/<自定义音色名称>/clone_status.json
```
**功能特性**：
- `--text` 参数为**可选**。如果不填，系统会自动调用自带的高精度 ASR 模型（如 SenseVoiceSmall）识别参考音频的文本内容并用于克隆。
- 支持 API 模式和 Local 本地推理模式。
- 克隆成功后，样本信息将持久化保存在 `data/voices/` 目录下，并自动提取 `.pt` 特征文件加速后续合成。

### 7. 独立功能：AI 智能配音 (支持多线程与异步查询)
支持根据高精度 SRT 字幕文件或直接输入纯文本，全自动生成高质量配音。
**⚠️ 重要提示：长文本配音非常耗时，Agent 调用时请务必使用 `async_run.sh` 脚本，它会自动转入后台执行并立即返回，避免 Agent 卡死超时！**

```bash
# 方式一：根据字幕文件配音（使用 async_run.sh 自动后台执行）
sh scripts/async_run.sh python scripts/dubbing.py dub --srt <字幕文件.srt> --voice <音色名> --out <输出音频.mp3>
# 查询状态: cat output/<输出音频所在目录>/dubbing_status.json

# 方式二：根据本地文本文件进行配音（推荐！彻底避免命令行长文本转义失败问题，使用 async_run.sh 自动后台执行）
sh scripts/async_run.sh python scripts/dubbing.py dub --text-file "长文本.md" --voice <音色名> --out <输出音频.mp3>
# 查询状态: cat output/<输出音频所在目录>/dubbing_status.json

# 方式三：直接输入纯文本配音（支持超长文本与副语言标签，使用 async_run.sh 自动后台执行）
sh scripts/async_run.sh python scripts/dubbing.py dub --text "大家晚上好啊[laughter]，今天我们要讲一个很有趣的话题[pause]..." --voice <音色名> --out <输出音频.mp3>
# 查询状态: cat output/<输出音频所在目录>/dubbing_status.json
```
**功能特性**：
- **副语言标签支持**：支持直接在文本中嵌入 `[laughter]`, `[breath]`, `[sigh]`, `[cough]`, `[cry]`, `[smack]`, `[pause]` 等标签，AI 会自动将其转换为极度逼真的声音或停顿，而不会直接读出标签文字。
- **LLM 口语化润色与参数自适应**：在配音前，大模型不仅会自动调整温度、Top K 等参数，还会**直接修改输入文本**，在不改变原意的情况下加入适当的口语化词汇（哈、呢、啊）和自然停顿，避免机器读稿感。（注：如果用户文本已包含副语言标签，大模型将原样保留，不会自作主张添加新的）。
- **智能长文本拆分**：遇到超长文本时，程序会按段落和语义标点智能切分为短句，避免单次生成显存溢出。
- **异步多线程极速合成**：利用线程池（API 最高 15 线程，本地 6 线程带锁保护）并发合成短句音频，合并时自动在段落之间加入 400ms 自然停顿。
- **异步状态查询**：由于本地大模型加载和配音生成非常耗时，**强烈建议使用 `async_run.sh` 脚本**。Agent 可以**立即返回并**每隔 20 秒定期读取 `output/text_dubbing_unknown/dubbing_status.json`（或克隆音色的 `clone_status.json`）以掌握进度，彻底防止工具调用超时卡死。

### 8. 独立功能：智能配字幕与翻译
一键为视频生成字幕并压制，支持基于语境的大模型翻译、语气词过滤与自动折行排版。
**⚠️ 重要提示：视频转码和压制字幕可能比较耗时，Agent 调用时请务必使用 `async_run.sh` 脚本！**
```bash
sh scripts/async_run.sh python scripts/subtitle.py <音视频文件路径> [--lang "目标语言，如：English"] [--out <输出视频路径>]
# 查询状态: cat output/<文件特征目录>/subtitle_status.json
```
**功能特性**：
- 如果不指定 `--lang` 或者与原视频语言一致，则直接进行错别字修正和智能排版折行。
- 如果指定了不同的语言，大模型会自动分析视频专业领域与上下文，进行非生硬的翻译，并自动忽略语气词。
- 自动适配视频宽度，中文超20字符、英文超40字符自动折行，保证排版一致。
- **状态查询**：Agent 可异步定期读取 `output/<文件特征目录>/subtitle_status.json` 跟踪进度。

### 9. 独立功能：自动提取精彩片段
根据视频内容自动提取包含金句、鲜明观点、实用技能的精彩片段，并进行智能剪辑（剔除无用废话）。
**⚠️ 重要提示：涉及视频切片和合并，耗时较长，Agent 调用时请务必使用 `async_run.sh` 脚本！**
```bash
sh scripts/async_run.sh python scripts/highlight.py <音视频文件路径> [--outdir <输出目录>]
# 查询状态: cat output/<文件特征目录>/highlight_status.json
```
**功能特性**：
- 结合语言大模型分析字幕提取 1-3 个最精彩的区间。
- 对每个片段独立执行极速 4 步智能剪辑法，去除其中的无声和废话。
- 每一个精彩片段单独输出为一个成片视频。
- **状态查询**：Agent 可异步定期读取 `output/<文件名>_highlights/highlight_status.json` 跟踪进度。

### 10. 联合处理：提取精彩片段 -> 智能剪辑 -> 配字幕
将上述能力串联，自动完成高光提取、精剪去废话、翻译并压制字幕的全流水线。
**⚠️ 重要提示：极度耗时的终极流程，Agent 调用时请务必使用 `async_run.sh` 脚本！**
```bash
sh scripts/async_run.sh python scripts/combine.py <音视频文件路径> [--lang "目标语言，如：English"] [--outdir <输出目录>]
# 查询状态: cat output/<文件特征目录>/combine_status.json
```
**功能特性**：
- 自动化端到端输出最终可发布的短视频矩阵。
- **状态查询**：Agent 可异步定期读取 `output/<文件名>_combined_highlights/combine_status.json` 跟踪进度。

### 11. 独立功能：PPT 视频生成
当用户提供多个场景的“图片+文字”组合时，系统会自动将图片作为背景，将文字进行 AI 配音，并为每一段加上字幕，最后拼成一个完整的视频。
**⚠️ 重要提示：由于涉及多次配音和视频合并，非常耗时，Agent 调用时请务必使用 `async_run.sh` 脚本！**
```bash
# 首先，将用户提供的场景数据保存为 scenes.json，格式如下：
# [
#   {"image_url": "http://...", "text": "第一段文字"},
#   {"image_url": "http://...", "text": "第二段文字"}
# ]
sh scripts/async_run.sh python scripts/ppt_video.py --scenes scenes.json [--voice "default"] [--out "output/ppt_final.mp4"]
# 注意：该脚本目前没有专用的 status.json，请 Agent 根据任务完成情况合理预估或检查最终文件是否生成。
```
**功能特性**：
- 自动下载每个场景的图片，缩放至 1920x1080 (带黑边填充避免变形)。
- 对文字进行自然流畅的 AI 配音。
- 使用 ffmpeg 生成“图片+声音”的单场景视频，并在声音结束时自动切换到下一个场景。
- 自动为每个场景压制字幕，最后无缝拼接成完整成片。

## 异常处理与性能
- 并发推理时需注意缓存冲突（可通过队列或单线程处理避免）。
- 遇到解码错误应跳过该片段并记录日志，不可中断整体长视频处理。
