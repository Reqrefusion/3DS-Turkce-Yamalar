# Phoenix Wright: Ace Attorney Trilogy — 3DS Türkçe Yama

[Yayın sayfası](https://gamebanana.com/mods/705559) · [Belgelenen hataların teknik incelemesi](ISSUE_4_ANALIZ.md) · [Araçların kullanımı](TOOLS_TR.md)

## Kurulum

Yama Avrupa sürümü, **0004000000133300**, içindir. Başlık klasörünü `sd:/luma/titles/` altına yerleştirin ve Luma oyun yamalarını etkinleştirin.

```text
luma/titles/0004000000133300/
    code.bin
    romfs/
        pack.dat
        pack.inc
```

`code.bin` doğrudan başlık klasöründe bulunur. `pack.dat` ile `pack.inc` birlikte değiştirilmelidir. Mevcut yama ve kayıt dosyalarınızı yedekleyin.

## Kaynak araçları

`tools/aat3ds_tool.py` paket açma, diyalog aktarımı ve yeniden oluşturma girişidir. `tools/repair_native_controls.py` mevcut Türkçe paketteki komutları ve atlama hedeflerini özgün 3DS senaryolarıyla karşılaştırır. Komut tablosu, metin koruması ve kontrol akışı paket üretiminden önce doğrulanır.

Araçlar sayısal parametreleri yazı karakteri gibi dönüştürmez. Çözülemeyen atlamalar, bilinmeyen metin kodları ve eksik senaryolar hatayla durur. Çıktı için yeni veya boş bir klasör kullanılmalıdır; başarısız onarım tamamlanmış sonuç gibi yayımlanmaz.

## Doğrulama durumu

103 senaryoda Türkçe metinlerin korunduğu; 1.776 yerel atlama ve 365 paketlenmiş tablo hedefinin özgün olay hedefleriyle eşleştiği doğrulandı. Portekizce çeviri karşılaştırma için kullanıldı; farklı bölgeye ait program dosyası kopyalanmadı.

Belgelenen beş sorunun oyun içinde giderildiği henüz doğrulanmadı. Ayrıntılı rapor, otomatik değiştirilmeyen farkları da listeler.
