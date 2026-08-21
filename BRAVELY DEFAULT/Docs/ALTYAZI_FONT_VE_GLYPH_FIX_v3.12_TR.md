# Altyazı fontu ve ı/ğ düzeltmesi — v3.12

Bu turda altyazı fontunun hangi dosya olduğu doğrudan BCLYT kaynağından doğrulandı.

- `Graphics/UI_en/Layout/70_Subtitles/root/blyt/Subtitles.bclyt`
- `Graphics/UI_en/Layout/71_SubtitlesLower/root/blyt/Subtitles.bclyt`

İki layout da `hikari.bcfnt` adını içeriyor. İngilizce/Avrupa layoutlarında txt1 font boyutu 14×14'tür ve bunun karşılığı `Graphics/UI_en/Font/Font` içindeki 14×14 `hikari.bcfnt` dosyasıdır.

v3.11'de `ı` kaynak `i`den nokta silinerek üretiliyordu; ancak küçük fontun gövdesinin ilk satırında sola taşan tek satırlık bir omuz/serif vardır. 3DS ölçeklemesinde bu şekil ters/çarpık i gibi görünür. v3.12 noktayı kaldırdıktan sonra yalnız ilk gövde satırını bir sonraki merkezlenmiş gövde satırıyla eşitler. Alt gövde ve alt serif değişmez.

v3.11 `ğ` kuyruğunu güçlendirmeye çalışıyordu. Gerçek cihaz geri bildiriminde bunun kuyruğu bloklaştırdığı görüldü. v3.12 kaynak `g` bitmapini ve kuyruğunu birebir korur; yalnız gövdenin üstünde bir boş satır bırakarak daha geniş, tam alpha, üç satırlı breve ekler. Böylece kuyruk artık oyunun kendi `g` harfiyle aynıdır.

Kontrol: `Reports/SUBTITLE_FONT_GLYPHS_v312.png`.
