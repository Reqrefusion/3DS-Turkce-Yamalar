# Tomodachi Life 3DS – Türkçe Çeviri Aracı v3

Bu araç Tomodachi Life (3DS) Avrupa `message` dosyaları için hazırlanmıştır.

İşlem zinciri:

`*_EU_English_LZ.bin` → **LZ11** → **DARC** → **MSBT** → Türkçe → **MSBT** → **DARC** → **LZ11**

Ek Python paketi gerekmez; Python 3 + Tkinter yeterlidir.

## v3'de değişenler

- Artık tek bir büyük CSV oluşturmaz.
- Her `.msbt` için ayrı bir `.csv` üretir.
- Çıktı klasör yapısını korur.
- Her CSV'de bütün diller aynı satırda yan yanadır:

`index | label | English | French | German | Italian | Spanish | Turkish`

- Arayüzde de English / French / German / Italian / Spanish / Türkçe aynı anda yan yana gösterilir.
- CSV klasörü geri içe alınabilir; `Turkish` sütunları MSBT'lere enjekte edilir.

## Örnek çıktı yapısı

Gönderilen gerçek dosyalarda örneğin:

```text
TranslationProject/
├─ _tomodachi_tr_manifest.json
├─ Chat/
│  ├─ ArcBase/
│  │  ├─ Chat_Cheerup.csv
│  │  ├─ Chat_Common.csv
│  │  ├─ Chat_Female.csv
│  │  └─ Chat_Male.csv
│  └─ ArcVoice/
│     ├─ Chat_Cheerup.csv
│     └─ ...
├─ Item/
│  ├─ ArcBase/
│  │  ├─ Food_Name.csv
│  │  ├─ Food_Desc.csv
│  │  └─ ...
│  └─ ArcVoice/
│     └─ ...
└─ Drama/
   ├─ ArcBase/
   ├─ Drama_Confession/
   │  └─ ...
   ├─ Drama_Dream/
   │  └─ ...
   └─ ...
```

Bir klasörde birden fazla `_LZ.bin` paketi varsa paket adı ayrıca alt klasör olarak kullanılır. Paket adı üst klasörle aynıysa gereksiz tekrar yapılmaz; örneğin `Chat/Chat/...` yerine doğrudan `Chat/...` oluşur.

## Çalıştırma

### Windows

1. Python 3 kurulu olmalı. Kurulumda **Tcl/Tk and IDLE** bileşenini açık bırakın.
2. `run_windows.bat` dosyasına çift tıklayın.

Alternatif:

```bat
py -3 tomodachi_tr_tool.py
```

### Linux/macOS

```bash
python3 tomodachi_tr_tool.py
```

Linux'ta Tkinter ayrı paket olabilir.

## Kullanım

1. **Message klasörü aç** ile oyundan çıkardığınız `message` klasörünü seçin.
2. Soldan bir `_EU_English_LZ.bin` paketi ve içindeki `.msbt` dosyasını seçin.
3. Mesaj listesinde İngilizce, Fransızca, Almanca, İtalyanca, İspanyolca ve Türkçe sütunlarını yan yana görebilirsiniz.
4. Alttaki editörlerde de beş kaynak dil aynı anda görünür. Sağdaki **Türkçe** alanına çeviriyi yazın.
5. Metindeki `{TAG_1}`, `{END_1}` gibi yer tutucuları silmeyin. Türkçe cümle yapısına göre konumlarını değiştirebilirsiniz.
6. **Projeyi kaydet** ile JSON proje dosyanızı saklayabilirsiniz.
7. **Çeviri klasörünü dışa aktar** ile her MSBT için ayrı CSV oluşturun.
8. CSV'leri Excel, LibreOffice, VS Code vb. ile açıp yalnızca `Turkish` sütununu doldurun. Kaynak dil sütunları karşılaştırma içindir.
9. **Çeviri klasörünü içe aktar** ile dışa aktarılan ana klasörü seçin. Araç `_tomodachi_tr_manifest.json` üzerinden her CSV'yi doğru MSBT ile eşleştirir.
10. **Yamayı oluştur** ile yalnızca Türkçe çeviri bulunan İngilizce paketleri yeniden üretin. Çıkışta orijinal `message/...` klasör yapısı korunur.

## Kontrol kodları

MSBT içindeki oyun kontrol kodları çeviri sırasında `{TAG_1}`, `{TAG_2}`, `{END_1}` gibi gösterilir. İngilizce kaynak satırında bulunan gerekli etiketler Türkçe çeviride eksik veya fazla olursa araç o satırı yamaya sokmaz.

Diğer Avrupa dillerinde etiket sayısı/konumu İngilizceden farklı olabilir. Türkçe hedef, oyunun İngilizce paketinin yerine yazıldığı için **korunması gereken etiketler English sütunundaki etiketlerdir**.

## Türkçe karakter/font desteği

MSBT metni UTF-16 olduğu için `ç ğ ı İ ö ş ü` karakterleri dosyaya yazılabilir. Ancak oyunun kullandığı BCFNT fontunda bu glifler yoksa oyunda kare/boş karakter görülebilir. Böyle bir durumda ayrıca font dosyasına Türkçe glif eklemek gerekir.

## Yedek

Araç kaynak dosyaların üzerine yazmaz. Orijinal `message` klasörünü her zaman ayrı bir yedek olarak tutun.

## Test edilen gerçek set

Gönderilen `message.zip` üzerinde:

- 68 İngilizce LZ11/DARC paketi
- 1.038 MSBT
- 53.195 metin satırı
- 1.038 ayrı klasör bazlı CSV

başarıyla işlendi.


## v3: boş CSV düzeltmesi

- Metin içermeyen MSBT dosyaları artık CSV olarak oluşturulmaz.
- English/French/German/Italian/Spanish sütunlarının tamamı boş olan satırlar dışa aktarılmaz.
- `index` değeri korunduğu için seyrek satırlar geri içe aktarılırken doğru MSBT mesajına enjekte edilir.
- Turkish sütunu doğal olarak ilk dışa aktarımda boştur; çeviriyi buraya yazın. Kaynak dil sütunları metin içermelidir.
