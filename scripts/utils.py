import os
import hashlib

def setup_env():
    config = load_config()
    model_dir = config.get("MODEL_DIR", os.path.expanduser("~/.models/"))
    os.makedirs(model_dir, exist_ok=True)
    os.environ["MODELSCOPE_CACHE"] = model_dir
    os.environ["HF_HUB_CACHE"] = os.path.join(model_dir, "hf_cache")
    os.environ["MODELSCOPE_FILE_LOCK"] = "False"
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

def load_config(config_path="config.txt"):
    """
    加载配置文件并返回配置字典
    """
    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    config[k.strip()] = v.strip()
    
    # 默认值处理
    if "OUTPUT_DIR" not in config:
        config["OUTPUT_DIR"] = "output"
        
    if "MODEL_DIR" not in config or not config["MODEL_DIR"].strip():
        # 默认使用用户主目录下的 .models 文件夹
        config["MODEL_DIR"] = os.path.expanduser("~/.models/")
    else:
        # 展开配置中的 ~ 符号
        config["MODEL_DIR"] = os.path.expanduser(config["MODEL_DIR"])
        
    # TTS 默认值处理
    if "TTS_ENGINE" not in config:
        config["TTS_ENGINE"] = "indextts"
    if "INDEXTTS_MODE" not in config:
        config["INDEXTTS_MODE"] = "api"
    if "QWEN3TTS_MODE" not in config:
        config["QWEN3TTS_MODE"] = "api"
    
    # ASR 默认值处理
    if "ASR_ENGINE" not in config:
        config["ASR_ENGINE"] = "funasr"
    if "QWEN3ASR_MODE" not in config:
        config["QWEN3ASR_MODE"] = "local"
    if "QWEN3ASR_BACKEND" not in config:
        config["QWEN3ASR_BACKEND"] = "transformers"
    if "QWEN3ASR_DEVICE" not in config:
        config["QWEN3ASR_DEVICE"] = "cuda:0"
        
    return config

def get_file_md5(file_path):
    """计算文件的 MD5 摘要"""
    if not os.path.exists(file_path):
        return None
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        # 分块读取，避免大文件占用过多内存
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

def get_unified_output_dir(file_path, config=None):
    """
    根据文件路径和 MD5 生成统一的输出目录
    目录格式: <OUTPUT_DIR>/<filename_without_ext>_<md5[:8]>
    如果目录不存在则创建
    """
    if config is None:
        config = load_config()
        
    output_base_dir = config.get("OUTPUT_DIR", "output")
    
    file_md5 = get_file_md5(file_path)
    if not file_md5:
        # 如果文件不存在，回退到仅使用文件名
        file_md5 = "unknown"
        
    base_name = os.path.basename(file_path)
    name_without_ext, _ = os.path.splitext(base_name)
    
    # 使用 MD5 的前 8 位即可保证足够的唯一性
    dir_name = f"{name_without_ext}_{file_md5[:8]}"
    full_output_dir = os.path.join(output_base_dir, dir_name)
    
    os.makedirs(full_output_dir, exist_ok=True)
    return full_output_dir


def get_openclaw_headers(config):
    """
    根据配置返回模拟 OpenClaw 调用的 Header 字典
    """
    extra_headers = {}
    if config.get("SIMULATE_OPENCLAW", "false").lower() == "true":
        extra_headers = {
            'HTTP-Referer': 'https://openclaw.ai',
            'X-OpenRouter-Title': 'OpenClaw',
            'X-OpenRouter-Categories': 'cli-agent'
        }
    return extra_headers

def create_openai_client(api_key, base_url):
    """
    创建并返回 OpenAI 客户端实例
    """
    from openai import OpenAI
    return OpenAI(api_key=api_key, base_url=base_url)

# 在模块加载时自动设置环境变量
setup_env()
