# Kirby's Extra Epic Yarn — Türkçe CSV Toolkit (Güvenli Final)

Bu sürüm GUI içermez. Ana çalışma dosyası `data/Kirby_TR_translated.csv` dosyasıdır.

## Bu finalde ne değişti?

- Kaynaktaki **2.238 etiket**, 10 dil sütunuyla birlikte yeniden çapraz kontrol edildi.
- Hedef ROM Avrupa `(E)` olduğu için zamanlanmış metin yapısında **EU_English kanonik yapı** olarak kullanılır.
- Fransızca, Almanca, İtalyanca, İspanyolca, US İngilizce, Japonca ve Korece sütunları anlam/terim doğrulaması için kullanılır.
- EU İngilizce'de bilerek boş olan 4 zamanlanmış yuva (`SD002_018`, `SD003_011`, `SD009_002`, `MSG_BOX_TEST`) **boş bırakılır**. Başka locale'deki farklı cümleler bu yuvalara taşınmaz.
- Tüm 10 `message/<locale>/fluff.msbt` dosyasına aynı kanonik Türkçe set enjekte edilir; böylece sistem dili değişse de Türkçe metin kullanılır.
- `test_sample.msbt` dosyaları Türkçe font/test metnine çevrilir.
- `exefs/icon.bin` içindeki düz HOME Menu başlığı ve `exefs/code.bin` içindeki düz oyun adı Türkçeleştirilir.
- **`exefs/banner.bin` değiştirilmez.** Stilize orijinal logo yaklaşık biçimde yeniden çizilmedi; final pakette banner kaynakla byte-byte aynıdır.

## Uzunluk / ekran taşması denetimi

Eski kontrol yalnız karakter sayısına dayanıyordu. Bu sürümde `GameFont1.bffnt` ve `GameFont2.bffnt` içindeki gerçek `CWDH` advance genişlikleri okunur.

- Her Türkçe satırın piksel genişliği iki font için muhafazakâr biçimde ölçülür.
- Etiket ailesinin 8 Latin-kaynak locale'inde gerçekten kullanılan en geniş satır referans kapasite kabul edilir.
- Satır sayıları da kaynak locale'lerde gözlenen yapıyla karşılaştırılır.
- Son denetimde **>%5 genişlik veya fazla satır uyarısı: 0**.
- Türkçe metinlerde iki font için **eksik glif: 0**.

Ayrıntılar:
- `reports/layout_pixel_audit.csv`
- `reports/cross_language_audit_v2.txt`
- `reports/full_validation_v2.json`

## Önemli çapraz-dil düzeltmeleri

Çapraz kontrolde bölgesel çevirilerin bazı yerlerde ciddi biçimde ayrıldığı görüldü. Finalde örneğin:

- `Quilty Square` → **Yorgan Meydanı**
- `Small/Large Chest` diğer dillerde açıkça dresser/commode olduğundan → **Küçük/Büyük Şifonyer**
- yatay çizgi desenlerinde US metnindeki `Border` ifadesi Japonca `ボーダー` ile birlikte değerlendirilip gerçek anlamı **yatay çizgili** olarak korundu
- `Grey/Black` uyuşmazlığında Avrupa ROM'u için EU kaynak önceliğiyle **Gri Çizgili** kullanıldı
- `Dusk Dunes` ve JP/KR gece anlamı birlikte değerlendirilerek daha kısa **Akşam Kumulları** seçildi
- müzik listesindeki gereksiz `Teması` ekleri, US/JP/KR adlandırmasıyla uyumlu ve daha kısa olacak şekilde kaldırıldı
- bazı yardım/sistem metinleri aynı anlam korunarak daha kısa satırlara bölündü

Tüm değişikliklerin önce/sonra dökümü `reports/translation_changes.csv` içindedir.

## Kullanım

### CSV doğrulama

```bat
01_validate_csv.bat
```

### Font kontrolü

```bat
04_font_check.bat
```

### Tüm 10 dil + düz HOME başlıkları için güvenli final ZIP

```bat
05_build_full_all_languages.bat
```

Çıktı:

`output/Kirby_Extra_Epic_Yarn_TR_FINAL_SAFE.zip`

Bu çıktı **stilize bannerı değiştirmez**.

### Tüm 10 dil için Luma3DS LayeredFS

```bat
06_build_layeredfs_all_languages.bat
```

Çıktı:

`output/layeredfs_all/luma/titles/00040000001D1F00/romfs/message/...`

### Son tam doğrulama

```bat
07_validate_full.bat
```

Başarılı finalde `all_critical_checks_pass: true` ve `pixel_warning_count: 0` görülmelidir.

## Dosyalar

- `data/Kirby_TR_translated.csv` — 10 kaynak dil yan yana + kanonik Türkçe
- `data/translations_tr.json` — etiket → Türkçe yeniden derleme sözlüğü
- `tools/refine_translation.py` — çapraz dil/uzunluk revizyonlarını yeniden uygular
- `tools/cross_language_audit.py` — 10 dil farklarını ve gerçek font genişliklerini denetler
- `tools/full_validate.py` — MSBT, placeholder, kontrol kodu, font, banner bütünlüğü ve çıktı doğrulaması
- `ktl/` — MSBT/BFFNT/enjeksiyon araçları
- `reports/translation_changes.csv` — finalde değişen Türkçe satırlar
- `reports/layout_pixel_audit.csv` — piksel genişliği sonuçları
- `reports/cross_language_audit_v2.txt` — locale fark raporu
- `reports/full_validation_v2.json` — makine tarafından okunabilir final doğrulama

## Sınır

Bu denetim kaynak ZIP'te bulunan dosyaları kapsar. Gerçek cihaz/emülatör üzerinde görsel test, özellikle oyun motorunun dinamik ölçekleme veya farklı metin kutusu davranışları için yine son kalite adımıdır. Ancak önceki karakter-sayısı kontrolünden farklı olarak bu sürüm gerçek BFFNT advance genişliklerini kullanır ve kaynak locale'lerde gözlenmiş metin genişliklerinin dışına taşan >%5 bir Türkçe satır bırakmaz.


## Mizah / kelime oyunu son denetimi

Bu sürümde hikâye, karakter açıklamaları, desen/eşya açıklamaları ve adlandırmalar ayrıca mizah açısından 10 dil ile çapraz kontrol edildi. Dil bağımlı şakalar düz çevrilmek yerine Türkçede çalışan eşdeğerlerle uyarlandı. Örnekler: `sock it to you` → `Başına bir çorap öreyim mi?`, `show you the ropes` → `işin iplerini göstereyim`, UFO açılımı → `Uzay Figürlü Oturaklar`. Kötü karakter `Yin-Yarn`, diğer resmi dillerin de yaptığı gibi kelime oyununu korumak için `Yün-Yang`; `Prince Fluff` ise `Prens Tiftik` olarak yerelleştirildi.

Stilize HOME Menu bannerı değiştirilmez; kaynak `banner.bin` byte-byte korunur.
