# MLSS Türkçe Çeviri / Build Aracı

Bu araç Mario & Luigi: Superstar Saga + Bowser's Minions Avrupa bölgesindeki mesaj dosyalarını CSV'ye aktarır ve `TR` sütununu tekrar oyunun MSBT/BG4 biçimine yazar.

Hazır CSV setinde toplam 7.867 kayıt bulunur ve `TR` sütunları doludur.

## Temel kullanım

Windows'ta `RUN_GUI.bat` dosyasını çalıştırabilirsiniz.

Komut satırından:

```bash
python mlss_translate.py unpack "oyun_dilleri.zip" extracted
python mlss_translate.py export extracted/Msg csv
python mlss_translate.py csv-check csv --source-lang EU_en
python mlss_translate.py build extracted/Msg csv build --base EU_en --slot EU_en
```

Build sonucu `build/Msg` klasörüne yazılır. Türkçe, İngilizce (`EU_en`) dil yuvasına uygulanır.

## Mesaj biçimleri

Araç doğrudan `.msbt` dosyalarını ve `BMsg.dat` / `FMsg.dat` içindeki gömülü MSBT dosyalarını işler. Metin içindeki `<0E:...>` ve `<0F:...>` kontrol kodlarını kaybetmeden CSV içinde korur.

## Fontlar

Build sırasında hedef dil klasöründeki şu fontlar Türkçe karakterler için yamalanır:

- `font.bffnt`
- `font_btl.bffnt`
- `font_l.bffnt`
- `font_sys.bffnt`
- `font_sys_btl.bffnt`

Eklenen karakter kümesi: `ç Ç ğ Ğ ı İ ö Ö ş Ş ü Ü`.

## Kontrol

```bash
python mlss_translate.py check build/Msg --lang EU_en
```

Bu komut MSBT ve BG4 yeniden paketleme tutarlılığını sınar.

## Grafik UI

Grafik olarak çizilmiş arayüz yazıları ayrı araçla işlenir. `UI` klasöründeki `README_UI_TR.txt`, `mlss_ui_tool.py` ve `ui_translations.csv` dosyalarına bakın. Hazır dağıtım paketinde oluşturulmuş UI yaması zaten `Yama/romfs/Obj/EU` altında bulunur.
