# Süreç ve Mimari

## 1. Kaynakların ayrılması

`Common_en` metin tabloları ve `Graphics/UI_en` arayüz kaynakları ayrı katmanlar olarak işlenir. Çalışma `.xls` dosyaları yalnız build girdisidir; LayeredFS paketine konmaz.

## 2. Common_en: XLS → BTBF

Bravely Default tabloları `BTBF` ailesidir. XLS'teki `Text` hücreleri UTF-16LE olarak binary text block'a yazılır. Metin uzunluğu değiştiği için `Text Pntr` alanları satır bazında yeniden hesaplanır. Record stride/header yapısı korunur. Ardından değişen binary'ler ilgili `crowd.fs` içine konur ve `index.fs` offset/size kayıtları 4-byte alignment ile yeniden üretilir.

## 3. UI: DARC / BCLYT

UI bileşenlerinin önemli bölümü DARC arşivleri içinde BCLYT layout'lardır. `txt1` metinleri UTF-16'dır. v3.2'den beri doğru alanlar kullanılır: pane width/height `0x44/0x48`, text length/buffer length `0x4C/0x4E`, text offset `0x58`. v3.1'deki yanlış `0x48` yazımı artık yoktur.

DE/ES/FR/IT layout'larından uygun genişlik/konum geometrisi donor olarak alınır. Sonra Türkçe CFNT advance width ile metin genişliği hesaplanır. Yalnız gerektiğinde yatay font boyutu sınırlı biçimde küçültülür. v3.3 baseline audit: 674 değişen UI metni, 171 fit-scale, overflow 0.

## 4. Font: CFNT

Oyunun kendi `hikari.bcfnt` CMAP'i okunur. Var olan `Ç/ç Ö/ö Ü/ü` korunur; `Ğ/ğ İ/ı Ş/ş` glyph'leri eklenir. Araç artık kaynak glyph indekslerini sabit sayıyla varsaymaz; Unicode→glyph CMAP'inden dinamik çözer. Önceki “Ç/ç off-by-one” şüphesi yeniden doğrulamada yanlış çıkmıştır; v3.2 font binary'si dinamik-CMAP build ile aynı hash'i vermiştir.

## 5. Raster: BCLIM

Resme gömülü UI yazıları BCLIM decode edilir, yalnız doğrulanmış metin bölgeleri Türkçeleştirilir ve RGBA8 BCLIM olarak tekrar kodlanır. `unique_bclim_index.json` çevrilmiş 242 benzersiz raster hedefin 448 arşiv kullanımını yeniden üretmek için v3.3 araç paketine eklenmiştir. Harita başlıkları ayrı eşleme ile eklenir.

## 6. Terminoloji ve kalite

Kullanıcının Common_en çevirisi tek terminoloji otoritesidir. Existing translated cell'ler normalde overwrite edilmez; yalnız EventViewer gibi karışık/bozuk kısmi çeviriler kaynak-keyed curated override ile düzeltilir. Kör kelime değiştirme yerine tam kaynak string veya bağlam tabanlı kural tercih edilir.

## 7. Doğrulama

Build sonunda crowd/index alignment, bounds, overlap; DARC parse; BTBF parse; ROMFS temizliği; SHA-256 manifest; kısa İngilizce exact-token taraması; UI pane overflow denetimi yapılır. v3.3 teknik audit error=0, warning=0 vermiştir.


## v3.4 font paketleme düzeltmesi

v3.3 hazır LayeredFS ZIP'lerinde gerçek `Graphics/UI_en/Font/Font` dosyası bulunmuyordu; yalnız üretim aracı bulunuyordu. v3.4'te yamalı DARC/CFNT doğrudan runtime `romfs` ağacına dahil edilmiştir. CMAP ve glyph görünür-piksel doğrulaması `Reports/FONT_VERIFICATION_v34.json` ile kaydedilir.
