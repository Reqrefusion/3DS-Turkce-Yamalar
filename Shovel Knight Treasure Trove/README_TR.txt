SHOVEL KNIGHT 3DS v4.1 TÜRKÇE YAMA + ARAÇ SETİ
===============================================

Bu paket iki şey içerir:
1) patch/SD_ROOT/ altında doğrudan SD karta kopyalanabilecek nihai Türkçe yama.
2) tools/ altında 3DS v4.1 loctext PAK/STL çıkarma, yeniden paketleme, dönüştürme ve doğrulama aracı.

HEDEF
Base Title ID:   000400000017C900 (EUR)
Update Title ID: 0004000E0017C900 (EUR)
Update:          Shovel Knight: Treasure Trove v4.1

NİHAİ DOSYA
patch/loctext_eng_3DS_v4.1_TR_FINAL.pak
SHA-256: a9e5f87e4990c31e4bc1fc08eb74ddf2c8c15161d0fe328cb426b4a4b1186f2d

KURULUM
Eski global_free.pak override'larını kaldırın.
patch/SD_ROOT/luma klasörünü SD kart köküne kopyalayın.
Enable game patching açık olsun ve oyunda English seçin.

PYTHON ARACI
Python 3 gerekir, harici modül gerekmez.

Bilgi göster:
  python tools/shovel_knight_3ds_v41_tr_tool.py info loctext_eng.pak

3DS v4.1 orijinal loctext + bilinen Steam Türkçe yamadan yeniden üret:
  python tools/shovel_knight_3ds_v41_tr_tool.py convert-steam 3DS_ORIGINAL_loctext_eng.pak STEAM_TR_loctext_eng.pak OUTPUT.pak --report report.json

Araç güvenlik için iki bilinen kaynak SHA-256'sını kontrol eder; yanlış sürüm verilirse dönüştürmeyi reddeder.

Orijinal ve yama yapısını doğrula:
  python tools/shovel_knight_3ds_v41_tr_tool.py verify 3DS_ORIGINAL_loctext_eng.pak OUTPUT.pak

Metinleri JSON'a çıkar:
  python tools/shovel_knight_3ds_v41_tr_tool.py extract-json loctext_eng.pak translations.json

Düzenlenmiş JSON'u orijinal 3DS PAK'a enjekte et:
  python tools/shovel_knight_3ds_v41_tr_tool.py inject-json 3DS_ORIGINAL_loctext_eng.pak translations.json OUTPUT.pak

QA
ShovelKnight_3DS_v4.1_TR_FINAL_QA.json dosyasında satır sayıları, NULL satırlar, pointer/alignment, kontrol kodları ve font karakter kapsamı kontrolleri bulunur.
