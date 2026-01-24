# Kid Icarus Uprising Türkçe Yama

Yama avrupa sürümü içindir. 0004000000030200 dosyasında sadece menüler vardır tüm altyazılar ile birlikte tüm yamayı gamebananadan indirebilirsiniz.

Çeviride hatalar bulursanız tr klasörlerinden düzeltebilir veya issue açabilirsiniz. Yardımcı olması adına ingilizceyide bırakıyorum.

Yamanın uygulanması biraz zahmetli bin dosyalarının içinden msbtleri çıkartmak gerekiyor bunu yapmadan önce bazı dosyaların şifrelenmesinide çözmek gerekiyor. Bunun için iki adet phyton kodu ekliyorum.

Bunların kullanımları aşağıdaki gibidir.

## zrc_batch_lz11.py — Batch LZ11 Unpack / Pack (.zrc)

Bu script, bazı **Nintendo 3DS** oyunlarında (örn. *Kid Icarus: Uprising*) kullanılan **`.zrc`** dosyalarını toplu şekilde:

-  **LZ11 açma (decompress / unpack)**
-  Geri **LZ11 sıkıştırma (compress / pack)**

için hazırlanmıştır. fileciteturn1file0

`.zrc` dosyalarının bir kısmı **LZ11 (0x11)** ile sıkıştırılmış olur. Bu script, klasör içindeki `.zrc` dosyalarını tarar, LZ11 olanları açar ve düzenledikten sonra tekrar `.zrc` olarak paketler.

---

### Özellikler

- Klasörü **recursive** (alt klasörler dahil) tarar
- Sadece **LZ11 (0x11)** ile başlayan `.zrc` dosyalarını işler
- Decompress sonrası çıktı uzantısını otomatik tahmin eder:
  - `darc` → `.darc`
  - `SARC` → `.sarc`
  - diğer → `.bin`
- Pack aşamasında `_dec` içeren dosyaları tekrar `.zrc` yapar
- Hataları yakalayıp dosya bazlı log basar: `[OK]`, `[SKIP]`, `[FAIL]`

---



### Kullanım

> Windows’ta örnekler `py -3` ile verilmiştir. Linux/macOS için `python3` kullanabilirsin.

#### 1) Unpack — `.zrc` dosyalarını aç (decompress)

```bash
py -3 zrc_batch_lz11.py unpack "INPUT_FOLDER"
```

Örnek:

```bash
py -3 zrc_batch_lz11.py unpack "game_dump"
```

Bu komut:
- `INPUT_FOLDER` içinde `*.zrc` arar
- LZ11 (0x11) ise açar
- çıktıyı otomatik bir klasöre yazar:

✅ **Çıktı klasörü:**
```
INPUT_FOLDER_DEC_OUT
```

Örnek:
```
game_dump_DEC_OUT/
```

---

#### 2) Pack — açılmış dosyaları geri `.zrc` yap (compress)

```bash
py -3 zrc_batch_lz11.py pack "DECOMPRESSED_FOLDER"
```

Örnek:

```bash
py -3 zrc_batch_lz11.py pack "game_dump_DEC_OUT"
```

Bu komut:
- `DECOMPRESSED_FOLDER` içinde **adı `_dec` içeren** dosyaları bulur
- LZ11 olarak sıkıştırıp `.zrc` üretir
- çıktıyı otomatik bir klasöre yazar:

✅ **Çıktı klasörü:**
```
DECOMPRESSED_FOLDER_PACKED_ZRC
```

Örnek:
```
game_dump_DEC_OUT_PACKED_ZRC/
```

---

### Çıktı yapısı

#### Unpack sonrası

Input:
```
game_dump/
└─ data/
   └─ sample.zrc
```

Output:
```
game_dump_DEC_OUT/
└─ data/
   └─ sample_dec.bin   (veya .darc / .sarc)
```

> Script, dosya adının sonuna otomatik olarak `_dec` ekler.

#### Pack sonrası

Input:
```
game_dump_DEC_OUT/
└─ data/
   └─ sample_dec.bin
```

Output:
```
game_dump_DEC_OUT_PACKED_ZRC/
└─ data/
   └─ sample.zrc
```

> Script, pack sırasında isimdeki `_dec` son ekini kaldırıp `.zrc` olarak yazar.

---

### Hangi dosyayı düzenleyeceğim?

Unpack sonrası düzenlemen gereken dosyalar:

- `*_dec.bin`
- `*_dec.darc`
- `*_dec.sarc`

Örnek:
```
game_dump_DEC_OUT/data/sample_dec.darc
```

Düzenlemeyi bitirince `pack` komutunu çalıştırıp tekrar `.zrc` üretirsin.

---

### Konsol mesajları ne anlama geliyor?

#### `[OK]`
İşlem başarılı.

Örnek:
```
[OK]  data/sample.zrc -> data/sample_dec.bin  (12345 bytes)
```

#### `[SKIP] LZ11 degil (0x11 yok)`
Dosya `.zrc` olsa bile LZ11 ile başlamıyordur → script bunu pas geçer.

Bu normaldir; her `.zrc` mutlaka LZ11 olmayabilir.

#### `[FAIL] ... -> <hata>`
Dosya okunamadı, bozuk olabilir veya içerik beklenenden farklı olabilir.

---

### Sık sorunlar ve çözümleri

#### “Bu klasörde .zrc bulunamadı”
- Yanlış klasör seçmiş olabilirsin
- Dosyalar alt klasörlerde değilse doğru yeri ver

#### “Bu dosya LZ11 (0x11) ile başlamıyor”
- Dosya `.zrc` ama LZ11 değil
- `[SKIP]` olarak geçmesi normal

#### Pack çalışıyor ama çıktı yok / çok az dosya işliyor
Pack modu, sadece **adı `_dec` içeren** dosyaları toplar.
- Unpack çıktısını değiştirdiysen dosya adında `_dec` kaldığından emin ol
- `_dec` yazmayan dosyalar pack listesine girmez

---

### Önerilen akış

1) Unpack:
```bash
py -3 zrc_batch_lz11.py unpack "game_dump"
```

2) Çıktıları düzenle:
```
game_dump_DEC_OUT/**/ *_dec.*
```

3) Pack:
```bash
py -3 zrc_batch_lz11.py pack "game_dump_DEC_OUT"
```

4) Üretilen `.zrc` dosyaları burada:
```
game_dump_DEC_OUT_PACKED_ZRC/
```

---

### Notlar

- Script sadece **LZ11 (0x11)** formatını hedefler.
- Decompress tarafı bazı “uzun boyut header” varyantlarını da destekler.
- Çok büyük projelerde hız/performans için önce küçük klasörde test etmen önerilir.

---

## MSBT Bulk Extract / Restore (MsgStdBn)

Bu proje, bazı **Nintendo 3DS** oyun dosyalarının (`.bin` vb.) içinde **gömülü** duran **MSBT (MsgStdBn)** bloklarını:

- **Toplu çıkarma (extract)**
- Düzenledikten sonra **aynı dosyaya geri gömme (restore)**

işlemleri için hazırlanmış bir Python scriptidir.

> Script “repack / yeniden paketleme” yapmaz. Sadece mevcut MSBT bloğunu **aynı offset ve aynı alan** içinde günceller.

---

### Özellikler

- Klasörleri **alt klasörlerle birlikte** tarar (recursive)
- Dosyalarda `MsgStdBn` imzasını bulup MSBT bloklarını çıkarır
- Çıkarılan her MSBT için `msbt_index.json` üretir (restore bununla çalışır)
- Restore sırasında güvenlik kontrolleri:
  - Kaynak dosya değişmişse **SHA1 uyarısı**
  - MSBT **büyüdüyse restore ETMEZ**
  - MSBT küçüldüyse **0x00 ile padding** yapar
  - Offset’te `MsgStdBn` yoksa yazmaz (offset kaymış olabilir)

---

### Gereksinimler

- **Python 3.8+**
- Ek bağımlılık yok

---

### Kurulum

```bash
git clone <repo-url>
cd <repo-klasoru>
```

---

### Kullanım

Genel format:

```bash
python msbt_bulk.py <extract|restore> -i "INPUT_FOLDER" -o "OUT_FOLDER"
```

> Path içinde boşluk varsa tırnak kullan (`"..."`).

---

### Extract (MSBT çıkarma)

```bash
python msbt_bulk.py extract -i "./game_dump" -o "./msbt_out"
```

Bu komut:
- `./game_dump` içini tarar
- Bulduğu MSBT bloklarını `./msbt_out` içine yazar
- `./msbt_out/msbt_index.json` oluşturur

---

### Restore (MSBT geri gömme)

```bash
python msbt_bulk.py restore -i "./game_dump" -o "./msbt_out"
```

Bu komut:
- `./msbt_out/msbt_index.json` okur
- Düzenlediğin `.msbt` dosyalarını alıp **INPUT_FOLDER içindeki** kaynak dosyaya geri yazar

**Restore IN-PLACE çalışır:** `INPUT_FOLDER` içindeki dosyalar doğrudan güncellenir.  
Yedek almak önerilir.

---

### Çıktı yapısı

Extract sonrası örnek:

```
msbt_out/
├─ msbt_index.json
└─ data/
   └─ __msbt__/
      ├─ message.bin__00__0x00012A40.msbt
      └─ message.bin__01__0x00018F10.msbt
```

Dosya adı formatı:

```
<orijinal_dosya>__<sıra>__0x<OFFSET>.msbt
```

- `sıra`: aynı dosyada kaçıncı MSBT
- `OFFSET`: kaynak dosya içindeki başlangıç konumu

---

### Hangi dosyaları düzenleyeceğim?

Düzenleyeceğin dosyalar:

- `OUT_FOLDER/**/__msbt__/*.msbt`

`msbt_index.json` genelde elle değiştirilmez.

---

### Sık hatalar ve ne yapmalı?

#### `Boyut büyümüş!`
**Sebep:** Düzenlediğin `.msbt` orijinalden büyük.  
**Çözüm:** Metni kısalt / gereksizleri temizle. Bu script büyüyen MSBT’yi yazmaz.

#### `MSBT yok`
**Sebep:** Index’teki `.msbt` dosyası bulunamadı (silinmiş/taşınmış).  
**Çözüm:** Dosyayı eski yerine koy veya yeniden `extract`.

#### `Source yok`
**Sebep:** Restore’ın yazacağı kaynak dosya `INPUT_FOLDER` içinde yok.  
**Çözüm:** `-i` parametresini doğru dump klasörüne ver.

#### `Orijinal offsette MsgStdBn yok`
**Sebep:** Dosya değişmiş/offset kaymış olabilir.  
**Çözüm:** Aynı dump üstünde çalış veya yeniden `extract`.

#### `SHA1 farklı (uyarı)`
**Sebep:** Kaynak dosya extract zamanından farklı.  
**Çözüm:** Mümkünse aynı dump’ı kullan, gerekirse yeniden extract al.

---

### Önerilen akış

1) Extract:
```bash
python msbt_bulk.py extract -i "./game_dump" -o "./msbt_out"
```

2) Şunları çevir/düzenle:
```
./msbt_out/**/__msbt__/*.msbt
```

3) Restore:
```bash
python msbt_bulk.py restore -i "./game_dump" -o "./msbt_out"
```

---


