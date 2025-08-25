@echo off
title WD14 Tagger Server with Authentication

echo Starting WD14 Tagger Server with Authentication...
echo.

set /p username=Enter username: 
set /p password=Enter password: 
set /p host=Enter host (default: 127.0.0.1): 
if "%host%"=="" set host=127.0.0.1

set /p port=Enter port (default: 8000): 
if "%port%"=="" set port=8000

echo.
echo Starting server with authentication...
echo.

set API_AUTH=%username%:%password%
python standalone.py --host %host% --port %port%

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