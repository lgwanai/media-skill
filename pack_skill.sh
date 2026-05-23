#!/bin/bash

# 打包 Media Skill 到 dist 目录
# 自动排除敏感文件和大文件，文件名加日期

set -e

# 配置
SKILL_NAME="media-skill"
DATE=$(date +%Y%m%d)
DIST_DIR="dist"
OUTPUT_FILE="${DIST_DIR}/${SKILL_NAME}-${DATE}.zip"

# 检查敏感文件
echo "🔍 检查敏感文件..."
SENSITIVE_FILES=(
    "config.txt"
    ".env"
    ".env.local"
    ".env.production"
    "credentials.json"
    "secrets.json"
)

FOUND_SECRETS=false
for file in "${SENSITIVE_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "⚠️  发现敏感文件: $file (将被排除)"
        FOUND_SECRETS=true
    fi
done

# 检查 config.txt 是否有真实密钥（非占位符）
if [ -f "config.txt" ]; then
    if grep -qE "sk-[a-zA-Z0-9]{20,}" "config.txt" 2>/dev/null; then
        echo "🚨 警告: config.txt 包含真实 API 密钥！"
        echo "   该文件将被排除在打包之外"
    fi
fi

# 创建 dist 目录
mkdir -p "$DIST_DIR"

# 删除旧包（同日期）
if [ -f "$OUTPUT_FILE" ]; then
    echo "🗑️  删除旧包: $OUTPUT_FILE"
    rm "$OUTPUT_FILE"
fi

# 打包（排除敏感文件和大文件）
echo "📦 打包到: $OUTPUT_FILE"
zip -r "$OUTPUT_FILE" . \
    -x "config.txt" \
    -x ".env*" \
    -x "credentials.json" \
    -x "secrets.json" \
    -x "*.pyc" \
    -x "__pycache__/*" \
    -x ".git/*" \
    -x ".gitignore" \
    -x "*.egg-info" \
    -x "dist/*" \
    -x "*.zip" \
    -x ".claude/*" \
    -x ".opencode/*" \
    -x "*.log" \
    -x "output/*" \
    -x "models/*" \
    -x "data/voices/*/ref_audio.wav" \
    -x "data/voices/*/ref_audio.mp3" \
    -x "*.mp3" \
    -x "*.mp4" \
    -x "*.wav" \
    -x "*.mov" \
    -x "*.MOV" \
    -x "*.m4a" \
    -x "*.M4A" \
    -x "*.png" \
    -x "*.jpg" \
    -x "*.jpeg" \
    -x ".env_initialized" \
    -x "test_*.py" \
    -x "test_*.m4a" \
    -x "test/" \
    -x ".ruff_cache/*" \
    -x ".mypy_cache/*" \
    -x ".benchmarks/*" \
    -x "patch.py" \
    -x "analyze_pop.py" \
    -x "fix_end_pop.py" \
    -x "audiodit" \
    -x "audio_waveform.png" \
    -x "index-tts/checkpoints/*" \
    -x "index-tts/.git/*" \
    -x "checkpoints/*" \
    -x "*.pt" \
    -x "*.pth" \
    -x "*.bin"

# 显示结果
echo ""
echo "✅ 打包完成!"
echo "📄 文件: $OUTPUT_FILE"
echo "📊 大小: $(du -h "$OUTPUT_FILE" | cut -f1)"
echo ""
echo "⚠️  请确认以下内容:"
echo "   - config.txt 已排除"
echo "   - 真实 API 密钥未包含"
echo "   - 大文件（模型、视频）已排除"
echo "   - 可安全分发"
