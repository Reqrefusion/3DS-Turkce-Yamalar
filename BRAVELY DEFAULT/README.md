# Bravely Default Türkçe Yama — Progress v3.6

Bu paket v3.5 üzerine gerçek cihazdaki Türkçe karakter `?` sorunu için Latin-1 uyumluluk katmanı ve yeni raster düzeltmeleri ekler.

**EUR kullanıcıları doğrudan `BravelyDefault_TR_Progress_v3.6_LayeredFS_EUR.zip` paketini SD kart köküne çıkarabilir. Font için ek araç çalıştırılması gerekmez.**

Ayrıntılar `Docs/` ve doğrulamalar `Reports/` altındadır.

# Bravely Default Türkçe Yama — Progress v3.5

> **Font düzeltmesi:** Gerçek 3DS testinde Türkçe Extended-A karakterlerinin `?` görünmesi üzerine v3.4 font katmanı yeniden incelendi. v3.5 hem `Graphics/UI/Font/Font` hem `Graphics/UI_en/Font/Font` arşivlerini hazır yamalı olarak içerir. Ayrıntı: `Docs/FONT_FIX_v3.5_TR.md`.

**Font düzeltmesi:** Bu sürümde iki hazır Türkçe font arşivi bulunur: `romfs/Graphics/UI/Font/Font` ve `romfs/Graphics/UI_en/Font/Font`. `Ğ ğ İ ı Ş ş` için ayrıca font patch komutu çalıştırmanız gerekmez.

Bu paket, kullanıcının mevcut `Common_en` Türkçe çevirisini ana terminoloji kaynağı kabul eden güncel çalışma sürümüdür. Final sürüm değildir; fakat bu noktaya kadar doğrulanmış bütün runtime yamalarını, kaynak araçları, audit raporlarını ve süreci içerir.

## v3.3 özeti

- 401 çalışma sayfası yeniden işlendi; 142 binary tablo yeniden üretildi.
- Common_en tarafında toplam 30.523 text-field değişimi bulunan build üretildi ve 11 crowd/index arşivi yeniden paketlendi.
- EventViewer için 553 yeni kalite override'ı; toplam 561 kaynak başlık için bağlama göre Türkçe eşleme hazırlandı. Karışık `Kristal of Wind` türü satırlar giderildi.
- Shop tarafında 73 yeni doldurma uygulandı; kaynak İngilizceyle birebir kalan kullanıcı repliği 0.
- Paramater tarafında 263 kullanıcıya görünür eşya açıklaması çevrildi; sentence-like açıklamalarda kaynakla birebir kalan kayıt 0.
- 34 yapılandırılmış sistem/komut metni, 27 legacy mesaj ve 16 konum ek olarak işlendi.
- UI BCLYT: 674 değişen metin; 171 dar alanda kontrollü font ölçekleme; yapısal audit'te taşma 0.
- `No/Yes/OK/On/Off/Close/Continue/Buy/Easy/Hard/Fast/None/Cancel/Quit/Confirm/Element` exact-token taramasında kaçak 0.
- 18 crowd/index çifti, 711 arşiv girdisi, 327 DARC girdisi ve 384 BTBF girdisi yapısal kontrolden geçti; error/warning 0.

## Kurulum

Ana pakette `romfs/` runtime yaması bulunur. Luma3DS için bu içerik bölge Title ID'sinin altındaki `romfs` klasörüne yerleştirilir. EUR: `00040000000FC600`, USA: `00040000000FC500`. Luma'da `Enable game patching` açık olmalıdır.

Türkçe `Ğ ğ İ ı Ş ş` desteği **v3.5 runtime paketine iki font katmanında hazır olarak gömülüdür**. `romfs/Graphics/UI/Font/Font` ve `romfs/Graphics/UI_en/Font/Font` yamalı DARC/CFNT arşivleridir; normal kurulumda ek font komutu gerekmez. `Tools/patch_font_layeredfs.py` ve `Tools/prepare_layeredfs.py` yalnız yeniden üretim/denetim amacıyla tutulur. Ayrıntılar `Docs/FONT_KURULUM_VE_DOGRULAMA_TR.md` içindedir.

## Terminoloji

Kullanıcının mevcut `Common_en` çevirisi otoritedir. Örnekler: `Freelancer → Serbest Savaşçı`, `Black Mage → Kara Büyücü`, `White Mage → Beyaz Büyücü`, `Spell Fencer → Büyü Kılıççısı`, `Salve-Maker → İlaç Ustası`, `Spiritmaster → Ruh Ustası`, `Party Chat → Parti Sohbeti`, `Abilink → Yetenek Bağı`, `MND → İRA`, `Time Mage → Zaman Büyücüsü`.

## Durum

v3.4 gerçek Avrupa 3DS testinde Türkçe Extended-A karakterleri `?` olarak raporlandı; bu geri bildirim v3.5 ortak-font düzeltmesini doğurdu. v3.5 dosya yapısı ve aktif CMAP zincirleri açısından doğrulanmıştır; yeni iki-font düzeltmesinin gerçek cihaz testi kullanıcı tarafında yapılacaktır. Kalan çalışma başlıkları `Docs/KALAN_ISLER_TR.md` içindedir.

## v3.9 notu
Dinamik kısa etiketler için MP/BP/JP kısalık denetimi ve TW_10 satır hizası düzeltmeleri eklendi. Ayrıntılar Docs/CHANGELOG_v3.9_TR.md içindedir.


## v3.10 terminoloji notu
Kısa puan adları artık İngilizce kaynak kısaltmalarından değil Türkçe ana kavramlardan türetilir: Büyü Puanı=BP, Cesaret Puanı=CP, Meslek Puanı=MP. Ayrıntılar `Docs/TERIM_KISALTMALARI_v3.10_TR.md`.
