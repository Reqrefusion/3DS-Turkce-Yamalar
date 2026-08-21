# WarioWare Gold Türkçe — teknik çalışma paketi v2

Bu paket **XMSBT/XML kullanmaz**. MSBT dosyaları doğrudan okunur/yazılır.

## Çok önemli: v1 fontlarını kullanma

Önceki `WarioWare_TR_Toolkit_v1` içindeki **Font Safe v4** gerçek oyunda regresyon yaptı: özellikle altyazıdaki `Ş/ş/Ğ/ğ` gibi glifler kaybolabildi. v2 bunun yerine **Font v5 Preserve User** kullanır.

v5'in temel farkı: senin oyunda çalışan Türkçe fontundaki Türkçe karakterler **başka indekslere taşınmaz**. Türkçe mapping, metric ve bitmap hücreleri birebir korunur; yalnız kullanıcı aracının eksik bıraktığı teknik kayıtlar/orijinal glifler güvenli şekilde onarılır.

## Oyuna koyulacak klasör

`PATCH_READY_TECHNICAL/romfs/`

İçerik:
- `Font/`: **v5 Preserve User** BFFNT'leri.
- `Message/EU/EUen/`: Türkçe MSBT'ler + daha önce doğrulanan 27 kontrol-kodu teknik onarımı.

## Font v5'in garanti ettiği şeyler

Üç font için de:
- fiziksel blok düzeni `FINF + TGLP + CWDH + CMAP` = **4 blok**;
- **tek CWDH + tek CMAP** kullanılır; bu düzen senin çalışan fontlarının düzeniyle aynıdır;
- CWDH son indeksi gerçek maksimum mapped glyph indeksini kapsar;
- bütün kullanıcı mappingleri aynı glyph indeksinde kalır;
- `ÇĞİÖŞÜçğıöşü` kullanıcı fontundaki indeks/metric/bitmapleri korunur;
- `Ğ/İ/Ş/ğ/ı/ş` özellikle hücre SHA-256 karşılaştırmasıyla kullanıcı fontuyla birebir doğrulanır;
- feda edilmiş orijinal `È/É/Ê/è/é/ê` glifleri boş atlas indekslerine geri eklenir (Common'da zaten korunan `ê` tekrar eklenmez);
- kullanıcı fontunda yanlışlıkla bozulmuş `UI_Caption_US: µ/¿/ò` ve `Common_Sura_B_16: ®` orijinalden geri yüklenir;
- kullanıcı font aracındaki son CWDH kaydı hatası düzeltilir (`Caption: ☆`, `UI: ≠`, `Common: ￥` artık width kaydı dışında değildir);
- temiz kaynak + kullanıcı fontundan yeniden build edilince final üç BFFNT **byte-identical** olmak zorundadır.

Ayrıntı: `reports/font_v5/README_FONT_V5_TR.txt`.

## Türkçe karakterlerin sabit kalan indeksleri

`Caption_US.bffnt`
- `Ğ=124`, `İ=125`, `Ş=126`, `ğ=152`, `ı=153`, `ş=154`

`UI_Caption_US.bffnt`
- `Ğ=122`, `İ=123`, `Ş=124`, `ğ=150`, `ı=151`, `ş=152`

`Common_Sura_B_16.bffnt`
- `Ğ=134`, `İ=135`, `Ş=136`, `ğ=166`, `ı=199`, `ş=167`

Bunlar senin kullanıcı fontundaki indekslerle aynıdır.

## İlk yapman gereken

Windows:

`VERIFY_ALL.bat`

Linux/macOS:

`./VERIFY_ALL.sh`

Doğrulama şunları tekrar test eder:
1. Paket SHA-256 manifesti.
2. 51 MSBT / 6.037 metnin teknik yapısı.
3. LBL1/TXT2 ve kontrol-kodu dizileri.
4. MSBT byte-identical round-trip.
5. Font v5 fiziksel blok düzeni ve FINF pointerları.
6. CWDH/CMAP kapsamı ve atlas kapasitesi.
7. Kullanıcı fontundaki tüm mappinglerin aynı indekslerde kalması.
8. Türkçe gliflerin kullanıcı fontuyla aynı indeks + metric + bitmap olması.
9. Orijinal base karakterlerin final fontta yeniden mevcut ve bitmap/metric olarak doğru olması.
10. Font v5 deterministik rebuild: 3/3 byte-identical.
11. CSV'ler değiştirilmeden enjekte edilince 51/51 MSBT byte-identical.
12. Final pakette `.xmsbt` veya `.xml` bulunmaması.

## CSV / MSBT araçları

`comparison_csv/` altında 51 MSBT için çok dilli CSV'ler vardır.

`TR` sütununu düzenleyip:
- Windows: `BUILD_MSBT_FROM_CSV.bat`
- Linux/macOS: `./BUILD_MSBT_FROM_CSV.sh`

çalıştırırsan çıktı `WORKING_MSBT/` klasörüne üretilir ve otomatik doğrulanır.

Tek dosya:

```bash
python tools/msbt_direct_tool.py export input.msbt output.csv
python tools/msbt_direct_tool.py inject input.msbt edited.csv output.msbt --column TR
python tools/msbt_direct_tool.py verify output_directory
```

Kontrol kodları CSV'de `<MSBT:GGGG:TTTT:PAYLOADHEX>` şeklindedir; elle silme/değiştirme.

## Fontu yeniden üretme

```bash
python tools/bffnt_preserve_user_v5.py references/font_base references/font_user_patch NEW_FONTS
python tools/font_v5_independent_verify.py references/font_base references/font_user_patch NEW_FONTS --report-dir NEW_FONTS_REPORT
```

Bu builder **kullanıcı patch fontunu öncelikli gerçek kaynak** kabul eder; Türkçe glifleri yeniden çizmeye veya başka indekslere taşımaya çalışmaz.

## Font karakter kapsamı

Mevcut teknik Türkçe MSBT korpusunda 140 farklı görünür karakter var.
- `Common_Sura_B_16`: 140/140 kapsıyor.
- Caption/UI fontlarında orijinal oyunda da bulunmayan bazı fullwidth/Japonca/private-use semboller mevcut; bunlar v5'in sildiği karakterler değildir.
- Türkçe çekirdek `ÇĞİÖŞÜçğıöşü` üç fontta da vardır.

Ayrıntı: `reports/font_v5/text_character_coverage_v5.csv`.

## Metin çevirisinin durumu

MSBT **teknik yapısı** doğrulanmıştır. Ancak 6.037 satırın tamamının anlam/espri bakımından manuel incelemesi henüz bitmemiştir. `reports/text_reaudit_v3/` mevcut manuel çalışma ve bekleyen satırları içerir.

Bu nedenle `PATCH_READY_TECHNICAL` adı bilinçlidir: teknik dosya tabanı hazırdır; çeviri dili henüz final değildir.
