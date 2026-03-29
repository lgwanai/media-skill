#!/bin/bash
# 统一的异步执行包装脚本，彻底解决 Agent 挂死问题

if [ $# -eq 0 ]; then
    echo "用法: sh scripts/async_run.sh <执行命令> [参数...]"
    echo "示例: sh scripts/async_run.sh python scripts/dubbing.py dub --text-file a.txt --voice v"
    exit 1
fi

echo ">> 正在将任务转入后台安全执行..."
# 使用 nohup 结合 setsid 脱离当前终端 session，并将输出重定向到空，彻底阻断挂死可能
nohup "$@" >/dev/null 2>&1 &
PID=$!

echo ">> 后台任务已成功启动 (PID: $PID)！Agent 可以立即退出等待。"
echo ">> 请通过相应的 status.json 轮询进度。"
exit 0
