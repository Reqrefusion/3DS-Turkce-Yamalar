VLR 3DS - TÜRKÇE GELİŞTİRME / TEŞHİS ARAÇLARI

Bu klasör, VLR Türkçe font ve siyah-ekran teşhisi sırasında kullandığım/kullandığım işlemleri yeniden üretmek için topladığım araç setidir.

ÖNEMLİ
- Resmî VLR Font Editor/Text Editor EXE'lerini bu pakete KOYMADIM. Bu çalışmada onların EXE'lerini çalıştırmadım; formatı Python ile inceleyip düzenledim.
- Oyunun orijinal RomFS/font dosyaları bu araç paketine dahil değildir.
- tools/apply_turkish_fonts_legacy.py ilk geliştirme aşamasındaki eski patcher'dır. V3 final font yerine kullanılmamalıdır; yalnızca geçmişte kullandığım aracı da istediğin için dahil edilmiştir.

ARAÇLAR
1) vlr_font_info.py
   .dat başlığı, font adı/stili, karakter haritası ve Türkçe karakter varlığını gösterir.

2) list_font_chars.py
   Unicode -> glyph index listesini metin olarak çıkarır.

3) verify_turkish_fonts.py
   Bir klasördeki fontlarda ç ğ ı ö ş ü Ç Ğ İ Ö Ş Ü var mı ve karakter çakışması var mı kontrol eder.

4) vlr_font_compare.py
   Orijinal ve patchlenmiş iki fontun map/boyut/hash farklarını karşılaştırır.

5) vlr_font_lzma_scan.py
   Font içerisindeki LZMA1 özellik imzası adaylarını offsetleriyle listeler. Glif kayıt yapısını tersine mühendislik ederken kullandığım teşhis tipidir.

6) romfs_compare.py
   İngilizce RomFS ile patch RomFS'yi dosya yolu, boyut ve SHA-256 üzerinden karşılaştırır.

7) lua51.py + lua51_dump_strings.py
   VLR'nin Lua 5.1 binary chunk dosyalarındaki string constantlarını güvenli şekilde okur/döker.

8) lua51_compare_code.py
   İngilizce ve Türkçe Lua chunklarında instruction byte'larının ve proto yapısının aynı kalıp kalmadığını kontrol eder. Çeviri sırasında kodun bozulup bozulmadığını ayırmak için kullanılır.

9) lua51_unicode_scan.py
   Çeviride kullanılan ASCII dışı karakterlerin frekansını çıkarır. â/î/û/’/“/”/ə gibi fontta eksik olabilecek karakterleri yakalamak için kullanılır.

10) lua51_find_strings.py
    Novel, System vb. dahili string/key adaylarını bütün language Lua dosyalarında arar.

11) sha256_tree.py
    Klasörün SHA-256 manifestini üretir.

12) make_contact_sheet.py
    Çıkarılmış glif PNG'lerinden büyütülmüş piksel önizleme sayfası üretir. Pillow gerekir.

13) apply_turkish_fonts_legacy.py + reference/patches_legacy.json
    İlk font geliştirme turunda kullandığım eski patch sistemi. V3 yerine kullanılmamalıdır.

ÖRNEK KOMUTLAR
python tools/vlr_font_info.py SKP2-Regular.12.dat
python tools/list_font_chars.py SKP2-Regular.12.dat charlist.txt
python tools/verify_turkish_fonts.py fonts
python tools/vlr_font_compare.py original.dat patched.dat
python tools/romfs_compare.py english_romfs patch_romfs
python tools/lua51_compare_code.py english.lua turkish.lua
python tools/lua51_unicode_scan.py romfs/script/language
python tools/lua51_find_strings.py romfs/script/language Novel System Anlatı Sistem
python tools/sha256_tree.py romfs -o SHA256SUMS.txt

V3 HİZALAMA HATASININ TEKNİK NOTU
V2'de Türkçe glif bitmapleri eklenmişti fakat VLR'nin font kayıtlarındaki escapement/horizontal/vertical metrikleri bir sonraki kayıt ilişkisi nedeniyle yanlış karakterlerle eşleşmişti. V3'te temel Latin harflerin metrikleri referans alınarak düzeltildi. examples/V3_FONT_METRIK_RAPORU.txt ayrıntılı önce/sonra değerlerini içerir.

RESMÎ TOPLULUK ARAÇLARI
VLR ROM Hacking Tools içinde Font Editor, Text Editor ve Graphics Toolset bulunur. Bunları bu çalışma sırasında çalıştırmadığım ve doğrulanmış EXE'lerini elimde bulundurmadığım için pakete binary eklemedim.
Kaynak bilgi: https://www.gamebrew.org/wiki/Virtues_Last_Reward_3DS
