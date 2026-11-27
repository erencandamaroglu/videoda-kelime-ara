@echo off
chcp 65001 >nul
title Videoda Kelime Ara - Guncelleme
echo Videoda Kelime Ara - Guncelleme
echo ---------------------------------
echo.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python ortami bulunamadi. Once kurulum.bat dosyasini calistirin.
  pause
  exit /b 1
)
if exist ".git" (
  where git >nul 2>nul && git pull --ff-only
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install --upgrade -r requirements.txt
if errorlevel 1 goto hata
where nvidia-smi >nul 2>nul
if not errorlevel 1 ".venv\Scripts\python.exe" -m pip install --upgrade -r requirements-gpu.txt
echo.
echo Guncelleme tamamlandi. Veriler ^(veriler klasoru^) ve modeller korunur.
pause
exit /b 0
:hata
echo Guncelleme tamamlanamadi. Yukaridaki hata mesajini kontrol edin.
pause
exit /b 1
