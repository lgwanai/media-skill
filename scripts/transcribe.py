import os
import json
import subprocess
from funasr import AutoModel

def load_config(config_path="config.txt"):
    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    config[k.strip()] = v.strip()
    return config

def extract_audio(video_path, audio_path):
    print(f"提取音频: {video_path} -> {audio_path}")
    cmd = [
        "ffmpeg", "-y", "-i", video_path, 
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", 
        audio_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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

def transcribe(media_path, output_dir="output"):
    config = load_config()
    model_dir = config.get("MODEL_DIR", "models/")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(model_dir, exist_ok=True)

    audio_path = media_path
    if media_path.lower().endswith((".mp4", ".mkv", ".avi")):
        audio_path = os.path.join(output_dir, "temp_audio.wav")
        extract_audio(media_path, audio_path)

    print("加载 FunASR 模型...")
    # Initialize the model pipeline (Paraformer + VAD + PUNC + CAM++)
    model = AutoModel(
        model="paraformer-zh",
        model_revision="v2.0.4",
        vad_model="fsmn-vad",
        vad_model_revision="v2.0.4",
        punc_model="ct-punc",
        punc_model_revision="v2.0.4",
        spk_model="cam++",
        spk_model_revision="v2.0.2",
    )

    print(f"开始识别: {audio_path}")
    res = model.generate(input=audio_path, batch_size_s=300, sentence_timestamp=True, return_spk_res=True)

    # Save JSON with timestamps
    json_path = os.path.join(output_dir, "transcription.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
        
    srt_path = os.path.join(output_dir, "transcription.srt")
    generate_srt(res, srt_path)
    
    txt_path = os.path.join(output_dir, "transcription.txt")
    generate_txt(res, txt_path)

    print(f"识别完成，结果已保存至: \n - {json_path}\n - {srt_path}\n - {txt_path}")
    return res

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        transcribe(sys.argv[1])
    else:
        print("Usage: python transcribe.py <media_file_path>")
