# Türkçe font kurulumu ve doğrulama — 

 paketinde fontlar hazırdır; normal LayeredFS kurulumunda ayrıca Python komutu çalıştırılmaz.

## Gerekli iki font

Bravely Default'un Avrupa dump'ında iki ayrı font katmanı vardır ve ikisi de yamalanmıştır:

1. `Graphics/UI/Font/Font`
2. `Graphics/UI_en/Font/Font`

EUR LayeredFS içinde karşılıkları:

- `luma/titles/00040000000FC600/romfs/Graphics/UI/Font/Font`
- `luma/titles/00040000000FC600/romfs/Graphics/UI_en/Font/Font`

İkinci dosya vardı; ilk dosya eksikti. Gerçek 3DS'te `Ğ/ğ/İ/ı/Ş/ş` karakterlerinin `?` görünmesi üzerine bu eksik tespit edildi.

## Yeniden üretmek istersen

Kendi orijinal RomFS dump'ından iki fontu tekrar üretmek için:

```bash
python araclar/patch_font_layeredfs.py --source-romfs "/orijinal/romfs" --region EUR --sd-root "/SD_KART_KOKU"
```

Araç iki fontu da üretir ve `FONT_PATCH_REPORT_v35.json` yazar.

## Doğrulama ölçütleri

`Reports/FONT_VERIFICATION_v35.json` şu kontrolleri içerir:

- DARC açılabiliyor mu?
- İç CFNT bulunuyor mu?
- FINF'den başlayan gerçek CMAP `next` zinciri takip edildiğinde `Ğ ğ İ ı Ş ş` bulunuyor mu?
- Glyph indeksleri TGLP kapasitesi içinde mi?
- Yeni glyph hücrelerinde görünür alpha pikseli var mı?
- Ortak ve `UI_en` fontları ayrı ayrı doğrulanıyor mu?

Bu doğrulama yalnız dosyayı lineer taramaz; oyunun kullandığı aktif CMAP zincirini takip eder.
