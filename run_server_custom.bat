@echo off
title WD14 Tagger Server - Custom Configuration

echo Starting WD14 Tagger Server with custom configuration...
echo.

set /p host=Enter host (default: 127.0.0.1): 
if "%host%"=="" set host=127.0.0.1

set /p port=Enter port (default: 8000): 
if "%port%"=="" set port=8000

set /p deepdanbooru_path=Enter DeepDanbooru models path (leave empty for default): 
set /p onnxtagger_path=Enter ONNX models path (leave empty for default): 

echo.
echo Starting server...
echo.

if "%deepdanbooru_path%"=="" (
    if "%onnxtagger_path%"=="" (
        python standalone.py --host %host% --port %port%
    ) else (
        python standalone.py --host %host% --port %port% --onnxtagger-path "%onnxtagger_path%"
    )
) else (
    if "%onnxtagger_path%"=="" (
        python standalone.py --host %host% --port %port% --deepdanbooru-path "%deepdanbooru_path%"
    ) else (
        python standalone.py --host %host% --port %port% --deepdanbooru-path "%deepdanbooru_path%" --onnxtagger-path "%onnxtagger_path%"
    )
)

if %errorlevel% neq 0 (
    echo.
    echo Error occurred while starting the server!
    echo Please make sure you have installed all required dependencies by running install.bat
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b %errorlevel%
)

echo.
echo Server stopped.
echo.
echo Press any key to exit...
pause >nul