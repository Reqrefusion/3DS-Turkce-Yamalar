# İş Akışı

## Mevcut TR yamayı düzenleme

1. `data/current_patch/tr/fmes/json/per_msbt/*.json` altından ilgili dosyayı aç.
2. Gerekirse karşılaştırma için `data/languages/EU_*` altındaki aynı `.msbt.json` dosyalarına bak.
3. JSON değişikliği bittikten sonra:

```bash
python tools/message_msbt_toolkit.py import-container-json   data/current_patch/tr/fmes/FMes.bin   data/current_patch/tr/fmes/FMes.dat   data/current_patch/tr/fmes/json   build/FMes.bin   build/FMes.dat
```

4. Sonra doğrula:

```bash
python tools/message_msbt_toolkit.py verify-container-noop build/FMes.bin build/FMes.dat --out-json build/verify.json
```

## Tek dosya üstünden daha güvenli yöntem

Bazı durumlarda tüm container yerine yalnız değişen `.msbt` dosyasını düzenlemek daha güvenlidir.

```bash
python tools/message_msbt_toolkit.py export-standalone-json data/current_patch/tr/fmes/msbt/0068.msbt build/0068.json
python tools/message_msbt_toolkit.py import-standalone-json data/current_patch/tr/fmes/msbt/0068.msbt build/0068.json build/0068.msbt
```

Sonra bunu container akışına geri eklemek için önce `extract-container`, ardından sadece değişen `.msbt`yi değiştirip `repack-container` kullan.
