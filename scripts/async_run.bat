@echo off
chcp 65001 >nul
:: 统一的异步执行包装脚本 (Windows 版)，彻底解决 Agent 挂死问题

if "%~1"=="" (
    echo 用法: scripts\async_run.bat ^<执行命令^> [参数...]
    echo 示例: scripts\async_run.bat python scripts\dubbing.py dub --text-file a.txt --voice v
    exit /b 1
)

echo ^>^> 正在将任务转入后台安全执行 (Windows)...
:: 使用 start /b 在后台运行并重定向输出，脱离当前控制台阻塞
start /b "" %* >nul 2>&1

echo ^>^> 后台任务已成功启动！Agent 可以立即退出等待。
echo ^>^> 请通过相应的 status.json 轮询进度。
exit /b 0