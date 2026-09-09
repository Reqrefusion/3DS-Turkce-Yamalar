# AR Games (CTR-N-HARP) Türkçe yerelleştirme projesi

Bu çalışma yüklenen EUR CXI üzerinde hazırlanmıştır. Tespit edilen Title ID: `0004001000022E00`.

## Dosya yapısı

Ana metinler `romfs/message/EU_*/AR_ACT.msbt` içindedir. Sekiz Avrupa dili aynı 354 mesaj indeksini/etiketini kullanır:

`EU_English`, `EU_Dutch`, `EU_French`, `EU_German`, `EU_Italian`, `EU_Portuguese`, `EU_Russian`, `EU_Spanish`.

`AR_ACT.msbt` içindeki LBL1/TXT2/TSY1 verileri ve `CPLAY_NCL_AR_ACT.msbp` içindeki SYL3 stil verileri araç tarafından okunur. CSV'de `RegionWidth`, `StyleLineLimit` ve resmi dillerden çıkarılan deneysel uzunluk ölçütleri bulunur.

MSBT kontrol kodları CSV'de geri dönüşümlü olarak saklanır:

- `[[C:GGGG:IIII:HEX]]` — kontrol/açılış etiketi
- `[[E:GGGG:IIII]]` — kapanış etiketi

Bunları çeviri sırasında değiştirmeyin.

## Kullanım

CXI'nin RomFS'ini çıkar:

```bash
python ar_games_tr_tool.py romfs-extract "oyun.cxi" romfs
```

Sekiz dili yan yana CSV'ye çıkar:

```bash
python ar_games_tr_tool.py csv-extract romfs ceviri.csv
```

Türkçe sütununu doldurduktan sonra doğrula:

```bash
python ar_games_tr_tool.py validate romfs ceviri.csv
```

Tek bir MSBT üret:

```bash
python ar_games_tr_tool.py inject romfs/message/EU_English/AR_ACT.msbt ceviri.csv AR_ACT_TR.msbt
```

LayeredFS ağacı üret:

```bash
python ar_games_tr_tool.py patch romfs ceviri.csv AR_Games_TR_LayeredFS --target EU_English
```

İstersen tüm sekiz EU dil klasörünü yamalayabilirsin:

```bash
python ar_games_tr_tool.py patch romfs ceviri.csv AR_Games_TR_LayeredFS_ALL --all-eu
```

Kalite kontrolü açısından hazır paket `EU_English` hedeflidir.

## Hazır çeviri hakkında

354 mesaj yuvasının 328'i dolu ve Türkçeye çevrilmiştir; 26 kaynak yuvası zaten boştur ve boş bırakılmıştır. Kontrol etiketi dizileri İngilizce kaynakla 354/354 eşleşir. MSBT yeniden paketleme ve tekrar okuma testi başarılıdır.

CSV'de yalnız iki metin görsel kontrol bayrağındadır: `Yılan Balığı` ve `Köpekbalığı`. Resmî dillerdeki karşılıklar çok kısa olduğu için karakter tabanlı yumuşak sınırı aşıyorlar; doğal Türkçeyi bozmak yerine cihaz/emülatör görsel testine bırakıldılar.

Türkçe `ğ/Ğ`, `ş/Ş`, `ı/İ` gliflerinin gerçek 3DS üzerinde doğru görünmesi ayrıca test edilmelidir.
