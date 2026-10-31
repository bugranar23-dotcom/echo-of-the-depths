# ECHO OF THE DEPTHS

Five bolumlu prosedurel 3B gerilim oyunu. Pencere hemen acilir; dokular ve sesler arka planda hazirlanir, ilk bolum yukleme ekrani sonrasi olusturulur.

## Kurulum
Windows'ta `RUN_GAME.bat` dosyasina cift tikla. Baslatici Ursina/Pillow kuruluysa tekrar kurulum yapmaz; eksikse ilk acilista kurar. Elle kurulum icin:

```bash
py -m pip install -r requirements.txt
py Echo_of_the_Depths.py
```

## Kontroller
- WASD hareket
- SHIFT kosma
- C cokelme
- E etkilesim
- F fener
- R telsiz
- TAB bolum/hedef durumu
- F11 tam ekran

## Bolumler
1. Karanlik Malikane — 5 sigorta
2. Kapatilmis Hastane — 5 veri diski
3. Sisli Orman Istasyonu — 5 sinyal rolesi
4. Yeraltı Siginagi — 5 basinc vanasi
5. Saat Kulesi — 6 saat parcasi

Her bolumde dusman daha hizli ve daha hassas olur. Yakalaninca o bolumdeki hedef ilerlemesi korunur.

## Ilk acilis
Ilk acilista oyun penceresi ve yukleme ekrani hemen gorunur. Dokular ve sesler arka planda hazirlandiktan sonra ilk bolum olusturulur. Sonraki acilislarda olusan dosyalar kullanildigi icin hazirlik daha hizli olur. `RUN_GAME.bat`, kutuphaneler zaten yuklu ise internetten tekrar kurulum yapmaz.

Gereksinimler: Python 3.10+, Ursina, Pillow.
