@echo off
if "%~1"=="" (
    echo Usage: %~nx0 ^<map name^> [--gui]
    exit /b 1
)
set MODE=raw
if "%2"=="--gui" set MODE=bot
python -m src.main.driver %1 %MODE%