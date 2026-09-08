# Luigi's Mansion 2 Türkçe — FONTFIX V4 DUALPLANE

Bu sürüm V3'ün metin/crash düzeltmelerini korur ve Türkçe fontu baştan düzeltir.

## Kullanılacak dosya

`Luigis_Mansion_2_TR_FONTFIX_V4_DUALPLANE.zip`

Eski `0004000000076500` LayeredFS/mod klasörünü tamamen silip bu ZIP'i temiz biçimde kurun. V3 font dosyasının klasörde kalmaması önemlidir.

## V4 font düzeltmeleri

- `Ğ ğ İ ı Ş ş` A4 alpha glifleri yeniden üretildi.
- ETC1 eşlik katmanı da Türkçe glifle senkronize edildi.
- `ı` artık gerçekten noktasızdır.
- `İ` oyunun kendi `i` noktasını kullanır.
- `Ş/ş`, oyunun kendi `Ç/ç` cedillasını kullanır.
- `Ğ/ğ` breve'si oyunun kendi yuvarlak font hatlarından oluşturuldu.
- Repurpose edilen slotların RenderWidth değerleri orijinal bırakıldı; sonraki gliflerin atlas koordinatı kaymıyor.
- 256/128/64/32/16 mip seviyeleri güncellendi.

## Doğrulamalar

- Font zlib akışları: OK
- Font dosya boyutu: orijinalle aynı
- Font texture compressed stream: 75.711 / 75.960 bayt
- FE Türkçe font kapsamı: 0 eksik glif
- NLOC/.dict doğrulaması: OK
- ZIP bütünlük testi: OK

`FONT_ANALYSIS_V4_TR.md` içinde V3'teki hatanın bayt/blok seviyesindeki açıklaması vardır.
`Turkish_Glyphs_V4_Preview.png` iki oyuniçi fontun yeni Türkçe glif alpha önizlemesidir.
