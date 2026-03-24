import os
import json
import base64
import subprocess
import requests

def load_config(config_path="config.txt"):
    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    config[k.strip()] = v.strip()
    return config

def encode_video_to_base64(video_path):
    """将视频文件编码为 Base64 字符串"""
    with open(video_path, "rb") as video_file:
        return base64.b64encode(video_file.read()).decode('utf-8')

def upload_video_to_cos(video_path, config):
    """使用 scripts/cos_client.py 上传视频到腾讯云COS并返回URL"""
    import os
    import sys
    
    # 将相关配置写入环境变量，供 cos_client 读取
    os.environ['COS_SECRET_ID'] = config.get("COS_SECRET_ID", "")
    os.environ['COS_SECRET_KEY'] = config.get("COS_SECRET_KEY", "")
    os.environ['COS_REGION'] = config.get("COS_REGION", "ap-beijing")
    os.environ['COS_BUCKET_NAME'] = config.get("COS_BUCKET_NAME", "")
    
    if not all([os.environ['COS_SECRET_ID'], os.environ['COS_SECRET_KEY'], os.environ['COS_BUCKET_NAME']]):
        print("缺少 COS 配置，跳过上传。")
        return None
        
    try:
        # 确保能导入同目录下的 cos_client
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        if scripts_dir not in sys.path:
            sys.path.append(scripts_dir)
            
        from cos_client import COSClient
        
        client = COSClient()
        print(f"正在使用 cos_client 上传 {video_path} 到 COS...")
        result = client.upload_file(video_path)
        
        if result.get('success'):
            url = result.get('url')
            print(f"上传成功: {url}")
            return url
        else:
            print(f"上传 COS 失败: {result.get('error')}")
            return None
            
    except Exception as e:
        print(f"上传 COS 发生异常: {e}")
        return None

def call_omini_model(video_path, config):
    """
    使用小米官方接口和 COS 上传调用 Omini 模型
    """
    api_key = config.get("MIMO_API_KEY", config.get("OMINI_API_KEY"))
    api_url = config.get("MIMO_URL", config.get("OMINI_URL", "https://api.xiaomimimo.com/v1"))
    model_name = config.get("OMINI_MODEL_NAME", "mimo-v2-omni")

    if not api_key:
        print("错误: 缺少 API_KEY (MIMO_API_KEY 或 OMINI_API_KEY)")
        return "keep"
        
    # 上传到 COS
    video_url = upload_video_to_cos(video_path, config)
    if not video_url:
        print("无法获取视频 URL，默认保留片段")
        return "keep"
        
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url=api_url
        )
        
        print(f"调用 Omini 模型: {model_name}, URL: {api_url}")
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are MiMo, an AI assistant developed by Xiaomi. Today is date: Tuesday, December 16, 2025. Your knowledge cutoff date is December 2024."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "video_url",
                            "video_url": {
                                "url": video_url
                            },
                            "fps": 2,
                            "media_resolution": "default"
                        },
                        {
                            "type": "text",
                            "text": "你是一个专业的视频剪辑师。请分析这段短视频的画面和声音，找出其中无意义的内容（如单纯的气口、结巴、严重的重复口误、没有实质性语义的片段、过长的无声停顿）。\n如果整个视频片段都完全没有意义（全是废话），请直接回复 'discard'。\n如果整个视频都很连贯、有意义，没有任何需要剪辑的地方，请直接回复 'keep'。\n如果视频中只有某一段是结巴、重复或冗长的停顿，需要精细裁剪，请返回一个 JSON 格式的数组，包含需要剔除的片段的开始和结束时间（以秒为单位，保留两位小数，从 0 开始计算）。例如：[{\"start\": 1.25, \"end\": 2.50}]\n请注意，只需输出 'keep'、'discard' 或 JSON 数组，绝不要输出其他任何文字，包括 markdown 标记！"
                        }
                    ]
                }
            ],
            max_completion_tokens=1024,
            temperature=0.1
        )
        
        result = completion.model_dump()
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0].get("message", {}).get("content", "").strip()
            print(f"Omini 模型原始返回: {content}")
            
            # 清理可能的 markdown 标记
            content = content.replace("```json", "").replace("```", "").strip()
            
            if content.lower() == "discard" or ("discard" in content.lower() and "[" not in content):
                return "discard"
            elif content.lower() == "keep" or ("keep" in content.lower() and "[" not in content):
                return "keep"
            else:
                import re
                match = re.search(r'\[.*\]', content, re.DOTALL)
                if match:
                    try:
                        import json
                        intervals = json.loads(match.group(0))
                        if isinstance(intervals, list):
                            return intervals
                    except Exception as e:
                        print(f"解析 Omini 时间戳 JSON 失败: {e}")
                return "keep"
        return "keep"
    except Exception as e:
        print(f"调用 Omini 模型发生异常: {e}")
        return "keep" # 失败时默认保留，防止误删

def step1_detect_silence(transcription_json_path, output_json="output/step1_silence.json"):
    """
    第一步：初步识别（时间戳打底）
    只识别，不剪辑，将视频中的“空白”、“气口”时间点记录在 json 文件中
    """
    print(f"Step 1: 分析 {transcription_json_path} 中的空白/气口...")
    with open(transcription_json_path, "r", encoding="utf-8") as f:
        res = json.load(f)
        
    if not res or not isinstance(res, list) or len(res) == 0:
        print("转写结果为空")
        return []
        
    sentences = res[0].get("sentence_info", [])
    silences = []
    
    # FunASR 在生成 sentence_info 时，为了句子连贯，start 和 end 有时会相连。
    # 为了寻找真实的空白/气口，我们需要提取词级别或子句级别的 timestamp。
    timestamps = res[0].get("timestamp", [])
    if not timestamps:
        print("未找到词级别时间戳")
        return []
        
    last_end = 0
    # 词级别时间戳阈值设为 400ms，认为停顿大于 400ms 就是一个气口/空白
    
    # 检测开头的静音（0 到第一个词的开始）
    if timestamps[0][0] > 100: # 如果开头超过 100ms 没声音
        silences.append({
            "start_ms": 0,
            "end_ms": timestamps[0][0],
            "type": "silence",
            "action": "discard",
            "reason": "开头静音"
        })
        
    for ts in timestamps:
        start_ms, end_ms = ts[0], ts[1]
        
        # 记录中间的空白气口
        if last_end > 0 and start_ms - last_end > 400:
            silences.append({
                "start_ms": last_end,
                "end_ms": start_ms,
                "type": "silence",
                "action": "discard",
                "reason": "中间停顿"
            })
            
        last_end = end_ms

    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(silences, f, ensure_ascii=False, indent=2)
    return silences

def call_llm_for_text(text_list, config):
    """
    调用大模型对纯文本片段进行语义分析
    输入: 包含字典的列表 [{"id": 0, "text": "呃"}, {"id": 1, "text": "嗯大家好啊"}]
    输出: 返回需要被剔除（无意义、严重重复、纯语气词）的 id 列表
    """
    api_key = config.get("TEXT_LLM_API_KEY", config.get("OMINI_API_KEY"))
    api_url = config.get("TEXT_LLM_URL", config.get("OMINI_URL"))
    model_name = config.get("TEXT_LLM_MODEL_NAME", "qwen/qwen-2.5-72b-instruct")

    if not api_key or not api_url:
        print("缺少 TEXT_LLM_API_KEY 或 TEXT_LLM_URL")
        return []

    prompt = (
        "你是一个极其严格的专业视频剪辑师。我将提供一组视频台词的 JSON 列表，每个对象包含 id 和 text。\n"
        "请帮我找出其中**完全没有实质意义**的整段废话，或者**前后句子严重重复**的口误片段，需要剔除的规则如下：\n"
        "1. 纯语气词：如仅包含“呃”、“啊”、“那个”、“然后”等，没有任何实际内容的完整句子。\n"
        "2. 句子间口误与重说：如果紧挨着的两句话表达了完全相同的意思（比如上一句是“大家好啊”，下一句是“大家好”），说明讲话者卡壳重说了。你必须把前面那句不完整的句子剔除。\n"
        "3. 注意：如果一句话内部存在局部的结巴或重复（例如“它专门是帮啊它专门是使用小米的”），但整句话包含重要信息，请**不要**将其剔除，保留它，后续会由其他模型进行精细裁剪。\n"
        "请返回一个 JSON 数组，里面包含所有需要剔除的片段的 id 数字，例如：[0, 1]。\n"
        "注意：除了 JSON 数组外，不要输出任何其他解释文字！直接输出形如 [0, 1, 2] 的结果。\n"
        f"台词列表：\n{json.dumps(text_list, ensure_ascii=False)}"
    )

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=api_url)
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        content = response.choices[0].message.content.strip()
        print(f"大模型原始返回: {content}")
        # 简单清理可能带有的 markdown 标记
        content = content.replace("```json", "").replace("```", "").strip()
        
        # 提取数组部分
        import re
        match = re.search(r'\[.*?\]', content, re.DOTALL)
        if match:
            content = match.group(0)
            
        return json.loads(content)
    except Exception as e:
        print(f"调用纯文本语义分析失败: {e}")
    return []

def step2_semantic_clip(transcription_json_path, video_path, temp_dir="output/temp_clips", output_json="output/step2_semantic_clips.json"):
    """
    第二步：文字语义精剪（切片摘取）
    对照时间轴切片视频，复制到临时文件夹，并记录时间片摘取时间轴
    """
    print(f"Step 2: 语义精剪与视频切片...")
    os.makedirs(temp_dir, exist_ok=True)
    
    with open(transcription_json_path, "r", encoding="utf-8") as f:
        res = json.load(f)
        
    sentences = res[0].get("sentence_info", []) if res else []
    clips = []
    config = load_config()
    
    # 构造供大模型分析的文本列表
    text_list_for_llm = []
    for i, sentence in enumerate(sentences):
        text_list_for_llm.append({"id": i, "text": sentence.get("text", "")})
        
    print("调用大模型进行纯文本语义分析，剔除无意义废话和重复...")
    discard_ids = call_llm_for_text(text_list_for_llm, config)
    print(f"大模型判定需要剔除的片段 ID: {discard_ids}")
    
    # 将被判定为 discard 的片段记录到 clips（之后将与 step1 合并剔除）
    # 同时，如果有些句子包含轻微语气词但不至于完全剔除，也可以摘出来进入 step3
    # 这里我们简化逻辑：被大模型纯文本判定为 discard 的直接记录为 discard。
    # 另外筛选一些长句子中包含模糊语气词的，进入 step3 多模态判定。
    
    # 获取完整的文本内容，以便检查模型是否由于切句问题没有给出正确的 id
    # FunASR 有时切句很长，大模型可能不返回这个长句的 ID，只希望剔除长句中的一部分。
    # 为了解决这个问题，我们需要让大模型返回“需要剔除的具体文本”，或者由我们在提示词中要求更精确的处理。
    # 但由于目前大模型返回的是句子 ID，如果一句话包含了重复部分和正常部分（没被切开），大模型就很难只剔除 ID。
    # 我们先检查 transcription.json 里的切句情况。
    
    filler_words = ["嗯", "啊", "呃", "那个", "然后"]
    clip_index = 0
    
    for i, sentence in enumerate(sentences):
        text = sentence.get("text", "")
        start_ms = sentence.get("start", 0)
        end_ms = sentence.get("end", 0)
        
        # 增加一个简单的规则：如果大模型没有剔除，但句子内部存在明显的重复，我们将其送入 step3 多模态，或者通过规则切分。
        # 由于这里是粗剪，如果当前句子没被标记为 discard，我们检查它是否需要进入 step3
        if i in discard_ids:
            # 纯文本就能确定的废话，直接打 discard 标
            clips.append({
                "clip_file": None,
                "text": text,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "action": "discard",
                "reason": "语义分析判定为废话"
            })
        elif len(text.replace("，", "").replace("。", "").replace("！", "").replace("？", "").strip()) <= 2 and any(w in text for w in filler_words):
            # 增加基于规则的硬匹配：如果一句话除掉标点后非常短(<=2个字)且包含语气词，直接丢弃
            clips.append({
                "clip_file": None,
                "text": text,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "action": "discard",
                "reason": "规则判定为纯语气词"
            })
        else:
            # 优化逻辑：只有包含明显的磕巴重复模式，或者包含语气词的长句，才进入 step3
            import re
            # 检查是否有明显的重复词（至少两个字重复，如 "专门是" -> "专门是"）
            has_repetition = bool(re.search(r'(.{2,4}).*\1', text))
            has_filler = any(w in text for w in filler_words) and len(text) > 2
            
            if has_repetition or has_filler:
                clip_index += 1
                clip_file = os.path.join(temp_dir, f"clip_{clip_index}.mp4")
                
                start_sec = start_ms / 1000.0
                duration_sec = (end_ms - start_ms) / 1000.0
                
                cmd = [
                    "ffmpeg", "-y", "-i", video_path,
                    "-ss", str(start_sec), "-t", str(duration_sec),
                    "-c", "copy",
                    clip_file
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                clips.append({
                    "clip_file": clip_file,
                    "text": text,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "action": "pending_multimodal" # 等待第三步处理
                })
            else:
                # 既没有重复也没有语气词的正常句子，直接保留，不进入 omini
                clips.append({
                    "clip_file": None,
                    "text": text,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "action": "keep",
                    "reason": "正常句子直接保留"
                })
            
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(clips, f, ensure_ascii=False, indent=2)
    return clips

def step3_multimodal_filter(clips_json_path, video_path, output_json="output/step3_multimodal_filter.json"):
    """
    第三步：多模态深度精剪（降本增效）
    如果只有单个短片段，压缩短片段送入 omini 大模型识别；
    如果连续多个片段都需要 omini 识别（可能是跨段的结巴、重复），则将它们合并成一个大片段后送给 omini 进行全局时间轴裁剪。
    """
    print(f"Step 3: 读取切片配置 {clips_json_path} 并调用 Omini 大模型进行多模态精剪...")
    config = load_config()
    
    with open(clips_json_path, "r", encoding="utf-8") as f:
        clips = json.load(f)
        
    filtered = []
    
    # 找出所有需要 omini 处理的连续区间
    # pending_multimodal
    blocks = []
    current_block = []
    
    for clip in clips:
        if clip.get("action") == "pending_multimodal":
            current_block.append(clip)
        else:
            if current_block:
                blocks.append(current_block)
                current_block = []
            filtered.append(clip)
            
    if current_block:
        blocks.append(current_block)
        
    for block in blocks:
        if not block:
            continue
            
        # 计算整个 block 的总时间跨度
        start_ms = block[0]["start_ms"]
        end_ms = block[-1]["end_ms"]
        start_sec = start_ms / 1000.0
        duration_sec = (end_ms - start_ms) / 1000.0
        
        # 截取整个大片段
        merged_clip_file = block[0]["clip_file"].replace(".mp4", "_merged.mp4")
        compressed_file = merged_clip_file.replace(".mp4", "_540p.mp4")
        
        print(f"合并连续待检测片段并压缩 -> {compressed_file} (start: {start_sec}, duration: {duration_sec})")
        # 直接从原视频截取合并后的完整大段并压缩
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-ss", str(start_sec), "-t", str(duration_sec),
            "-vf", "scale=-2:540", "-r", "30",
            "-c:v", "libx264", "-crf", "28", "-preset", "faster",
            compressed_file
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(compressed_file):
            print(f"调用 Omini 模型分析合并后的视频 {compressed_file}...")
            action_result = call_omini_model(compressed_file, config)
            print(f"合并视频模型判断结果: {action_result}")
            
            # 因为我们把几个 clip 合并起来检测了，所以这里把它们作为一个整体大 clip 存入 filtered
            # 原来的短 clip 丢弃不用，替换成这个大 clip
            merged_clip = {
                "clip_file": compressed_file,
                "text": " ".join([c["text"] for c in block]),
                "start_ms": start_ms,
                "end_ms": end_ms,
            }
            
            if isinstance(action_result, list):
                merged_clip["action"] = "partial_discard"
                merged_clip["discard_intervals"] = action_result
            else:
                merged_clip["action"] = action_result
                
            filtered.append(merged_clip)
            
            # 清理临时合并文件（如果需要保留排查可以注释掉）
            # os.remove(compressed_file)
        else:
            # 如果截取失败，原样放回 keep
            for c in block:
                c["action"] = "keep"
                filtered.append(c)

    # 按 start_ms 重新排序，因为前面的分组把原本的顺序打乱了
    filtered.sort(key=lambda x: x["start_ms"])
    
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)
    return filtered

def step4_merge_final(video_path, all_jsons, output_video="output/final_output.mp4"):
    """
    第四步：综合成片合并
    结合所有环节的 json，综合给出有效时间 json，最后对原有视频进行切割合并
    """
    print(f"Step 4: 综合有效时间，最终切割合并 -> {output_video}")
    
    # 获取需要剔除的无效片段列表 (以毫秒计)
    discard_intervals = []
    
    # 解析 step1 空白/气口
    if "step1" in all_jsons and os.path.exists(all_jsons["step1"]):
        with open(all_jsons["step1"], "r", encoding="utf-8") as f:
            silences = json.load(f)
            for s in silences:
                if s.get("action") == "discard":
                    discard_intervals.append((s["start_ms"], s["end_ms"]))
                    
    # 解析 step2 纯文本精剪剔除
    if "step2" in all_jsons and os.path.exists(all_jsons["step2"]):
        with open(all_jsons["step2"], "r", encoding="utf-8") as f:
            semantics = json.load(f)
            for s in semantics:
                if s.get("action") == "discard":
                    discard_intervals.append((s["start_ms"], s["end_ms"]))
                
    # 解析 step3 多模态精剪结果，支持 action 为 discard 以及 partial_discard
    if "step3" in all_jsons and os.path.exists(all_jsons["step3"]):
        with open(all_jsons["step3"], "r", encoding="utf-8") as f:
            multimodal = json.load(f)
            for m in multimodal:
                if m.get("action") == "discard":
                    discard_intervals.append((m["start_ms"], m["end_ms"]))
                elif m.get("action") == "partial_discard":
                    for interval in m.get("discard_intervals", []):
                        rel_start_ms = int(interval.get("start", 0) * 1000)
                        rel_end_ms = int(interval.get("end", 0) * 1000)
                        abs_start = m["start_ms"] + rel_start_ms
                        abs_end = m["start_ms"] + rel_end_ms
                        abs_end = min(abs_end, m["end_ms"]) # 防止超出当前片段
                        if abs_end > abs_start:
                            discard_intervals.append((abs_start, abs_end))
                    
    # 如果没有需要剔除的，直接 copy 结束
    if not discard_intervals:
        print("没有需要剔除的片段，直接拷贝原视频。")
        subprocess.run(["ffmpeg", "-y", "-i", video_path, "-c", "copy", output_video], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
        
    # 合并重叠的剔除区间
    discard_intervals.sort(key=lambda x: x[0])
    merged_discards = []
    for interval in discard_intervals:
        if not merged_discards:
            merged_discards.append(interval)
        else:
            last = merged_discards[-1]
            if interval[0] <= last[1]:
                merged_discards[-1] = (last[0], max(last[1], interval[1]))
            else:
                merged_discards.append(interval)
                
    # 根据剔除区间计算保留区间 (有效时间)
    # 假设视频总长度通过 ffprobe 获取（这里粗略从最后一个 discard 加上一个足够大的数，或者直接切到末尾）
    # 为简单起见，利用保留区间生成 filter_complex
    
    keep_intervals = []
    current_time = 0
    for start_ms, end_ms in merged_discards:
        if start_ms > current_time:
            keep_intervals.append((current_time, start_ms))
        current_time = end_ms
        
    # 使用 ffmpeg filter_complex 合并
    filter_parts = []
    
    # 修复末尾无语言表达内容没有去掉的 bug：
    # 如果视频总长度比最后一句的结束时间长很多，说明后面全是没说话的废画面
    # 我们应该截取到最后一个有意义句子的结束时间，而不是近似到末尾 999999999
    # 首先找出所有保留片段中的最大 end_ms，然后把最后一段修正为真实的结束时间
    max_valid_end = 0
    if "step2" in all_jsons and os.path.exists(all_jsons["step2"]):
        with open(all_jsons["step2"], "r", encoding="utf-8") as f:
            semantics = json.load(f)
            if semantics:
                # 最后一个句子的结束时间
                max_valid_end = semantics[-1]["end_ms"]
    
    # 添加最后一段
    if current_time < max_valid_end:
        keep_intervals.append((current_time, max_valid_end))
    elif current_time == 0 and not discard_intervals:
         # 没有剔除任何东西的情况
         keep_intervals.append((0, max_valid_end if max_valid_end > 0 else 999999999))
    
    for i, (start_ms, end_ms) in enumerate(keep_intervals):
        start_sec = start_ms / 1000.0
        end_sec = end_ms / 1000.0
        # 统一使用 trim=start=xx:end=xx 进行精确裁剪，防止把末尾没说话的废片带入
        filter_parts.append(f"[0:v]trim=start={start_sec}:end={end_sec},setpts=PTS-STARTPTS[v{i}];[0:a]atrim=start={start_sec}:end={end_sec},asetpts=PTS-STARTPTS[a{i}];")
            
    concat_filter = "".join(filter_parts)
    concat_str = "".join([f"[v{i}][a{i}]" for i in range(len(keep_intervals))])
    concat_filter += f"{concat_str}concat=n={len(keep_intervals)}:v=1:a=1[outv][outa]"
    
    print("生成合并视频...")
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-filter_complex", concat_filter,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-c:a", "aac",
        output_video
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"最终视频合并完成: {output_video}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python clip_video.py <transcription_json> <video_path>")
        sys.exit(1)
        
    trans_json = sys.argv[1]
    video_file = sys.argv[2]
    
    os.makedirs("output", exist_ok=True)
    
    # 步骤执行
    step1_out = "output/step1_silence.json"
    step2_out = "output/step2_semantic_clips.json"
    step3_out = "output/step3_multimodal_filter.json"
    
    step1_detect_silence(trans_json, step1_out)
    step2_semantic_clip(trans_json, video_file, "output/temp_clips", step2_out)
    step3_multimodal_filter(step2_out, video_file, step3_out)
    
    all_jsons = {
        "step1": step1_out,
        "step2": step2_out,
        "step3": step3_out
    }
    
    step4_merge_final(video_file, all_jsons, "output/final_output.mp4")
