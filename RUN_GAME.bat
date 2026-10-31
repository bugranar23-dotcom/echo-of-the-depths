@echo off
chcp 65001 >nul
cd /d "%~dp0"
title ECHO OF THE DEPTHS

where py >nul 2>&1
if errorlevel 1 (
    echo Python bulunamadi. Python 3.10 veya daha yenisini kurup tekrar dene.
    pause
    exit /b 1
)

py -c "import ursina; from PIL import Image" >nul 2>&1
if errorlevel 1 (
    echo Gerekli kutuphaneler eksik. Ilk kurulum yapiliyor...
    py -m pip install --disable-pip-version-check -r requirements.txt
    if errorlevel 1 (
        echo Kurulum tamamlanamadi. Internet baglantisini ve Python kurulumunu kontrol et.
        pause
        exit /b 1
    )
)

echo Oyun baslatiliyor...
py Echo_of_the_Depths.py
if errorlevel 1 (
    echo Oyun kapanirken bir hata olustu. echo_hata.txt dosyasini kontrol et.
    pause
)
