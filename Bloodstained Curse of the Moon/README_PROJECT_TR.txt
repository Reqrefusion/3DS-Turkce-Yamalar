BLOODSTAINED: CURSE OF THE MOON (3DS) - TÜRKÇE YAMA TAM PROJE ARŞİVİ
=====================================================================

Bu arşiv bu konuşma sırasında kullanılan/üretilen proje materyallerini tek yerde toplar.

KLASÖRLER
---------
00_ORIGINAL_INPUT/
  Kullanıcının sağladığı bloodstain.zip. Projeyi baştan üretmek için kaynak girdi.

01_TOOLS/
  core/  : TTB/OSBCTR container açma-paketleme, zlib/XOR, texture decode/encode,
           TTB okuma/yazma gibi temel araçlar.
  v2/    : v2 tam yama üretim ve önizleme scriptleri.
  v4/    : OSB node analizi, doğru node-relative vertex adresleme, native glyph bank,
           v4 build ve doğrulama scriptleri.
  v5/    : v5 build, başlık/arayüz patch, Result çoklu dil slot patch ve tam doğrulama.

02_TRANSLATIONS/
  Çeviri tabloları ve CSV şablonları.

03_FINAL_V5/
  En güncel v5 LayeredFS yamaları, RomFS override dosyaları, SHA256 ve denetim raporları.

04_INTERMEDIATE_PATCHES/
  İlk sürümden v4'e kadar ara paketler ve geliştirme kitleri.

05_REPORTS_PREVIEWS/
  Orijinal/Türkçe render karşılaştırmaları, OSB atlasları, doğrulama önizlemeleri.

06_WORKFILES/
  Analiz sırasında üretilen glyph/node debug görselleri, taramalar ve loglar.
  Orijinal oyundan çıkarılmış tam RomFS/CXI kopyası ayrıca tekrar eklenmemiştir;
  bunun yerine 00_ORIGINAL_INPUT/bloodstain.zip kaynak olarak bulunur.

07_HARDWARE_TEST_REFERENCES/
  Gerçek oyun/emülatör çıktısı olarak konuşmada sağlanan ve düzeltmelerde referans alınan ekran görüntüleri.

ÖNEMLİ ARAÇ
-----------
01_TOOLS/core/bloodstained_tr_tool.py
  Temel container ve format aracıdır. Diğer scriptlerin çoğu bunu import eder.

SON YAMA
--------
03_FINAL_V5/bloodstained_tr_v5_complete_layeredfs.zip

Kurulum hedefi:
SD:/luma/titles/00040000001D3C00/romfs/

NOT
---
Scriptlerin bir kısmında çalışma sırasında kullanılan /mnt/data/... mutlak yolları bulunabilir.
Başka bilgisayarda çalıştırırken BASE/ORIG/OUT gibi yol sabitlerini kendi klasörlerine göre değiştir.
