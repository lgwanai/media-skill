import os
import sys
# 确保可以引入 scripts 目录下的其他模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import load_config, get_file_md5, get_unified_output_dir

import json
import subprocess
import hashlib
from funasr import AutoModel

# 为 funasr 1.x 补充注册 ERes2Net 模型
from funasr.register import tables
import time
import torch
import numpy as np
from funasr.models.campplus.utils import extract_feature
from funasr.utils.load_utils import load_audio_text_image_video

try:
    from funasr.models.eres2net.eres2net_aug import ERes2NetAug
    class ERes2NetAugWrapper(ERes2NetAug):
        def __init__(self, **kwargs):
            super().__init__(
                m_channels=kwargs.get("m_channels", 64),
                feat_dim=kwargs.get("feat_dim", 80),
                embedding_size=kwargs.get("embedding_size", 192),
                pooling_func=kwargs.get("pooling_func", "TSTP"),
                two_emb_layer=kwargs.get("two_emb_layer", False),
            )
            
        def inference(self, data_in, data_lengths=None, key: list = None, tokenizer=None, frontend=None, **kwargs):
            meta_data = {}
            time1 = time.perf_counter()
            audio_sample_list = load_audio_text_image_video(
                data_in, fs=16000, audio_fs=kwargs.get("fs", 16000), data_type="sound"
            )
            time2 = time.perf_counter()
            meta_data["load_data"] = f"{time2 - time1:0.3f}"
            speech, speech_lengths, speech_times = extract_feature(audio_sample_list)
            speech = speech.to(device=kwargs["device"])
            time3 = time.perf_counter()
            meta_data["extract_feat"] = f"{time3 - time2:0.3f}"
            meta_data["batch_data_time"] = np.array(speech_times).sum().item() / 16000.0
            
            with torch.no_grad():
                spk_embedding = self.forward(speech.to(torch.float32))
            results = [{"spk_embedding": spk_embedding}]
            return results, meta_data

    tables.register("model_classes", "iic/speech_eres2net_sv_zh-cn_16k-common")(ERes2NetAugWrapper)
except Exception as e:
    print(f"注册 ERes2Net 模型失败，请确认 funasr 版本: {e}")

def extract_audio(video_path, audio_path):
    print(f"提取音频并进行降噪处理: {video_path} -> {audio_path}")
    cmd = [
        "ffmpeg", "-y", "-i", video_path, 
        "-vn", "-af", "afftdn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", 
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
    # 统一使用 ffmpeg 处理所有音视频格式，转换为 16kHz 单声道 wav 格式以适配 FunASR
    # 这样可以支持广泛的视频 (mp4, mkv, avi, mov) 和音频 (mp3, wav, aac, m4a, flac) 格式
    if media_path.lower().endswith((".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mp3", ".wav", ".aac", ".m4a", ".flac", ".ogg", ".wma")):
        audio_path = os.path.join(specific_output_dir, "temp_audio.wav")
        if not os.path.exists(audio_path):
            extract_audio(media_path, audio_path)
        else:
            print(f"✅ 发现已提取的音频文件，跳过音频提取: {audio_path}")

    # 为了让 FunASR (ModelScope) 统一使用我们指定的目录
    
    print("加载 FunASR 模型...")
    # Initialize the model pipeline (Paraformer-large + VAD + PUNC + ERes2Net)
    model = AutoModel(
        model="iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        model_revision="v2.0.4",
        vad_model="damo/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        vad_model_revision="v2.0.4",
        punc_model="damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
        punc_model_revision="v2.0.4",
        spk_model="iic/speech_eres2net_sv_zh-cn_16k-common",
        spk_model_revision="v1.0.5",
        disable_update=True # 加快启动速度
    )

    print(f"开始识别: {audio_path}")
    # 缩小 batch_size_s 以应对快速交替对话（原为 300）
    res = model.generate(
        input=audio_path, 
        batch_size_s=60, 
        sentence_timestamp=True, 
        return_spk_res=True,
        vad_kwargs={
            "max_single_segment_time": 15000,  # 缩小单段最大时长至15秒(默认30秒)，防止多人在同一长段中混杂
            "max_end_silence_time": 400,       # 尾部静音阈值缩短至400ms(默认800ms)，遇到极短停顿立刻切分，极大地提升抢话/快语速场景的准确度
        }
    )

    # 将 md5 摘要信息保存到识别结果中
    if isinstance(res, list):
        if len(res) > 0:
            res[0]["file_md5"] = file_md5
        else:
            res.append({"file_md5": file_md5, "sentence_info": []})

    # Save JSON with timestamps
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
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
