@echo off
title LOTRO Narrator
color 0B

if not exist venv (
    echo [ERROR] Virtual environment not found.
    echo Please run 'install.bat' first.
    pause
    exit
)

echo Activating AI Core...
call venv\Scripts\activate

echo Starting Application...
python main.py

pause
