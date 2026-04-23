# DreamTeam MSBT Translation Workflow

Bu repo, MSBT tabanlı çeviri iş akışı için temiz çalışma alanıdır.

## İçerik

- `tools/`:
  - `message_msbt_toolkit.py` — container/MSBT/JSON iş akışı
  - `tr_name_localizer.py` — özel ad ve kelime oyunu yerelleştirme scripti
- `data/languages/`:
  - tüm EU dilleri için FMes container dosyaları
  - FMes içinden çıkarılmış ham `.msbt` dosyaları
  - her MSBT için ayrı JSON ve toplu `all.json`
  - bağımsız `.msbt` dosyaları
  - doğrulama raporları
- `data/current_patch/tr/`:
  - mevcut çalışan TR yama paketi
  - bu paketin FMes `.bin/.dat` dosyaları
  - FMes içinden çıkarılmış ham `.msbt` dosyaları
  - JSON yedekleri
  - değişiklik ve doğrulama raporları
- `reports/`: genel doğrulama özetleri

## Klasör düzeni

Her dil klasöründe aynı yapı kullanılır:

```text
<data/languages/LANG>
├── fmes/
│   ├── FMes.bin
│   ├── FMes.dat
│   ├── msbt/
│   └── json/
│       ├── all.json
│       └── per_msbt/
├── standalone_msbt/
└── verify_report.json
```

## Temel kullanım

### 1) FMes container'ı çıkar
```bash
python tools/message_msbt_toolkit.py extract-container data/current_patch/tr/fmes/FMes.bin data/current_patch/tr/fmes/FMes.dat out/extracted
```

### 2) FMes container'ı JSON'a dök
```bash
python tools/message_msbt_toolkit.py export-container-json data/current_patch/tr/fmes/FMes.bin data/current_patch/tr/fmes/FMes.dat out/json
```

### 3) JSON'dan tekrar FMes üret
```bash
python tools/message_msbt_toolkit.py import-container-json data/current_patch/tr/fmes/FMes.bin data/current_patch/tr/fmes/FMes.dat out/json out/FMes.bin out/FMes.dat
```

### 4) No-op doğrulama yap
```bash
python tools/message_msbt_toolkit.py verify-container-noop data/current_patch/tr/fmes/FMes.bin data/current_patch/tr/fmes/FMes.dat --out-json out/verify.json
```

### 5) Tek bir MSBT'yi JSON ile düzenle
```bash
python tools/message_msbt_toolkit.py export-standalone-json data/current_patch/tr/fmes/msbt/0653.msbt out/0653.json
python tools/message_msbt_toolkit.py import-standalone-json data/current_patch/tr/fmes/msbt/0653.msbt out/0653.json out/0653.msbt
```

## Çalışma kuralı

1. Önce `fmes/msbt/` içindeki ham `.msbt` dosyasıyla çalış.
2. JSON'u yedek ve düzenleme formatı olarak kullan.
3. Değişmeyen girdilerde `raw_full_hex` korunur.
4. Her importtan sonra `verify-container-noop` veya tekrar export karşılaştırması yap.
5. Özel ad çevirilerinde diğer dillerle kıyas yapmadan karar verme.

## Not

Bu repo içinde dosya adları bilerek sade tutuldu. Sürüm etiketi yerine klasör ve rapor üzerinden takip yapman daha güvenli olur.
