# Pokémon Omega Ruby / Alpha Sapphire Türkçe Çeviri Araçları

Bu depo, Pokémon Omega Ruby / Alpha Sapphire metinlerini karşılaştırmalı olarak
çevirip tekrar oyun dosyalarına enjekte etmek için gerekli temel dosyaları içerir.

Paket özellikle sade tutulmuştur:

```text
ORAS_TR_GitHub_Sade_Paket_v46_TUR36/
├── README.md
├── comparison/
│   ├── 01_Text_Set_A.tsv
│   └── 02_Text_Set_B.tsv
└── tools/
    ├── ORAS_TR_Text_Tool.py
    ├── BASLAT.bat
    └── BASLAT.sh
```

## Karşılaştırmalı çeviri tabloları

`comparison/` klasöründeki TSV dosyaları v46 / TUR36 Türkçe çevirisiyle
senkronize edilmiş karşılaştırma tablolarıdır.

Sütunlar:

| Sütun | Açıklama |
|---|---|
| `entry` | GARC içindeki metin dosyası kimliği |
| `bit` | Metin bloğu kimliği |
| `line_id` | Satır kimliği |
| `Japanese_Kana` | Japonca kana sürümü |
| `Japanese_Kanji` | Japonca kanji sürümü |
| `Turkish` | Türkçe çeviri — düzenlenecek ana sütun |
| `French` | Fransızca referans |
| `Italian` | İtalyanca referans |
| `German` | Almanca referans |
| `Spanish` | İspanyolca referans |
| `Korean` | Korece referans |

Çeviri yaparken normalde yalnızca **`Turkish`** sütununu değiştirin.

`entry`, `bit` ve `line_id` sütunlarına dokunmayın. Bunlar metnin oyundaki
yerini belirlemek için kullanılır.

## Araç ne yapıyor?

`tools/ORAS_TR_Text_Tool.py` Omega Ruby / Alpha Sapphire'ın Gen 6 metin
GARC arşivlerini açar.

Araç:

1. `7` ve `8` klasörlerindeki dil GARC'larını okur.
2. GARC arşivlerini açar.
3. Gen 6 metin şifrelemesini çözer.
4. Dilleri aynı satırda karşılaştırmalı TSV'ye dönüştürür.
5. Düzenlenen `Turkish` sütununu tekrar şifreler.
6. Türkçe metni yeniden `7/3` ve `8/1` GARC dosyalarına paketler.

Karşılaştırmalı modda diğer dil sütunları yalnızca referanstır.
**Geri enjeksiyon sırasında sadece `Turkish` sütunu kullanılır.**

## Gereksinim

Python 3.10 veya daha yeni bir sürüm önerilir.

Windows'ta Python kurulurken **Add Python to PATH** seçeneğini açmak işleri
kolaylaştırır.

## En kolay kullanım — Windows

`tools/BASLAT.bat` dosyasına çift tıklayın.

Açılan pencerede varsayılan olarak:

**Karşılaştırmalı 8 dil (önerilen)**

seçeneği işaretlidir.

### 1. Metinleri çıkarma

**1) Metinleri Çıkar** düğmesine basın.

Araç sizden kaynak olarak şunlardan birini ister:

- `7` ve `8` klasörlerini içeren klasör
- veya bu klasörleri içeren ZIP dosyası

Çıktı için yeni bir proje klasörü seçin.

Projenin içinde `comparison/01_Text_Set_A.tsv` ve
`comparison/02_Text_Set_B.tsv` oluşur.

### 2. Çeviri

TSV dosyalarını UTF-8 destekleyen bir programla açın.

Örnek:

- Excel
- LibreOffice Calc
- VS Code
- Notepad++
- herhangi bir TSV editörü

Sadece **`Turkish`** sütunundaki metinleri düzenleyin.

Bu depoda bulunan hazır `comparison/*.tsv` dosyalarını kullanmak istiyorsanız,
araçla oluşturduğunuz projenin `comparison/` klasöründeki iki TSV'nin yerine
bu depodaki dosyaları kopyalayabilirsiniz.

### 3. Geri enjekte etme

GUI'de **2) Geri Enjekte / Paketle** düğmesine basın ve proje klasörünü seçin.

Araç yeni GARC dosyalarını oluşturur:

```text
7/3
8/1
```

Bunlar Türkçe metnin bulunduğu dil slotlarıdır.

## Komut satırı kullanımı

Grafik arayüz:

```bash
python tools/ORAS_TR_Text_Tool.py gui
```

8 dili karşılaştırmalı çıkar:

```bash
python tools/ORAS_TR_Text_Tool.py extract --compare KAYNAK.zip ORAS_TR_Project
```

Klasörden çıkarmak da mümkündür:

```bash
python tools/ORAS_TR_Text_Tool.py extract --compare ROMFS_KLASORU ORAS_TR_Project
```

Düzenlenen projeyi tekrar paketle:

```bash
python tools/ORAS_TR_Text_Tool.py build ORAS_TR_Project rebuilt
```

Projeyi kontrol et:

```bash
python tools/ORAS_TR_Text_Tool.py verify ORAS_TR_Project
```

## Kontrol kodlarına dikkat

Oyun metinlerinde normal yazı dışında kontrol kodları bulunabilir.

Örnekler:

```text
[VAR 1234]
[VAR 1234(0001,0002)]
[WAIT 30]
[~ 15]
\n
\r
\c
```

Bunlar isim, sayı, bekleme, satır geçişi veya metin kutusu davranışı gibi
işlevler için kullanılır.

Çeviri sırasında kontrol kodlarını mümkün olduğunca **aynen koruyun**.

Örneğin:

```text
Merhaba [VAR 0100]!
```

satırındaki `[VAR 0100]` kısmını silmek veya bozmak oyunda yanlış metin
gösterilmesine neden olabilir.

## Türkçe karakterler

Araç UTF-8 TSV kullanır ve aşağıdaki Türkçe karakterleri destekler:

```text
ç Ç
ğ Ğ
ı İ
ö Ö
ş Ş
ü Ü
```

Oyunda karakterlerin görünmesi ayrıca kullanılan font/yama tarafındaki glif
desteğine bağlıdır.

## İki metin grubu neden var?

ORAS dil metinleri tek GARC dosyasında tutulmadığı için çeviri iki ana
karşılaştırma tablosuna ayrılır:

- `01_Text_Set_A.tsv`
- `02_Text_Set_B.tsv`

İki dosya birlikte kullanıldığında v46 / TUR36 çalışmasındaki yaklaşık
45 bin hizalanmış metin satırını kapsar.

## Önemli

Araç doğrudan `.3ds` veya `.cia` dosyasını değiştirmez.

Çalışma mantığı:

```text
ROM / yedek
   ↓
çıkarılmış RomFS dil dosyaları
   ↓
ORAS_TR_Text_Tool
   ↓
TSV çeviri
   ↓
ORAS_TR_Text_Tool
   ↓
yeniden oluşturulan 7/3 ve 8/1
```

Kendi oyun yedeğiniz ve RomFS çıkarma/yama yönteminizle kullanmanız gerekir.

Her zaman değiştirmeden önce orijinal `7/3` ve `8/1` dosyalarının yedeğini
saklayın.

---

**Sürüm:** v46 / TUR36 karşılaştırma kaynakları  
**Araç:** ORAS TR Text Tool
