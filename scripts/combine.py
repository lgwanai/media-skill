import os
import sys
import argparse
import json

# 确保可以引入 scripts 目录下的其他模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from highlight import process_highlights
from subtitle import process_subtitle

def process_combine(video_path, target_lang=None, output_dir=None):
    if not output_dir:
        base = os.path.splitext(os.path.basename(video_path))[0]
        output_dir = f"output/{base}_combined_highlights"
    os.makedirs(output_dir, exist_ok=True)
    
    status_path = os.path.join(output_dir, "combine_status.json")
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "running", "progress_percent": 5, "message": "启动联合流水线..."}, f, ensure_ascii=False)
        
    print(f"==================================================")
    print(f"🚀 开始执行联合技能：自动提取精彩片段 -> 智能剪辑 -> 配字幕")
    print(f"==================================================\n")
    
    # 1. 提取精彩片段并智能剪辑
    print(f"【阶段一】开始从 {video_path} 提取精彩片段并智能剪辑...")
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "running", "progress_percent": 10, "message": "阶段一：提取精彩片段并智能剪辑..."}, f, ensure_ascii=False)
        
    highlight_videos = process_highlights(video_path, output_dir=os.path.join(output_dir, "clips"))
    
    if not highlight_videos:
        print("未能提取到任何精彩片段，流程结束。")
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump({"status": "error", "message": "未能提取到精彩片段"}, f, ensure_ascii=False)
        return []
        
    print(f"\n【阶段一完成】共生成 {len(highlight_videos)} 个剪辑好的片段视频。\n")
    
    # 2. 为每个片段配字幕（包含翻译/排版）
    final_videos = []
    print(f"【阶段二】开始为提取的片段添加字幕 (目标语言: {target_lang if target_lang else '原语言'})...")
    
    total = len(highlight_videos)
    for i, clip_path in enumerate(highlight_videos):
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump({"status": "running", "progress_percent": 50 + int(50 * i / total), "message": f"阶段二：正在为第 {i+1}/{total} 个片段添加字幕..."}, f, ensure_ascii=False)
            
        print(f"\n---> 正在处理第 {i+1} 个片段: {clip_path}")
        # 输出路径加上 _sub 标记
        base_name, ext = os.path.splitext(os.path.basename(clip_path))
        final_out = os.path.join(output_dir, f"{base_name}_sub{ext}")
        
        # 调用配字幕技能
        res_video = process_subtitle(clip_path, target_lang=target_lang, output_path=final_out)
        if res_video and os.path.exists(res_video):
            final_videos.append(res_video)
            
    print(f"\n==================================================")
    print(f"🎉 联合技能执行完毕！共输出 {len(final_videos)} 个最终带字幕精彩视频：")
    for f in final_videos:
        print(f" ✅ {f}")
    print(f"==================================================")
    
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "done", "progress_percent": 100, "message": "流水线全部完成", "outputs": final_videos}, f, ensure_ascii=False)
        
    return final_videos

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Combine Pipeline")
    parser.add_argument("video", help="输入的视频文件路径")
    parser.add_argument("--lang", default=None, help="目标字幕语言，如 'English', '中文'。不填则使用原视频语言。")
    parser.add_argument("--outdir", default=None, help="最终输出目录")
    args = parser.parse_args()
    
    process_combine(args.video, args.lang, args.outdir)
