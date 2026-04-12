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
    items = []
    if result.timestamps:
        for ts in result.timestamps:
            items.append({
                "text": ts.text,
                "start": int(ts.start_time * 1000),
                "end": int(ts.end_time * 1000),
                "spk": ts.speaker or "Speaker",
            })

    is_char_level = all(len((item.get("text", "") or "").strip()) <= 1 for item in items) if items else False
    sentence_items = build_semantic_segments_from_text_and_tokens(result.text, items) if is_char_level else items
    char_items = items if is_char_level else []
    
    return [{
        "file_md5": file_md5,
        "text": result.text,
        "sentence_info": sentence_items,
        "char_level_info": char_items,
    }]

def ms_to_srt_time(ms):
    """将毫秒转换为 SRT 时间格式 (HH:MM:SS,mmm)"""
    hours = int(ms / 3600000)
    minutes = int((ms % 3600000) / 60000)
    seconds = int((ms % 60000) / 1000)
    milliseconds = int(ms % 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def build_semantic_segments_from_text_and_tokens(full_text, tokens):
    if not full_text or not tokens:
        return []

    hard_breaks = set("。！？!?；;")
    trailing_chars = set(" \t\r\n\"'”’）)]】》」』")

    segments = []
    token_idx = 0
    current_text = ""
    current_start = None
    current_end = None
    current_spk = "Speaker"
    pending_finalize = False

    def flush():
        nonlocal current_text, current_start, current_end, current_spk, pending_finalize
        text = current_text.strip()
        if text and current_start is not None and current_end is not None:
            segments.append({
                "text": text,
                "start": current_start,
                "end": current_end,
                "spk": current_spk,
            })
        current_text = ""
        current_start = None
        current_end = None
        current_spk = "Speaker"
        pending_finalize = False

    for ch in full_text:
        if pending_finalize and ch not in trailing_chars:
            flush()

        matched_token = None
        if token_idx < len(tokens):
            token_text = (tokens[token_idx].get("text", "") or "").strip()
            if token_text == ch:
                matched_token = tokens[token_idx]

        if matched_token is not None:
            if current_end is not None and matched_token.get("start", 0) - current_end >= 700 and current_text.strip():
                flush()
            current_text += ch
            if current_start is None:
                current_start = matched_token.get("start", 0)
                current_spk = matched_token.get("spk", "Speaker")
            current_end = matched_token.get("end", current_end)
            token_idx += 1
        else:
            current_text += ch

        if ch in hard_breaks:
            pending_finalize = True

    flush()

    if not segments:
        return tokens
    return segments

def _looks_like_char_level(items):
    if not items:
        return False
    short_count = 0
    for item in items:
        text = (item.get("text", "") or "").strip()
        if len(text) <= 1 and not str(item.get("spk", "")).startswith("SPEAKER_"):
            short_count += 1
    return short_count / max(len(items), 1) >= 0.8

def normalize_legacy_result(res):
    if not res or not isinstance(res, list) or len(res) == 0:
        return res

    item = res[0]
    text = item.get("text", "") or ""
    sentence_info = item.get("sentence_info", []) or []
    char_level_info = item.get("char_level_info")

    if char_level_info:
        semantic = item.get("sentence_info", []) or build_semantic_segments_from_text_and_tokens(text, char_level_info)
        item["sentence_info"] = semantic
        item["char_level_info"] = char_level_info
        return res

    if _looks_like_char_level(sentence_info):
        item["char_level_info"] = sentence_info
        item["sentence_info"] = build_semantic_segments_from_text_and_tokens(text, sentence_info)

    return res

def build_semantic_segments(res):
    if not res or not isinstance(res, list) or len(res) == 0:
        return []

    item = normalize_legacy_result(res)[0]
    sentences = item.get("sentence_info", []) or []
    if sentences:
        return sentences

    full_text = item.get("text", "") or ""
    tokens = item.get("char_level_info", []) or []
    return build_semantic_segments_from_text_and_tokens(full_text, tokens)

def apply_speaker_labels(sentence_items, diarization_items):
    if not sentence_items or not diarization_items:
        return sentence_items

    for sentence in sentence_items:
        best_spk = sentence.get("spk", "Speaker")
        best_overlap = -1
        sent_start = sentence.get("start", 0)
        sent_end = sentence.get("end", 0)
        sent_mid = (sent_start + sent_end) / 2

        for diar in diarization_items:
            diar_start = diar.get("start", 0)
            diar_end = diar.get("end", 0)
            overlap = min(sent_end, diar_end) - max(sent_start, diar_start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_spk = diar.get("spk", best_spk)
            elif best_overlap <= 0 and diar_start <= sent_mid <= diar_end:
                best_spk = diar.get("spk", best_spk)

        sentence["spk"] = best_spk

    return sentence_items

def normalize_speaker_names(res):
    if not res or not isinstance(res, list) or len(res) == 0:
        return res

    item = res[0]
    speaker_map = {}
    next_index = 0

    def normalize_spk(value):
        nonlocal next_index
        raw = str(value or "Speaker").strip()
        if raw.startswith("SPEAKER_"):
            return raw
        if raw not in speaker_map:
            speaker_map[raw] = f"SPEAKER_{next_index:02d}"
            next_index += 1
        return speaker_map[raw]

    for key in ("sentence_info", "char_level_info"):
        for entry in item.get(key, []) or []:
            entry["spk"] = normalize_spk(entry.get("spk"))

    return res

def generate_srt(res, srt_path):
    """
    根据 FunASR 结果生成带毫秒级时间戳的 SRT 文件
    res: FunASR generate 返回的列表，通常形如 [{"text": "...", "timestamp": [[start_ms, end_ms], ...], "spk": [...]}]
    """
    if not res or not isinstance(res, list) or len(res) == 0:
        return
    
    sentences = build_semantic_segments(res)
    speaker_set = {
        str(sentence.get("spk", "")).strip()
        for sentence in sentences
        if str(sentence.get("spk", "")).strip()
    }
    include_speaker_label = len(speaker_set) > 1

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
            content = f"{spk}: {text}" if include_speaker_label else text
            f.write(f"{content}\n\n")

def generate_txt(res, txt_path):
    """生成纯文本全文"""
    if not res or not isinstance(res, list) or len(res) == 0:
        return
    
    sentences = build_semantic_segments(res)
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
                    saved_data = normalize_legacy_result(saved_data)
                    saved_data = normalize_speaker_names(saved_data)
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(saved_data, f, ensure_ascii=False, indent=2)
                    generate_srt(saved_data, srt_path)
                    generate_txt(saved_data, txt_path)
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
    res = normalize_legacy_result(res)

    diarization_enabled = (
        config.get("ASR_ENGINE", "funasr") == "qwen3-asr"
        and config.get("QWEN3ASR_ENABLE_DIARIZATION", "false").strip().lower() == "true"
    )
    if diarization_enabled:
        try:
            print("使用 FunASR 说话人分离为 Qwen3-ASR 结果补充 speaker 标签...")
            diarization_config = dict(config)
            diarization_config["ASR_ENGINE"] = "funasr"
            diarization_engine = create_asr_engine(diarization_config)
            diarization_result = diarization_engine.transcribe(
                audio_path=audio_path,
                return_timestamps=True,
            )
            diarization_res = _convert_result_to_legacy(diarization_result, file_md5)
            diarization_res = normalize_legacy_result(diarization_res)
            diarization_items = diarization_res[0].get("sentence_info", [])
            res[0]["sentence_info"] = apply_speaker_labels(res[0].get("sentence_info", []), diarization_items)
        except Exception as e:
            print(f"Qwen3-ASR 说话人分离补充失败，继续输出无 speaker 版本: {e}")

    res = normalize_speaker_names(res)

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
