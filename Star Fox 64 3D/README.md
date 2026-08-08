# Star Fox 64 3D Türkçe Yama

Topluluk katkısına açık **Star Fox 64 3D Türkçe yerelleştirme projesi**. Bu depo, çeviri verisini ve yamayı kullanıcının kendi oyun kaynaklarından üreten araçları içerir.

> **Nintendo oyun dosyaları bu repoya dahil değildir.** `Resources.zip`, `.msbt`, `.msbp`, ROM/CIA/3DS dosyaları veya başka özgün oyun varlıkları commit edilmemelidir.

## Proje durumu

- Yerel ayar: **tr-TR**
- Çeviri kaydı: **7.680**
- Kaynak MSBT dosyası: **10**
- Son kaynak üzerinde Türkçesi/orijinali farklı kayıt: **4.752**
- Ana hedef: **EUR** (`0004000000049100`)
- İsteğe bağlı build hedefi: **USA** (`0004000000049000`)

Çeviri, menü ve eğitim metinleri dahil olacak şekilde daha önce uzun satır ve MSBT kontrol kodu kontrollerinden geçirilmiştir. Gerçek donanım/emülatör testleri için geri bildirim özellikle değerlidir.

## Katkı vermenin en kolay yolu

1. Repoyu fork'layın ve yeni bir branch açın.
2. `translations/tr_TR.jsonl` içindeki yalnızca `translation` alanını düzenleyin.
3. `python scripts/validate_translation.py` çalıştırın.
4. Pull Request açın.

JSONL dosyasında **her oyun metni tek fiziksel satırdır**; bu yüzden GitHub diff'leri eski çok satırlı TSV biçimine göre çok daha okunaklıdır.

### Orijinal İngilizce metni yanında görmek istiyorsanız

Kendi oyununuzdan çıkardığınız `Resources.zip` ile:

```bash
python scripts/make_review_tsv.py /path/to/Resources.zip
```

Bu komut `review/tr_TR_review.tsv` üretir. Dosyayı Excel/LibreOffice gibi bir araçta düzenleyebilirsiniz. Değişiklikleri ana JSONL'e geri almak için:

```bash
python scripts/import_review_tsv.py review/tr_TR_review.tsv
python scripts/validate_translation.py
```

`review/` klasörü bilerek `.gitignore` içindedir; İngilizce oyun metninin toplu kopyasını repoya commit etmeyin.

## Yama oluşturma

Python 3.10+ yeterlidir; harici paket gerektirmez.

```bash
python scripts/build_luma_patch.py /path/to/Resources.zip --region EUR
```

Çıktı varsayılan olarak `dist/StarFox64_3D_TR_Luma_EUR.zip` olur. ZIP, Luma3DS için `luma/titles/<TitleID>/romfs/Resources/` yapısını içerir.

## Çeviri kuralları

- Kelime kelime değil, **oyun bağlamına uygun doğal Türkçe** kullanın.
- Karakter tonunu koruyun: Falco daha alaycı, General Pepper daha resmî vb.
- `{MSBT:...}` tokenlarını **silmek, eklemek veya sırasını değiştirmek yasaktır**.
- Çevirinin satır sayısını ve en uzun görünür satırı kaynak uzunluğunu **+8 karakterden fazla** aşmamalıdır.
- Star Fox evrenindeki yerleşik özel adları gereksiz yere çevirmeyin.
- Terminoloji için `docs/TERMINOLOGY.md` dosyasına bakın.

## Otomatik kontroller

Her Pull Request'te GitHub Actions şunları denetler:

- JSONL biçimi ve benzersiz `file + index` anahtarları
- MSBT kontrol tokenlarının korunması
- kaynak satır sayısı sınırı
- kaynak maksimum görünür satır uzunluğu +8 karakter toleransı
- temel alanların ve kaynak SHA-256 bilgilerinin geçerliliği

Build sırasında ayrıca kullanıcının `Resources.zip` içindeki İngilizce kaynak metinlerinin SHA-256 değerleri kontrol edilir. Böylece yanlış bölge/sürüm kaynaklarına sessizce yama uygulanmaz.

## Dosya yapısı

```text
translations/       Türkçe çeviri kaynağı
scripts/            doğrulama, review TSV ve build araçları
tools/              MSBT parser/rebuilder
docs/               katkı, terminoloji, test ve yayın belgeleri
.github/             PR/issue şablonları ve CI
```

## Telif ve proje durumu

Bu bağımsız bir hayran yerelleştirme projesidir; Nintendo ile bağlantılı veya Nintendo tarafından onaylanmış değildir. **Star Fox, Nintendo ve ilgili marka/oyun içerikleri hak sahiplerine aittir.** Bu repo özgün oyun kaynaklarını dağıtmayı amaçlamaz.

Araç kodu MIT lisansı altındadır. Çeviri katkıları için ayrıntılar `LICENSES/TRANSLATION_NOTICE.md` dosyasındadır.

Katkıda bulunmadan önce [CONTRIBUTING.md](CONTRIBUTING.md) dosyasını okuyun.
