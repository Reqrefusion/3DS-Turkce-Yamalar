# Star Fox 64 3D Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen klasörü SD kartınızdaki `luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** seçeneğini etkinleştirin. Mevcut yamanızı değiştirmeden önce yedekleyin.

- `0004000000049100/` → `sd:/luma/titles/0004000000049100/`

Ana hedef EUR, `0004000000049100`; USA hedefi `0004000000049000` için kendi oyun kaynağınızdan ayrıca çıktı üretin. Oyunu İngilizce başlatın.

## Çeviri ve araçlar

Ana kaynak `ceviri/tr_TR.jsonl` dosyasıdır. Yalnız `translation` alanlarını düzenleyin; kontrol kodlarını koruyun. Komutları oyun klasöründe çalıştırın.

```text
python araclar/validate_translation.py
python araclar/build_luma_patch.py <Resources.zip> --region EUR
```

Özgün `Resources.zip` girdisini kendiniz sağlamalısınız. Çıktı `dist/` altında oluşturulur. Ayrıntılar: [üretim](belgeler/BUILDING.md), [çeviri biçimi](belgeler/TRANSLATION_FORMAT.md), [terminoloji](belgeler/TERMINOLOGY.md).

## Açıklamalar

- [BUILDING](belgeler/BUILDING.md)
- [GITHUB SETUP](belgeler/GITHUB_SETUP.md)
- [PROJECT STATUS](belgeler/PROJECT_STATUS.md)
- [RELEASE CHECKLIST](belgeler/RELEASE_CHECKLIST.md)
- [TERMINOLOGY](belgeler/TERMINOLOGY.md)
- [TESTING](belgeler/TESTING.md)
- [TRANSLATION FORMAT](belgeler/TRANSLATION_FORMAT.md)
- [kullanim notlari](belgeler/kullanim_notlari.md)
