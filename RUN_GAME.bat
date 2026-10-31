@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title ECHO OF THE DEPTHS

echo [1/3] Python 3.12+ kontrol ediliyor...
set "PYVER="
py -3.14 --version >nul 2>&1 && set "PYVER=3.14"
if not defined PYVER py -3.13 --version >nul 2>&1 && set "PYVER=3.13"
if not defined PYVER py -3.12 --version >nul 2>&1 && set "PYVER=3.12"
if not defined PYVER (
  echo Python 3.12 veya daha yenisi bulunamadi.
  echo Yuklu Python surumleri:
  py -0p
  echo Python 3.12+ kurduktan sonra bu dosyayi yeniden ac.
  pause
  exit /b 1
)
echo Python %PYVER% bulundu.
echo [2/3] Oyun kutuphaneleri kontrol ediliyor...
py -%PYVER% -c "import ursina; from PIL import Image" >nul 2>&1
if errorlevel 1 (
  echo Eksik kutuphaneler kuruluyor. Bu adim internet gerektirir.
  py -%PYVER% -m pip install --disable-pip-version-check -r requirements.txt
  if errorlevel 1 (
    echo KUTUPHANE KURULUMU BASARISIZ. Ekrandaki hata mesajini kontrol et.
    pause
    exit /b 1
  )
)
echo [3/3] Oyun baslatiliyor...
py -%PYVER% -u Echo_of_the_Depths.py
if errorlevel 1 (
  echo Oyun hata ile kapandi. echo_hata.txt dosyasini kontrol et.
  pause
)
endlocal
