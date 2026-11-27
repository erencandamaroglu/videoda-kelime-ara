@echo off
chcp 65001 >nul
title Videoda Kelime Ara
echo Videoda Kelime Ara
echo ------------------
echo Arayuz aciliyor...
echo.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python ortami bulunamadi. Once kurulum.bat dosyasini calistirin.
  pause
  exit /b 1
)
rem Paketler yalnizca bulunuyor mu diye bakilir; ice aktarmak ag surucusunde cok yavas.
".venv\Scripts\python.exe" -c "import importlib.util as u, sys; sys.exit(0 if all(u.find_spec(p) for p in ('PyQt6', 'faster_whisper')) else 1)" >nul 2>nul
if errorlevel 1 (
  echo Python ortami bu bilgisayarda eksik veya bozuk. kurulum.bat dosyasini calistirin.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" main.py %*
if errorlevel 1 pause
