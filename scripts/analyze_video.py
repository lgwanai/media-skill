import os
import sys
import argparse
import subprocess

from utils import load_config, create_openai_client, get_openclaw_headers, get_unified_output_dir
from cos_client import COSClient

def compress_video(input_path, output_dir):
    """
    压缩视频到 540p，降低 Omini 模型分析的 token 消耗。
    返回压缩后的视频路径。
    """
    base_name = os.path.basename(input_path)
    name_without_ext, _ = os.path.splitext(base_name)
    compressed_path = os.path.join(output_dir, f"{name_without_ext}_540p.mp4")
    
    print(f"正在将视频压缩为 540p 以降低 Token 消耗...")
    # 使用 ffmpeg 压缩：调整分辨率至高为 540，宽度自适应；帧率设为 30；降低码率
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", "scale=-2:540", "-r", "30",
        "-c:v", "libx264", "-crf", "28", "-preset", "faster",
        compressed_path
    ]
    
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if os.path.exists(compressed_path):
            print(f"✅ 视频压缩完成: {compressed_path}")
            return compressed_path
    except Exception as e:
        print(f"⚠️ 视频压缩失败，将使用原视频进行分析: {e}")
        
    return input_path

def upload_video_to_cos(video_path, config):
    """使用 scripts/cos_client.py 上传视频到腾讯云COS并返回URL"""
    os.environ['COS_SECRET_ID'] = config.get("COS_SECRET_ID", "")
    os.environ['COS_SECRET_KEY'] = config.get("COS_SECRET_KEY", "")
    os.environ['COS_REGION'] = config.get("COS_REGION", "ap-beijing")
    os.environ['COS_BUCKET_NAME'] = config.get("COS_BUCKET_NAME", "")
    
    if not all([os.environ['COS_SECRET_ID'], os.environ['COS_SECRET_KEY'], os.environ['COS_BUCKET_NAME']]):
        print("缺少 COS 配置，跳过上传。")
        return None
        
    try:
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        if scripts_dir not in sys.path:
            sys.path.append(scripts_dir)
            
        client = COSClient()
        print(f"正在使用 cos_client 上传 {video_path} 到 COS...")
        result = client.upload_file(video_path)
        
        if result.get('success'):
            url = result.get('url')
            print(f"上传成功: {url}")
            return url
        else:
            print(f"上传 COS 失败: {result.get('error')}")
            return None
    except Exception as e:
        print(f"上传 COS 发生异常: {e}")
        return None

PROMPT_TEXT = """# 🎬 专业Prompt：爆款视频深度解构与分析系统

## 1. 角色设定
你是一位顶级的**视频内容策略分析师**，代号“Omni-Analyst”。你拥有全感知能力，能够精准同步处理视觉画面、音频情绪、字幕文本以及后台数据逻辑。你的任务不是简单描述视频内容，而是从**认知心理学**、**传播学**和**算法推荐机制**的角度，解构视频成为“爆款”的本质原因。

## 2. 输入格式说明
我将为你提供该视频的以下信息：
- **视觉流**：关键画面构图、色彩、人物动作、场景切换。
- **听觉流**：背景音乐（BGM）节奏、音效、人声语调、环境音。
- **文本流**：字幕文案、口播脚本、标题与评论区高赞反馈。

## 3. 分析任务要求
请严格按照以下维度进行深度分析：

### 第一阶段：关键时间节点的“钩子”拆解
请重点分析视频的时间线，解释每个节点如何对抗用户的“滑动本能”：
- **0-3秒（生死滑门期）**：
  - 视觉上的“视觉锤”（反差色、巨物、微距、动态模糊）是什么？
  - 听觉上的“音爆”（静默突转巨响、悬疑音效、第一秒高能台词）是什么？
  - *策略分析*：它是如何利用“认知失调”或“好奇心缺口”在瞬间留住用户的？
- **3-10秒（留存确认期）**：
  - 是否出现了“进度条承诺”（如“最后一点最重要”、“不看后悔”）？
  - 剪辑节奏是否开始建立“爽感”？是否有明确的“诱因”（痛点或痒点）被提出？
- **中段（完播率维护）**：
  - 指出“情绪过山车”的点：设置了几个“微型高潮”？是否有“信息增量”的持续轰炸？
- **结尾（互动引导）**：
  - 分析其“交互设计”：是在引导评论（立场站队）、点赞（情绪共鸣）还是收藏（资料属性）？是否有“彩蛋”或“悬念”留住最后5秒？

### 第二阶段：字幕与画面的“化学效应”
- **同步性分析**：指出字幕弹出与画面动作的精准卡点。例如：字幕是“画外音”还是“内心OS”？字幕字体、动效是否强化了画面的冲击力？
- **信息冗余度**：画面和字幕是“互为补充”还是“同义反复”？在关键爆点处，是否存在“声画字”三位一体（画面爆炸+音效炸裂+字幕放大）的强刺激？

### 第三阶段：爆款逻辑归因
- **完播率设计**：视频用了什么“诱饵”让用户舍不得划走？（悬念、视觉奇观、情感共鸣、有用性）
- **点赞/收藏动机**：
  - *点赞*：是价值观认同，还是被“爽感”驱使？
  - *收藏*：视频提供了何种“干货价值”？是否是“收藏即学会”的心理满足？
- **评论/转发诱因**：视频是否预留了“槽点”或“辩论点”？是否触发了用户的“表现欲”或“利他心理”？

### 第四阶段：观众画像精准描绘
请基于内容风格、梗密度、价值观输出，构建出该视频的**核心受众画像**（不要泛泛而谈“年轻人”，要具体）：
- **基础属性**：年龄层、地域特征、职业倾向。
- **心理特征**：焦虑点、渴望点、审美偏好（如：偏爱强逻辑/偏爱情绪价值）。
- **行为标签**：TA们在刷视频时的场景（通勤、睡前、摸鱼），以及该视频如何适配这一场景。

### 第五阶段：批判性客观评估与优化建议（非常重要）
不要默认该视频已经是爆款。请跳出“它一定是爆款”的预设，客观、犀利地评估它的真实潜力：
- **爆款元素是否充足**：它的钩子够不够硬？内容是否有硬伤（如节奏拖沓、画质粗糙、表达不清）？
- **潜在风险与瓶颈**：如果它没能爆，最大的原因可能是什么？（受众太窄、门槛太高、竞争太激烈等）
- **具体改进建议**：给出3条能立竿见影提升数据（完播/互动）的优化建议（如：修改前3秒文案、增加特定音效、调整画面构图）。

---

## 4. 输出格式要求
请将分析结果以**结构化报告**的形式输出，语言精练、一针见血，避免废话。使用以下Markdown结构：

# 📊 爆款视频深度解构报告

### 🕒 1. 关键时间线决策点
> *提炼出视频的“黄金前5秒”和“核心转折点”*

### 🧩 2. 声画字的协同效应
> *分析视听的化学反应*

### 💡 3. 爆款策略总结
> *拆解其在完播、点赞、收藏、评论上的具体手段*

### 👥 4. 精准观众画像
> *定义谁会被这个视频精准击中*

### ⚖️ 5. 批判性评估与优化建议
> *客观评价其真实潜力，指出硬伤并给出具体的爆款改造建议*
"""

def analyze_video(video_path):
    config = load_config()
    output_dir = get_unified_output_dir(video_path)
    os.makedirs(output_dir, exist_ok=True)
    
    status_path = os.path.join(output_dir, "analyze_status.json")
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "running", "progress_percent": 10, "message": "正在压缩视频..."}, f, ensure_ascii=False)
        
    # 0. 压缩视频到 540p 以降低 Token 消耗
    compressed_video_path = compress_video(video_path, output_dir)
    
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "running", "progress_percent": 30, "message": "正在上传视频至云端..."}, f, ensure_ascii=False)
        
    # 1. 上传视频获取可供大模型读取的 URL
    video_url = upload_video_to_cos(compressed_video_path, config)
    if not video_url:
        print("无法上传视频，请检查 COS 配置。")
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump({"status": "error", "message": "无法上传视频"}, f, ensure_ascii=False)
        return
        
    # 2. 调用 Omini 多模态模型进行拆解
    api_key = config.get("MIMO_API_KEY", config.get("OMINI_API_KEY"))
    api_url = config.get("MIMO_URL", config.get("OMINI_URL", "https://api.xiaomimimo.com/v1"))
    model_name = config.get("OMINI_MODEL_NAME", "mimo-v2-omni")
    
    if not api_key:
        print("未配置 OMINI_API_KEY，无法调用大模型。")
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump({"status": "error", "message": "未配置 OMINI_API_KEY"}, f, ensure_ascii=False)
        return
        
    client = create_openai_client(api_key=api_key, base_url=api_url)
    extra_headers = get_openclaw_headers(config)
    
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({"status": "running", "progress_percent": 60, "message": "正在调用大模型分析视频，请耐心等待..."}, f, ensure_ascii=False)
        
    print(f"\n正在调用 {model_name} 分析视频（深度多模态分析可能需要几分钟，请耐心等待）...")
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are Omni-Analyst, an AI assistant specialized in video analysis."},
                {"role": "user", "content": [
                    {"type": "video_url", "video_url": {"url": video_url}, "fps": 2},
                    {"type": "text", "text": PROMPT_TEXT}
                ]}
            ],
            temperature=0.7,
            extra_headers=extra_headers if extra_headers else None
        )
        content = completion.choices[0].message.content.strip()
        
        output_file = os.path.join(output_dir, "viral_video_analysis.md")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
            
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump({"status": "done", "progress_percent": 100, "output_path": output_file}, f, ensure_ascii=False)
            
        print(f"\n✅ 分析完成！深度解构报告已保存至: {output_file}")
        
    except Exception as e:
        print(f"调用 Omini 模型发生异常: {e}")
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump({"status": "error", "message": f"调用大模型异常: {e}"}, f, ensure_ascii=False)

if __name__ == "__main__":
    if '--async-run' in sys.argv and os.environ.get('ANALYZE_ASYNC_WORKER') != '1':
        print(">> 检测到 --async-run 参数，正在将任务转入后台异步执行...")
        cmd = [sys.executable] + sys.argv
        cmd.remove('--async-run')
        env = os.environ.copy()
        env['ANALYZE_ASYNC_WORKER'] = '1'
        
        subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        print(">> 后台任务已启动！Agent 可以立即退出等待，不被阻塞。请通过 analyze_status.json 轮询进度。")
        sys.exit(0)

    args = [arg for arg in sys.argv[1:] if arg != '--async-run']
    if len(args) < 1:
        print("用法: python scripts/analyze_video.py <video_path>")
        sys.exit(1)
    
    video_path = args[0]
    if not os.path.exists(video_path):
        print(f"文件不存在: {video_path}")
        sys.exit(1)
        
    analyze_video(video_path)
