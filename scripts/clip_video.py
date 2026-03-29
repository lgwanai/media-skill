import os
import json
import subprocess
import re
import sys
import base64

from utils import load_config, get_openclaw_headers, create_openai_client, get_unified_output_dir
from cos_client import COSClient

def get_video_duration(video_path):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of",
        "default=noprint_wrappers=1:nokey=1", video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return float(result.stdout.strip()) * 1000  # 转换为毫秒

def upload_video_to_cos(video_path, config):
    """使用 scripts/cos_client.py 上传视频到腾讯云COS并返回URL"""
    os.environ['COS_SECRET_ID'] = config.get("COS_SECRET_ID", "")
    os.environ['COS_SECRET_KEY'] = config.get("COS_SECRET_KEY", "")
    os.environ['COS_REGION'] = config.get("COS_REGION", "ap-beijing")
    os.environ['COS_BUCKET_NAME'] = config.get("COS_BUCKET_NAME", "")
    
    if not all([os.environ['COS_SECRET_ID'], os.environ['COS_SECRET_KEY'], os.environ['COS_BUCKET_NAME']]):
        print("缺少 COS 配置，跳过上传。")
        return None
        
    try:
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        if scripts_dir not in sys.path:
            sys.path.append(scripts_dir)
            
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

def step1_hard_slicing(transcription_json_path, temp_dir="output/temp_clips"):
    """
    第一步：虚拟硬切片
    根据字幕时间戳：前后都需要多保留 300 毫秒，确保语气连贯。
    为了提升性能，我们不再调用 ffmpeg 实际切片，而是只计算并记录元数据（metadata）。
    """
    print(f"\n=== Step 1: 虚拟硬切片 (基于 {transcription_json_path}) ===")
    os.makedirs(temp_dir, exist_ok=True)
    
    with open(transcription_json_path, "r", encoding="utf-8") as f:
        res = json.load(f)
        
    sentences = res[0].get("sentence_info", []) if res else []
    clips = []
    
    for i, sentence in enumerate(sentences):
        text = sentence.get("text", "")
        orig_start = sentence.get("start", 0)
        orig_end = sentence.get("end", 0)
        
        # 前后保留 300 毫秒
        clip_start = max(0, orig_start - 300)
        clip_end = orig_end + 300
        
        start_sec = clip_start / 1000.0
        duration_sec = (clip_end - clip_start) / 1000.0
        
        print(f"记录虚拟切片 [{i}]: {start_sec}s - {start_sec + duration_sec}s")
        
        clips.append({
            "id": i,
            "text": text,
            "orig_start": orig_start,
            "orig_end": orig_end,
            "clip_start": clip_start,
            "clip_end": clip_end,
            "timestamp_array": sentence.get("timestamp", [])
        })
        
    output_json = os.path.join(temp_dir, "step1_clips.json")
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(clips, f, ensure_ascii=False, indent=2)
        
    return clips, output_json

def step2_llm_analysis(clips_json_path, config, temp_dir):
    """
    第二步：语言大模型分析语义
    """
    print(f"\n=== Step 2: 语言大模型语义分析 ===")
    with open(clips_json_path, "r", encoding="utf-8") as f:
        clips = json.load(f)
        
    api_key = config.get("TEXT_LLM_API_KEY", config.get("OMINI_API_KEY"))
    api_url = config.get("TEXT_LLM_URL", config.get("OMINI_URL"))
    model_name = config.get("TEXT_LLM_MODEL_NAME", "qwen/qwen-2.5-72b-instruct")
    
    text_list = [{"id": c["id"], "text": c["text"]} for c in clips]
    
    prompt = """你是一个专业的视频剪辑语义分析专家。我将提供一组按时间顺序排列的视频台词片段（包含 id 和 text）。
你需要严格按照以下 4 条逻辑对这些片段进行分析：

1、判断本身语言是否有实际意义，比如整个字幕，只有“啊啊”、“哦”、“嗯”、“那个”这种语气词，那么直接标记动作：discard。
2、如果判断是打招呼等正常语句，需要保留，但是保留后还需要对比**前一个片段**的语义，是否一致（是语义一致，不是字幕完全一致。比如“大家好啊”和“呃大家好”就是语义一致）。那么选择两个中表达最通顺的一个，标记为：keep，另一个标记为：discard。
  【注意】：在对比时，如果开始对比发现前一个已经被标记为 discard，那么就需要再往前追溯，直到找到没有标记为 discard 的一条进行对比。
3、如果单条语句中间出现了重复词汇、磕巴或明显不通顺的情况（例如“它专门是帮它专门是”），将其标记为 partial_discard，并且必须在 `discard_text` 字段中提取出需要被精确剔除的**冗余文字片段**（例如 "它专门是帮" 或者 "啊这个"，总之是你认为需要剪掉的那部分废话原话）。
4、如果有连续的两个或多个片段合起来看出现了部分语义重复的情况（即出现了其他语句，导致两句话合并起来有重复），你需要把这几个片段合并为一个处理单元，动作标记为 partial_discard，并在 `discard_text` 字段中给出需要从这几句话中剔除的连续冗余文字。

输出格式要求：
请直接输出一个 JSON 数组，每个元素包含 ids（当前动作涉及的片段id数组）、action（必须是 discard、keep 或 partial_discard）以及 reason（理由）。如果是 partial_discard，还必须包含 discard_text 字段。
例如：
[
  {"ids": [0], "action": "discard", "reason": "纯语气词无意义"},
  {"ids": [1], "action": "keep", "reason": "正常打招呼，保留"},
  {"ids": [2], "action": "discard", "reason": "与id=1语义一致且包含语气词，故剔除"},
  {"ids": [3], "action": "keep", "reason": "无异常保留"},
  {"ids": [4], "action": "partial_discard", "reason": "内部存在重复词汇，需精细化处理", "discard_text": "它专门是帮"},
  {"ids": [5, 6], "action": "partial_discard", "reason": "5和6合并起来存在部分语义重复", "discard_text": "重复的一句话"}
]
绝对不要输出任何其他解释文字或 markdown 代码块标记，只能输出纯 JSON 字符串！

台词列表：
""" + json.dumps(text_list, ensure_ascii=False)

    try:
        client = create_openai_client(api_key=api_key, base_url=api_url)
        extra_headers = get_openclaw_headers(config)
            
        print("正在调用文本大模型进行分析...")
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            extra_headers=extra_headers if extra_headers else None
        )
        content = response.choices[0].message.content.strip()
        print(f"大模型原始返回:\n{content}")
        
        # 提取 JSON
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            content = match.group(0)
            
        llm_results = json.loads(content)
        
        # 将结果映射回 clips，支持多片段共用一个 action 和 discard_text
        for res in llm_results:
            action = res.get("action")
            reason = res.get("reason", "")
            ids = res.get("ids", [])
            discard_text = res.get("discard_text", "")
            
            for cid in ids:
                # 寻找对应 clip
                for clip in clips:
                    if clip["id"] == cid:
                        clip["action"] = action
                        clip["reason"] = reason
                        if action == "partial_discard":
                            clip["group_ids"] = ids
                            clip["discard_text"] = discard_text
                            
    except Exception as e:
        print(f"调用纯文本语义分析失败: {e}")
        # 如果失败，默认全部 keep
        for clip in clips:
            if "action" not in clip:
                clip["action"] = "keep"

    output_json = os.path.join(temp_dir, "step2_clips.json")
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(clips, f, ensure_ascii=False, indent=2)
        
    return clips, output_json

def tokenize(text):
    import re
    tokens = []
    matches = re.finditer(r'[a-zA-Z0-9]+|[^\s\w]|[\u4e00-\u9fa5]', text)
    for m in matches:
        token = m.group(0)
        if re.match(r'[，。、！？：；（）《》“”‘’"\'\.,!?;:\(\)\[\]-]', token):
            continue
        if token.strip():
            tokens.append(token)
    return tokens

def get_timestamp_for_substring(text, substring, timestamps):
    text_tokens = tokenize(text)
    sub_tokens = tokenize(substring)
    if not sub_tokens:
        return None
    start_idx = -1
    for i in range(len(text_tokens) - len(sub_tokens) + 1):
        match = True
        for j in range(len(sub_tokens)):
            if text_tokens[i+j].lower() != sub_tokens[j].lower():
                match = False
                break
        if match:
            start_idx = i
            break
    if start_idx == -1:
        return None
    end_idx = start_idx + len(sub_tokens) - 1
    if start_idx < len(timestamps) and end_idx < len(timestamps):
        return {
            "start": timestamps[start_idx][0],
            "end": timestamps[end_idx][1]
        }
    return None

def step3_precise_trimming(clips_json_path, temp_dir):
    """
    第三步：精确提取剔除时间戳
    将标记为 partial_discard 的片段，通过 FunASR 提供的字符级/词级时间戳，
    精确找出 discard_text 对应的绝对时间。
    """
    print(f"\n=== Step 3: 基于字级时间戳精细化处理 ===")
    with open(clips_json_path, "r", encoding="utf-8") as f:
        clips = json.load(f)
        
    processed_ids = set()
    for clip in clips:
        if clip["id"] in processed_ids:
            continue
            
        action = clip.get("action", "keep")
        if action == "partial_discard":
            group_ids = clip.get("group_ids", [clip["id"]])
            discard_text = clip.get("discard_text", "")
            
            # 组合这几个片段的文本和时间戳
            combined_text = ""
            combined_ts = []
            target_clips = []
            
            for cid in group_ids:
                # 寻找 clip
                c = next((item for item in clips if item["id"] == cid), None)
                if c:
                    target_clips.append(c)
                    combined_text += c["text"]
                    combined_ts.extend(c.get("timestamp_array", []))
                    processed_ids.add(cid)
                    
            if discard_text and target_clips:
                print(f"正在匹配废话 '{discard_text}' ...")
                interval = get_timestamp_for_substring(combined_text, discard_text, combined_ts)
                if interval:
                    print(f"成功匹配到剔除区间: {interval}")
                    # 将这个剔除区间记录在第一条 clip 上，在合并时统一计算即可，因为这是基于原视频的绝对时间
                    target_clips[0].setdefault("discard_intervals", []).append(interval)
                else:
                    print(f"警告：未能在原文 '{combined_text}' 中精确匹配到 '{discard_text}'")
                    
    output_json = os.path.join(temp_dir, "step3_clips.json")
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(clips, f, ensure_ascii=False, indent=2)
        
    return clips, output_json

def step4_analyze_silence(clips_json_path, video_path, config, temp_dir="output/temp_clips"):
    """
    第四步：非语言片段分析（默认关闭）
    找出所有语言片段之间的间隙（非语言片段），如果大于 500ms，压缩后交给 Omini 判断是否有意义。
    如果有意义（保留），记录这些间隙以供最后合并。
    """
    enable_silence_analysis = config.get("ENABLE_SILENCE_ANALYSIS", "false").lower() == "true"
    print(f"\n=== Step 4: 非语言片段智能保留 (当前配置: {'开启' if enable_silence_analysis else '关闭'}) ===")
    
    with open(clips_json_path, "r", encoding="utf-8") as f:
        clips = json.load(f)
        
    rescued_silences = []
    
    if not enable_silence_analysis:
        output_json = os.path.join(temp_dir, "step4_silences.json")
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(rescued_silences, f, ensure_ascii=False, indent=2)
        return rescued_silences, output_json

    try:
        video_duration = get_video_duration(video_path)
    except Exception as e:
        print(f"获取视频长度失败，跳过非语言片段分析: {e}")
        return [], os.path.join(temp_dir, "step4_silences.json")
        
    # 收集所有的有效语言片段（包含 keep 和 partial_discard 的硬切片区间，去除完全 discard 的片段）
    speech_intervals = []
    for clip in clips:
        if clip.get("action") != "discard":
            speech_intervals.append([clip["clip_start"], clip["clip_end"]])
            
    speech_intervals.sort(key=lambda x: x[0])
    
    # 提取所有大于 500ms 的间隙
    gaps = []
    current_time = 0
    for s_start, s_end in speech_intervals:
        if s_start > current_time + 500:
            gaps.append([current_time, s_start])
        current_time = max(current_time, s_end)
        
    if video_duration > current_time + 500:
        gaps.append([current_time, video_duration])
        
    if not gaps:
        print("未发现明显的非语言片段间隙。")
    else:
        print(f"共发现 {len(gaps)} 个非语言片段，开始分析...")
        
    api_key = config.get("MIMO_API_KEY", config.get("OMINI_API_KEY"))
    api_url = config.get("MIMO_URL", config.get("OMINI_URL", "https://api.xiaomimimo.com/v1"))
    model_name = config.get("OMINI_MODEL_NAME", "mimo-v2-omni")
    
    client = None
    if api_key:
        client = create_openai_client(api_key=api_key, base_url=api_url)
        
    for idx, gap in enumerate(gaps):
        gap_start, gap_end = gap[0], gap[1]
        start_sec = gap_start / 1000.0
        duration_sec = (gap_end - gap_start) / 1000.0
        
        compressed_file = os.path.join(temp_dir, f"silence_gap_{idx}_540p.mp4")
        print(f"\n正在准备非语言片段 {idx}: {start_sec}s - {start_sec + duration_sec}s -> {compressed_file}")
        
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-ss", str(start_sec), "-t", str(duration_sec),
            "-vf", "scale=-2:540", "-r", "30",
            "-c:v", "libx264", "-crf", "28", "-preset", "faster",
            compressed_file
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if client and os.path.exists(compressed_file):
            video_url = upload_video_to_cos(compressed_file, config)
            if video_url:
                prompt_text = (
                    "你是一个专业的视频画面分析专家。这段视频是去除了人物语音的非语言片段。请你判断这个画面是否具有保留价值。\n"
                    "有意义的定义是：\n"
                    "1、如果是电脑或者软件界面，需要有明显的鼠标操作或者界面交互；如果只有画面抖动，没有实质性的画面变化，判定为无意义。\n"
                    "2、如果是人物，需要有明确的人物形象、动作和表情变化；如果没有明显变化，只是画面晃动或者静止，判定为无意义。\n"
                    "3、如果是物品，需要有明确的运动或者运镜；如果物品静止或者只是画面抖动，判定为无意义。\n\n"
                    "请先简要分析视频内容，然后必须在最后一行给出结论：\n"
                    "【结论】: keep （如果有意义，需要保留）或者 【结论】: discard （如果无意义，需要删除）。"
                )
                
                try:
                    extra_headers = get_openclaw_headers(config)
                    print(f"调用 Omini 模型判断该片段是否有意义...")
                    completion = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": "You are MiMo, an AI assistant developed by Xiaomi."},
                            {"role": "user", "content": [
                                {"type": "video_url", "video_url": {"url": video_url}, "fps": 2},
                                {"type": "text", "text": prompt_text}
                            ]}
                        ],
                        max_completion_tokens=200,
                        temperature=0.1,
                        extra_headers=extra_headers if extra_headers else None
                    )
                    content = completion.choices[0].message.content.strip()
                    print(f"Omini 判定结果:\n{content}")
                    
                    if "【结论】: keep" in content.lower() or "【结论】：keep" in content.lower() or "keep" in content.lower()[-20:]:
                        rescued_silences.append({
                            "start": gap_start,
                            "end": gap_end,
                            "reason": "Omini 判定为有意义的非语言片段"
                        })
                except Exception as e:
                    print(f"调用 Omini 模型发生异常: {e}")
                    
    output_json = os.path.join(temp_dir, "step4_silences.json")
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(rescued_silences, f, ensure_ascii=False, indent=2)
        
    return rescued_silences, output_json

def step5_final_merge(clips_json_path, silences_json_path, video_path, output_video="output/final_output.mp4"):
    """
    第五步：最终合并
    根据时间轴信息，提取原视频内容，合并成一个最终视频，画质需要按照原视频为准。
    """
    print(f"\n=== Step 5: 最终视频合并 ===")
    with open(clips_json_path, "r", encoding="utf-8") as f:
        clips = json.load(f)
        
    with open(silences_json_path, "r", encoding="utf-8") as f:
        silences = json.load(f)
        
    keep_intervals = []
    global_discards = []
    
    # 1. 收集语言片段保留区间和需要挖空的废话区间
    for clip in clips:
        action = clip.get("action", "keep")
        if action == "discard":
            continue
            
        c_start = clip["clip_start"]
        c_end = clip["clip_end"]
        
        if action in ["keep", "partial_discard"]:
            keep_intervals.append([c_start, c_end])
            discards = clip.get("discard_intervals", [])
            for d in discards:
                global_discards.append([d["start"], d["end"]])
                
    # 2. 收集 Omini 判定保留的非语言片段
    for silence in silences:
        keep_intervals.append([silence["start"], silence["end"]])
                
    if not keep_intervals:
        print("没有可保留的片段！")
        return
        
    # 3. 区间合并 (Union)，解决 clip 之间前后缓冲导致的重叠，以及与非语言片段的重叠
    keep_intervals.sort(key=lambda x: x[0])
    merged_keeps = []
    for interval in keep_intervals:
        if not merged_keeps:
            merged_keeps.append(interval)
        else:
            last = merged_keeps[-1]
            if interval[0] <= last[1]:
                merged_keeps[-1] = [last[0], max(last[1], interval[1])]
            else:
                merged_keeps.append(interval)
                
    # 4. 从合并后的保留区间中，彻底挖去所有的 discard_intervals
    final_keeps = []
    for k in merged_keeps:
        current_k = [k]
        for d in global_discards:
            d_start, d_end = d[0], d[1]
            next_k = []
            for ck in current_k:
                ck_start, ck_end = ck[0], ck[1]
                if d_end <= ck_start or d_start >= ck_end:
                    next_k.append(ck)
                else:
                    if ck_start < d_start:
                        next_k.append([ck_start, d_start])
                    if d_end < ck_end:
                        next_k.append([d_end, ck_end])
            current_k = next_k
        final_keeps.extend(current_k)
        
    print("最终保留的时间轴区间 (ms):", final_keeps)
    
    filter_parts = []
    for i, interval in enumerate(final_keeps):
        start_sec = interval[0] / 1000.0
        end_sec = interval[1] / 1000.0
        filter_parts.append(f"[0:v]trim=start={start_sec}:end={end_sec},setpts=PTS-STARTPTS[v{i}];[0:a]atrim=start={start_sec}:end={end_sec},asetpts=PTS-STARTPTS[a{i}];")
        
    concat_filter = "".join(filter_parts)
    concat_str = "".join([f"[v{i}][a{i}]" for i in range(len(final_keeps))])
    concat_filter += f"{concat_str}concat=n={len(final_keeps)}:v=1:a=1[outv][outa]"
    
    print("正在生成合并视频，请稍候...")
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-filter_complex", concat_filter,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-c:a", "aac",
        output_video
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"最终视频合并完成: {output_video}")


def process_smart_clip(trans_json, video_file, output_video=None):
    config = load_config()
    output_dir = get_unified_output_dir(video_file, config)
    
    status_path = os.path.join(output_dir, "clip_status.json")
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "running", "progress_percent": 10, "message": "正在进行虚拟硬切片..."}, f, ensure_ascii=False)
        
    if not output_video:
        base_name = os.path.basename(video_file)
        name_without_ext, ext = os.path.splitext(base_name)
        output_video = os.path.join(output_dir, f"{name_without_ext}_clipped{ext}")

    # 步骤 1：虚拟硬切片 (仅元数据)
    _, step1_out = step1_hard_slicing(trans_json, temp_dir=output_dir)
    
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "running", "progress_percent": 30, "message": "正在进行大模型语义分析..."}, f, ensure_ascii=False)

    # 步骤 2：大模型语义分析
    _, step2_out = step2_llm_analysis(step1_out, config, temp_dir=output_dir)
    
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "running", "progress_percent": 60, "message": "正在进行字级时间戳精细对齐..."}, f, ensure_ascii=False)

    # 步骤 3：基于字级时间戳精细处理
    _, step3_out = step3_precise_trimming(step2_out, temp_dir=output_dir)
    
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "running", "progress_percent": 80, "message": "正在进行非语言片段分析及合并..."}, f, ensure_ascii=False)

    # 步骤 4：非语言片段分析（Omini 视觉判断，默认关闭）
    _, step4_out = step4_analyze_silence(step3_out, video_file, config, temp_dir=output_dir)
    
    # 步骤 5：最终合并成片
    step5_final_merge(step3_out, step4_out, video_file, output_video)
    
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "done", "progress_percent": 100, "output_path": output_video}, f, ensure_ascii=False)
        
    return output_video

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python clip_video.py <transcription_json> <video_path>")
        sys.exit(1)
        
    trans_json = sys.argv[1]
    video_file = sys.argv[2]
    
    process_smart_clip(trans_json, video_file)
