import os
import sys

# 确保可以引入 scripts 目录下的其他模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import load_config, create_openai_client, get_unified_output_dir

import json
import argparse
import requests
import re
import concurrent.futures
import subprocess
from pydub import AudioSegment
import tempfile

def split_text_into_paragraphs_and_sentences(text, max_len=150):
    """
    仅按段落拆分文本，不再进行标点符号碎拆。
    返回: list of paragraphs, 每个 paragraph 是一组句子的列表 (list of str)（这里每个列表只有一个元素即整个段落）
    """
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    
    # 检查超长段落并发出警告
    for idx, p in enumerate(paragraphs):
        if len(p) > max_len:
            print(f"警告: 段落 {idx+1} 长度为 {len(p)} 字符，超过建议长度 {max_len} 字符，将完整保留不拆分。")
            
    # 返回段落列表（每个段落作为单个元素）
    return [[p] for p in paragraphs]

def synthesize_worker(args):
    idx, text, api_key, voice_id, mode, model, tts_params, temp_dir, engine, config = args
    temp_audio_path = os.path.join(temp_dir, f"chunk_{idx}.mp3")
    print(f"[{idx}] 正在合成: {text[:20]}...")
    success = synthesize_speech(api_key, text, voice_id, temp_audio_path, mode=mode, model=model, tts_params=tts_params, engine=engine, config=config)
    if success:
        return idx, temp_audio_path
    else:
        return idx, None

def dub_text(api_key, text, voice_id, output_audio_path, mode="api", model=None, tts_params=None, engine="indextts", config=None):
    print("正在对长文本进行拆分...")
    paragraphs = split_text_into_paragraphs_and_sentences(text)
    
    # 扁平化所有片段，并记录它们所属的段落，以便后续合并
    flat_chunks = []
    chunk_idx = 0
    for p_idx, sentences in enumerate(paragraphs):
        for s_idx, sentence in enumerate(sentences):
            flat_chunks.append({
                "idx": chunk_idx,
                "p_idx": p_idx,
                "text": sentence
            })
            chunk_idx += 1
            
    print(f"文本共拆分为 {len(paragraphs)} 个段落，总计 {len(flat_chunks)} 个配音片段。")
    
    if not flat_chunks:
        print("没有可配音的文本内容！")
        return

    # 如果没有指定输出路径，提供一个默认的
    if not output_audio_path:
        config = load_config()
        output_dir = get_unified_output_dir("text_dubbing.txt", config)
        output_audio_path = os.path.join(output_dir, "dubbed_text.mp3")
    else:
        output_dir = os.path.dirname(output_audio_path)
        if not output_dir:
            config = load_config()
            output_dir = get_unified_output_dir("text_dubbing.txt", config)
            output_audio_path = os.path.join(output_dir, output_audio_path)

    temp_dir = os.path.join(output_dir, "temp_dubbing_chunks")
    os.makedirs(temp_dir, exist_ok=True)
    
    # 状态文件，用于供外部（如 Agent）查询进度
    status_file = os.path.join(output_dir, "dubbing_status.json")
    
    def update_status(completed, total, current_text=""):
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump({
                "status": "processing" if completed < total else "completed",
                "completed_chunks": completed,
                "total_chunks": total,
                "current_text": current_text,
                "progress_percent": round((completed / total) * 100, 2) if total > 0 else 0
            }, f, ensure_ascii=False)
            
    update_status(0, len(flat_chunks), "开始初始化多线程配音...")
    
    # 多线程并发生成
    max_workers = 6 if mode == "local" else 15
    print(f"开始多线程配音，最大线程数: {max_workers}")
    
    tasks = []
    for chunk in flat_chunks:
        tasks.append((chunk["idx"], chunk["text"], api_key, voice_id, mode, model, tts_params, temp_dir, engine, config))
        
    results = {}
    completed_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(synthesize_worker, task): task for task in tasks}
        for future in concurrent.futures.as_completed(futures):
            idx, path = future.result()
            results[idx] = path
            completed_count += 1
            # 获取对应的文本用于状态更新
            current_text = next((c["text"] for c in flat_chunks if c["idx"] == idx), "")
            update_status(completed_count, len(flat_chunks), current_text)

    # 按照原始顺序合并音频
    print("开始合并配音片段...")
    final_audio = AudioSegment.empty()
    pause_400ms = AudioSegment.silent(duration=400)
    
    current_p_idx = 0
    for chunk in flat_chunks:
        idx = chunk["idx"]
        p_idx = chunk["p_idx"]
        
        # 跨段落时添加 400ms 停顿
        if p_idx > current_p_idx:
            final_audio += pause_400ms
            current_p_idx = p_idx
            
        path = results.get(idx)
        if path and os.path.exists(path):
            try:
                seg_audio = AudioSegment.from_file(path)
                final_audio += seg_audio
            except Exception as e:
                print(f"合并片段 [{idx}] 失败: {e}")
        else:
            print(f"警告: 片段 [{idx}] 生成失败，已跳过。")
            
    # 清理临时文件
    try:
        import shutil
        shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"清理临时目录失败: {e}")

    # 导出最终音频
    print(f"导出最终配音文件到: {output_audio_path}")
    final_audio.export(output_audio_path, format="mp3")
    print("配音完成！")
    
    # 写入最终状态
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump({
            "status": "done",
            "completed_chunks": len(flat_chunks),
            "total_chunks": len(flat_chunks),
            "output_file": output_audio_path,
            "progress_percent": 100
        }, f, ensure_ascii=False)

def analyze_text_for_tts_params(text, config, tts_params_override=None):
    # 默认配音参数（先从 config 读取，如果没有则使用硬编码默认值）
    default_params = {
        "temperature": float(config.get("TTS_DEFAULT_TEMPERATURE", 0.65)),
        "top_k": int(config.get("TTS_DEFAULT_TOP_K", 40)),
        "top_p": float(config.get("TTS_DEFAULT_TOP_P", 0.8)),
        "max_text_tokens_per_segment": int(config.get("TTS_DEFAULT_MAX_TEXT_TOKENS", 130))
    }
    
    llm_url = config.get("TEXT_LLM_URL")
    llm_api_key = config.get("TEXT_LLM_API_KEY")
    llm_model = config.get("TEXT_LLM_MODEL_NAME", "deepseek-chat")
    
    if not llm_url or not llm_api_key:
        print("未配置 TEXT_LLM_URL 或 TEXT_LLM_API_KEY，使用默认配音参数。")
        final_params = default_params.copy()
        if tts_params_override:
            final_params.update(tts_params_override)
        return final_params, text
        
    print("正在使用大模型分析文本情景以优化配音参数...")
    client = create_openai_client(llm_api_key, llm_url)
    
    prompt = f"""你是一个专业的配音导演和 IndexTTS-2 调参专家。请分析以下文本的情境、情感和语气需求，并输出一组适合 IndexTTS-2 的参数。

除了参数分析外，请务必**大力修改并润色文本**，使其极具自然口语表达感：
1. **必须加入大量口语化语气词**（如：哈、啊、呢、哎、啦、哦等），让生硬的文字变得像日常聊天一样自然。
2. 遇到长句时，不要随意切断成很多小句，**保持原有的段落结构**，只在合适的地方加入逗号或微小的停顿。
3. 整体风格要像一个人在镜头前自然地聊天或演讲，绝对不能有“机器读稿感”或“书面宣读感”。
4. **重要**：如果用户传入的文本中自带了情绪标签（如 `[惊讶:1.2]`, `[高兴:0.8]` 等），请**原样保留它们**在原本的位置。但是，**你绝对不能自己主动添加任何新的标签**。你的任务只是润色文字，禁止无中生有地添加任何 `[xxx]` 或 `[xxx:x.x]` 格式的内容。
5. 请将修改后带有浓厚口语化风格的文本，放在 JSON 的 `refined_text` 字段中。**必须保证段落结构不变（原先有几段，修改后仍是几段）**。

当前系统配置的基准配音参数为：
- temperature: {default_params['temperature']}
- top_k: {default_params['top_k']}
- top_p: {default_params['top_p']}
- max_text_tokens_per_segment: {default_params['max_text_tokens_per_segment']}

请根据上述基准参数，结合文本情感进行**微调**。
如果文本情绪平稳，请尽量保持基准参数不变。
如果情绪激烈或有特殊需求，可以适当调整。

请输出一个 JSON 对象，不要包含其他任何解释文字或 Markdown 标记。格式如下：
{{
    "temperature": 0.65,
    "top_k": 40,
    "top_p": 0.8,
    "max_text_tokens_per_segment": 130,
    "max_mel_tokens": 1500,
    "refined_text": "修改后带有口语化语气词的文本..."
}}

待分析文本：
""" + text[:2000]

    try:
        response = client.chat.completions.create(
            model=llm_model,
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.choices[0].message.content.strip()
        
        # 尝试提取 JSON
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            result = result.split("```")[1].split("```")[0].strip()
            
        params = json.loads(result)
        refined_text = params.pop("refined_text", text)
        
        # 将大模型未返回的参数用默认参数补齐
        final_params = default_params.copy()
        final_params.update(params)
        
        # 如果外部有强制指定的参数，优先级最高，进行覆盖
        if tts_params_override:
            final_params.update(tts_params_override)
            
        print(f"分析完成，应用参数: {json.dumps(final_params, ensure_ascii=False)}")
        return final_params, refined_text
    except Exception as e:
        print(f"参数分析失败，使用默认参数: {e}")
        final_params = default_params.copy()
        if tts_params_override:
            final_params.update(tts_params_override)
        return final_params, text

# 解析 SRT 时间戳为毫秒
def parse_time(time_str):
    # 00:00:01,234
    h, m, s_ms = time_str.split(":")
    s, ms = s_ms.split(",")
    return (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + int(ms)

def parse_srt(srt_path):
    subs = []
    with open(srt_path, "r", encoding="utf-8") as f:
        blocks = f.read().strip().split("\n\n")
        for block in blocks:
            lines = block.split("\n")
            if len(lines) >= 3:
                idx = lines[0]
                times = lines[1].split(" --> ")
                text = " ".join(lines[2:])
                if len(times) == 2:
                    start_ms = parse_time(times[0])
                    end_ms = parse_time(times[1])
                    subs.append({"index": idx, "start": start_ms, "end": end_ms, "text": text})
    return subs

def auto_transcribe_audio(audio_path, config):
    print(f"未提供文本内容，正在检查缓存或自动识别音频: {audio_path}")
    
    # 获取统一的输出目录
    specific_output_dir = get_unified_output_dir(audio_path, config)
    cache_txt_path = os.path.join(specific_output_dir, "auto_transcribe_cache.txt")
    
    # 检查缓存
    if os.path.exists(cache_txt_path):
        try:
            with open(cache_txt_path, "r", encoding="utf-8") as f:
                cached_text = f.read().strip()
            if cached_text:
                print(f"✅ 发现已存在的识别记录，跳过大模型调用！直接使用: {cached_text}")
                return cached_text
        except Exception as e:
            print(f"读取历史识别结果失败，将重新识别: {e}")

    try:
        from funasr import AutoModel
    except ImportError:
        print("缺少 funasr 库，无法进行 ASR 识别。请先执行 pip install funasr")
        sys.exit(1)
        
    config = load_config()
    model_dir = config.get("MODEL_DIR")
    os.makedirs(model_dir, exist_ok=True)
    
    model_id = "iic/SenseVoiceSmall"
    
    try:
        # 直接使用 FunASR AutoModel 进行推理，避免引入 modelscope 的冗余依赖和潜在冲突
        model = AutoModel(
            model=model_id,
            trust_remote_code=True,
            remote_code="./model.py",
            vad_model="fsmn-vad",
            vad_kwargs={"max_single_segment_time": 30000},
            device="cpu"
        )
        
        res = model.generate(
            input=audio_path,
            cache={},
            language="auto",
            use_itn=True,
            batch_size_s=60
        )
        
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from vocab_utils import load_vocab, apply_vocab_to_result
        
        vocab_path = os.path.join("data", "hotwords.yaml")
        vocab = load_vocab(vocab_path)
        if vocab:
            print(f"应用专业词库 ({len(vocab)} 个映射规则)...")
            res = apply_vocab_to_result(res, vocab)
        
        if isinstance(res, list) and len(res) > 0 and 'text' in res[0]:
            # SenseVoiceSmall 可能会输出带语种和情感标签的文本，如 <|zh|><|NEUTRAL|><|Speech|>你好
            text = res[0]['text']
            import re
            # 清理标签
            clean_text = re.sub(r'<\|.*?\|>', '', text).strip()
            print(f"ASR 自动识别结果: {clean_text}")
            with open(cache_txt_path, "w", encoding="utf-8") as f:
                f.write(clean_text)
            return clean_text
        elif isinstance(res, dict) and 'text' in res:
            text = res['text']
            import re
            clean_text = re.sub(r'<\|.*?\|>', '', text).strip()
            print(f"ASR 自动识别结果: {clean_text}")
            with open(cache_txt_path, "w", encoding="utf-8") as f:
                f.write(clean_text)
            return clean_text
        else:
            print(f"ASR 识别结果格式异常: {res}")
            sys.exit(1)
    except Exception as e:
        print(f"ASR 自动识别失败: {e}")
        sys.exit(1)

def get_voices_dir():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    voices_dir = os.path.join(base_dir, "data", "voices")
    os.makedirs(voices_dir, exist_ok=True)
    return voices_dir

def get_saved_voices():
    voices_dir = get_voices_dir()
    voices = {}
    for name in os.listdir(voices_dir):
        meta_path = os.path.join(voices_dir, name, "meta.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    voices[name] = json.load(f)
            except Exception:
                pass
    return voices

def migrate_old_voices_json():
    old_json_path = "voices.json"
    if os.path.exists(old_json_path):
        try:
            print("正在将旧版 voices.json 迁移至标准的 data/voices/ 目录结构...")
            with open(old_json_path, "r", encoding="utf-8") as f:
                old_voices = json.load(f)
            
            voices_dir = get_voices_dir()
            for name, info in old_voices.items():
                voice_path = os.path.join(voices_dir, name)
                os.makedirs(voice_path, exist_ok=True)
                
                # 拷贝本地音频到标准路径
                local_audio = info.get("local_audio")
                if local_audio and os.path.exists(local_audio):
                    import shutil
                    new_audio_path = os.path.join(voice_path, "ref_audio.wav")
                    # 使用 pydub 统一转换为 wav 格式
                    try:
                        audio = AudioSegment.from_file(local_audio)
                        audio.export(new_audio_path, format="wav")
                        info["local_audio"] = new_audio_path
                    except Exception as e:
                        print(f"转换音频失败 {local_audio}: {e}")
                        shutil.copy2(local_audio, new_audio_path)
                        info["local_audio"] = new_audio_path
                        
                with open(os.path.join(voice_path, "meta.json"), "w", encoding="utf-8") as f:
                    json.dump(info, f, ensure_ascii=False, indent=2)
                    
            # 备份旧文件
            os.rename(old_json_path, old_json_path + ".bak")
            print("迁移完成！\n")
        except Exception as e:
            print(f"迁移旧版 voices.json 失败: {e}")

def clone_voice(api_key, ref_audio_path, text, voice_name, mode="api", model=None, config=None, engine="indextts"):
    if not config:
        config = load_config()
    if not text:
        text = auto_transcribe_audio(audio_path, config)
        if not text:
            print("自动识别文本为空，无法进行克隆。")
            sys.exit(1)
            
    # 准备保存的目录结构
    voices_dir = get_voices_dir()
    voice_path = os.path.join(voices_dir, voice_name)
    os.makedirs(voice_path, exist_ok=True)
    
    # 统一转换音频格式为 wav，并保存到标准库中
    ref_audio_path = os.path.join(voice_path, "ref_audio.wav")
    try:
        audio = AudioSegment.from_file(audio_path)
        audio.export(ref_audio_path, format="wav")
    except Exception as e:
        print(f"音频转换失败，尝试直接拷贝: {e}")
        import shutil
        shutil.copy2(audio_path, ref_audio_path)
        
    meta = {
        "name": voice_name,
        "text": text,
        "mode": mode,
        "original_audio": audio_path,
        "local_audio": ref_audio_path,
        "engine": engine
    }
            
    if engine == "qwen3-tts":
        print(f"正在配置 Qwen3-TTS 声音样本进行克隆: {ref_audio_path}")
        # Qwen3-TTS 无论是 local 还是 api，都只需要保存音频和文本
        # 它支持 zero-shot 推理，无需提前提取特征
        with open(os.path.join(voice_path, "meta.json"), "w", encoding="utf-8") as vf:
            json.dump(meta, vf, ensure_ascii=False, indent=2)
            
        print(f"音色已保存到本地样本库目录 {voice_path} (Qwen3-TTS)")
        return "qwen:" + ref_audio_path

    if not model:
        model = config.get("INDEXTTS_MODEL_NAME", "IndexTeam/IndexTTS-2")
        
    if mode == "local":
        print(f"正在配置本地声音样本进行克隆: {ref_audio_path}")
        
        # 保存元数据
        with open(os.path.join(voice_path, "meta.json"), "w", encoding="utf-8") as vf:
            json.dump(meta, vf, ensure_ascii=False, indent=2)
            
        print(f"音色已保存到本地样本库目录 {voice_path} (本地模式)")
        
        # 自动触发特征提取并持久化为 .pt 文件，加快后续配音速度
        print("正在提取并持久化音色特征，以提升后续生成速度...")
        try:
            model = get_local_tts_model()
            # 这里的 get_local_tts_model 返回的是 IndexTTS2 对象
            # 触发一次简单的假推理（不产生实际文件输出）来让底层的特征持久化逻辑运行
            # 但是为了避免真的产生音频，我们只需要触发它的前向即可，或者依赖我们在 infer_v2 里的逻辑：
            # 既然我们已经在 infer_v2 里加上了保存 .pt 的逻辑，这里只要触发一次完整的加载和前向即可
            dummy_wav = ref_audio_path + ".dummy.wav"
            try:
                # 只生成几个字，让它走通特征提取并保存的逻辑
                model.infer(ref_audio_path, text[:2], output_path=dummy_wav)
            except Exception:
                pass
            if os.path.exists(dummy_wav):
                os.remove(dummy_wav)
            print(f"音色特征提取完成，已持久化到: {ref_audio_path}.pt")
        except Exception as e:
            print(f"持久化音色特征时出错 (不影响使用，但下次会重新提取): {e}")
            
        return "local:" + ref_audio_path

    print(f"正在上传声音样本进行克隆: {ref_audio_path}")
    # 硅基流动平台的 URL 可以通过配置指定，默认值为其公有云接口
    url = config.get("INDEXTTS_URL", "https://api.siliconflow.cn/v1/audio/speech").replace("/audio/speech", "/uploads/audio/voice")
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    with open(ref_audio_path, "rb") as f:
        files = {"file": f}
        data = {
            "model": model,
            "customName": voice_name,
            "text": text
        }
        response = requests.post(url, headers=headers, files=files, data=data)
    
    if response.status_code == 200:
        result = response.json()
        voice_uri = result.get("uri")
        print(f"声音克隆成功！音色 ID (URI): {voice_uri}")
        
        # 存入本地样本库
        meta["uri"] = voice_uri
        with open(os.path.join(voice_path, "meta.json"), "w", encoding="utf-8") as vf:
            json.dump(meta, vf, ensure_ascii=False, indent=2)
        print(f"音色已保存到本地样本库目录 {voice_path}")
        return voice_uri
    else:
        print(f"克隆失败: {response.status_code} {response.text}")
        sys.exit(1)

import threading

_local_tts_model = None
_tts_model_lock = threading.Lock()
_tts_infer_lock = threading.Lock()

# ==================== Qwen3-TTS 逻辑 ====================

qwen_tts_model_cache = None

def get_qwen3tts_model(model_path="Qwen/Qwen3-TTS-12Hz-0.6B-Base"):
    global qwen_tts_model_cache
    if qwen_tts_model_cache is not None:
        return qwen_tts_model_cache
        
    print(f"正在加载 Qwen3-TTS 模型 ({model_path})...")
    try:
        from qwen_tts import Qwen3TTSModel
        import torch
        device = "cuda:0" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
        qwen_tts_model_cache = Qwen3TTSModel.from_pretrained(
            model_path,
            device_map=device,
            dtype=torch.bfloat16 if device != "cpu" else torch.float32,
        )
        print("Qwen3-TTS 模型加载成功！")
        return qwen_tts_model_cache
    except Exception as e:
        print(f"加载 Qwen3-TTS 模型失败: {e}")
        return None

def synthesize_speech_qwen3tts(api_key, text, voice_id, output_path, mode="api", model=None, tts_params=None, parsed_tags=None, config=None):
    if not config:
        config = load_config()
    
    if not model:
        model = config.get("QWEN3TTS_MODEL_NAME", "qwen3-tts")
    if not text.strip():
        print("文本为空，跳过 Qwen3-TTS 合成")
        return False
        
    # 获取音色信息
    ref_audio = None
    ref_text = None
    
    if voice_id.startswith("qwen:"):
        ref_audio = voice_id[5:]
        voices_dir = get_voices_dir()
        for vname in os.listdir(voices_dir):
            vpath = os.path.join(voices_dir, vname)
            meta_path = os.path.join(vpath, "meta.json")
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                if meta.get("local_audio") == ref_audio:
                    ref_text = meta.get("text")
                    break
    else:
        # 如果不是自定义音色，处理内置音色
        pass
        
    if mode == "local":
        model_path = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
        qwen_model = get_qwen3tts_model(model_path)
        if not qwen_model:
            return False
            
        try:
            import soundfile as sf
            with _tts_infer_lock: # 复用全局锁
                if ref_audio and ref_text:
                    wavs, sr = qwen_model.generate_voice_clone(
                        text=text,
                        language="Chinese",
                        ref_audio=ref_audio,
                        ref_text=ref_text,
                    )
                else:
                    # 基础合成，使用预设的音色或不提供参考
                    # 待补充，这里简单调用
                    wavs, sr = qwen_model.generate_custom_voice(
                        text=text,
                        language="Chinese"
                    )
            sf.write(output_path, wavs[0], sr)
            print(f"Qwen3-TTS (Local) 语音合成成功，保存到 {output_path}")
            return True
        except Exception as e:
            print(f"Qwen3-TTS (Local) 语音合成失败: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    elif mode == "api":
        try:
            import dashscope
            dashscope.api_key = api_key or (config.get("QWEN3TTS_API_KEY", "") if config else "")
            
            # 使用配置中的 base_url（如果存在且有效）
            base_url = config.get("QWEN3TTS_URL", "") if config else ""
            if base_url:
                dashscope.base_http_api_url = base_url
                
            # 使用 MultiModalConversation 接口进行合成和克隆
            print(f"调用 DashScope {model} 接口...")
            
            messages = []
            if ref_audio and ref_text:
                # 构造克隆模式的 messages
                ref_audio_uri = f"file://{ref_audio}" if not ref_audio.startswith(("http", "file://")) else ref_audio
                messages = [{
                    "role": "user",
                    "content": [
                        {"audio": ref_audio_uri},
                        {"text": f"<|ref_audio|>\n<|text|>{ref_text}\n<|gen_text|>{text}"}
                    ]
                }]
            else:
                # 基础合成模式
                # 如果没有 voice 参数，这里默认传一个系统音色或仅传文本
                # 为了兼容性，如果没有配置，我们可以尝试仅传文本
                messages = [{
                    "role": "user",
                    "content": [
                        {"text": f"<|gen_text|>{text}"}
                    ]
                }]

            response = dashscope.MultiModalConversation.call(
                model=model if model != "qwen3-tts" else "qwen3-tts-flash",
                messages=messages,
                language_type="Chinese",
            )
            
            if response.status_code == 200:
                # 处理返回的音频
                # response.output.audio 可能是字节流或者包含在 response 中
                if hasattr(response, 'output') and hasattr(response.output, 'audio') and response.output.audio is not None:
                    # 某些版本可能返回 base64 或直接提供二进制数据
                    audio_data = response.output.audio.data if hasattr(response.output.audio, 'data') else response.output.audio
                    with open(output_path, 'wb') as f:
                        f.write(audio_data)
                    print(f"Qwen3-TTS (API) 语音合成成功，保存到 {output_path}")
                    return True
                else:
                    # 回退到基础 TTS
                    print("Qwen3-TTS API 返回格式不支持，尝试回退基础合成...")
                    # ... 如果需要
                    
            print(f"Qwen3-TTS (API) 失败: {response}")
            return False
        except Exception as e:
            print(f"Qwen3-TTS (API) 调用异常: {e}")
            import traceback
            traceback.print_exc()
            return False

# ========================================================

def get_local_tts_model():
    global _local_tts_model
    with _tts_model_lock:
        if _local_tts_model is not None:
            return _local_tts_model
            
        try:
            from modelscope import snapshot_download
        except ImportError:
            print("缺少 modelscope 库，请执行: pip install modelscope")
            sys.exit(1)
            
        print("正在检查/下载 IndexTTS 本地模型 (首次运行可能需要一些时间)...")
        config = load_config()
        model_base = config.get("MODEL_DIR")
        os.makedirs(model_base, exist_ok=True)
        
        model_dir = snapshot_download('IndexTeam/IndexTTS-2', cache_dir=model_base)
        
        try:
            import indextts
        except ImportError:
            print("错误: 未找到 indextts。请先安装 IndexTTS 运行环境。")
            print("安装参考:")
            print("  git clone https://github.com/index-tts/index-tts.git")
            print("  cd index-tts")
            print("  pip install -r requirements.txt")
            print("  pip install -e .")
            sys.exit(1)
            
        try:
            import torch
            device = "cuda:0" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"
            
        try:
            # 尝试使用 v2 接口
            from indextts.infer_v2 import IndexTTS2
            _local_tts_model = IndexTTS2(
                cfg_path=os.path.join(model_dir, "config.yaml"),
                model_dir=model_dir,
                device=device
            )
        except ImportError:
            try:
                # 回退到 v1 接口
                from indextts.infer import IndexTTS
                _local_tts_model = IndexTTS(
                    model_dir=model_dir,
                    cfg_path=os.path.join(model_dir, "config.yaml")
                )
            except Exception as e:
                print(f"本地模型加载失败: {e}")
                sys.exit(1)
                
        return _local_tts_model

def synthesize_speech_local(text, voice_audio, output_path, tts_params=None):
    if tts_params is None:
        tts_params = {}
    model = get_local_tts_model()
    
    # 强制 IndexTTS 输出 .wav 格式，避免 torchaudio 直接保存 .mp3 出现整数溢出导致的沙沙声杂音
    temp_wav_path = output_path + ".temp.wav"
    
    with _tts_infer_lock:
        try:
            # v2 接口参数
            infer_kwargs = {
                "spk_audio_prompt": voice_audio,
                "text": text,
                "output_path": temp_wav_path
            }
            # 注入分析出的参数
            for k, v in tts_params.items():
                infer_kwargs[k] = v
                
            model.infer(**infer_kwargs)
            
            # 将生成的 wav 转换为目标格式 (mp3)
            if os.path.exists(temp_wav_path):
                # 使用 librosa 加载音频以自动将 16-bit 整数缩放至浮点数
                import librosa
                import soundfile as sf
                
                y, sr = librosa.load(temp_wav_path, sr=None)
                
                if output_path.lower().endswith(".mp3"):
                    # 已经确保数据缩放正确，直接使用 pydub 转换格式
                    audio = AudioSegment.from_wav(temp_wav_path)
                    audio.export(output_path, format="mp3")
                else:
                    import shutil
                    shutil.move(temp_wav_path, output_path)
                
                if os.path.exists(temp_wav_path):
                    os.remove(temp_wav_path)
            return True
        except TypeError:
            try:
                # v1 接口参数
                model.infer(voice_audio, text, output_path=temp_wav_path)
                
                if os.path.exists(temp_wav_path):
                    import librosa
                    import soundfile as sf
                    
                    y, sr = librosa.load(temp_wav_path, sr=None)
                    
                    if output_path.lower().endswith(".mp3"):
                        audio = AudioSegment.from_wav(temp_wav_path)
                        audio.export(output_path, format="mp3")
                    else:
                        import shutil
                        shutil.move(temp_wav_path, output_path)
                        
                    if os.path.exists(temp_wav_path):
                        os.remove(temp_wav_path)
                return True
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"本地合成失败 (v1): {e}")
                return False
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"本地合成失败 (v2): {e}")
            return False

def synthesize_speech(api_key, text, voice_id, output_path, mode="api", model=None, tts_params=None, engine="indextts", config=None):
    if not config:
        config = load_config()
    print(f"[{mode}模式] 正在调用 {engine} 进行语音合成...")
    if tts_params is None:
        tts_params = {}
    else:
        tts_params = tts_params.copy()
        
    # --- 解析并移除情绪标签（如 [惊讶:1.2]），转换为 IndexTTS emo_vector ---
    emotion_tags = ["高兴", "愤怒", "悲伤", "恐惧", "反感", "低落", "惊讶", "自然"]
    import re
    matches = re.finditer(r'\[([^\]:]+):([\d.]+)\]', text)
    emo_vector = None
    parsed_tags = []
    for match in matches:
        emo_name = match.group(1)
        if emo_name in emotion_tags:
            try:
                emo_val = float(match.group(2))
                emo_vector = [0.0] * 8
                emo_index = emotion_tags.index(emo_name)
                emo_vector[emo_index] = emo_val
                parsed_tags.append({"type": "emotion", "name": emo_name, "intensity": emo_val})
                print(f"    -> 成功解析情绪标签: {emo_name} (强度: {emo_val})")
            except ValueError:
                pass
    if emo_vector:
        tts_params["emo_vector"] = emo_vector
        
    # 将所有的情绪标签（无论是否支持）都从文本中移除，避免被当做文字读出来
    clean_text = re.sub(r'\[([^\]:]+):([\d.]+)\]', '', text).strip()

    # 移除原本对副语言标签（如 [laughter] 等）的映射支持，因为模型无法生成逼真效果。
    # 我们直接通过正则将可能残留的副语言标签彻底删除，避免读出来。
    clean_text = re.sub(r'\[(?:laughter|laugh|breath|sigh|cough|cry|smack|uv_break|pause)\]', '', clean_text, flags=re.IGNORECASE)
    
    # 进一步兜底，移除所有未被识别的方括号内容，防止作为文本读出
    clean_text = re.sub(r'\[[^\]]+\]', '', clean_text).strip()

    if engine == "qwen3-tts":
        return synthesize_speech_qwen3tts(api_key, clean_text, voice_id, output_path, mode, model, tts_params, parsed_tags, config)
        
    if not model:
        model = config.get("INDEXTTS_MODEL_NAME", "IndexTeam/IndexTTS-2")
        
    # 保持向后兼容的 text 变量覆盖
    text = clean_text

    if mode == "local":
        # local 模式下，voice_id 实际上是本地音频的路径
        local_audio_path = voice_id.replace("local:", "") if voice_id.startswith("local:") else voice_id
        
        # 处理默认音色
        if local_audio_path.startswith("IndexTeam/IndexTTS-2:"):
            # 如果是默认音色，我们在运行时临时生成一个或要求用户提供
            # 因为 index-tts 自带的 examples 音频可能是 git-lfs 指针文件并未真实下载
            print("提示: 默认音色需要依赖真实的参考音频。请使用 clone 功能先克隆一个音色，或在 voices.json 中配置。")
            return False
                
        if not os.path.exists(local_audio_path):
            print(f"本地参考音频不存在: {local_audio_path}")
            return False
        return synthesize_speech_local(text, local_audio_path, output_path, tts_params)
        
    if engine == "indextts":
        url = config.get("INDEXTTS_URL", "https://api.siliconflow.cn/v1/audio/speech")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "input": text,
            "voice": voice_id,
            "response_format": "mp3",
            "sample_rate": 32000,
            "stream": False,
            "speed": 1.0,
            "gain": 0.0
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            return True
        else:
            print(f"语音合成失败: {response.status_code} {response.text}")
            return False

def dub_subtitle(api_key, srt_path, voice_id, output_audio_path=None, mode="api", model=None, tts_params=None, engine="indextts", config=None):
    print(f"解析字幕文件: {srt_path}")
    subs = parse_srt(srt_path)
    if not subs:
        print("未找到有效的字幕片段！")
        return
        
    if not config:
        config = load_config()
    output_dir = get_unified_output_dir(srt_path, config)
    
    if not output_audio_path:
        base_name = os.path.basename(srt_path)
        name_without_ext, _ = os.path.splitext(base_name)
        output_audio_path = os.path.join(output_dir, f"{name_without_ext}_dubbed.mp3")
    
    # 获取总时长
    total_duration = subs[-1]["end"]
    print(f"字幕总片段数: {len(subs)}, 预计总时长: {total_duration}ms")
    
    # 创建一个静音的音频背景
    final_audio = AudioSegment.silent(duration=total_duration)
    
    temp_dir = os.path.join(output_dir, "temp_dubbing")
    os.makedirs(temp_dir, exist_ok=True)
    
    for sub in subs:
        text = sub["text"].strip()
        if not text:
            continue
            
        print(f"[{sub['index']}] 正在合成: {text}")
        temp_audio_path = os.path.join(temp_dir, f"sub_{sub['index']}.mp3")
        
        # 合成语音
        success = synthesize_speech(api_key, text, voice_id, temp_audio_path, mode=mode, model=model, tts_params=tts_params, engine=engine, config=config)
        if success:
            # 读取合成的音频
            seg_audio = AudioSegment.from_file(temp_audio_path)
            
            # 将音频叠加到对应的时间戳位置
            final_audio = final_audio.overlay(seg_audio, position=sub["start"])
        else:
            print(f"跳过片段 {sub['index']} 因为合成失败。")
            
    print(f"导出最终配音文件到: {output_audio_path}")
    final_audio.export(output_audio_path, format="mp3")
    print("配音完成！")
    return output_audio_path



def main():
    migrate_old_voices_json()
    
    parser = argparse.ArgumentParser(description="Media Skill 语音合成与克隆工具 (基于 SiliconFlow IndexTTS-2)")
    
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # clone 子命令
    clone_parser = subparsers.add_parser("clone", help="提取个人声音特征并以自定义名称保存至本地样本库")
    clone_parser.add_argument("--audio", required=True, help="参考音频文件路径")
    clone_parser.add_argument("--text", help="参考音频中的文字内容（可选，如果不填则自动使用 ASR 识别）")
    clone_parser.add_argument("--name", required=True, help="自定义音色名称（用于后续配音任务）")
    
    # dub 子命令
    dub_parser = subparsers.add_parser("dub", help="基于字幕文件与本地样本库生成对齐的配音文件")
    dub_parser.add_argument("--srt", help="输入的高精度 SRT 字幕文件路径")
    dub_parser.add_argument("--text", help="直接输入需要配音的文字内容")
    dub_parser.add_argument("--text-file", help="输入需要配音的长文本文件路径 (例如 .md 或 .txt)，避免命令行传递长文本引发的转义问题")
    dub_parser.add_argument("--voice", help="本地样本库中保存的自定义音色名称")
    dub_parser.add_argument("--out", help="输出的音频文件路径 (如 output.mp3)。如果不填，默认生成到统一 output 目录下。")
    # 添加高级配音参数支持
    dub_parser.add_argument("--temperature", type=float, help="控制情绪波动，范围 0.1~1.0")
    dub_parser.add_argument("--top_k", type=int, help="控制候选词范围，范围 10~50")
    dub_parser.add_argument("--top_p", type=float, help="平稳度控制，范围 0.5~0.95")
    dub_parser.add_argument("--max_text_tokens", type=int, help="单句最大长度，范围 50~150")
    
    args = parser.parse_args()
    
    config = load_config()
    
    # 动态确定引擎和模式
    engine = config.get("TTS_ENGINE", "indextts").strip().lower()
    
    if engine == "qwen3-tts":
        mode = config.get("QWEN3TTS_MODE", "api").strip().lower()
        api_key = config.get("QWEN3TTS_API_KEY", "")
        if mode == "api" and not api_key:
            print("错误: 在 api 模式下使用 Qwen3-TTS，请在 config.txt 中配置有效的 QWEN3TTS_API_KEY")
            sys.exit(1)
    else:
        mode = config.get("INDEXTTS_MODE", "api").strip().lower()
        api_key = config.get("INDEXTTS_API_KEY", "")
        if mode == "api" and (not api_key or api_key == "your_indextts_api_key_here"):
            print("错误: 在 api 模式下使用 IndexTTS，请在 config.txt 中配置有效的 INDEXTTS_API_KEY")
            print("提示: 如果想在本地运行，请在 config.txt 中设置 INDEXTTS_MODE = local")
            sys.exit(1)
        
    if args.command == "clone":
        clone_voice(api_key, args.audio, args.text, args.name, mode=mode, config=config, engine=engine)
    elif args.command == "dub":
        if not args.srt and not args.text and not args.text_file:
            print("错误: 必须提供 --srt、--text 或 --text-file 其中之一")
            sys.exit(1)
            
        if args.text_file:
            try:
                with open(args.text_file, 'r', encoding='utf-8') as f:
                    args.text = f.read().strip()
                print(f">> 成功从文件 {args.text_file} 加载长文本。")
            except Exception as e:
                print(f"错误: 读取文本文件失败 - {e}")
                sys.exit(1)
            
        if not args.voice:
            print("\n未指定音色，请选择配音音色：")
            choice = input("是否使用保存的克隆音色？(y/n) [y]: ").strip().lower()
            if choice != 'n':
                voices = get_saved_voices()
                if voices:
                    print("已保存的音色: ", ", ".join(voices.keys()))
                args.voice = input("请输入保存的音色名称: ").strip()
            else:
                gender = input("请选择默认音色性别 (男/m 或 女/f) [女]: ").strip().lower()
                if gender in ['男', 'm', 'male']:
                    args.voice = "IndexTeam/IndexTTS-2:alex"
                else:
                    args.voice = "IndexTeam/IndexTTS-2:anna"
                    
        # 分析文本参数
        tts_params_override = {}
        if args.temperature is not None: tts_params_override["temperature"] = args.temperature
        if args.top_k is not None: tts_params_override["top_k"] = args.top_k
        if args.top_p is not None: tts_params_override["top_p"] = args.top_p
        if args.max_text_tokens is not None: tts_params_override["max_text_tokens_per_segment"] = args.max_text_tokens

        tts_params = {}
        if mode == "local":
            full_text = ""
            if args.text:
                full_text = args.text
            elif args.srt:
                subs = parse_srt(args.srt)
                full_text = " ".join([s["text"] for s in subs[:10]]) # 取前几句分析
                
            if full_text:
                tts_params, refined_text = analyze_text_for_tts_params(full_text, config, tts_params_override)
                if args.text:
                    args.text = refined_text
                
        # 检查是否是本地保存的名称
        voice_id = args.voice
        voices = get_saved_voices()
        if args.voice in voices:
            v_engine = voices[args.voice].get("engine", "indextts")
            # 如果样本的引擎与当前配置不符，给出警告，但尝试兼容
            if v_engine != engine:
                print(f"警告: 音色样本 {args.voice} 是由 {v_engine} 创建的，当前配置引擎为 {engine}，可能会有兼容性问题。")
                
            if v_engine == "qwen3-tts":
                voice_id = "qwen:" + voices[args.voice].get("local_audio")
                print(f"使用 Qwen3-TTS 本地库音色 {args.voice} -> {voice_id}")
            elif mode == "local":
                # 本地模式需要获取本地音频路径
                voice_id = voices[args.voice].get("local_audio")
                if not voice_id:
                    print(f"错误: 样本 {args.voice} 没有本地音频路径。请在 local 模式下重新克隆。")
                    sys.exit(1)
                print(f"使用本地库音色 {args.voice} -> 本地音频: {voice_id}")
            else:
                voice_id = voices[args.voice].get("uri", args.voice)
                print(f"使用本地库音色 {args.voice} -> {voice_id}")
                        
        if args.srt:
            dub_subtitle(api_key, args.srt, voice_id, args.out, mode=mode, tts_params=tts_params, engine=engine, config=config)
        elif args.text:
            dub_text(api_key, args.text, voice_id, args.out, mode=mode, tts_params=tts_params, engine=engine, config=config)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
