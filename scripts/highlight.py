import os
import sys
import json
import argparse
import subprocess

# 确保可以引入 scripts 目录下的其他模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from transcribe import transcribe
from utils import load_config, get_openclaw_headers, create_openai_client
from clip_video import process_smart_clip

def extract_highlights_intervals(sentences, config):
    print("\n>>> 正在使用 LLM 提取精彩片段（金句、鲜明观点、实用技能/方法）...")
    client = create_openai_client(
        api_key=config.get("TEXT_LLM_API_KEY"),
        base_url=config.get("TEXT_LLM_URL")
    )
    model_name = config.get("TEXT_LLM_MODEL_NAME", "deepseek-chat")
    extra_headers = get_openclaw_headers(config)

    # 准备文本供 LLM 分析
    text_lines = []
    for i, s in enumerate(sentences):
        text_lines.append(f"[{i}] {s.get('text', '')}")
    
    # 如果视频过长，这里可以做分块处理。为简单起见，假设一次性传入。
    full_text = "\n".join(text_lines)

    prompt = f"""你是一个专业的短视频剪辑编导。
请阅读以下带编号的视频字幕文本，圈选出其中【最精彩的片段】。
精彩片段的定义：包含“金句”、“鲜明观点”、或“非常实用的技能/方法”。

请返回一个 JSON 数组，每个元素包含：
- "start_id": 片段开始的句子编号
- "end_id": 片段结束的句子编号（包含该句）
- "reason": 为什么选这段（金句/观点/技能）
- "title": 给这个片段起个简短的标题

要求：
1. 提取的片段应当语义完整，不要从半句话开始或结束。
2. 宁缺毋滥，只提取真正的精彩部分（通常1-3个片段即可）。
3. 必须返回合法的 JSON 数组，不包含 markdown 标签（如 ```json）。

字幕文本：
{full_text}
"""

    try:
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            extra_headers=extra_headers if extra_headers else None
        )
        res_text = resp.choices[0].message.content.strip()
        res_text = res_text.replace("```json", "").replace("```", "").strip()
        highlights = json.loads(res_text)
        print(f"成功提取 {len(highlights)} 个精彩片段：")
        for h in highlights:
            print(f"- {h.get('title')}: [{h.get('start_id')} - {h.get('end_id')}] ({h.get('reason')})")
        return highlights
    except Exception as e:
        print(f"提取精彩片段失败: {e}\nLLM返回内容: {res_text if 'res_text' in locals() else ''}")
        return []

def process_highlights(video_path, output_dir=None):
    if not output_dir:
        base = os.path.splitext(os.path.basename(video_path))[0]
        output_dir = f"output/{base}_highlights"
    os.makedirs(output_dir, exist_ok=True)
    
    status_path = os.path.join(output_dir, "highlight_status.json")
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "running", "progress_percent": 10, "message": "正在转录并获取全量字幕..."}, f, ensure_ascii=False)
        
    config = load_config()
    
    print(">>> 步骤 1：转写并获取全量字幕...")
    res = transcribe(video_path, output_dir)
    if not res or not isinstance(res, list) or len(res) == 0:
        print("未能提取到字幕信息。")
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump({"status": "error", "message": "未能提取到字幕信息"}, f, ensure_ascii=False)
        return []
    
    sentences = res[0].get("sentence_info", [])
    if not sentences:
        print("未能提取到字幕信息。")
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump({"status": "error", "message": "未能提取到字幕信息"}, f, ensure_ascii=False)
        return []

    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "running", "progress_percent": 30, "message": "正在使用大模型圈选精彩片段..."}, f, ensure_ascii=False)

    print("\n>>> 步骤 2：LLM 圈选精彩片段...")
    highlights = extract_highlights_intervals(sentences, config)
    if not highlights:
        print("未找到任何精彩片段。")
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump({"status": "done", "progress_percent": 100, "message": "未找到精彩片段", "outputs": []}, f, ensure_ascii=False)
        return []

    print("\n>>> 步骤 3：切割片段并进行智能四步法剪辑...")
    final_outputs = []
    
    total_clips = len(highlights)
    for idx, h in enumerate(highlights):
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump({"status": "running", "progress_percent": 40 + int(60 * idx / total_clips), "message": f"正在处理第 {idx+1}/{total_clips} 个片段..."}, f, ensure_ascii=False)
            
        start_id = h.get("start_id")
        end_id = h.get("end_id")
        title = h.get("title", f"片段_{idx+1}").replace(" ", "_").replace("/", "_")
        
        # 获取该片段的时间区间（前后各放宽 500ms 防止切字）
        start_ms = max(0, sentences[start_id].get("start", 0) - 500)
        end_ms = sentences[end_id].get("end", 0) + 500
        
        start_sec = start_ms / 1000.0
        duration_sec = (end_ms - start_ms) / 1000.0
        
        temp_video = os.path.join(output_dir, f"temp_{idx}.mp4")
        print(f"\n正在截取片段 {idx+1}: {title} ({start_sec}s - {start_sec + duration_sec}s)...")
        
        # 使用 ffmpeg 切割原视频作为临时底物
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-ss", str(start_sec), "-t", str(duration_sec),
            "-c:v", "libx264", "-c:a", "aac",
            temp_video
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 构建针对这个临时片段的独立 sentence_info
        segment_sentences = []
        for i in range(start_id, end_id + 1):
            s = sentences[i].copy()
            # 时间戳对齐到新片段（减去 start_ms，注意底物视频是从 start_sec 切割的，所以相对时间就是减去 start_ms）
            s["start"] = max(0, s["start"] - start_ms)
            s["end"] = max(0, s["end"] - start_ms)
            # timestamp 数组也需要对齐
            if "timestamp" in s:
                s["timestamp"] = [[max(0, t[0] - start_ms), max(0, t[1] - start_ms)] for t in s["timestamp"]]
            segment_sentences.append(s)
            
        temp_trans_json = os.path.join(output_dir, f"temp_trans_{idx}.json")
        with open(temp_trans_json, "w", encoding="utf-8") as f:
            # clip_video.py 需要的格式：[{"sentence_info": [...]}]
            json.dump([{"sentence_info": segment_sentences}], f, ensure_ascii=False, indent=2)
            
        # 调用智能视频剪辑的四步法/五步法，剔除无用片段
        out_clip = os.path.join(output_dir, f"{idx+1}_{title}.mp4")
        print(f"正在对片段进行智能剪辑（剔除废话/无声等），输出到: {out_clip}")
        process_smart_clip(temp_trans_json, temp_video, out_clip, config)
        
        if os.path.exists(out_clip):
            final_outputs.append(out_clip)
            # 清理临时文件
            os.remove(temp_video)
            os.remove(temp_trans_json)

    print("\n✅ 所有精彩片段智能剪辑完成！")
    for f in final_outputs:
        print(f" - {f}")
        
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "done", "progress_percent": 100, "message": "处理完成", "outputs": final_outputs}, f, ensure_ascii=False)
        
    return final_outputs

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="提取视频精彩片段并智能剪辑")
    parser.add_argument("video", help="输入的视频文件路径")
    parser.add_argument("--outdir", default=None, help="输出目录")
    parser.add_argument("--async-run", action="store_true", help="是否在后台异步执行以避免阻塞")
    args = parser.parse_args()

    # 如果指定了异步运行，并且当前不是子进程，则启动子进程并在主进程立即退出
    if getattr(args, 'async_run', False) and os.environ.get('HIGHLIGHT_ASYNC_WORKER') != '1':
        print(">> 检测到 --async-run 参数，正在将任务转入后台异步执行...")
        import subprocess, sys, os
        cmd = [sys.executable] + sys.argv
        if '--async-run' in cmd:
            cmd.remove('--async-run')
        env = os.environ.copy()
        env['HIGHLIGHT_ASYNC_WORKER'] = '1'
        
        subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        print(">> 后台任务已启动！Agent 可以立即退出等待，不被阻塞。请通过 highlight_status.json 轮询进度。")
        sys.exit(0)

    process_highlights(args.video, args.outdir)
