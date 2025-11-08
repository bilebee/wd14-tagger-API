@echo off
REM WD14 Tagger API 启动脚本

REM 检查是否存在配置文件
if not exist config.json (
    echo 创建默认配置文件...
    python config_manager.py --show >nul 2>&1
)

echo 启动 WD14 Tagger API...
echo.

REM 启动API服务
python standalone.py

pause