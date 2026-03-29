import os
import sys
import subprocess
import argparse
from utils import load_config, get_unified_output_dir
from transcribe import transcribe, extract_audio, ms_to_srt_time
from subtitle import detect_domain_and_translate, burn_subtitles_and_merge
from dubbing import clone_voice, dub_subtitle, analyze_text_for_tts_params

def find_best_audio_sample(sentences, audio_path, output_dir):
    """
    寻找一个时长在 5-15 秒之间、连续且完整的语音片段作为克隆样本
    """
    sample_text = ""
    start_ms = 0
    end_ms = 0
    
    for i in range(len(sentences)):
        chunk_text = sentences[i].get("text", "")
        # 过滤掉太短的无意义语气词片段
        if len(chunk_text) < 3: 
            continue
            
        current_start = sentences[i].get("start", 0)
        current_end = sentences[i].get("end", 0)
        current_text = chunk_text
        
        # 尝试向后拼接，形成连续完整的长句
        for j in range(i + 1, len(sentences)):
            next_start = sentences[j].get("start", 0)
            next_end = sentences[j].get("end", 0)
            
            # 如果两句话之间停顿超过 2 秒，认为不连续，中断拼接
            if next_start - current_end > 2000:
                break
                
            current_text += " " + sentences[j].get("text", "")
            current_end = next_end
            
            # 如果时长已经达到 15 秒以上，停止拼接
            if current_end - current_start >= 15000:
                break
                
        # 只要找到了 5-15 秒之间的片段，就认为是一个合格的样本
        if 5000 <= current_end - current_start <= 15000:
            sample_text = current_text
            start_ms = current_start
            end_ms = current_end
            break
            
    # 兜底策略：如果没找到完美的，直接取前几句凑够约 10 秒
    if not sample_text and sentences:
        start_ms = sentences[0].get("start", 0)
        end_ms = min(sentences[-1].get("end", 0), start_ms + 10000)
        sample_text = " ".join(s.get("text", "") for s in sentences if start_ms <= s.get("start", 0) and s.get("end", 0) <= end_ms)
        
    if not sample_text:
        return None, None
        
    sample_wav = os.path.join(output_dir, "clone_sample.wav")
    start_sec = start_ms / 1000.0
    duration_sec = (end_ms - start_ms) / 1000.0
    
    cmd = ["ffmpeg", "-y", "-i", audio_path, "-ss", str(start_sec), "-t", str(duration_sec), "-c", "copy", sample_wav]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    return sample_wav, sample_text

def process_translate_video(video_path, target_lang, output_path=None):
    config = load_config()
    output_dir = get_unified_output_dir(video_path, config)
    
    if not output_path:
        base_name = os.path.basename(video_path)
        name_without_ext, ext = os.path.splitext(base_name)
        output_path = os.path.join(output_dir, f"{name_without_ext}_translated{ext}")
        
    print(">>> 步骤 1：提取原视频音频并进行精准字幕识别...")
    res = transcribe(video_path, output_dir)
    if not res or not isinstance(res, list) or len(res) == 0:
        print("未能提取到字幕信息。")
        return None
        
    sentences = res[0].get("sentence_info", [])
    if not sentences:
        print("未能提取到字幕信息。")
        return None
        
    audio_path = os.path.join(output_dir, "temp_audio.wav")
    if not os.path.exists(audio_path):
        extract_audio(video_path, audio_path)
        
    print("\n>>> 步骤 2：提取优质音频样本并克隆音色...")
    sample_wav, sample_text = find_best_audio_sample(sentences, audio_path, output_dir)
    if not sample_wav:
        print("未能找到合适的音频样本进行克隆。")
        return None
        
    api_key = config.get("SILICONFLOW_API_KEY", "")
    mode = config.get("INDEXTTS_MODE", "api").strip().lower()
    
    voice_name = f"clone_{os.path.basename(output_dir)}"
    print(f"提取到样本: {sample_text} ({sample_wav})")
    voice_id = clone_voice(api_key, sample_wav, sample_text, voice_name, mode=mode, config=config)
    if not voice_id:
        print("音色克隆失败。")
        return None
        
    print(f"\n>>> 步骤 3：字幕翻译 (目标语言: {target_lang})...")
    translated_sentences = detect_domain_and_translate(sentences, target_lang, config)
    
    translated_srt_path = os.path.join(output_dir, "translated.srt")
    with open(translated_srt_path, "w", encoding="utf-8") as f:
        for i, sentence in enumerate(translated_sentences, 1):
            start_time = ms_to_srt_time(sentence.get("start", 0))
            end_time = ms_to_srt_time(sentence.get("end", 0))
            text = sentence.get("text", "").strip()
            f.write(f"{i}\n{start_time} --> {end_time}\n{text}\n\n")
            
    print(f"\n>>> 步骤 4：使用克隆音色进行同声配音...")
    dubbed_audio_path = os.path.join(output_dir, "dubbed_audio.mp3")
    
    full_text = " ".join([s["text"] for s in translated_sentences[:10]])
    tts_params = analyze_text_for_tts_params(full_text, config) if mode == "local" else {}
    
    dubbed_audio_path = dub_subtitle(api_key, translated_srt_path, voice_id, dubbed_audio_path, mode=mode, tts_params=tts_params)
    if not dubbed_audio_path or not os.path.exists(dubbed_audio_path):
        print("配音生成失败。")
        return None
        
    print(f"\n>>> 步骤 5：剔除原声，烧录翻译字幕与合成新语音...")
    burn_subtitles_and_merge(video_path, translated_sentences, dubbed_audio_path, output_path, output_dir)
    
    print(f"\n🎉 同音色翻译视频生成完毕: {output_path}")
    return output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="同音色翻译视频")
    parser.add_argument("video", help="输入的视频文件路径")
    parser.add_argument("--lang", required=True, help="目标翻译语言，如 'English', '日语'")
    parser.add_argument("--out", default=None, help="输出的视频路径")
    args = parser.parse_args()
    
    process_translate_video(args.video, args.lang, args.out)
