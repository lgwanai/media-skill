import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import load_config, get_file_md5, get_unified_output_dir, setup_env

setup_env()

import json
import subprocess
from asr_engines.base import TranscriptionResult
from asr_engines.factory import create_asr_engine

def extract_audio(video_path, audio_path):
    print(f"提取音频并进行降噪处理: {video_path} -> {audio_path}")
    cmd = [
        "ffmpeg", "-y", "-i", video_path, 
        "-vn", "-af", "afftdn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", 
        audio_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def _convert_result_to_legacy(result: TranscriptionResult, file_md5: str) -> list:
    """Convert TranscriptionResult to legacy FunASR format for compatibility.
    
    Maintains backward compatibility with existing output generation code.
    """
    sentences = []
    if result.timestamps:
        for ts in result.timestamps:
            sentences.append({
                "text": ts.text,
                "start": int(ts.start_time * 1000),
                "end": int(ts.end_time * 1000),
                "spk": "Speaker",
            })
    
    return [{
        "file_md5": file_md5,
        "text": result.text,
        "sentence_info": sentences,
    }]

def ms_to_srt_time(ms):
    """将毫秒转换为 SRT 时间格式 (HH:MM:SS,mmm)"""
    hours = int(ms / 3600000)
    minutes = int((ms % 3600000) / 60000)
    seconds = int((ms % 60000) / 1000)
    milliseconds = int(ms % 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def generate_srt(res, srt_path):
    """
    根据 FunASR 结果生成带毫秒级时间戳的 SRT 文件
    res: FunASR generate 返回的列表，通常形如 [{"text": "...", "timestamp": [[start_ms, end_ms], ...], "spk": [...]}]
    """
    if not res or not isinstance(res, list) or len(res) == 0:
        return
    
    # 适配不同的返回结构，FunASR 1.x 中带时间戳和说话人的结果通常在 sentence_info 字段
    sentences = res[0].get("sentence_info", [])
    if not sentences and "timestamp" in res[0]:
        # 如果没有结构化 sentence_info，尝试兜底解析 (这里仅做简单的防空处理)
        pass

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, sentence in enumerate(sentences, 1):
            start_ms = sentence.get("start", 0)
            end_ms = sentence.get("end", 0)
            text = sentence.get("text", "").strip()
            spk = sentence.get("spk", "Unknown")
            
            start_time = ms_to_srt_time(start_ms)
            end_time = ms_to_srt_time(end_ms)
            
            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"[说话人{spk}]: {text}\n\n")

def generate_txt(res, txt_path):
    """生成纯文本全文"""
    if not res or not isinstance(res, list) or len(res) == 0:
        return
    
    sentences = res[0].get("sentence_info", [])
    with open(txt_path, "w", encoding="utf-8") as f:
        for sentence in sentences:
            text = sentence.get("text", "").strip()
            spk = sentence.get("spk", "Unknown")
            f.write(f"[说话人{spk}]: {text}\n")

def transcribe(media_path, output_dir=None):
    config = load_config()
    model_dir = config.get("MODEL_DIR", "models/")
    os.makedirs(model_dir, exist_ok=True)

    print(f"计算文件 MD5: {media_path} ...")
    file_md5 = get_file_md5(media_path)
    print(f"文件 MD5: {file_md5}")

    # 获取统一输出目录
    specific_output_dir = get_unified_output_dir(media_path, config)

    json_path = os.path.join(specific_output_dir, "transcription.json")
    srt_path = os.path.join(specific_output_dir, "transcription.srt")
    txt_path = os.path.join(specific_output_dir, "transcription.txt")
    status_path = os.path.join(specific_output_dir, "transcribe_status.json")

    # 写入初始状态
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "running", "progress_percent": 10}, f, ensure_ascii=False)

    # 检查是否已经解析过（MD5 匹配）
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
            
            if isinstance(saved_data, list) and len(saved_data) > 0:
                saved_md5 = saved_data[0].get("file_md5", "")
                if saved_md5 == file_md5:
                    print(f"✅ 发现已存在的解析记录且 MD5 匹配，跳过大模型调用！直接使用: {specific_output_dir}")
                    with open(status_path, "w", encoding="utf-8") as f:
                        json.dump({"status": "done", "progress_percent": 100}, f, ensure_ascii=False)
                    return saved_data
        except Exception as e:
            print(f"读取历史解析结果失败，将重新解析: {e}")

    audio_path = media_path
    if media_path.lower().endswith((".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mp3", ".wav", ".aac", ".m4a", ".flac", ".ogg", ".wma")):
        audio_path = os.path.join(specific_output_dir, "temp_audio.wav")
        if not os.path.exists(audio_path):
            extract_audio(media_path, audio_path)
        else:
            print(f"✅ 发现已提取的音频文件，跳过音频提取: {audio_path}")

    config = load_config()
    
    print(f"加载 ASR 引擎: {config.get('ASR_ENGINE', 'funasr')}...")
    engine = create_asr_engine(config)
    
    print(f"开始识别: {audio_path}")
    result = engine.transcribe(
        audio_path=audio_path,
        return_timestamps=True,
    )
    
    res = _convert_result_to_legacy(result, file_md5)

    from vocab_utils import load_vocab, apply_vocab_to_result
    
    vocab_path = os.path.join("data", "hotwords.yaml")
    vocab = load_vocab(vocab_path)
    if vocab:
        print(f"应用专业词库 ({len(vocab)} 个映射规则)...")
        res = apply_vocab_to_result(res, vocab)
        
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)

    # Generate output files
    generate_srt(res, srt_path)
    generate_txt(res, txt_path)

    print(f"解析完成！输出目录: {specific_output_dir}")
    
    # 写入完成状态
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "done", "progress_percent": 100}, f, ensure_ascii=False)
        
    return res

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Transcribe media file.")
    parser.add_argument("media_file_path", nargs="?", help="Path to the media file")
    args = parser.parse_args()

    if args.media_file_path:
        transcribe(args.media_file_path)
    else:
        print("Usage: python transcribe.py <media_file_path>")
