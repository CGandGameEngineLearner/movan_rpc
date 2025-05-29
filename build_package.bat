@echo off
REM 清理旧的构建文件和发布目录
rmdir /s /q build dist movan_rpc.egg-info 2>nul

REM 构建源代码分发包和轮子
python -m build

echo 构建完成！检查 dist 目录中的包文件。