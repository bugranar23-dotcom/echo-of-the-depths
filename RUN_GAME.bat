@echo off
cd /d "%~dp0"
echo ECHO OF THE DEPTHS - Kurulum kontrol ediliyor...
py -m pip install -r requirements.txt
if errorlevel 1 (
    echo Kurulum basarisiz. Python ve internet baglantisini kontrol et.
    pause
    exit /b 1
)
echo Oyun baslatiliyor...
py Echo_of_the_Depths.py
if errorlevel 1 pause
