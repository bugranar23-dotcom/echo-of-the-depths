# ECHO OF THE DEPTHS

Five bolumlu prosedurel 3B gerilim oyunu.

## Kurulum
Windows'ta `RUN_GAME.bat` dosyasina cift tikla. Baslatici Python 3.12+ surumlerinden birini bulur, Ursina/Pillow paketlerini yalnizca eksikse kurar ve oyunu baslatir. Ilk kurulum internet gerektirir.

Elle kurulum: `py -3.12 -m pip install -r requirements.txt` ve `py -3.12 Echo_of_the_Depths.py`.

## Acilis duzeltmeleri
- Ilk acilista yalnizca 1. bolumun dokulari ve sesleri hazirlanir.
- Sonraki bolumlerin dokulari o bolume gecildiginde olusturulur.
- Uretilen dosyalar oyunun bulundugu klasordeki `echo_assets` klasorune yazilir.
- Hata olursa `echo_hata.txt` dosyasi ayni klasore kaydedilir.

## Kontroller
WASD hareket; SHIFT kosma; C cokelme; E etkilesim; F fener; R telsiz; TAB bolum/hedef durumu; F11 tam ekran.

## Bolumler
1. Karanlik Malikane - 5 sigorta
2. Kapatilmis Hastane - 5 veri diski
3. Sisli Orman Istasyonu - 5 sinyal rolesi
4. Yeraltı Siginagi - 5 basinc vanasi
5. Saat Kulesi - 6 saat parcasi

Gereksinimler: Python 3.12+, Ursina 8.3.0, Pillow.
