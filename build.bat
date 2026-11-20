@echo off
cd /d "%~dp0"
title Zomboid Day Launcher - Build EXE
echo ========================================================
echo  Zomboid Day Launcher - Автоматичне збирання Release EXE
echo ========================================================
echo.
python build.py
echo.
echo Натисніть будь-яку клавішу для виходу...
pause >nul
