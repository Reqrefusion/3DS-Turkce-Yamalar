# Build Rehberi

## Gereksinimler

- Python 3.10 veya daha yeni
- Kendi Star Fox 64 3D kopyanızdan çıkarılmış `Resources.zip` veya `Resources/` klasörü
- Luma3DS ile oyun yaması kullanacaksanız game patching desteği

Harici Python paketi gerekmez.

## EUR build

```bash
python scripts/validate_translation.py
python scripts/build_luma_patch.py /path/to/Resources.zip --region EUR
```

Varsayılan çıktı:

```text
dist/StarFox64_3D_TR_Luma_EUR.zip
```

ZIP içinde:

```text
luma/titles/0004000000049100/romfs/Resources/*.msbt
```

## USA build

```bash
python scripts/build_luma_patch.py /path/to/Resources.zip --region USA
```

USA Title ID klasörü `0004000000049000` olarak oluşturulur. Kaynak metin SHA-256 eşleşmiyorsa build durur; farklı oyun sürümünün aynı metin indekslerine sahip olduğunu varsaymaz.

## Neden Resources.zip repoda yok?

Build sistemi yamanın kullanıcıya ait orijinal kaynaklardan üretilmesini amaçlar. Böylece repo özgün oyun binary dosyalarını taşımak zorunda kalmaz.
