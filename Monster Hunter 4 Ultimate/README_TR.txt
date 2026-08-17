MH4U Türkçe v32 - USA v1.3.0 CRASHGUARD v8
Title ID: 0004000000126300
Update Title ID: 0004000E00126300

KURULUM
1) 1_SD_KARTINA_KOPYALA içindeki luma klasörünü SD kartın köküne kopyala.
2) Mevcut dosyaların üzerine yaz. Klasörü silmek zorunda değilsin.
3) Luma3DS'de game patching açık olmalı.
4) Aynı kayıtla doğrudan "Karakter yükleniyor" aşamasını yeniden dene.

V8'DEKİ YENİ CRASH DÜZELTMESİ
- crash_dump_00000053 gerçek v1.3.0 update executable ile adres-adres analiz edildi.
- Crash 0x006894B0'da NULL pointer dereference: oyun geçersiz enemy ID 0 / em000 kaynağını yüklemeye çalışıyor.
- Executable'ın enemy resource tablosu 124 kayıtlı: index 0 NULL, index 1..123 geçerli.
- v8 code.ips yalnız preload taramasının başlangıcını 0'dan 1'e alır (mov r4,#0 -> mov r4,#1).
- Geçerli em001..em123 kaynaklarının hiçbirine dokunulmaz.
- Yama exact v1.3.0 decompressed .code offset 0x55BD78'e uygulanır.
- Luma'nın kurulum yolu: luma/titles/0004000000126300/code.ips

ROMFS / FONT
- RomFS ve Türkçe font tarafı v7 REALUPDATE ile aynıdır ve kullanıcının v1.3.0 update CXI'sine dayanır.
- Gerçek font_loc atlası kullanılır; LFD update orijinali korunur.
- Ana UI Türkçe karakter çözümü korunmuştur.

TEST İÇİN ÖNEMLİ
- Bu sürümde kayıt dosyanı silme; aynı karakter/kayıtla test et.
- Eğer yine crash olursa yeni dump'ı gönder.
- Eğer yeni dump'ın PC'si yine TAM OLARAK 0x006894B0 olursa code.ips yüklenmemiş demektir (game patching / dosya yolu kontrol edilir).
- PC değişirse guard çalışmış ve bir sonraki gerçek hata noktasına geçmişiz demektir.

Detaylar 2_TEKNIK_VE_ARACLAR/CRASH_00000053_ANALIZ_VE_V8_GUARD.txt içindedir.
