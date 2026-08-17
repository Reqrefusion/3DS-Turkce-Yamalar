https://gamebanana.com/mods/705559
# Ace Attorney Trilogy 3DS Türkçe v27 — Yüzey Tamamlama + İ Origin Fix

Bu sürüm çalışan v26 tabanını korur.

## Yeni
- Büyük `İ`, küçük `ı` ile aynı güvenli renderer-origin düzeltmesini alır: yalnız çizim konumu 2 px sola; cursor/advance korunur.
- GS2/GS3: New Game → **Yeni Oyun**, Continue → **Devam**, SAVE → **KAYDET**, LOAD → **YÜKLE**.
- GS2/GS3 dil düğmeleri: **İngilizce / Japonca**.
- GS1/GS2/GS3 araştırma eylemleri: Move/Examine/Present/Talk → **Git / İncele / Sun / Konuş**.
- GS2/GS3 stilize CHECK → **İNCELE**.
- GS1/GS2/GS3 Event → **Olay**.
- GS3 QUIT / Quit the game? → **ÇIKIŞ / Oyundan çık?**.
- 5+4+5 bölüm başlığı görsel olarak denetlendi; 14'ü de zaten Türkçe olduğundan korunmuştur.

## Luma EUR kurulumu
`code.bin` doğrudan `sd:/luma/titles/0004000000133300/code.bin` konumunda olmalıdır.
`romfs` klasörü aynı TitleID klasörünün altındadır.

**code.bin'i exefs klasörüne koyma.**

## Araçlar
`tools/` altında code.bin patcher, IPS aracı, BCH texture aracı, pack/LZ11 aracı, yüzey UI patcher ve önceki analiz yardımcıları bulunur. Sistem fontları kullanılır; font dosyaları pakete dahil değildir.
