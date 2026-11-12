# Fire Emblem Awakening — Pass242–Pass243 Kalite ve Yama Raporu

Tarih: 2026-11-12
Kapsam: Türkçe çevirinin F/G/I/S/U resmi dilleriyle ve Patriots Türkçesiyle satır satır karşılaştırılması, kalite düzeltmeleri ve çalışır Luma/m yamasının üretilmesi.

## 1. Özet

- 854 CSV dosyası ve 15.817 kayıt doğrulandı.
- Türkçe dolu kayıt: 14.931; boş kayıt: 886. Boş Türkçe hücrelerin tamamı kaynak U sütununda da boş.
- Pass242'de 113 metin düzeltildi; Pass243'te 72 ek düzeltme yapıldı. **Toplam 185 metin düzeltmesi.**
- Pass243 tam denetiminde 14.931 satırın tamamı F/G/I/S/U ve Patriots Türkçesine karşı otomatik olarak karşılaştırıldı; yüksek riskli tüm adaylar tek tek okundu.
- Pass243 düzeltmeleri: 19 eksik cümle/ifade, 4 yanlış anlam/nüans, 5 eksik UI etiketi, 2 İngilizce kalıntı, 42 uzunluk/satır düzeni.
- Kontrol kodu taraması temiz: `remaining_non_G=0`, `G_rows=124`, `sbp_empty=0`, `bad_color=0`, `unknown={}`.
- Çapraz dil taraması: `tr_vs_u_mismatch=0`, `tr_matches_no_source=0`, `e_comma_rows=0`, `g_only_rows=124`.
- Token-aware kalite taraması: gerçek çevrilmemiş prose 0; aynı kalan metinler film başlığı, isim/credits ve "Emm..." ünlemidir.
- Altı fontun tamamında 12/12 Türkçe glif gerçek `.bfnt.lz` içinde doğrulandı.
- Kurulabilir yama `000400000009F100/romfs` altında üretildi ve CSV ile birebir doğrulandı.

## 2. Karşılaştırma Yöntemi

Kanunî kaynak: `ceviri/project_normalized_with_manifest/csv/`.
Sütun düzeni: `index,key,F,G,I,S,U,TR` (UTF-8 BOM + CRLF, hücre içi kırıklar dahil).

Karşılaştırmalar:

1. **Kontrol kodu iskeleti**: TR ile U (ve F/G/I/S) arasında `$Wm`, `$Ws`, `$Wa`, `$E`, `$G`, `$Svp`, `$k`, `$p`, `$b`, `$Nu` gibi kodların çoklu küme eşitliği.
2. **Çapraz dil tutarlılığı**: TR'nin en az bir resmi dille kod iskeleti eşleşmesi; hiçbir kaynakla eşleşmeyen satırların ayıklanması.
3. **Görünür metin karşılaştırması**: Kodlar söküldükten sonra U ile birebir aynı kalan İngilizce prose.
4. **Satır genişliği**: Kodlar sökülerek en uzun görünür satır uzunluğu; F/G/I/S/U dağılımlarıyla kıyas.
5. **Kısa çeviri oranı**: TR görünür uzunluğunun U'ya oranı; yarım kalmış çeviri adayları.
6. **Noktalama/biçim taraması**: Harf + boşluk + noktalama, tekrarlanan kelime, renk kodu ve `$Sbp` boş parametre kontrolleri.
7. **Patriots eşleştirmesi**: `patriotsceviri/00040000000A0500/romfs/m/E` içindeki Türkçe metin, dosya adı + anahtar + sıra bazında hizalandı. 14.793 satır birebir eşleşti; 138 satır Patriots'ta bulunmayan 10 dosyada; 741 satırda Patriots yalnızca Japonca kalmıştı. Bu satırlar U/F/G/I/S üzerinden doğrulandı.
8. **Çok ölçütlü karşılaştırma**: Patriots ve U için karakter benzerliği, içerik kelime Jaccard/kosinüs, uzunluk oranı, cümle sayısı, sayı kümesi ve İngilizce kalıntı taraması birlikte kullanıldı.

## 3. Bulgular ve Düzeltmeler

### 3.1 Uygulanan düzeltmeler

- Pass242: 113 metin düzeltmesi.
  - 92 dosyada 99 değişiklik (73 `Ve` calque kalıbı, 1 "Bir kaç" ve diğer net hatalar).
  - 13 dosyada 14 ek net hata düzeltmesi.
  - Doğal `Ve` kullanımları korundu; `$G` ve satır sonu farkları toplu değiştirilmedi.
- Pass243: 52 dosyada 72 metin düzeltmesi.
  - 19 eksik cümle/ifade tamamlandı.
  - 4 yanlış anlam/nüans düzeltildi.
  - 5 eksik UI etiketi tamamlandı: "Müzik" → "Müzik Sesi", "Sistem" → "Sistem Sesi", "Efekt" → "Efekt Sesi", "Morgan (M)/(F)" → "Morgan (E)/(K)".
  - 2 İngilizce kalıntı Türkçeye çevrildi: "HEEEEEELP!" → "İMDAAAAT!", "Let's" → "Sonra kutlarız."
  - 42 satırda uzunluk/satır düzeni düzeltildi: 400 px üstü satırlar bölündü, normal kutuya sığmayan replikler kısaltıldı.
- **Toplam: 185 metin düzeltmesi.**

### 3.2 Bilinçli olarak değiştirilmeyenler

- Doğal `Ve` kullanımları korundu.
- `$G` kod farkları ve satır sonu (`\r\n`) farkları toplu olarak değiştirilmedi; yalnızca bağlamı doğrulanan net hatalar düzeltildi.
- 39 satırda U/TR boşken İtalyanca (bazen F/G/S) dolu; bunlar kullanılmayan PCF2/PCF3 varyantları olarak bırakıldı.

### 3.3 Aynı kalan metinler

Ham olarak U ile aynı görünen 1.502 eşleşmenin çoğu isim, credits ve onomatopoeia'dır. Token-aware taramada gerçek çevrilmemiş İngilizce prose sayısı **5**'tir:

- `007.csv` / `MID_007_ED1_05` — "Emm... Emm?! Ah..." (ünlem/onomatopoeia)
- `013.csv` / `MID_013_MOVIE1` — film başlığı
- `013.csv` / `MID_013_MOVIE2` — film başlığı
- `021.csv` / `MID_021_OP2_ムービー` — film başlığı
- `023.csv` / `MID_023_MOVIE1` — film başlığı

### 3.4 Kısa çeviriler

Pass243 sonrası hem U'dan hem Patriots'tan %30+ kısa kalan 18 satırın tamamı tek tek incelendi. Kalanlar kompakt ama doğal çevirilerdir (ör. "İşi bitti." → "That's the end of him."). Pass243'te bu grupta bulunan gerçek eksikler ayrıca düzeltildi.

### 3.5 Pass243 tam denetim bulguları

Pass243'te önceki otomatik taramaların kaçırdığı gerçek hatalar bulundu ve düzeltildi:

- **Eksik cümle/ifade (19):** Flavia'nın "Annen gibi iyi bir dövüşü seviyorsun!", Vaike'nin "Her rol modeli öyle yapmalı!", Cynthia'nın "Ben de seni seviyorum.", Lissa'nın "Senin gibi... Hayalimsin, Emm!", Basilio'nun "Özellikle benim için.", Say'ri'nin "Hayatta kalacağına yemin et, aşkım." gibi ifadeleri.
- **Yanlış anlam/nüans (4):** Dejerel'in "Bir çözüm bulursun" yerine "Bulabileceğin her kadından daha güçlüyüm"; Chambray'ın "Benden saklama" yerine "Bir şeyin şıngırdadığını duyuyorum"; Chambray'ın tavşan kulakları repliği; Henry'nin "talim" yerine "sahte savaş".
- **Eksik UI etiketi (5):** `Menu.csv` "Müzik" → "Müzik Sesi", "Sistem" → "Sistem Sesi", "Efekt" → "Efekt Sesi", "Morgan (M)/(F)" → "Morgan (E)/(K)".
- **Uzunluk/satır düzeni (42):** piksel bazlı taramada normal kutu sınırını aşan satırlar bölündü veya kısaltıldı; sayfa başına satır sayısı resmi dillerin üstüne çıkarılmadı.
- **İngilizce kalıntı (2):** `P002.csv` "HEEEEEELP!" → "İMDAAAAT!"; `マイルーム挨拶.csv` "Let's celebrate later" → "Sonra kutlarız."
- **İncelenen ama değiştirilmeyenler:** `Lord`/`General` (unvan/rütbe), `Ambrosia`/`Argent`/`Astral` (özel isim/terim), `Bonjour`/`mes amis`/`Moi` (Anna'nın Fransız aksanı), `Heh`/`Hee`/`Hah`/`Mmm`/`Nngh` (kahkaha/ünlem) ve `Gah`/`Ugh`/`Tsk`/`Argh`/`Eek`/`Oof`/`Huh` (ses efekti). Bunlar çevrilmemiş prose değildir; istenirse ayrı bir ünlem Türkçeleştirme turu yapılabilir.

Denetim kapsamı:

- 14.931 TR satırının tamamı U ve Patriots ile karşılaştırıldı.
- 14.793 satır Patriots anahtarıyla birebir eşleşti; 138 satır Patriots'ta olmayan dosyalarda; 741 satırda Patriots Japonca kaldığı için U/F/G/I/S referans alındı.
- 59 kısa/uzun satır, 45 eksik adayı, 28 çok düşük örtüşmeli uzun satır, 10 aynı kalan prose, 28 sayı adayı, 40 anlam farkı örneği ve tüm İngilizce kelime/ünlem taraması tek tek okundu.
- Kalan farkların çoğu eşanlamlı/üslup farkı veya Patriots'un kendi çeviri tercihidir; bunlar hata olarak değiştirilmedi.

### 3.6 Satır genişliği dağılımı

| Dil | n | Medyan | p90 | p95 | p99 | Max |
|-----|---|--------|-----|-----|-----|-----|
| F | 14.020 | 35 | 84 | 90 | 119 | 165 |
| G | 13.989 | 35 | 83 | 88 | 115 | 189 |
| I | 14.096 | 32 | 80 | 87 | 114 | 203 |
| S | 14.157 | 32 | 81 | 86 | 116 | 155 |
| U | 14.931 | 31 | 79 | 84 | 111 | 159 |
| TR | 14.931 | 33 | 76 | 83 | 108 | 164 |

TR dağılımı U ile uyumlu; p90/p95/p99 değerleri U'dan düşük, yani taşma riski artmamıştır.

## 4. Yapısal ve Metin Doğrulaması

```
files=854 records=15817
tr_filled=14931 tr_exact=14931 fallback_u=886
count_mismatch=0 key_mismatch=0 value_mismatch=0
patch_files=860
errors=0
RESULT=PASS
```

Pass243 toplamı: 72 metin / 52 dosya. Son artımlı üretimde 26 metin / 19 dosya güncellendi. Pass243 düzeltmeleri sonrası yama klasörü CSV ile birebir eşleşiyor.

Ek kontroller:

- CSV bütünlüğü: `files=854 data_rows=15817 bad=0`.
- TR dolu: 14.931; TR boş ve U boş: 886; TR boş ama U dolu: 0.
- Manifest: `turkish_file_count=854`, `turkish_row_count=14931`.
- Kod taraması: `remaining_non_G=0 G_rows=124 sbp_empty=0 bad_color=0 unknown={}`.
- Çapraz dil: `tr_vs_u_mismatch=0 tr_matches_no_source=0 g_only_rows=124 e_comma_rows=0`.

## 5. Font Doğrulaması

`glyphs.csv` dökümleri eski olduğu için güvenilmedi. Doğrulama gerçek `.bfnt.lz` dosyaları üzerinden `fea_font_tool.py turkish-report` ile yapıldı.

Altı fontta (System, UI_L, UI_M, UI_S, Debug, ank) 12/12 glif OK:

`Ç Ğ İ Ö Ş Ü ç ğ ı ö ş ü`

## 6. Üretilen Yamalar

Kaynak/şablon: `000400000009F100/romfs` (tek dilli U dosya düzeni; `06_REFERENCE_INPUTS/m.zip` mevcut değil).
Pass243 üretimi: 72 metin / 52 dosya güncellendi; 886 boş TR hücresi U fallback ile yazıldı. Yama toplam 14.931 Türkçe kayıt içeriyor.

**Kurulabilir yama konumu:** `000400000009F100/romfs/`

- 860 dosya: 854 `.bin.lz` + 6 `.bfnt.lz`
- CSV ile birebir: `files=854 records=15817 tr_filled=14931 tr_exact=14931 fallback_u=886`
- `count_mismatch=0 key_mismatch=0 value_mismatch=0`
- Üretim sırasında staging ve Luma ZIP içeriği yama klasörüyle birebir doğrulandı.

Depoda yalnızca kurulabilir yama klasörü tutulur. `m_TR_Pass202_full.zip` ve `FEA_TR_Pass202_Luma.zip` isteğe bağlı ara çıktılardır; varsayılan olarak sistem geçici klasörüne üretilir ve depoda saklanmaz. Saklamak için `--out <klasör>` kullanın. ZIP girişleri sabit zaman damgasıyla yazıldığı için aynı içerik aynı SHA256 değerini verir.

Kurulum: `000400000009F100/` klasörünü `sd:/luma/titles/000400000009F100/` altına kopyalayın; Luma3DS'te **Enable game patching** açık olsun.

## 7. Araç Değişiklikleri

- `araclar/Language_Tool_V2/fea_lang_tool.py`
  - `ZipSource`, `DirSource`, `open_source` artık `langs` parametresi alıyor.
  - Tek dilli (yalnız U) kaynak/çıktı destekleniyor.
  - `inject` hedef dili (`--target`) üzerinden kaynak taraması yapıyor.
  - `verify --langs U` ile tek dil doğrulaması yapılabiliyor.
- `araclar/Build_Helper/rebuild_pass202_patch.py`
  - `--m` olarak `m.zip`, U içeren romfs klasörü veya m klasörü kabul ediliyor.
  - `--title-id`, font klasörü/ZIP ve `--langs U` doğrulaması eklendi.
  - `--fonts` varsayılanı izlenen `varliklar/fontlar` klasörü; `--out` varsayılanı sistem geçici klasörü.
  - Üretim sonunda kurulabilir yama otomatik olarak `000400000009F100/romfs` altına senkronize ediliyor.
  - `--patch-dir` ile farklı hedef, `--no-install` ile kurulum atlama desteği eklendi.
  - `m_TR_Pass202_full.zip`, romfs ağacı ve Luma ZIP'i yalnızca isteğe bağlı ara çıktı olarak üretiliyor; depoda saklanmıyor.
  - ZIP girişleri sabit zaman damgasıyla yazılıyor; aynı içerik aynı SHA256 değerini veriyor.

## 8. Bilinen Sınırlamalar

- `06_REFERENCE_INPUTS/m.zip` mevcut değil; tam çok dilli orijinal arşiv tabanlı üretim yapılamıyor. U romfs düzeniyle yama üretimi tamamlandı.
- F/G/I/S binary dil ağaçları yok; çapraz dil doğrulaması yalnızca CSV sütunları üzerinden yapılabiliyor.
- Patriots ayrı bir çeviridir ve altın standart değildir. 741 satırda Patriots Japonca kalmış, 138 satır Patriots'ta bulunmayan dosyalardadır; bu satırlarda U/F/G/I/S referans alındı. Patriots ile farklı ama doğru olan çeviriler değiştirilmedi.
- 39 satırda U/TR boşken İtalyanca (bazen F/G/S) dolu; bunlar kullanılmayan PCF2/PCF3 varyantlarıdır.
- Uzunluk denetimi `System.bfnt.lz` glif genişliklerine dayalıdır; gerçek kutu marjı küçük farklar gösterebilir. 360 px altında kalan 494 satır "sınırda" olarak bırakıldı; cihaz/Citra testi önerilir.
- Yama gerçek donanımda veya Citra'da test edilmedi; doğrulama yapısal ve piksel bazlıdır.
- Kaynak CSV dışında elle binary düzenlemesi yapılmadı; kurulabilir Title ID klasörü üretilen çıktıyla senkronize edildi.

## 9. Yeniden Üretim

```powershell
python araclar/Build_Helper/rebuild_pass202_patch.py --m 000400000009F100/romfs
```

Bu komut yamayı doğrudan `000400000009F100/romfs` altına kurar. Sadece ara çıktı üretmek için `--no-install` ekleyin.

Doğrulama:

```powershell
python araclar/Language_Tool_V2/fea_lang_tool.py verify 000400000009F100/romfs --langs U
```

İsteğe bağlı arşiv üretmek için komuta `--out build_output` ekleyin; arşiv doğrulaması üretim sırasında otomatik yapılır.
