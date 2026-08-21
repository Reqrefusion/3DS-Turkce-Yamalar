# Araçlar

Tüm scriptler `Tools/` içindedir ve Python 3 içindir.

- `repack_bravely.py`: BIFF/XLS okuma, BTBF yeniden üretme, crowd.fs/index.fs paketleme.
- `build_common_v33.py`: Common_en çeviri/terminoloji katmanlarını uygular ve runtime dosyalarını üretir.
- `eventviewer_v33_tr.py`: EventViewer kaynak-string → Türkçe curated başlıklar.
- `shop_v33_tr.py`: dükkân replikleri.
- `parameter_v33_tr.py`: eşya/açıklama cümleleri için kontrollü bağlam kuralları.
- `misc_v33_tr.py`: sistem/komut/legacy exact-string düzeltmeleri.
- `bravely_ui_tools.py`: DARC, BCLYT, CFNT parse/patch/rebuild.
- `bclim_tools.py`: BCLIM decode/encode.
- `raster_patch_tools.py` + `raster_translations.py`: resme gömülü metin yamaları.
- `unique_bclim_index.json`: doğrulanmış raster occurrence indeksi. v3.2'de yanlışlıkla pakete konmamıştı; v3.3'te düzeltildi.
- `audit_final_v33.py`: runtime structural audit ve SHA-256.
- `prepare_layeredfs.py`: paket `romfs` içeriğini Title ID yoluna kurar; istenirse kaynak dump üzerinden fontu yeniden üretmek için de kullanılabilir. v3.4 runtime paketinde yamalı font zaten hazırdır.
- `patch_font_layeredfs.py`: orijinal `Graphics/UI_en/Font/Font` arşivinden `Ğ ğ İ ı Ş ş` CMAP/glyph yamasını yeniden üretmek için bağımsız araçtır.

## Gereksinimler

`python>=3.10`, `Pillow`, `numpy`, `opencv-python`. Raster render işlemleri için sistemde erişilebilir bir Unicode font gerekir; herhangi bir font dosyası bu pakete gömülmez.

Kurulum: `python -m pip install -r Tools/requirements.txt`

## Common_en'i yeniden üretme

Linux/macOS örneği:

```bash
BD_COMMON_SRC=/path/to/Common_en BD_COMMON_WORK=/tmp/bd/Common_en_rebuilt BD_COMMON_GAME_OUT=/tmp/bd/Common_en_gamefiles/Common_en BD_COMMON_AUDIT=/tmp/bd/COMMON_EN_AUDIT.json python Tools/build_common_v33.py
```

Windows PowerShell'de aynı değişkenler `$env:BD_COMMON_SRC=...` biçiminde ayarlanabilir.

## LayeredFS kurulumu ve fontu yeniden üretme

v3.4'te hazır LayeredFS ZIP'ini kullanıyorsanız ayrıca font üretmeniz gerekmez. Yeniden üretim/test için:

```bash
python Tools/prepare_layeredfs.py --source-romfs /path/to/original/romfs --region EUR --output /path/to/SD
```

Bu yol, paket içindeki runtime ağacını kopyalayıp fontu sizin orijinal dump'ınızdan tekrar üretir. Hazır v3.4 fontuyla sonuç binary olarak eşdeğer olmalıdır.
