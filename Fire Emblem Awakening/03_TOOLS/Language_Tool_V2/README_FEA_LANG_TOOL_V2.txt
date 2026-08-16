Fire Emblem Awakening - Çok Dilli Metin Extract / Inject Aracı v2
================================================================

Bu sürüm masaüstü arayüzü değildir. Komut satırından çalışır.
Her .bin.lz dosyası için AYRI bir CSV üretir.

Gereksinim:
- Python 3.10+ (ek paket gerekmez)

Diller:
F = French
G = German
I = Italian
S = Spanish
U = English
TR = Türkçe çalışma sütunu

1) NORMAL EXTRACT
-----------------
python fea_lang_tool.py extract m.zip FEA_Project

Örnek çıktı:
FEA_Project/
  manifest.json
  csv/
    000.csv
    001.csv
    Menu.csv
    GameData.csv
    E009.csv
    ...

Her CSV'nin sütunları:
index,key,F,G,I,S,U,TR

F/G/I/S/U aynı metin anahtarının resmi dillerini yan yana gösterir.
TR sütununa Türkçe çeviriyi yaz.
index ve key sütunlarını değiştirme.

2) ESKİ TÜRKÇE YAMAYI TR SÜTUNUNA AKTARARAK EXTRACT
----------------------------------------------------
python fea_lang_tool.py extract m.zip FEA_TR_Project --tr-patch tr-m.zip

Araç eski yamanın U klasöründeki metinlerini anahtar (MID_...) bazında
orijinal dosyalarla eşleştirir ve ilgili CSV'nin TR sütununa taşır.

Eski yamadaki dosyalar şu biçimlerde olabilir:
- normal Nintendo LZ11 (0x11)
- Fire Emblem 0x13 + LZ11 sarmalı
- zaten açılmış mesaj arşivi

3) INJECT
---------
python fea_lang_tool.py inject m.zip FEA_TR_Project --target U --column TR --fallback U --output m_turkish_new.zip

Bu komut:
- FEA_TR_Project içindeki 854 ayrı CSV'yi okur
- TR metinlerini U slotuna yazar
- TR boşsa U metnini korur
- mesaj offsetlerini yeniden oluşturur
- LZ11 ile tekrar sıkıştırır
- ürettiği veriyi kendi içinde doğrular

Boş TR hücresinin gerçekten boş oyun metni olmasını istiyorsan:
python fea_lang_tool.py inject m.zip FEA_TR_Project --target U --column TR --fallback U --blank-is-empty --output m_turkish_new.zip

4) VERIFY
---------
python fea_lang_tool.py verify m_turkish_new.zip

5) ESKİ TEK CSV DESTEĞİ
-----------------------
v1 ile üretilmiş translations.csv dosyaları inject tarafında hâlâ desteklenir:
python fea_lang_tool.py inject m.zip translations.csv --target U --column TR --fallback U --output out.zip

Bu sürümde extract artık tek translations.csv üretmez.

NOTLAR
------
- Türkçe karakterler UTF-16LE olarak yazılır.
- Oyunun fontunda ğ, Ğ, ş, Ş, ı, İ vb. glifler yoksa font yaması ayrıca gerekir.
- CSV'leri Excel/LibreOffice ile açarken UTF-8 olarak koru. Dosyalar UTF-8 BOM ile yazılır.
- Oyun kontrol kodlarını ($k, $p, $Wm..., $Wa vb.) silmemeye dikkat et.
