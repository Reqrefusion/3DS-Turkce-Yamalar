# Zeus Quest Remastered (Nintendo 3DS) — Aşama 34 İngilizce → Türkçe yaması

**Bu sürümde yalnızca İngilizce metin yuvası (`EN`) Türkçeleştirilir.** Daha önceki İngilizce+Yunanca karma yama yerine bunu kullanın. Türkçe dublaj **eklenmez**; yalnızca yazılar ve font değişir. Orijinal oyunun Yunanca, Fransızca, Almanca, İtalyanca ve İspanyolca **konuşma/çeviri metni blokları aynen korunur**. Arayüz sahne verileri birden fazla dil tarafından ortak kullanıldığı için dil değiştirildiğinde bazı sabit arayüz yazıları yine Türkçe kalabilir; bunlar tek dil seçimine bağlı değil.

**Gerekenler:** Hazır yama için kendi oyununuz ve uyumlu 3DS LayeredFS yükleyicisi. Yeniden üretmek için Python 3.9+ ve **kendi orijinal oyun arşiviniz** `Zeus Quest Remastered.zip`. Temel araçlarda ek Python modülü gerekmiyor (grafik CSV editörü için standart Tkinter gerekli). Oyun kopyasını paketle **dağıtmıyoruz**.

**Test:** Orijinal dosyayla karşılaştırmalı metadata, Unity UI, font glif kapsamı ve ZIP kontrolü yapıldı. Fiziksel 3DS veya Azahar üzerinde *oyun çalıştırılarak test yapılmadı*.

## 1. Yeni sürümde neler düzeltildi?

- **Yunanca çeviri kaldırıldı:** `EL` dil yuvası, diğer tüm dillere ait metinler dahil, orijinal haliyle bırakılıyor.
- **Music** kontrolü: `romfs/Data/sharedassets1.assets` içindeki iki ayrı Unity Text nesnesi (`path_id=526` ve `532`) **Müzik** olarak yazılıyor ve denetleyici her ikisini **tekrar açıp karşılaştırıyor**. Metadata içindeki `Music Settings` da **Müzik Ayarları**. Bunlar Aşama 33 CSV'sinde de çevrilmişti; bu sürüm ayrıca yamada gerçekten bulunduğunu kontrol ediyor.
- Metin içinde unutulan bir İngilizce ifade düzeltildi: `META:7714` satırındaki **`'ok' düğmesi` → `'Tamam' düğmesi`**.
- **Eksik çeviri tarayıcısı** eklendi: İngilizce bırakılmış olabilecek kısa terimleri, kaynakla bire bir kalan satırları ve boş hedefleri CSV raporuna döker. Bu bir yazılım taramasıdır; görsel/bağlamsal incelemenin yerine geçmez.
- **Yama doğrulayıcı** eklendi: İngilizce 3.092 kaynak satırını, 125 UI Text kaydını, değişmeyen diğer metadata metinlerini ve fontun 525 karakterini inceler. Sahne dosyalarında çevrilen UI ve font nesneleri dışındaki nesnelerin değişmediğini denetler.

| Konu | Dosya düzeyi sonuç |
|---|---:|
| İngilizce metin sayısı | 3.092 |
| Değişen İngilizce metin | 3.083 |
| Sahne UI kaydı / değişen | 125 / 78 |
| Orijinal font / yamalı font | 517 / 525 |
| Eklenen glifler | `Ğ ğ İ ı Ş ş ’ •` |
| Yama dosyası | 33 adet `romfs/Data/...` |
| Denetleyicinin bulduğu eksik font karakteri | 0 |
| Diğer dillerin metadata blokları | Bire bir aynı |

9 İngilizce kayıt (`PayPal`, konuşmacı adları, sayım ve ünlem gibi şeyler) bilerek aynı bırakılmıştır. 47 UI girdisi sayı/yüzde karakteridir; metin olarak değiştirilmemiştir. Kaynak dosyada `Music` adının geçmesi tek başına eksik çeviri kanıtı değildir: `Butt_Music`, `Musicoff` gibi dizeler UI nesne/olay **kimlikleridir**, görünür etiket değildir, oyunu bozmamak için değiştirilmez.

## 2. Hangi dosya ne işe yarıyor?

```text
ZeusQuest_Asama34_Sadece_Ingilizce_AracSeti/
├─ README_TR.md
├─ 01_CEVIRI_EDITORU.bat                 # CSV'yi GUI ile düzenle
├─ 02_INGILIZCE_YAMA_OLUSTUR.bat        # EN + UI + font yeni yama üret
├─ 03_YAMAYI_DOGRULA.bat                # Hazır yamayı orijinal oyunla karşılaştır
├─ 04_EKSIK_CEVIRI_TARAMASI.bat         # İncelenecek adayları CSV'ye yaz
├─ 05_FONT_KONTROL.bat                  # Kaynak fontun eksik gliflerini incele
├─ 06_HAM_METINLERI_CIKAR.bat           # Ham oyun CSV'lerini tekrar çıkar
├─ ceviriler/
│  ├─ EN_TR.csv                          # meta_index | İngilizce | Türkçe
│  └─ UI_EN_TR.csv                       # dosya | path_id | İngilizce | Türkçe
├─ araclar/
│  ├─ zeusquest_tool.py                 # Unity+IL2CPP yama altyapısı
│  ├─ turkce_font.py                    # ETC1A4 font yaması
│  ├─ tek_dil_dogrula.py                # İngilizce yuvası bütünlük testi
│  ├─ ingilizce_denetime_al.py           # Eksik çeviri adayları tespiti
│  └─ ceviri_editoru.py                 # Tkinter CSV editörü
├─ hazir_yama/
│  └─ ZeusQuest_ASAMA34_EN_TR_Font_LayeredFS.zip
├─ font/
│  └─ Mevcut karakter listeleri ve font önizleme görseli
└─ raporlar/
   ├─ YAMA_DOGRULAMA.json
   ├─ CEVIRI_DENETIMI.json
   └─ INGILIZCE_KALMIS_OLABILIR.csv
```

**Dikkat:** CSV'deki `meta_index`, `id`, `dosya`, `path_id` ve `kaynak_metin` değerlerini değiştirmeyin; yalnızca `turkce` sütununu düzenleyin. CSV dosyaları Excel/LibreOffice ile de açılırsa UTF-8 karakterlerin korunduğunu ve `id` değerlerinin bozulmadığını kontrol edin. En güvenlisi paket içindeki editör ya da düz metin CSV düzenleyicidir.

## 3. Hazır yamayı 3DS'e yükleme

1. Eski **Aşama 33 EN+EL** yamasını yama klasöründen silin veya güvenli bir yere taşıyın; **eski yamayla üst üste birleştirmeyin**. Eski ekstra dosyaların orada kalması beklenmeyen sonuç doğurabilir.
2. `hazir_yama/ZeusQuest_ASAMA34_EN_TR_Font_LayeredFS.zip` dosyasını açın.
3. Arşivin `romfs` klasörünü oyunun **gerçek 16 haneli Title ID** klasörünün altına yerleştirin:

   ```text
   SD:/luma/titles/<OYUN_TITLE_ID>/romfs/Data/Managed/Metadata/global-metadata.dat
   SD:/luma/titles/<OYUN_TITLE_ID>/romfs/Data/sharedassets0.assets
   SD:/luma/titles/<OYUN_TITLE_ID>/romfs/Data/sharedassets1.assets
   SD:/luma/titles/<OYUN_TITLE_ID>/romfs/Data/level0
   ...
   ```

   `romfs/romfs/Data` gibi çift dizin oluşturmayın. Oyunun Title ID'sini tahmin ederek sabitlemiyoruz; cihazınızdaki sürümü esas alın.
4. Luma3DS yapılandırmasında **Enable game patching** açık olsun (genellikle cihazı SELECT basılı açarak ayarlanır).
5. Oyunda **English** seçin. Menüde bu adın English kalması normaldir; yeni bir Turkish dil seçimi eklemiyoruz.

**Azahar / Citra:** Oyunun *Open Mods Location* / mod klasörünü açın. Mevcut eski yamayı oradan kaldırın, yeni ZIP içindeki `romfs/` dizinini bu klasöre kopyalayın. Oyun sürümü ve güncelleme farklıysa uyumluluk garantisi yoktur.

**“Music” hâlâ İngilizce görünüyorsa:** (a) Eski mod klasörünü temizleyin, (b) yeni yamadaki `romfs/Data/sharedassets1.assets` dosyasının gerçekten mod klasöründe olduğunu kontrol edin, (c) konsolda mod patching açık olsun, (d) oyunu tamamen kapatıp açın. Hangi ekranda göründüğünü gösteren ekran görüntüsü, kaynağını bulmak için faydalı olur. Eğer resmin içine çizilmiş metinse XML/metadata yaması bunu çeviremez.

## 4. CSV düzenle ve yeniden yama oluştur

1. Paket klasörünün içine kendi `Zeus Quest Remastered.zip` dosyanızı koyun; adı birebir böyle olmalı. Orijinal arşivde `romfs/Data/Managed/Metadata/global-metadata.dat` bulunmalı.
2. `01_CEVIRI_EDITORU.bat` çalıştırıp `ceviriler/EN_TR.csv` veya `ceviriler/UI_EN_TR.csv` açın. Türkçe sütununu kaydedin.
3. `04_EKSIK_CEVIRI_TARAMASI.bat` ile `raporlar/INGILIZCE_KALMIS_OLABILIR.csv` dosyasını üretin; adayları elle kontrol edin.
4. `02_INGILIZCE_YAMA_OLUSTUR.bat` çalıştırın. Yeni `ZeusQuest_ASAMA34_EN_TR_Font_LayeredFS.zip` oluşturulur ve arkasından doğrulama yapılır.
5. `03_YAMAYI_DOGRULA.bat`, paket içindeki hazır yama içindir; yeni oluşturduğunuz yamayı test etmek için 02'nin hemen ardından çalışan kontrolü kullanın.

Windows dışındaki sistemlerde komutlar:

```bash
python3 araclar/zeusquest_tool.py build \
  --game "Zeus Quest Remastered.zip" \
  --csv ceviriler/EN_TR.csv --slot en \
  --ui-csv ceviriler/UI_EN_TR.csv \
  --out ZeusQuest_ASAMA34_EN_TR_Font_LayeredFS.zip

python3 araclar/tek_dil_dogrula.py \
  --game "Zeus Quest Remastered.zip" \
  --patch ZeusQuest_ASAMA34_EN_TR_Font_LayeredFS.zip \
  --en ceviriler/EN_TR.csv --ui ceviriler/UI_EN_TR.csv \
  --report raporlar/YAMA_DOGRULAMA.json

python3 araclar/ingilizce_denetime_al.py \
  --en ceviriler/EN_TR.csv --ui ceviriler/UI_EN_TR.csv --out raporlar
```

**Font tekniği:** Unity 5.2.4f1 v15 asset tabloları okunur. `sharedassets0.assets` içindeki `bitmapfont` karakter tablosuna 8 kod noktası eklenir. 3DS `ETC1A4` (61) alfa atlası 512×512'den 1024×512'ye taşınır; var olan glifler korunur, ek glifler mevcut harf ve aksanlardan üretilir. Eski atlas UV'leri yeni genişliğe göre güncellenir. Fontun ve dokunun değiştirilmesi, **3DS üzerindeki görüntünün kesin düzgün olacağı** anlamına gelmez; ekran testi gerekir.

**Metadata tekniği:** IL2CPP metadata sürüm 16, string literal tablosu ve offsetleri kontrol edilir. EN indeksi 7628–10719 değiştirilirken `LANGS['EL']` ve diğer bloklar yeniden inşa sırasında **değer bazında aynı** tutulur. Unity `Text` objeleri `m_Script pathID=385` ve metin alanı `offset=248` üzerinden değiştirilir. Nesne boyutları/yazı uzunluğu değiştiği için Unity dosyası nesne ofsetleri yeniden oluşturulur. Marker `<color=...>` ve `{0}` gibi biçimlendirme yer tutucuları kontrol edilir.

## 5. Sınırlar ve güvenlik

- Oyun videosu/seslendirmesi **çevirilmedi**. Yunanca için özel seslendirme olduğuna ilişkin bir doğrulamamız yok.
- Çeviri dosyalarına almadığımız bazı kısa sabitler ses, giriş ayarı veya **nesne adı/kod kimliği** olabilir. Görünür olduğundan emin olmadan değiştirmek oyunu bozabilir.
- Paket yalnızca değiştirilmiş ROMFS parçalarını içerir. Telif hakkıyla korunan oyunun tamamını içermez.
- Orijinal dosyalarınızın ve kayıtlarınızın yedeğini alın. Gerçek cihaz/emülatör testinde ek düzeltmeler gerekebilir.
