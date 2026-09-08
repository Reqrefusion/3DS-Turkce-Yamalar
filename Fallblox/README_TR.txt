FALLBLOX TÜRKÇE YAMA
====================

Oyun / Title ID
---------------
Fallblox
Title ID: 00040000000B4F00

Kurulum (Luma3DS LayeredFS)
---------------------------
1. SD kartındaki mevcut Fallblox yamalarını yedekle.
2. Bu paketin içindeki "luma" klasörünü SD kartın kök dizinine kopyala.
3. Luma3DS yapılandırmasında game patching / oyun yamalama özelliğinin açık olduğundan emin ol.
4. Oyunu İngilizce dil yuvasıyla çalıştır. Yama EURen dosyalarını Türkçe karşılıklarla değiştirir.

Kurulan ana dosyalar
--------------------
luma/titles/00040000000B4F00/romfs/EURen/msg/autumn.msbt
luma/titles/00040000000B4F00/romfs/EURen/msg/event.msbt
luma/titles/00040000000B4F00/romfs/EURen/msg/staff.msbt
luma/titles/00040000000B4F00/romfs/EURen/msg/stage.msbt
luma/titles/00040000000B4F00/romfs/EURen/lyt/Game_U.lz
luma/titles/00040000000B4F00/romfs/EURen/lyt/Res_U.lz

Çeviri kapsamı
--------------
- 1639 MSBT etiketi incelendi.
- 1507 gerçek/dolu kaynak metnin 1507'si Türkçe.
- İngilizce, Almanca, İspanyolca, Fransızca, İtalyanca ve Türkçe metinler
  translation/fallblox_tr.csv içinde yan yana tutulur.
- Fallblox'a özgü öğreticiler, hikâye, Studio, yardım ekranları, sahne adları,
  sistem metinleri ve krediler çevrildi.
- Terminoloji Pullblox yamasıyla uyumlu tutuldu:
  Papa Blox -> Usta Blox
  manhole -> geçit
  inverted manhole -> ters geçit
  floating block -> uçan blok
  move switch -> hareket düğmesi
  Training -> Alıştırma
  Extras -> Ekler

Görsel yazılar
--------------
START! -> BAŞLA!
CLEAR! -> TAMAM!
Congratulations! -> TEBRİKLER!

Görseller Fallblox'un kendi İngilizce Game_U.lz / Res_U.lz arşivleri temel
alınarak yeniden oluşturulur. Hedef BCLIM boyutları ve formatları korunur:
- BAŞLA!: 198x42, format 8 (RGBA4)
- TAMAM!: 194x52, format 8 (RGBA4)
- TEBRİKLER! katmanları: 304x48, format 2 (LA4) ve format 12 (L4)
Hedef olmayan DARC dosyaları değiştirilmez.

Tuş ikonları ve Fallblox fontu
-------------------------------
- Genişlik ölçümü Fallblox'un kendi romfs/COMMON/font/Kurokane.lz fontundan yapılır.
- Fallblox Kurokane fontu Pullblox fontuyla aynı dosya değildir; bu paket Fallblox
  font metriklerini kullanır.
- 3DS sistem ikonları (A/B/X/Y/L/R, Circle Pad ve yön ikonları) oyun fontunun
  CMAP tablosunda bulunmadığından, fit kontrolünde temkinli 32 px genişlik kabul edilir.
- Tuş ekleri Türkçe telaffuza göre düzeltildi: A'ya, B'yi, X'e/X'i,
  Y'ye/Y'yi, L'ye/L'yi, R'ye/R'yi. Uzun alanlarda gerektiğinde
  "A tuşuna bas / B tuşunu basılı tut" yapısı kullanılır.
- 85 sistem-ikonlu metnin tamamı ayrıca kontrol edildi: dilbilgisi hatası 0,
  resmî genişlik/satır sınırı aşımı 0. Ayrıntı: reports/icon_font_qc.json

Taşma ve teknik QC
------------------
Son doğrulamada:
- eksik Türkçe metin: 0
- kontrol kodu envanter/yapı hatası: 0
- UTF-16 kodlama hatası: 0
- eksik yeni Türkçe glif: 0
- iki satırlık resmî kutuda Türkçe taşma: 0
- İngilizcesi 1-2 satır olup Türkçede 3+ satıra çıkan metin: 0
- MSBT üretim sonrası metin farkı: 0
- hedef dışı DARC değişikliği: 0
- temiz klasörde ikinci üretim farkı: 0

Otomatik piksel kıyaslamasında kalan birkaç uyarı tek satırlık doğal UI
kelimeleridir (ör. Hayır, Açık, Kapalı, Yardım). Bunları "Hyr/Kpl" gibi
düşük kaliteli kısaltmalara çevirmemek bilinçli bir tercihtir. Ayrıntılar
reports/text_qc.json ve reports/translation_audit.json içindedir.

Araçlar
-------
tools/fallblox_tool.py
  Çok dilli CSV çıkarma, doğrulama ve dört MSBT'yi enjekte etme aracı.

tools/fallblox_assets.py
  Game_U.lz ve Res_U.lz içindeki Türkçe bitmap yazıları üretir ve paketler.

tools/verify_patch.py
  Kaynak Fallblox ZIP'i ile patch'i karşılaştırarak MSBT metinlerini,
  kontrol kodlarını, DARC değişikliklerini ve BCLIM metadata'sını doğrular.

tools/msbt_core.py, bclim_codec.py, asset_probe.py
  MSBT, CFNT, BCLIM, DARC ve LZ11 yardımcı kodları.

Örnek doğrulama
----------------
Python ve Pillow kurulu bir ortamda, kaynak dump ZIP'in varsa:

python tools/verify_patch.py --source-zip "00040000000B4F00 Fallblox.zip" --patch-root .

CSV'den MSBT üretmek için kaynak ROMFS gerekir:

python tools/fallblox_tool.py inject --romfs <kaynak_romfs> \
  --csv translation/fallblox_tr.csv --out-romfs <çıktı_romfs>

Not
---
Statik/binary testler ve satır genişliği kontrolleri geçmiştir. Gerçek 3DS'de
oyunun bütün olası ekranlarını otomatik olarak baştan sona oynatmak bu çalışma
ortamında mümkün değildir; bu nedenle cihaz üzerinde karşılaşılan bağlama özgü
bir görsel sorun olursa ilgili etiket CSV üzerinden düzeltilebilir.
