# ECHO OF THE DEPTHS

Five bolumlu prosedurel 3B gerilim oyunu.

## Performans / oda yukleme
- Harita 49 bagimsiz oda chunk'ina ayrildi.
- Oyuncunun etrafindaki yakin odalar acik kalir.
- Kamera yonundeki yakin odalar gorus konisine gore etkinlestirilir.
- Yaratigin cevresindeki odalar da acik tutulur; dusman yol bulma sistemi calismaya devam eder.
- Uzak odalar silinmez; sadece devre disi birakilir ve yaklasinca tekrar acilir.
- Carpismalar ve gorus kontrolu tum harita yerine yakindaki oda kovalarini tarar.
- Dunyadaki statik modeller Ursina'nin her-kare entity listesine eklenmez.
- Dinamik nokta isiklari 6'dan 3'e indirildi; en yakin isiklar her kare yerine aralikli secilir.

## Kurulum
Windows'ta `RUN_GAME.bat` dosyasina cift tikla. Baslatici Python 3.12+ surumlerinden birini bulur; Ursina/Pillow eksikse kurar. Ilk kurulum internet gerektirir.

Elle kurulum: `py -3.12 -m pip install -r requirements.txt` ve `py -3.12 Echo_of_the_Depths.py`.

## Kontroller
WASD hareket; SHIFT kosma; C cokelme; E etkilesim; F fener; R telsiz; TAB bolum/hedef durumu; F11 tam ekran.

## Bolumler
1. Karanlik Malikane - 5 sigorta
2. Kapatilmis Hastane - 5 veri diski
3. Sisli Orman Istasyonu - 5 sinyal rolesi
4. Yeraltı Siginagi - 5 basinc vanasi
5. Saat Kulesi - 6 saat parcasi

Hata olursa `echo_hata.txt` dosyasini gonder.
