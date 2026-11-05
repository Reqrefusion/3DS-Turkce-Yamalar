# Araçların kullanımı

Python 3 ile komutları bu proje klasöründen çalıştırın. Paket oluştururken `pack.dat` ve ona ait `pack.inc` aynı kaynaktan gelmelidir. Çıktı için yeni veya boş bir klasör kullanın.

## Mevcut Türkçe paketin kontrol ve onarımı

```powershell
python tools/repair_native_controls.py --original "OZGUN_ROMFS" --translated "TURKCE_ROMFS" --output "YENI_CIKTI" --build-pack
```

Her iki girdi klasöründe de `pack.dat` ve `pack.inc` bulunmalıdır. Komut tablosu ve paket aracı varsayılan olarak aynı `tools` klasöründen alınır. Başka konumlar gerektiğinde `--schema` ve `--tool` kullanılabilir.

Araç her senaryoda yazı kodlarını korur; sayısal bozulma örüntülerini, HD komut çiftlerini, yerel atlamaları ve paketlenmiş hedefleri inceler. Sonuçlar `control_fix_report.json` içine yazılır. Belirsiz parametreler ve genel komut sırası farklı sayfalar raporda tutulur; çözülemeyen atlama hedefleri paket üretimini durdurur. Tüm denetimler geçmeden sonuç klasörü tamamlanmış çıktı olarak oluşturulmaz.

## Switch senaryolarını 3DS'e aktarma

```powershell
python tools/aat3ds_tool.py port-switch "OZGUN_PACK_DAT" "SWITCH_KAYNAK_KLASORU" "YENI_CIKTI" --make-pack --inc "OZGUN_PACK_INC"
```

Metin dönüştürücü komutların argümanlarını atlar; yalnız gerçek metin kodlarını dönüştürür. Her senaryo çıktı arşivine eklenmeden önce yerel 3DS komut onarımından, hedef taşımasından ve metin koruma kontrolünden geçer. Bilinmeyen karakterler, eksik senaryolar ve çözülemeyen hedefler sessizce geçilmez. Paket üretimi için `--inc` zorunludur.

Bu aktarım senaryo ve font katmanını işler. Menü görselleri ve programdaki font ölçüsü/çizim düzeltmeleri ayrı araçlardır; bunların kaynak program ve bölgeyle uyumu ayrıca korunmalıdır.

## Paket kaynaklarını türlerine göre ayırma

```powershell
python tools/aat3ds_tool.py extract-pack "PACK_DAT" "YENI_CIKTI" --grouped
```

Eski paket aracının yararlı klasör düzeni kullanılır: `bch`, `ans`, `font`, `mcol`, `dialogues`, `unknown`. Türler dosya imzalarıyla belirlenir; diyalog arşivleri ayrıca kayıt tablosu ve sıkıştırılmış kayıt başlıklarıyla tanınır. Büyük bir dosya yalnız boyutuna bakılarak diyalog sayılmaz.

`pack_manifest.json` her dosyanın paket indeksini, çıktı yolunu, boyutlarını ve SHA-256 özetini tutar. Dosya içerikleri değiştirilmez. `--grouped` verilmezse düz numaralı `.bin` çıktısı korunur.

## Paket içindeki bir girdiyi değiştirme

```powershell
python tools/aat3ds_tool.py inject-pack-entry "PACK_DAT" 58 "YENI_GIRDI" "YENI_PACK_DAT" --inc "PACK_INC" --out-inc "YENI_PACK_INC"
```

İndeks olmadan yalnız `pack.dat` üretilmez. Birden çok girdi için:

```powershell
python tools/aat3ds_tool.py rebuild-pack "PACK_DAT" "PACK_INC" "YENI_PACK_DAT" "YENI_PACK_INC" --replace "58=YENI_GIRDI"
```

## Araç dosyaları

- `aat3ds_tool.py`: paket, sıkıştırma ve diyalog aktarımı.
- `repair_native_controls.py`: ortak komut tablosu, metin koruması ve mevcut paket onarımı.
- `relocate_local_jumps.py`: yerel atlamaların ve paketlenmiş tablo hedeflerinin taşınması.
- `opcodes_3ds.json`: yerel işleyicilerle gözden geçirilmiş argüman uzunlukları ve kaynak bilgisi.
- `bch_utils.py`: BCH texture işlemleri.
- `ips_tool.py`: IPS oluşturma/uygulama.
- Diğer dosyalar font, program kodu, yüzey görselleri ve tanı yardımcılarıdır. Eski betik girişleri, çağıran araçların uyumluluğu için korunur.

## Tekrarlanabilir kontroller

```powershell
python -m unittest discover -s tests -v
```

Kontroller, geçmişte görülen metin bozulmasını, karaktere benzeyen komut argümanlarını, atlama hedeflerini, HD komut çiftlerini, indeks güncellemesini ve başarısız çıktı davranışını kapsar. Oyun içi sahne denemesinin yerine geçmez.

## Eski araçlar

[AATri Tools klasöründeki eski araçların incelemesi](ESKI_ARACLAR.md), komut tablosu farklarını, karakter desteğini, sıkıştırma önbelleğini ve sabit font yamasının etkisini açıklar.
