# Kirby Triple Deluxe Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen klasörü SD kartınızdaki `luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** seçeneğini etkinleştirin. Mevcut yamanızı değiştirmeden önce yedekleyin.

- `000400000010C000/` → `sd:/luma/titles/000400000010C000/`

Oyun EUR bölgesi içindir.

## Çeviri ve araçlar

`ceviri/MSBT_CSV/` içindeki tabloların `TR_Turkish` alanlarını düzenleyin. `kaynaklar/MSBT_SABLON/` üretim şablonlarını içerir.

Oyun klasöründe:

```text
python araclar/build_patch.py
python araclar/verify_package.py
```

Üretim çıktısı `calisma/uretim/` altındadır. Araç kurulum klasörüne metinleri de aktarır; üretmeden önce mevcut yamanızı yedekleyin. Font düzenleme ve kontrol araçları `araclar/` altındadır.

[Araçta kullanılan MSBT projesi](https://github.com/IcySon55/3DLandMSBTeditor)

## Açıklamalar

- [00 OKU BENI](belgeler/00_OKU_BENI.txt)
- [KURULUM VE CALISMA AKISI](belgeler/KURULUM_VE_CALISMA_AKISI.md)
- [kullanim notlari](belgeler/kullanim_notlari.md)
