@echo off
title WD14 Tagger Server

echo Starting WD14 Tagger Server...
echo.

python standalone.py --port 8080 --host 0.0.0.0
if %errorlevel% neq 0 (
    echo.
    echo Error occurred while starting the server!
    echo Please make sure you have installed all required dependencies by running install.bat
    echo.
    echo Make sure you have installed the required packages:
    echo   pip install fastapi uvicorn pillow pydantic
    echo.
    echo For full functionality, you might also need:
    echo   pip install gradio onnxruntime tensorflow huggingface-hub
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