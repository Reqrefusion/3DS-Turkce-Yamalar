# Font düzeltmesi — v3.5

## Sorun
v3.4 LayeredFS paketinde yalnızca `Graphics/UI_en/Font/Font` yamalanmıştı. Tam oyun dump'ında bundan bağımsız ikinci bir font arşivi daha var:

- `Graphics/UI/Font/Font` — ortak UI/metin fontu, 17×17 hücre, 128×128 LA4 sheet, 82 sheet
- `Graphics/UI_en/Font/Font` — İngilizce yerelleştirilmiş UI fontu, 14×14 hücre, 256×256 LA4 sheet, 14 sheet

3DS testinde Türkçe Extended-A karakterlerinin `?` görünmesi, aktif ekranların ortak fontu kullanmasıyla uyumludur. v3.5 iki fontu da doğrudan LayeredFS paketine ekler.

## Eklenen karakterler
Her iki CFNT'nin aktif FINF→CMAP zincirine şu Unicode karakterleri eklendi:

- U+011E `Ğ`
- U+011F `ğ`
- U+0130 `İ`
- U+0131 `ı`
- U+015E `Ş`
- U+015F `ş`

`Ç ç Ö ö Ü ü` zaten fontlarda vardı ve korunmuştur.

## Teknik yöntem
Yeni glyph'ler mevcut TGLP texture sheet'lerindeki boş hücrelere yazılır. Yeni glyph ölçüleri için CWDH uzantısı ve Unicode eşlemesi için CMAP scan uzantısı eklenir. Yeni CMAP/CWDH blokları yalnız dosyanın sonunda bulunmakla kalmaz; eski zincirin `next` alanlarına bağlanır. Doğrulayıcı FINF'den başlayıp CMAP zincirini gerçek oyun okuyucusunun yaptığı şekilde takip eder.

v3.5 patcher sabit glyph indekslerine veya 256×256 sheet varsayımına bağlı değildir; iki farklı font geometrisini de kaynak CFNT'den okur.

## Paket içi yollar
EUR paketinde iki dosyanın da bulunması gerekir:

`luma/titles/00040000000FC600/romfs/Graphics/UI/Font/Font`

`luma/titles/00040000000FC600/romfs/Graphics/UI_en/Font/Font`

## Doğrulama
`Reports/FONT_VERIFICATION_v35.json` içinde iki fontun SHA-256 değerleri, aktif Unicode→glyph eşlemeleri, glyph hücre boyutları ve görünür piksel sayıları bulunur.
