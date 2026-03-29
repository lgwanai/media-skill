import os
import sys
import json
import argparse
import subprocess
import math
import cv2
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import re
import shutil
import concurrent.futures
import string

# 确保可以引入 scripts 目录下的其他模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from transcribe import transcribe, ms_to_srt_time
from utils import load_config, get_openclaw_headers, create_openai_client, get_unified_output_dir

def clean_punctuation(text):
    """去除中英文字符串中的标点符号"""
    # 英文标点
    text = text.translate(str.maketrans('', '', string.punctuation))
    # 中文标点
    zh_punct = "！？｡。＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏."
    text = text.translate(str.maketrans('', '', zh_punct))
    return text

def split_subtitle_text(text, max_len_zh=10, max_len_en=20):
    """根据字数限制拆分长字幕，返回多个等分片段，同时确保不截断英文单词"""
    text = clean_punctuation(text).strip()
    text = re.sub(r'\s+', ' ', text)
    if not text:
        return []
        
    def get_len(char_or_word):
        if re.match(r'^[a-zA-Z0-9_]+$', char_or_word):
            return len(char_or_word) * (max_len_zh / max_len_en)
        elif char_or_word.isspace():
            return 0.5
        else:
            return 1.0

    # 拆分为英文单词、空格或单个字符
    tokens = re.findall(r'[a-zA-Z0-9_]+|\s+|.', text)
    total_len = sum(get_len(t) for t in tokens)
    
    if total_len <= max_len_zh:
        return [text.strip()]
        
    num_parts = math.ceil(total_len / max_len_zh)
    target_len = total_len / num_parts
    
    parts = []
    current_part = []
    current_len = 0
    
    for token in tokens:
        tok_len = get_len(token)
        # 如果当前片段加上新 token 后的一半超过目标长度，且还有剩余的分段额度，则在此切分
        if current_len + tok_len/2 > target_len and len(parts) < num_parts - 1:
            if current_part:
                parts.append("".join(current_part).strip())
                current_part = [token]
                current_len = tok_len
            else:
                current_part.append(token)
                current_len += tok_len
        else:
            current_part.append(token)
            current_len += tok_len
            
    if current_part:
        parts.append("".join(current_part).strip())
        
    return parts

def prepare_subtitles_data(sentences, is_vertical=False):
    """处理转录结果：去标点、按屏幕方向进行长字幕拆分，返回 {start, end, text} 列表"""
    max_zh = 10 if is_vertical else 16
    max_en = 20 if is_vertical else 32
    
    subtitles_data = []
    for sentence in sentences:
        start_sec = sentence.get("start", 0) / 1000.0
        end_sec = sentence.get("end", 0) / 1000.0
        text = sentence.get("text", "")
        
        parts = split_subtitle_text(text, max_len_zh=max_zh, max_len_en=max_en)
        if not parts:
            continue
            
        if len(parts) == 1:
            subtitles_data.append({"start": start_sec, "end": end_sec, "text": parts[0]})
        else:
            # 如果拆分了，把时间平分给每个片段
            duration = end_sec - start_sec
            part_dur = duration / len(parts)
            for i, p in enumerate(parts):
                subtitles_data.append({
                    "start": start_sec + i * part_dur,
                    "end": start_sec + (i + 1) * part_dur,
                    "text": p
                })
    return subtitles_data

def draw_rounded_rectangle(draw, xy, rad, fill):
    """绘制圆角矩形"""
    x0, y0, x1, y1 = xy
    draw.rectangle([x0, y0 + rad, x1, y1 - rad], fill=fill)
    draw.rectangle([x0 + rad, y0, x1 - rad, y1], fill=fill)
    draw.pieslice([x0, y0, x0 + rad * 2, y0 + rad * 2], 180, 270, fill=fill)
    draw.pieslice([x1 - rad * 2, y0, x1, y0 + rad * 2], 270, 360, fill=fill)
    draw.pieslice([x0, y1 - rad * 2, x0 + rad * 2, y1], 90, 180, fill=fill)
    draw.pieslice([x1 - rad * 2, y1 - rad * 2, x1, y1], 0, 90, fill=fill)

def render_video_chunk(video_path, start_frame, end_frame, subtitles_data, width, height, fps, font, font_size, output_path):
    """多线程 worker：渲染视频的指定帧范围"""
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    frame_idx = start_frame
    while frame_idx < end_frame:
        ret, frame = cap.read()
        if not ret: break
        
        current_time = frame_idx / fps
        
        # 找当前字幕
        current_text = None
        for sub in subtitles_data:
            if sub["start"] <= current_time <= sub["end"]:
                current_text = sub["text"]
                break
                
        if current_text:
            img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img_pil)
            
            try:
                bbox = font.getbbox(current_text)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
            except:
                text_w = len(current_text) * font_size
                text_h = font_size
                
            # 调整高度：再往上升一行字的高度 (大约为 text_h 的 1.5 倍加上原来的 margin)
            margin_bottom = int(height * 0.1) + int(text_h * 1.5)
            x = (width - text_w) // 2
            y = height - text_h - margin_bottom
            
            # 白底圆角矩形，自适应文字长度，左右各加一些 padding
            padding_x = int(font_size * 0.5)
            padding_y = int(font_size * 0.3)
            bg_rect = [x - padding_x, y - padding_y, x + text_w + padding_x, y + text_h + padding_y]
            
            draw_rounded_rectangle(draw, bg_rect, rad=int(font_size * 0.3), fill=(255, 255, 255))
            
            # 黑字
            draw.text((x, y), current_text, font=font, fill=(0, 0, 0))
            
            frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            
        out.write(frame)
        frame_idx += 1
            
    cap.release()
    out.release()
    return output_path
def detect_domain_and_translate(sentences, target_lang, config):
    print(f"\n>>> 正在使用 LLM 分析领域并进行【{target_lang}】翻译...")
    client = create_openai_client(
        api_key=config.get("TEXT_LLM_API_KEY"),
        base_url=config.get("TEXT_LLM_URL")
    )
    model_name = config.get("TEXT_LLM_MODEL_NAME", "deepseek-chat")
    extra_headers = get_openclaw_headers(config)

    # 1. 提取全文本用于领域分析
    full_text = " ".join([s.get("text", "") for s in sentences])
    # 限制分析文本长度
    sample_text = full_text[:2000] 

    domain_prompt = f"""你是一个内容分析专家。请根据以下视频文本，分析其【专业领域】和【核心上下文】。
文本：
{sample_text}

请只输出一两句话，描述该视频的专业领域和背景，不要有任何废话。"""

    try:
        domain_resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": domain_prompt}],
            temperature=0.3,
            extra_headers=extra_headers if extra_headers else None
        )
        domain_context = domain_resp.choices[0].message.content.strip()
        print(f"识别到的专业领域及上下文：\n{domain_context}\n")
    except Exception as e:
        print(f"领域分析失败: {e}")
        domain_context = "通用领域"

    # 2. 分块翻译
    chunk_size = 30 # 每次翻译30句
    translated_sentences = []
    
    for i in range(0, len(sentences), chunk_size):
        chunk = sentences[i:i+chunk_size]
        chunk_data = [{"id": j, "text": s.get("text", "")} for j, s in enumerate(chunk)]
        
        trans_prompt = f"""你是一个专业的字幕翻译专家。
当前视频的专业领域与上下文：{domain_context}

任务：
请将以下 JSON 格式的字幕句子翻译成【{target_lang}】。
要求：
1. 结合上下文，理解语义后再翻译，避免错别字。
2. 不要字对字、词对词生硬翻译。
3. 原文中的语气词（如“呃”、“啊”、“那个”）请直接忽略，不要翻译。
4. 保持 JSON 格式返回，包含 id 和翻译后的 text。
5. 必须返回合法的 JSON 数组，绝不要包含 ```json 标签或其他废话。

待翻译内容：
{json.dumps(chunk_data, ensure_ascii=False)}"""

        try:
            trans_resp = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": trans_prompt}],
                temperature=0.3,
                extra_headers=extra_headers if extra_headers else None
            )
            res_text = trans_resp.choices[0].message.content.strip()
            # 清理可能的 markdown 标记
            res_text = res_text.replace("```json", "").replace("```", "").strip()
            trans_data = json.loads(res_text)
            
            # 合并结果
            for j, s in enumerate(chunk):
                # 寻找对应 id
                match = next((item for item in trans_data if item.get("id") == j), None)
                if match:
                    s["text"] = match.get("text", "")
                translated_sentences.append(s)
        except Exception as e:
            print(f"翻译块 {i} 失败: {e}，将使用原文")
            # 失败则使用原文
            for s in chunk:
                translated_sentences.append(s)

    return translated_sentences

def burn_subtitles_and_merge(video_path, sentences, audio_path, output_path, output_dir):
    # 4. 视频字幕硬烧录 (多线程 OpenCV)
    print(f"\n>>> 步骤 4：多线程压制字幕到视频 -> {output_path}")
    
    abs_video_path = os.path.abspath(video_path)
    abs_output_path = os.path.abspath(output_path)
    
    # 获取视频属性
    cap = cv2.VideoCapture(abs_video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0 or np.isnan(fps): fps = 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    
    is_vertical = height > width
    subtitles_data = prepare_subtitles_data(sentences, is_vertical=is_vertical)
    
    # 字体准备
    font_path = "/System/Library/Fonts/PingFang.ttc"
    if not os.path.exists(font_path):
        font_path = "/System/Library/Fonts/STHeiti Light.ttc"
    
    # 调整字体大小，竖屏更小一些
    if is_vertical:
        font_size = int(width / 14) # 竖屏适配10个字左右
    else:
        font_size = int(height * 0.06) # 横屏
        
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()
    
    # 多线程分段渲染
    num_threads = min(8, os.cpu_count() or 4)
    chunk_size = math.ceil(total_frames / num_threads)
    
    temp_chunks = []
    futures = []
    
    print(f"总帧数: {total_frames}, 启动 {num_threads} 个线程进行分段渲染...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        for i in range(num_threads):
            start_frame = i * chunk_size
            end_frame = min((i + 1) * chunk_size, total_frames)
            if start_frame >= total_frames:
                break
                
            chunk_output = os.path.join(output_dir, f"chunk_{i}.mp4")
            temp_chunks.append(chunk_output)
            
            futures.append(
                executor.submit(
                    render_video_chunk,
                    abs_video_path, start_frame, end_frame, subtitles_data,
                    width, height, fps, font, font_size, chunk_output
                )
            )
            
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"渲染线程报错: {e}")
                
    # 合并分段视频
    print("所有分段渲染完成，正在合并分段视频...")
    concat_list_path = os.path.join(output_dir, "concat_list.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for chunk in temp_chunks:
            f.write(f"file '{os.path.abspath(chunk)}'\n")
            
    temp_video_no_audio = os.path.join(output_dir, "merged_no_audio.mp4")
    concat_cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path, "-c", "copy", temp_video_no_audio]
    subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print("硬字幕烧录完毕！正在合并音频...")
    if audio_path and os.path.exists(audio_path):
        merge_cmd = ["ffmpeg", "-y", "-i", temp_video_no_audio, "-i", audio_path, "-c:v", "copy", "-c:a", "aac", abs_output_path]
    else:
        merge_cmd = ["ffmpeg", "-y", "-i", temp_video_no_audio, "-c:v", "copy", abs_output_path]
        
    subprocess.run(merge_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 清理
    for chunk in temp_chunks:
        if os.path.exists(chunk): os.remove(chunk)
    if os.path.exists(concat_list_path): os.remove(concat_list_path)
    if os.path.exists(temp_video_no_audio): os.remove(temp_video_no_audio)
    
    print(f"\n✅ 焊死字幕视频生成完成: {output_path}")
    return output_path

def process_subtitle(video_path, target_lang=None, output_path=None):
    config = load_config()
    output_dir = get_unified_output_dir(video_path, config)
    
    if not output_path:
        base_name = os.path.basename(video_path)
        name_without_ext, ext = os.path.splitext(base_name)
        output_path = os.path.join(output_dir, f"{name_without_ext}_subtitled{ext}")

    status_path = os.path.join(output_dir, "subtitle_status.json")
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "running", "progress_percent": 10, "message": "正在进行语音识别..."}, f, ensure_ascii=False)

    print(">>> 步骤 1：毫秒级转字幕...")
    res = transcribe(video_path, output_dir)
    if not res or not isinstance(res, list) or len(res) == 0:
        print("未能提取到字幕信息。")
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump({"status": "error", "message": "未能提取到字幕信息"}, f, ensure_ascii=False)
        return None
    
    sentences = res[0].get("sentence_info", [])
    if not sentences:
        print("未能提取到字幕信息。")
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump({"status": "error", "message": "未能提取到字幕信息"}, f, ensure_ascii=False)
        return None

    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "running", "progress_percent": 40, "message": "正在处理/翻译字幕..."}, f, ensure_ascii=False)

    print(f"\n>>> 步骤 2：字幕处理 (目标语言: {target_lang if target_lang else '原语言'})")
    if target_lang and target_lang.lower() not in ["", "none", "null"]:
        # 使用大模型翻译
        sentences = detect_domain_and_translate(sentences, target_lang, config)

    # 3. 生成临时 SRT (仅供调试参考，非必须)
    srt_path = os.path.join(output_dir, "temp.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, sentence in enumerate(sentences, 1):
            start_time = ms_to_srt_time(sentence.get("start", 0))
            end_time = ms_to_srt_time(sentence.get("end", 0))
            text = sentence.get("text", "").strip()
            f.write(f"{i}\n{start_time} --> {end_time}\n{text}\n\n")

    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "running", "progress_percent": 70, "message": "正在渲染硬字幕..."}, f, ensure_ascii=False)

    # 4. 提取原视频音频并烧录合并
    abs_video_path = os.path.abspath(video_path)
    video_dir = os.path.dirname(abs_video_path)
    
    temp_audio = os.path.join(output_dir, "temp_original_audio.aac")
    subprocess.run(["ffmpeg", "-y", "-i", abs_video_path, "-vn", "-c:a", "copy", temp_audio], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    burn_subtitles_and_merge(video_path, sentences, temp_audio, output_path, output_dir)
    
    if os.path.exists(temp_audio): os.remove(temp_audio)
    
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "done", "progress_percent": 100, "output_path": output_path}, f, ensure_ascii=False)

    return output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Media Skill 智能字幕与翻译工具")
    parser.add_argument("video", help="输入的音视频文件路径")
    parser.add_argument("--lang", help="目标翻译语言 (如 English)。如果不填，则仅生成原语言字幕。")
    parser.add_argument("--out", help="输出的带字幕视频路径。如果不填，默认在统一 output 目录下生成。")
    
    args = parser.parse_args()

    process_subtitle(args.video, args.lang, args.out)
