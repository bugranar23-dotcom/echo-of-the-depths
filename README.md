# ECHO OF THE DEPTHS

Five bolumlu, birinci sahis 3B gerilim oyunu.

## Gorsel ve doku duzeltmeleri
- Ursina renk API'si 0-1 araligiyla calisir. 0-255 renk paletleri artik `rgb32/rgba32` ile dogru normalize edilir; duvarlarin, zeminlerin ve UI panellerinin beyaza donmesi duzeltilmistir.
- Doku PNG'leri mutlak yol aramak yerine acik `echo_assets/textures` klasorunden yuklenir; texture nesnesi bulunamazsa acik hata verir.
- Her bolum icin ayri v5 duvar, zemin ve metal dokulari uretilir. Ah sap damarlari, tas/seramik derzleri, beton catlaklari, kir, surtunme izleri ve metal oksitlenmesi PNG'lere onceden islenir; oyun sirasinda ek GPU maliyeti olusturmaz. v5 dosya adlari onceki dokulari otomatik yeniler.
- Ilk acilista yalnizca 1. bolumun dokulari hazirlanir; diger bolumler bolum yuklenirken uretilir.
- Tum dokulari onceden olusturmak icin: `py Echo_of_the_Depths.py --generate-textures`. PNG'ler `echo_assets/textures` klasorune kaydedilir.
- Oda chunk sistemi oyuncunun yakinini, kamera onundeki alanlari ve yaraticigin cevresini etkin tutar. Statik dekorlar her kare update listesine eklenmez.

## Bes bolum
1. **Karanlik Malikane:** 5 sigorta, renk devresi bulmacasi ve cikisa donus kovalamacasi.
2. **Kapatilmis Hastane:** 5 veri diski, arsiv sifresi ve asansor kovalamacasi.
3. **Sisli Orman Istasyonu:** 5 sinyal rolesi, telsiz frekansi bulmacasi ve orman kovalamacasi.
4. **Yeraltı Sığınağı:** 5 basinc vanasi, basinc hatti bulmacasi ve celik kapidan kacis.
5. **Saat Kulesi:** 6 saat parcasi, mekanizma bulmacasi ve final kacisi.

## Kurulum
1. ZIP'i tamamen yeni bir klasore cikart.
2. `RUN_GAME.bat` dosyasina cift tikla.
3. Baslatici Python 3.12 veya 3.13 arar; Ursina/Pillow eksikse kurar. Ilk kurulum internet gerektirir.

Elle kurulum:

```bash
py -3.12 -m pip install -r requirements.txt
py -3.12 Echo_of_the_Depths.py --diagnostics
py -3.12 Echo_of_the_Depths.py --generate-textures
py -3.12 Echo_of_the_Depths.py
```

`--diagnostics` Python, Ursina ve Panda3D surumlerini yazar. `--generate-textures` bes bolumun v5 dokularini `echo_assets/textures` klasorune yeniden olusturur.

## Kontroller
- WASD: hareket
- Mouse: bakis
- SHIFT: kosma
- C: cokelme
- E: etkilesim / esya alma / terminal
- F: fener
- R: telsiz
- TAB: durum
- Bulmaca: 1-4 tuslari, BACKSPACE sil, ENTER onayla, ESC kapat
- F11: tam ekran

## Test
GitHub Actions oyunu sanal ekranda baslatir ve bir gercek render ekran goruntusunu kontrol eder. Bu test Windows/RTX sisteminin yerini tutmaz; son test sonucunu GitHub Actions sekmesinden gorebilirsin. Yerel hata olursa `echo_hata.txt` dosyasini paylas.
