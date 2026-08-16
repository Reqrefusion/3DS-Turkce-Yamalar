FEA TÜRKÇE PASS202 — COMPLETE DEV BUNDLE
========================================

01_READY_PATCH
  Doğrudan kullanılabilir RomFS/Luma yaması ve tam replacement arşivleri.

02_SOURCE_REVIEW
  Kullanıcının son Pass202 review paketi, Pass202 changelog ve
  yeniden oluşturulmuş manifest ile 854 ayrı CSV projesi.

03_TOOLS
  Ayrı-CSV metin çıkarma/enjekte aracı (V2), BFNT font aracı ve tek komutluk
  yeniden-yapılandırma yardımcı scripti.

04_FONT_WORK
  Türkçeleştirilmiş fontlar, çıkarılmış font projesi ve önizleme.

05_HISTORY_INTERMEDIATE
  Bu çalışma sırasında kullandığımız/eski oluşturduğumuz ara paketler ve
  önceki Türkçe yama referansı.

06_REFERENCE_INPUTS
  Çalışmada kullanılan orijinal m.zip ve fonts.zip girdileri.

07_VALIDATION_LOGS
  Son enjeksiyon ve yapısal doğrulama kayıtları.

YENİDEN DERLEME
---------------
Python ile:
  python 03_TOOLS/Build_Helper/rebuild_pass202_patch.py

Hazır yama için:
  01_READY_PATCH/README_KURULUM_TR.txt

FONT HOTFIX 1
-------------
U+0131 (ı) bitmapinin i ile aynı olması düzeltildi. Font Tool raporu bu hatayı artık otomatik yakalar.
