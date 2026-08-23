# Heroes of Ruin Türkçe Yama — Sesle Hizalı Altyazılar

Heroes of Ruin — Sesle Hizalı Türkçe Ara Sahne Altyazıları

Bu paket önceki görsel-sahne tahminli zamanlamayı kaldırır. CINE_02–CINE_06, oyunun İngilizce Wwise sesine resmî İngilizce STRL senaryosu kullanılarak kelime seviyesinde forced-alignment ile bağlandı. CINE_01 ve CINE_06B serbest ASR + satır bazlı akustik kontrolle denetlendi; ses miksinde okunmayan STRL satırları ve yönetmen notları/çığlık kayıtları çıkarıldı.

Bir replik görsel sahne değişimini aşıyorsa aynı altyazı sonraki BCLAN sahnesinde devam eder. Stil: arka plan yok, beyaz yazı, siyah dış kontur, en fazla iki satır.

Kurulum: Eski yamanın romfs/UI/aniscene_*.arc_ dosyalarını tamamen silin. Ardından SADECE_ALTYAZI_DUZELTME içeriğini mevcut Türkçe yamanızın üzerine kopyalayın.

# ÖNEMLİ — Ara sahne + altyazı görünürlük düzeltmesi

Siyah ekran sorunu çözüldükten sonra ikinci bir hata bulundu: altyazı texture footer formatı yanlış yazılmış ve altyazı pane Z değerleri oyun sahnesinin normal derinlik aralığının dışındaydı. Bu paket hem siyah ekran düzeltmesini hem de altyazı görünürlük düzeltmesini içerir. **Eski mod klasörünü tamamen silip bu paketi temiz kurun.** Yalnız son düzeltmeyi denemek isterseniz `SADECE_ALTYAZI_DUZELTME/` klasörünü kullanabilirsiniz.

# Heroes of Ruin Türkçe Yama – Tam Paket

Bu pakette sürüm etiketi yoktur. Hedef oyun **CTR-P-AH6P Avrupa / Title ID 0004000000074000**.

## İçerik

- 6.824 Türkçe STRL kaydı (`_UK` slotu; İngilizce ses korunur).
- Yedi ana ara sinematik için 97 resmî repliğin EN/FR/DE/IT/ES/TR karşılıkları.
- BASL zaman çizelgesinden türetilmiş sahne zamanları ve `RAPORLAR/cutscene_multilang_timeline.csv`.
- Sinematiklerde font bağımsız çalışan BCLIM/BCLYT hard-sub katmanları.
- Oyunun `demo_font.bcfnt_` dosyasından üretilen Türkçe glifli font.
- Çeviri CSV+JSON kaynakları ve STRL/BLZ/DARC/BCLYT/BCFNT araçları.

## Ara sinematik yöntemi

Oyun tek parça video kullanmıyor; animatic sahneleri DARC içindeki BCLYT/BCLAN/BCLIM varlıklarından oluşturuluyor. Yama her kullanılan fiziksel sahne arşivine iki yeni RGBA4444 BCLIM ekler: yarı saydam arka plan ve Türkçe raster altyazı. Bu format oyunun kendi animatic texture'larında da kullanılır. BCLYT'ye üst katman olarak iki `pic1` pane eklenir. Böylece sinematik altyazısı sistem fontundan bağımsızdır.

Bazı fiziksel sahne arşivleri birden fazla BASL mikro-sahnesinde yeniden kullanıldığı için bu arşivlerde ilgili replikler aynı altyazı kartında birleştirilmiştir. Bu, runtime `AnimaticText` komutu tam çözülmeden elde edilen doğrudan kullanılabilir ve geri alınabilir yaklaşımdır.

## Font

`FONT/demo_font.bcfnt_` kullanıcı tarafından sağlanan oyun fontundan üretilmiştir. Türkçe harfler font atlasına yeni glif olarak eklenmiş; tipografik tire/tırnak gibi işaretler güvenli mevcut gliflere eşlenmiştir. `ARACLAR/tam_yama_hazirla.py`, tam RomFS içinde orijinal font yolunu otomatik bulup yamalı fontu aynı konuma yerleştirir.

## Doğrulama

- STRL: 7/7 paket ve 6.824 kayıt.
- Cutscene kaynak metni: 97/97 satır.
- DARC: eklenen BCLIM dosyaları yeniden parse edildi.
- Render zinciri: `pic1 -> mat1 -> txl1 -> BCLIM` 50/50 sahnede doğrulandı.
- Altyazı BCLIM: RGBA4444 / format 8; pane Z değerleri 20/21.
- BLZ: tüm üretilen arşivler açılıp byte düzeyinde round-trip kontrol edildi.
- Font: BLZ round-trip + CMAP Türkçe karakter kontrolü yapıldı.

Emülatör/gerçek 3DS render testi bu ortamda yapılamadığı için `ONIZLEME/` klasöründe oluşturulan altyazı kartlarının PNG önizlemeleri bulunur.

## Ses araştırma araçları

`ARACLAR/wwise_cutscene_extract.py`, tam `Sounds/` klasöründeki beş PCK'den yedi ana sinematiğin Wwise medyasını çıkarır ve Nintendo DSP ADPCM'i WAV'a çözer. Bilinen event/media eşleşmeleri `RAPORLAR/wwise_cutscene_media_ids.csv` içindedir.

```text
python ARACLAR/wwise_cutscene_extract.py /yol/Sounds CIKAN_SESLER
```

`ARACLAR/yama_dogrula.py` hazır STRL, DARC altyazı katmanları ve Türkçe font CMAP'ini kontrol eder.
