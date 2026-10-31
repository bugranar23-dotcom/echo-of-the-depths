# ECHO OF THE DEPTHS

5 bolumlu, birinci sahis 3B gerilim oyunu.

## Bu surumdeki degisiklikler
- Bes tema icin ayri 512x512 duvar, zemin ve metal dokulari: ahsap malikane, hastane fayansi, sisli orman kabugu, beton siginak ve saat kulesi.
- ZIP surumunde hazir PNG dokulari ve ses dosyalari vardir. Kaynak kod tek basina calistirilirsa dokulari kendi olusturur.
- Oyun penceresi koyu arka planla acilir; bolum girisinde hareket kilitlenmez. Pencere klavye girdisi almiyorsa bir kez sol tikla.
- Oyuncunun yakinindaki odalar, kameranin onundeki yakin odalar ve yaraticigin cevresi ayri chunk olarak etkin tutulur.
- Uzak odalar silinmeden uyutulur; geri donunce tekrar acilir.
- Daha az dinamik isik ve yakindaki collider kovalarini tarayan kontroller.
- Hedefler tamamlaninca bolume ozel terminal bulmacasi cozulur; ardindan yaraticiktan kacis baslar.
- Bolumler sadece esya toplamayla bitmez: her bolumde ipucu, sifre/yon/renk dizisi bulmacasi ve geri donus kovalamacasi vardir.

## Bes bolum
1. **Karanlik Malikane:** 5 sigorta, renkli ana devre bulmacasi ve malikane kovalamacasi.
2. **Kapatilmis Hastane:** 5 veri diski, hasta arsivi sifresi ve hastane kovalamacasi.
3. **Sisli Orman Istasyonu:** 5 sinyal rolesi, telsiz frekans dizisi ve orman kovalamacasi.
4. **Yeraltı Sığınağı:** 5 basinc vanasi, basinc hatti bulmacasi ve siginak kovalamacasi.
5. **Saat Kulesi:** 6 saat parcasi, saat mekanizmasi bulmacasi ve final kacisi.

## Kurulum
1. ZIP dosyasini tamamen yeni bir klasore cikart.
2. `RUN_GAME.bat` dosyasina cift tikla.
3. Baslatici Python 3.12 veya 3.13 arar; Ursina/Pillow eksikse kurar. Ilk kurulum internet gerektirir.

Elle kurulum:

```bash
py -3.12 -m pip install -r requirements.txt
py -3.12 Echo_of_the_Depths.py
```

## Kontroller
- WASD: hareket
- Mouse: bakis
- SHIFT: kosma
- C: cokelme
- E: etkilesim / esya alma / terminal
- F: fener
- R: telsiz
- TAB: durum
- Bulmaca sirasinda 1-4: tus gir, BACKSPACE: sil, ENTER: onayla, ESC: kapat
- F11: tam ekran

## Sorun giderme
Oyun hata ile kapanirsa ayni klasordeki `echo_hata.txt` dosyasini paylas. Python sozdizimi ve ZIP icerigi kontrol edilmistir; bu ortamda Ursina olmadigi icin gercek 3B acilis/FPS testi yapilamadi.
