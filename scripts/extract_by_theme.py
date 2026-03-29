import os
import sys
import json
import subprocess
import re

# 确保可以引入 scripts 目录下的其他模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.transcribe import transcribe
from scripts.utils import load_config, get_openclaw_headers, create_openai_client

def extract_by_theme(media_path, theme, output_dir="output/theme_extract"):
    os.makedirs(output_dir, exist_ok=True)
    status_path = os.path.join(output_dir, "extract_status.json")
    
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "running", "progress_percent": 5, "message": "正在转录字幕..."}, f, ensure_ascii=False)
        
    # 1. 毫秒级转字幕
    print(">>> 步骤 1：毫秒级转字幕...")
    res = transcribe(media_path, output_dir)
    if not res or not isinstance(res, list) or len(res) == 0:
        print("未能提取到字幕信息。")
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump({"status": "error", "message": "未能提取到字幕信息"}, f, ensure_ascii=False)
        return
    sentences = res[0].get("sentence_info", [])
    
    if not sentences:
        print("未能提取到字幕信息。")
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump({"status": "error", "message": "未能提取到字幕信息"}, f, ensure_ascii=False)
        return

    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "running", "progress_percent": 30, "message": "正在优化主题描述..."}, f, ensure_ascii=False)

    # 2. LLM 分析提取
    print("\n>>> 步骤 2：优化主题描述...")
    config = load_config()
    
    extra_headers = get_openclaw_headers(config)
        
    client = create_openai_client(
        api_key=config.get("TEXT_LLM_API_KEY"),
        base_url=config.get("TEXT_LLM_URL")
    )
    model_name = config.get("TEXT_LLM_MODEL_NAME", "deepseek-chat")

    enhance_prompt = f"""你是一个专业的视频内容分析专家。用户提供了一个简短的主题描述，希望从长视频中提取相关片段。
为了让后续的提取更加精准，请你对用户的原始描述进行补充和完善，将其转化为一个极其明确、具体的“提取标准”。

原始主题描述：“{theme}”

请输出完善后的提取标准（字数控制在100-200字之间）。
要求：
1. 明确该主题通常包含哪些核心特征、行为或上下文。
2. 明确排除那些仅仅“顺带提及关键词”但缺乏实质性展开的无关片段。
3. 语言要客观、严谨，作为后续 AI 分析的严格准则。
4. 直接输出完善后的标准文本，绝不包含“好的”、“这是完善后的标准”等废话。"""

    try:
        enhance_resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": enhance_prompt}],
            temperature=0.7,
            extra_headers=extra_headers if extra_headers else None
        )
        enhanced_theme = enhance_resp.choices[0].message.content.strip()
        print(f"优化后的提取标准：\n{enhanced_theme}\n")
    except Exception as e:
        print(f"主题优化失败，将使用原始主题: {e}")
        enhanced_theme = theme

    print(">>> 步骤 3：调用文本大模型进行分块字幕提取分析...")
    # 设定每个切片大致字符上限（低于 10000）
    max_chars = 9000
    chunks = []
    current_chunk = []
    current_length = 0
    
    for i, s in enumerate(sentences):
        start_ms = s.get('start', 0)
        end_ms = s.get('end', 0)
        text = f"[{i}] [{start_ms}-{end_ms}] {s.get('text', '')}\n"
        
        if current_length + len(text) > max_chars and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_length = 0
            
        current_chunk.append({"id": i, "text": text, "start": start_ms, "end": end_ms})
        current_length += len(text)
        
    if current_chunk:
        chunks.append(current_chunk)

    all_selected_intervals = []

    for idx, chunk in enumerate(chunks):
        chunk_text = "".join([c["text"] for c in chunk])
        prompt = f"""你是一个极其严格的专业视频内容分析和剪辑专家。
你的任务是根据给定的【提取标准】，从带编号的字幕片段中找出所有“强相关”的片段区间。

【提取标准】：
{enhanced_theme}

【字幕片段】（格式：[编号] [开始时间-结束时间] 文本）：
{chunk_text}

【提取规则】（请极其严格地遵守）：
1. 宁缺毋滥：只提取与【提取标准】高度一致、有实质性展开的片段。如果只是顺带提及词汇但没有实质内容，坚决不要提取！
2. 保证语义连贯性：如果片段 2 和 4 强相关，为了保证上下文连贯，应该连同中间的 3 一起提取（即提取 2,3,4）。但如果中间无关内容过长（比如 2 和 10 相关，中间全无关），则分别提取。
3. 包含上下文边缘：如果某片段相关，其前后一两句通常包含重要铺垫或收尾，请一并划入区间。
4. 如果整个片段中没有任何符合标准的内容，请严格返回空数组 []。

【输出格式】：
仅返回一个 JSON 数组，包含需要提取的连续片段区间，不要输出任何其他内容（不要 Markdown 标记，如 ```json）。格式如下：
[
  {{"start_id": 2, "end_id": 4, "reason": "这段详细展开了...，符合提取标准"}},
  {{"start_id": 8, "end_id": 10, "reason": "..."}}
]
"""
        print(f"正在处理第 {idx+1}/{len(chunks)} 部分...")
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                extra_headers=extra_headers if extra_headers else None
            )
            content = response.choices[0].message.content.strip()
            # 清理可能的 markdown 标记
            content = re.sub(r"^```json\s*", "", content)
            content = re.sub(r"^```\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            
            intervals = json.loads(content)
            if isinstance(intervals, list):
                all_selected_intervals.extend(intervals)
        except Exception as e:
            print(f"LLM 调用或解析失败: {e}")
            print(f"LLM 返回内容: {content if 'content' in locals() else '无'}")

    # 3. 合并区间与剪辑
    print("\n>>> 步骤 3：合并区间与视频剪切...")
    merged_intervals = []
    valid_intervals = []
    for it in all_selected_intervals:
        if "start_id" in it and "end_id" in it:
            # 确保 start_id <= end_id
            start_id, end_id = min(it["start_id"], it["end_id"]), max(it["start_id"], it["end_id"])
            valid_intervals.append([start_id, end_id])
    
    # 排序并合并相邻或重叠的区间
    valid_intervals.sort(key=lambda x: x[0])
    for it in valid_intervals:
        if not merged_intervals:
            merged_intervals.append(it)
        else:
            last = merged_intervals[-1]
            if it[0] <= last[1] + 1: # 允许相邻或重叠的区间合并，甚至相隔 1 句也直接合并
                last[1] = max(last[1], it[1])
            else:
                merged_intervals.append(it)

    if not merged_intervals:
        print("没有找到符合主题的片段。")
        return

    print(f"分析完成，最终合并后的提取区间为: {merged_intervals}")
    
    clips_dir = os.path.join(output_dir, "clips")
    os.makedirs(clips_dir, exist_ok=True)
    clip_files = []
    
    for idx, (start_id, end_id) in enumerate(merged_intervals):
        start_id = max(0, min(start_id, len(sentences) - 1))
        end_id = max(0, min(end_id, len(sentences) - 1))
        
        start_ms = sentences[start_id]["start"]
        end_ms = sentences[end_id]["end"]
        
        start_sec = start_ms / 1000.0
        duration_sec = (end_ms - start_ms) / 1000.0
        
        clip_path = os.path.join(clips_dir, f"clip_{idx}.mp4")
        # 使用 -strict experimental 以兼容某些音频编码
        cmd = [
            "ffmpeg", "-y", "-ss", str(start_sec), "-t", str(duration_sec),
            "-i", media_path, "-c:v", "libx264", "-c:a", "aac", "-strict", "experimental", clip_path
        ]
        print(f"正在剪辑片段 {idx+1}/{len(merged_intervals)}: {start_sec:.2f}s - {start_sec+duration_sec:.2f}s")
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        clip_files.append(clip_path)
        
    if not clip_files:
        return

    # concat
    concat_txt = os.path.join(output_dir, "concat.txt")
    with open(concat_txt, "w", encoding="utf-8") as f:
        for c in clip_files:
            f.write(f"file '{os.path.abspath(c)}'\n")
            
    final_output = os.path.join(output_dir, "theme_final.mp4")
    concat_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_txt,
        "-c", "copy", final_output
    ]
    print("正在合并最终视频...")
    subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "done", "progress_percent": 100, "output_path": final_output}, f, ensure_ascii=False)
        
    print(f"\n✅ 提取完成！最终视频保存在: {final_output}")

if __name__ == "__main__":
    # 如果指定了异步运行，并且当前不是子进程，则启动子进程并在主进程立即退出
    if '--async-run' in sys.argv and os.environ.get('EXTRACT_ASYNC_WORKER') != '1':
        print(">> 检测到 --async-run 参数，正在将任务转入后台异步执行...")
        cmd = [sys.executable] + sys.argv
        cmd.remove('--async-run')
        env = os.environ.copy()
        env['EXTRACT_ASYNC_WORKER'] = '1'
        
        subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        print(">> 后台任务已启动！Agent 可以立即退出等待，不被阻塞。请通过 extract_status.json 轮询进度。")
        sys.exit(0)

    if '--async-run' in sys.argv:
        sys.argv.remove('--async-run')

    if len(sys.argv) < 3:
        print("用法: python scripts/extract_by_theme.py <音视频路径> <主题描述> [--async-run]")
        sys.exit(1)
    extract_by_theme(sys.argv[1], sys.argv[2])