ANIMAL CROSSING: NEW LEAF - TÜRKÇE YAMA PAKETİ
================================================

İÇERİK
- PATCH/romfs/Script : EN dil yuvasına Türkçe enjekte edilmiş değiştirilmiş UMSBT dosyaları.
- PATCH/romfs/Font   : Gönderilen BCFNT fontları. Ana diyalog fontu Türkçe glyphleri zaten içeriyor.
- TRANSLATIONS_TR_FINAL : 3125 ayrı CSV'nin son/uyumluluk-normalize edilmiş hali.
- TOOLS/acnl_script_tool.py : UMSBT/MSBT export, validate ve inject aracı (3. parti bağımlılık yok).
- TOOLS/acnl_font_check.py  : BCFNT v3 CMAP Türkçe karakter kontrol aracı.
- TOOLS/build_patch.py      : Orijinal Script + CSV + Font'tan romfs yamayı yeniden üretir.
- REPORTS                   : doğrulama ve font raporları.

FONT NOTU
Garden_msg_size16.bcfnt içinde şu karakterlerin tamamı zaten gerçek glyph olarak mevcut:
ç Ç ğ Ğ ı İ ö Ö ş Ş ü Ü
Bu nedenle ana diyalog font atlasını yeniden çizmek, kalite kaybı ve bozulma riski yaratacağından yapılmadı.
Garden_ruby.bcfnt Japonca ruby/furigana fontudur. Garden_no.bcfnt ve Garden_no_f16.bcfnt ise sayı/noktalama fontlarıdır.
Bunlar normal diyalog metni için gerekli Türkçe alfabetik fontlar değildir.

ASR DOSYALARI
Orijinal *_ASR.umsbt dosyaları 8-bit Batı Avrupa metni kullanıyor. Türkçe ğ/ş/ı gibi karakterler bu yapıda kayıpsız
saklanamadığı için araç gerektiğinde yalnız hedef EN MSBT'yi UTF-16LE'ye dönüştürür. Bu pakette iki dosya dönüştürüldü:
- Str/STR_Reset_ASR.umsbt
- Str/STR_SPNpc_name_ASR.umsbt
Kontrol tagleri dönüşüm sırasında korunur.

ÇEVİRİ UYUMLULUK DÜZELTMELERİ
- Birleşik Unicode 'u + diaeresis' dizileri NFC ile 'ü' yapıldı (2 satır).
- 'zilinə' yazımı 'ziline' yapıldı (1 satır).
- STR_Common içindeki 分 / 本 / 匹 karakterleri değiştirilmedi; bunlar orijinal EN dosyada da aynen bulunuyor.

LUMA3DS - AVRUPA ORİJİNAL SÜRÜM
Hazır kurulum için INSTALL_LUMA_EUR_ORIGINAL.bat dosyasına SD kartın kök yolunu ver.
Elle kurulumda PATCH/romfs içeriğini şuraya kopyala:
SD:/luma/titles/0004000000086400/romfs/
Luma yapılandırmasında "Enable game patching" açık olmalıdır.

ÖNEMLİ SÜRÜM NOTU
Bu yama, bu çalışma için gönderilen Script.zip/Font.zip dosyalarından üretildi. Başka bölge veya farklı ROMFS revizyonuna
körlemesine uygulanmamalıdır. Farklı sürüm kullanıyorsan TOOLS/build_patch.py ile kendi çıkardığın Script/Font üzerinden
yeniden üretmek en güvenli yöntemdir.

YENİDEN ÜRETME
Windows:
  cd TOOLS
  01_VALIDATE_TR.bat C:\ROMFS\Script C:\Yama\TRANSLATIONS_TR_FINAL
  02_BUILD_PATCH.bat C:\ROMFS\Script C:\Yama\TRANSLATIONS_TR_FINAL C:\ROMFS\Font C:\ACNL_TR_PATCH

Komut satırı:
  python acnl_script_tool.py validate <Script> <TRANSLATIONS_TR_FINAL> --target EN
  python build_patch.py --script <Script> --translations <TRANSLATIONS_TR_FINAL> --font <Font> --out <patch> --target EN

DOĞRULAMA ÖZETİ
- 3125 UMSBT parse edildi.
- 64702 dolu TRANSLATION satırı çıktıdan tekrar okunup birebir karşılaştırıldı.
- Eşleşmeyen satır: 0.
- Değiştirilmiş UMSBT: 3120.
- Hedef dışındaki ES/FR/IT/DE MSBT parçaları byte düzeyinde değişmeden kaldı.
