# Kurulum ve çalışma akışı

Title ID klasörü `000400000010C000/` oyun klasörünün kökündedir. Bu klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS oyun yamalama özelliğini etkinleştirin; oyun EU_English metinlerini kullanmalıdır.

## Metin düzenleme

`ceviri/MSBT_CSV/` içindeki 23 CSV dosyasının `TR_Turkish` alanlarını düzenleyin. Kontrol belirteçlerini koruyun. Oyun klasöründe:

```text
python araclar/build_patch.py
python araclar/verify_package.py
```

Kaynak şablonlar `kaynaklar/MSBT_SABLON/` altındadır. Üretim `calisma/uretim/` altında çıktı oluşturur ve kökteki Title ID ağacına mesajları da kopyalar. Üretimden önce mevcut yamanızı yedekleyin.

## Fontlar

`kaynaklar/FONT_ORIJINAL/` temiz fontları, `kaynaklar/FONT_ACILMIS/` açılmış çalışma dosyalarını içerir. Font araçları ve Windows/macOS/Linux başlatıcıları `araclar/` altındadır.

Noktasız `ı` üretiminde fontun büyük `I` glifi kullanılır; düz orta gövde kısaltılırken üst ve alt gölge ayrıntıları korunur. Genişlik bilgisi küçük `i` glifinden alınır. `CommonStd_OL` içindeki özgün Türkçe glif korunur.

## Doğrulama

`verify_package.py`, CSV ve üretilmiş MSBT metinlerinin eşleşmesini, kontrol belirteçlerini, Türkçe gliflere erişimi ve noktasız `ı` geometrisini denetler. Yerel kontrolde 23 MSBT, 1.847 kayıt ve 10 metin fontu başarılı bulundu. Gerçek cihazdaki görünüm ayrıca denenmelidir.
