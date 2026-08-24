# Poochy & Yoshi's Woolly World (3DS EUR) — Türkçe CSV Final Paket

Bu paket GUI içermez. Desteklenen iş akışı **CSV-only**'dir.

## En hızlı kullanım

### 1. Sadece yamayı uygulamak
`PATCH/` klasörünü kullanın. Python 3 dışında bağımlılık yoktur.

Windows:

```bat
PATCH\UYGULA.bat "orijinal_oyun.zip" "Poochy_Yoshi_TR.zip"
```

Linux/macOS:

```sh
./PATCH/uygula.sh "orijinal_oyun.zip" "Poochy_Yoshi_TR.zip"
```

Yama kaynak arşivdeki 808 girdiyi hash ile doğrular ve yalnız 4 dosyayı değiştirir.

### 2. CSV'yi düzenleyip yeniden build almak

```sh
python TOOLS/yww_csv_tool.py export "orijinal_oyun.zip" yeni.csv
python TOOLS/yww_csv_tool.py qa "orijinal_oyun.zip" FINAL/merino.msbt.TR.final.csv --out qa.json
python TOOLS/yww_csv_tool.py build "orijinal_oyun.zip" FINAL/merino.msbt.TR.final.csv cikti.zip
python TOOLS/yww_csv_tool.py verify "orijinal_oyun.zip" cikti.zip FINAL/merino.msbt.TR.final.csv --out verify.json
```

`yww_csv_tool.py` yalnız Python standart kütüphanesini kullanır. MSBT içindeki `LBL1/TXT2` yapısını doğrudan okur/yazar, 11 dili yan yana çıkarır, kontrol tag/placeholder QA yapar, Türkçeyi `EU_English` slotuna enjekte eder ve hazırlanmış `static_char.msbt` + iki BFFNT font desteğini uygular.

## Final metin durumu

- 2230/2230 MSBT kayıt sırası korunur.
- Anlamlı Türkçe metinlerin tamamı doldurulmuştur; kaynakta yalnız boş/boşluk olan kayıt korunmuştur.
- Kontrol tag hatası: 0.
- Placeholder hatası: 0.
- Çok dilli anlam/kelime oyunu çapraz kontrolü yapılmıştır.
- 1P/2P hitap ayrımları gözden geçirilmiştir.
- Baby Bowser'ın kasıtlı çocuk konuşması korunmuştur.
- Boss/film/bölüm adlarındaki kelime oyunları Türkçede yeniden kurulmuştur.
- BFFNT gerçek ilerleme genişliğiyle bağlamsal uzunluk denetimi yapılmıştır; +10 px üzeri aday 0, ek satır/dikey taşma adayı 0.

## Font

`ÇĞİÖŞÜçğıöşü` desteği iki `keito25pt.bffnt` dosyasında mevcuttur. Build sırasında `TOOLS/support/` altındaki doğrulanmış destek dosyaları uygulanır.

## Görseller

`ASSETS/` altında 21 dil-bağımlı texture'ın çok dilli manifesti ve Türkçe metin planı vardır. **Bu final yama görsel piksellerini değiştirmez.** Görsel metin kararları korunmuştur; ileride texture düzenlemesi için kullanılabilir.

## Klasörler

- `FINAL/` — kullanılacak son Türkçe CSV ve sözlük.
- `TOOLS/` — çalışan CSV-only CLI + font/static_char destek dosyaları.
- `PATCH/` — paylaşılabilir bağımsız metin+font yaması.
- `QA/` — çapraz dil, kelime oyunu, uzunluk ve round-trip raporları.
- `ASSETS/` — görsel yerelleştirme planları/manifestleri.
- `INTERMEDIATE/` — önceki CSV sürümleri ve çalışma/QA ara çıktıları.
- `REFERENCE_BUILD/` — bu oturumda kullanıcının yüklediği kaynak arşivden oluşturulmuş doğrulanmış kişisel test build'i. Paylaşım için `PATCH/` paketini tercih edin.

## Kaynak sürüm

Beklenen orijinal ZIP SHA-256:

`e04a702c3caf8fca1cb35c9b50b48bccf7b6f6a7cbb0e7fcc11fd1efd5faef0b`

Son CSV'den üretilen referans build SHA-256:

`1b9fa7ae1624ef8f8c34c26da8da467b63b6de993861a5678a3453031964077d`

Bağımsız yama, ZIP byte hash'i farklı olsa bile 808 girdinin içerik hash'leri birebir aynıysa yeniden paketlenmiş aynı kaynağı kabul eder.
