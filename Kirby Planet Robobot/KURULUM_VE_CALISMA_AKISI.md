# Kurulum ve çalışma akışı

1. Çeviri dosyaları: `01_CEVIRI/MSBT_CSV`.
2. `TR_Turkish` sütununu düzenleyin.
3. `01_YAMAYI_OLUSTUR` komutunu çalıştırın.
4. Build aracı önce resmî-dil ölçek kuralını uygular; desteklenmeyen Türkçe ölçek tokenlarını otomatik kaldırır.
5. MSBT'ler `BUILD_OUTPUT/ROMFS_ONLY/romfs/msg/EU_English` altında üretilir.
6. Fontlar `03_FONTLAR/TR_PATCHED_CMP` klasöründen build'e kopyalanır.
7. `02_BUILD_DOGRULA` ile CSV/MSBT ve Türkçe font runtime kontrolünü çalıştırın.
8. Luma3DS için `BUILD_OUTPUT/SD_ROOT` içeriğini SD karta birleştirin.

Siyah ekran analizi ve kaldırılan ölçek kodları için `05_RAPORLAR/SON_KONTROL_OZETI.txt` ve `05_RAPORLAR/KALDIRILAN_DESTEKLENMEYEN_OLCEKLER.csv` dosyalarına bakın.
