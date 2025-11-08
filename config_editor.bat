@echo off
REM WD14 Tagger API 配置编辑脚本

:menu
cls
echo ================================
echo   WD14 Tagger API 配置管理
echo ================================
echo.

if exist config.json (
    echo 当前配置:
    type config.json
    echo.
) else (
    echo 配置文件不存在，将使用默认配置
    echo.
)

echo 请选择操作:
echo 1. 显示当前配置
echo 2. 修改监听地址 (host)
echo 3. 修改监听端口 (port)
echo 4. 切换调试模式 (debug)
echo 5. 切换自动重载模式 (reload)
echo 6. 重置为默认配置
echo 7. 启动 API 服务
echo 8. 退出
echo.

set /p choice=请输入选项 (1-8): 

if "%choice%"=="1" goto show_config
if "%choice%"=="2" goto set_host
if "%choice%"=="3" goto set_port
if "%choice%"=="4" goto set_debug
if "%choice%"=="5" goto set_reload
if "%choice%"=="6" goto reset_config
if "%choice%"=="7" goto start_api
if "%choice%"=="8" goto exit

echo 无效选项，请重新选择
pause
goto menu

:show_config
cls
echo 当前配置:
echo ================================
python config_manager.py --show
echo.
pause
goto menu

:set_host
set /p new_host=请输入新的监听地址 (默认: 0.0.0.0): 
if "%new_host%"=="" set new_host=0.0.0.0
python config_manager.py --set host %new_host%
pause
goto menu

:set_port
set /p new_port=请输入新的监听端口 (默认: 8080): 
if "%new_port%"=="" set new_port=8080
python config_manager.py --set port %new_port%
pause
goto menu

:set_debug
echo 切换调试模式...
for /f "tokens=* delims=" %%i in ('python -c "import json; c=json.load(open(\"config.json\")); print(not c.get(\"debug\", False)) if \"debug\" in c or True else print(True)" 2^>nul') do set new_debug=%%i
python config_manager.py --set debug %new_debug%
echo 调试模式已设置为: %new_debug%
pause
goto menu

:set_reload
echo 切换自动重载模式...
for /f "tokens=* delims=" %%i in ('python -c "import json; c=json.load(open(\"config.json\")); print(not c.get(\"reload\", False)) if \"reload\" in c or True else print(False)" 2^>nul') do set new_reload=%%i
python config_manager.py --set reload %new_reload%
echo 自动重载模式已设置为: %new_reload%
pause
goto menu

:reset_config
echo 重置为默认配置...
python config_manager.py --reset
pause
goto menu

:start_api
echo 启动 WD14 Tagger API...
python standalone.py
goto menu

:exit
exit /b