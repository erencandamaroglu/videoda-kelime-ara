@echo off
chcp 65001 >nul
title Videoda Kelime Ara - Kurulum
echo Videoda Kelime Ara - Kurulum
echo -------------------------------
echo.
cd /d "%~dp0"
set PY=
call :python_bul "python"
if not defined PY call :python_bul "py -3.13"
if not defined PY call :python_bul "py -3"
if not defined PY (
  echo Python 3.10 veya uzeri bulunamadi. https://www.python.org adresinden Python 3.13 kurun
  echo ^(kurulumda "Add python.exe to PATH" secenegini isaretleyin^).
  goto hata
)
echo Kullanilan Python: %PY%
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import sys" >nul 2>nul
  if errorlevel 1 (
    echo Mevcut .venv bu bilgisayarda calismiyor; yeniden olusturuluyor...
    rmdir /s /q .venv
  )
)
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv
  if errorlevel 1 goto hata
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto hata
where nvidia-smi >nul 2>nul
if not errorlevel 1 (
  echo NVIDIA ekran karti bulundu; GPU kutuphaneleri kuruluyor ^(altyazi hizlanir^)...
  ".venv\Scripts\python.exe" -m pip install -r requirements-gpu.txt
)
echo.
echo Kurulum tamamlandi. baslat.bat ile programi acabilirsiniz.
echo Not: Ilk altyazida secilen konusma tanima modeli internetten indirilir ^(modeller klasorune^).
pause
exit /b 0
:hata
echo Kurulum tamamlanamadi. Yukaridaki hata mesajini kontrol edin.
pause
exit /b 1
:python_bul
%~1 -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>nul
if not errorlevel 1 set "PY=%~1"
exit /b 0
