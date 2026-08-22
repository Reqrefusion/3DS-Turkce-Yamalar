# Heroes of Ruin — Türkçe Yama ve Araçlar

Bu paket, sağlanan çok dilli Türkçe çevirilerden oluşturulmuş hazır STRL yamalarını, Türkçe karakter desteği eklenmiş `demo_font.bcfnt_` dosyasını ve yeniden çıkarma/paketleme araçlarını içerir.


## Hazır yama

Türkçe metinler İngilizce dil slotunun (`_UK`) üzerine hazırlanmıştır. Yedi ana metin dosyasının tamamı hazırdır:

- `buffs.strl_`
- `characterparts.strl_`
- `dialogues.strl_`
- `names.strl_`
- `quests.strl_`
- `strings.strl_`
- `weapons.strl_`

Toplam **6.824** Türkçe kayıt vardır.

### Luma3DS

`YAMA_HAZIR/Luma3DS_SD_KOKUNE_KOPYALA/` klasörünün **içeriğini SD kartın köküne** kopyalayın.

Sonuçta metin dosyaları şu yapıda olmalıdır:

`luma/titles/0004000000074000/romfs/_UK/*.strl_`

Luma ayarlarında **game patching** açık olmalıdır. Yama `_UK` slotunu değiştirdiği için oyun/sistem dili İngilizce olduğunda Türkçe metinler kullanılır.

### Azahar / Citra uyumlu mod klasörü

Oyunun mod klasörünü açın ve:

`YAMA_HAZIR/Azahar_Citra_Mod_Klasorune_Kopyala/romfs`

klasörünü doğrudan oyunun mod klasörüne kopyalayın. Manuel yapıda hedef genellikle:

`load/mods/0004000000074000/romfs`

olur.

### Doğrudan RomFS

Kendi RomFS yeniden paketleme akışınız varsa `YAMA_HAZIR/romfs/` içeriğini aynı göreli yollarla kullanabilirsiniz.

## Font

Sağlanan `demo_font.bcfnt_` BLZ ile sıkıştırılmış bir CFNT fontudur. Açıldığında:

- 95 temel ASCII glifi,
- 16 adet 32x32 A8 sheet,
- 9x13 glif hücreleri

bulunmuştur. Orijinal fontta Türkçe karakterler yoktur.

Paket içindeki yamalı `FONT/demo_font.bcfnt_` dosyasında glif sayısı **114**, sheet sayısı **19** olmuştur. Şu karakterler için yeni bitmap glifleri eklenmiştir:

`Â Ç Ö Ü â ç é î ö û ü Ğ ğ İ ı Ş ş … ⇒`

Ayrıca çeviride geçen şu tipografik karakterler mevcut ASCII gliflerine güvenli şekilde eşlenmiştir:

- NBSP → normal boşluk
- `–` / `—` → `-`
- `’` → `'`
- `“` / `”` → `"`

Böylece çeviride kullanılan **tüm ASCII-dışı kod noktaları font CMAP'inde karşılık bulur**.

### Font konumu hakkında önemli not

Yüklenen font dosyası bu sohbete yalnızca `demo_font.bcfnt_` adıyla geldi; orijinal RomFS içindeki göreli klasör yolu upload sırasında korunmadı. Bu nedenle hazır yama, uyumluluk için fontu hem RomFS köküne hem `UI/` altına, hem sıkıştırılmış (`.bcfnt_`) hem ham (`.bcfnt`) biçimde koyar.

Eğer kendi tam RomFS dump'ınızda `demo_font.bcfnt_` dosyasının gerçek yolunu görebiliyorsanız en kesin yöntem şudur:

```bash
cd ARACLAR
python font_romfs_bul_yama.py "ORIJINAL_ROMFS" "YAMALI_ROMFS"
```

Araç RomFS'de tek BCFNT bulursa yamalı fontu **aynı göreli yola** yazar.

Fontu tek başına yeniden üretmek için:

```bash
python hor_font_patch.py patch ../FONT/demo_font_orijinal.bcfnt_ ../FONT/demo_font.bcfnt_ --raw-output ../FONT/demo_font.bcfnt
```

Kontrol:

```bash
python hor_font_patch.py check ../FONT/demo_font.bcfnt_
```

## Çeviri kaynakları

`CEVIRI/translation_multilang/` altında her STRL için ayrı **CSV ve JSON** vardır:

- `buffs.csv` / `buffs.json`
- `characterparts.csv` / `characterparts.json`
- `dialogues.csv` / `dialogues.json`
- `names.csv` / `names.json`
- `quests.csv` / `quests.json`
- `strings.csv` / `strings.json`
- `weapons.csv` / `weapons.json`

Her satırda `EN | FR | DE | IT | ES | TR` karşılıkları yan yanadır.

## Yamayı yeniden oluşturma

Python 3.10+ yeterlidir; harici Python paketi gerekmez.

Windows:

`ARACLAR/YAMAYI_YENIDEN_OLUSTUR.bat`

Komut satırı:

```bash
cd ARACLAR
python build_patch.py
```

Bu işlem CSV çevirilerinden yedi STRL'yi yeniden üretir, fontu yeniden yamalar ve Luma/Azahar/ham RomFS klasörlerini oluşturur.

JSON kullanmak için:

```bash
python build_patch.py --input-format json
```

Başka bir mevcut dil slotunu Türkçeyle değiştirmek isterseniz:

```bash
python build_patch.py --slot _GE
```

## Diğer araçlar

`ARACLAR/hor_tool.py` içinde:

- BLZ açma / sıkıştırma
- STRL çıkarma / geri paketleme
- EN/FR/DE/IT/ES/TR yan yana çıkarma
- DARC çıkarma / sınırlı geri enjeksiyon
- BCLYT `txt1` metin çıkarma / oluşturma
- oyun yapısı analizi

komutları bulunur.

Örnek:

```bash
python hor_tool.py --help
python hor_tool.py multilang-extract "ROMFS" translation_multilang --csv
python hor_tool.py language-build ../CEVIRI/translation_multilang built_TR --input-format csv
```

## Otomatik doğrulama

Paket oluşturulurken şu kontroller başarılı geçti:

- 6.824 / 6.824 Türkçe kayıt STRL'ye yazıldı ve geri okundu.
- Boş TR satırı: 0.
- CSV/JSON TR farkı: 0.
- Korunan oyun token/değişken uyuşmazlığı: 0.
- Yedi STRL dosyası: 7/7 başarılı.
- Türkçe font glif eksikliği: 0.
- Çeviride kullanılan ASCII-dışı karakterlerden fontta eksik olan: 0.
- Font BLZ aç → sıkıştır → aç doğrulaması başarılı.
- Hazır Luma/Azahar/ham RomFS kopyaları byte-byte aynıdır.

Ayrıntılı sonuç: `RAPORLAR/yama_dogrulama.txt`.

## Dosya özeti

- `YAMA_HAZIR/` — doğrudan kullanıma hazır yama yapıları
- `CEVIRI/` — düzenlenebilir CSV/JSON ve kalite kayıtları
- `FONT/` — orijinal/yamalı font, glif haritası ve önizleme
- `ARACLAR/` — çıkarma, paketleme, font ve yama oluşturma araçları
- `RAPORLAR/` — teknik inceleme ve doğrulama sonuçları
