import os

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
    return config

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
