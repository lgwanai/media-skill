#!/usr/bin/env python3
"""
Media Skill 更新脚本

功能：
1. 拉取 GitHub 最新代码
2. 备份旧文件到 backup 目录
3. 显示更新日志
"""

import os
import sys
import subprocess
import shutil
import zipfile
from datetime import datetime
from pathlib import Path


REPO_URL = "https://github.com/lgwanai/media-skill"
BACKUP_DIR = "backup"
EXCLUDE_FILES = [
    "config.txt",
    ".env",
    "output/",
    "models/",
    "backup/",
    "dist/",
    "index-tts/",
    "checkpoints/",
    "data/voices/*/*.pt",
    "data/voices/*/*.wav",
    "*.mp4",
    "*.mp3",
    "*.wav",
    "*.m4a",
    "*.mov",
    "*.pt",
    "*.pth",
    "*.bin",
    "__pycache__/",
    ".ruff_cache/",
    ".mypy_cache/",
    ".benchmarks/",
    ".DS_Store",
    ".git/",
    ".claude/",
    ".opencode/",
    ".planning/",
    "test/",
    "*.zip",
    "*.log",
]


def run_command(cmd: list[str], cwd: str = None) -> tuple[int, str]:
    """执行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode, result.stdout + result.stderr
    except Exception as e:
        return 1, str(e)


def should_exclude(path: str) -> bool:
    """检查文件是否应该排除"""
    path_lower = path.lower()
    for pattern in EXCLUDE_FILES:
        pattern = pattern.rstrip("/")
        if pattern.startswith("*"):
            if path_lower.endswith(pattern[1:].lower()):
                return True
        elif pattern.endswith("/*"):
            dir_path = pattern[:-2].lower()
            if path_lower.startswith(dir_path + "/") or path_lower == dir_path:
                return True
        elif path_lower == pattern.lower() or path_lower.startswith(pattern.lower() + "/"):
            return True
    return False


def create_backup() -> str:
    """创建备份文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"media-skill-backup-{timestamp}.zip")
    
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    print(f"📦 创建备份: {backup_file}")
    
    file_count = 0
    total_size = 0
    
    with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk('.'):
            rel_root = root[2:] if root.startswith('./') else root
            
            dirs[:] = [d for d in dirs if not should_exclude(os.path.join(rel_root, d))]
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.join(rel_root, file) if rel_root else file
                
                if should_exclude(rel_path):
                    continue
                
                try:
                    zf.write(file_path, rel_path)
                    file_count += 1
                    total_size += os.path.getsize(file_path)
                except Exception:
                    pass
    
    size_mb = os.path.getsize(backup_file) / (1024 * 1024)
    print(f"✅ 备份完成: {file_count} 文件, {size_mb:.1f} MB")
    return backup_file


def pull_updates() -> tuple[bool, str]:
    """拉取最新代码"""
    print("🔄 检查远程更新...")
    
    ret, output = run_command(["git", "fetch", "origin"])
    if ret != 0:
        return False, f"git fetch 失败: {output}"
    
    ret, output = run_command(["git", "status", "-uno"])
    if "Your branch is up to date" in output or "Your branch is behind" in output:
        if "Your branch is behind" in output:
            print("📥 发现新版本，正在拉取...")
            ret, output = run_command(["git", "pull", "origin", "main"])
            if ret != 0:
                return False, f"git pull 失败: {output}"
            
            ret, log = run_command(["git", "log", "--oneline", "-5"])
            print(f"✅ 更新完成!")
            return True, log
        else:
            print("✅ 当前已是最新版本")
            return True, "已是最新版本"
    
    return True, output


def show_update_log():
    """显示更新日志"""
    ret, log = run_command(["git", "log", "--oneline", "-10"])
    if ret == 0:
        print("\n📋 最近更新:")
        print(log)


def main():
    print("=" * 50)
    print("  Media Skill 更新工具")
    print("=" * 50)
    print()
    
    cwd = os.getcwd()
    print(f"📂 当前目录: {cwd}")
    
    if not os.path.exists(".git"):
        print("❌ 当前目录不是 Git 仓库")
        print("请确保在 media-skill 项目目录下运行此脚本")
        sys.exit(1)
    
    print()
    
    backup_file = create_backup()
    print()
    
    success, message = pull_updates()
    print()
    
    if success:
        show_update_log()
    else:
        print(f"❌ 更新失败: {message}")
        if backup_file:
            print(f"💡 可从备份恢复: {backup_file}")
        sys.exit(1)
    
    print()
    print("=" * 50)
    print("  ✅ 更新完成!")
    print("=" * 50)
    print()
    print("⚠️ 请检查 config.txt 是否需要重新配置")
    print("💡 如有问题，可从 backup 目录恢复")


if __name__ == "__main__":
    main()