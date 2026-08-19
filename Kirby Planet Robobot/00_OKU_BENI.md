# Kirby Planet Robobot Türkçe Yama ve Çeviri Araçları

Bu paket, son UI uzunluk düzeltmeleri korunarak hazırlanmıştır. Bölüm/alan yüklemesinde siyah ekran oluşturma ihtimali bulunan kontrol kodları ayrıca ayıklanmıştır.

## Önemli güvenlik kuralı

Bir Türkçe metinde küçültme/ölçek kontrol kodu **yalnızca aynı MSBT kaydının resmî dillerinden en az birinde bu ölçek komutu kullanılıyorsa** tutulur.

Resmî dillerin hiçbirinde ölçek kullanılmayan bir kayda sonradan ölçek kodu eklenmez. `01_YAMAYI_OLUSTUR` bu kuralı build öncesinde otomatik uygular.

Bu temizlikte görünür Türkçe metin değiştirilmedi. Son UI düzenlemelerindeki kısaltmalar, yeniden ifadeler ve satır düzenleri korunmuştur.

## Hızlı kurulum

Doğrudan Luma3DS kurulumu için `BUILD_OUTPUT/SD_ROOT` içeriğini SD kart köküne birleştirin.

Yalnız RomFS gerekiyorsa `BUILD_OUTPUT/ROMFS_ONLY/romfs` klasörünü kullanın.

## Çeviri düzenleme

`01_CEVIRI/MSBT_CSV` içindeki 30 CSV dosyasında `TR_Turkish` sütununu düzenleyin.

Kontrol tokenlarını mümkün olduğunca elle değiştirmeyin. Özellikle `⟦MSBT:...⟧` ve `⟦U16:...⟧` parçaları oyun içi biçim/tuş/renk komutları olabilir.

Build:

- Windows: `01_YAMAYI_OLUSTUR.bat`
- Linux/macOS: `01_YAMAYI_OLUSTUR.sh`

Doğrulama:

- Windows: `02_BUILD_DOGRULA.bat`
- Linux/macOS: `02_BUILD_DOGRULA.sh`

Ölçek kuralını ayrıca kontrol etmek için `05_OLCEK_KODU_KONTROL` kullanılabilir.

## Siyah ekran için yapılan inceleme

Önceki çalışan çeviri ile son UI-düzeltilmiş çevirinin fontları 25/25 bayt-bayt aynıydı. Değişen katman MSBT metin/kontrol kodlarıydı.

Son UI çalışmasında, resmî dillerin aynı kaydında hiç ölçek komutu bulunmamasına rağmen Türkçede ölçek kullanılan 83 kayıt tespit edildi. Bunların 79'u son UI düzenlemesi sırasında eklenmişti. Bölüm seçim/yükleme akışında kullanılan bazı `Confetti`, `WMap` ve `GameInfo` kayıtları da bu gruptaydı.

Bu 83 kayıttan yalnız ölçek tokenları çıkarıldı. Görünür Türkçe metin değişikliği yapılmadı.

Ayrıntılar `05_RAPORLAR` klasöründedir.

## Fontlar

Final build'deki 25 font, önceki çalışan çeviri paketindeki fontlarla bayt-bayt aynıdır. Böylece siyah ekran incelemesinde font katmanı değişken olmaktan çıkarılmıştır. Türkçe karakter runtime kontrolü 15/15 Latin metin fontunda geçmektedir.

## Not

Desteklenmeyen ölçek komutları kaldırıldığından bazı uzun satırlar görsel olarak sıkı kalabilir. Bunlar `GUVENLI_OLCEK_SONRASI_GORSEL_KONTROL.csv` içinde işaretlidir. Bu kayıtlar gerekiyorsa yeni ve desteklenmeyen kontrol kodu eklemek yerine metin kısaltılarak düzeltilmelidir.
