DONKEY KONG COUNTRY RETURNS 3D - TÜRKÇE YAMA V4 SAFE FONT
=========================================================

Hedef: EUR / CTR-AYTP / Title ID 00040000000CCF00

V3 KULLANMAYIN
---------------
V3, font .tex atlasını yeniden encode ettiği için eklenen Türkçe gliflerde
bozulma oluşturdu. V4 bu yöntemi tamamen kaldırır.

V4 NASIL ÇALIŞIR?
------------------
Fontun .tex dosyaları ORİJİNAL V2 ile byte-for-byte aynıdır; hiçbir piksel veya
ETC1 bloğu yeniden encode edilmez.

Türkçe harfler güvenli kompozit çizimle oluşturulur:
  Ğ = G + breve (˘)
  ğ = g + breve (˘)
  İ = I + nokta (˙)
  Ş = S + cedilla (¸)
  ş = s + cedilla (¸)
  ı = mevcut glif indeksini korur ama ana fonttaki kalın i gövdesini kullanır

Breve/nokta/cedilla gliflerinin yatay ilerlemesi 0 yapılır ve önceki harfin
üzerine ortalanır. Böylece ana gövde oyunun kendi kalın fontudur ve aksan
sonraki harfin konumunu kaydırmaz.

KURULUM - LUMA3DS
------------------
ZIP içindeki LUMA3DS\luma klasörünü SD kart köküne birleştirin.
Dosya yolu:
  luma\titles\00040000000CCF00\romfs\euenglish.res

Eski V2/V3 euenglish.res dosyasının yerine V4 gelmelidir. Aynı anda tek yama
kullanın. Oyunun İngilizce dil kaynağını kullanması gerekir.

EMÜLATÖR
--------
Hazır yapı:
  EMULATOR\load\mods\00040000000CCF00\romfs\euenglish.res

DOĞRULAMA
---------
- 855/855 Türkçe satır V4-aware export ile birebir geri okundu.
- RST resource CRC: OK
- RST definition CRC: OK
- RST header CRC: OK
- Değiştirilen kaynaklar sadece: mslang.lng, uifnt_o.fnt, ouifnt_o.fnt
- Dört .tex font atlasının tamamı V2 ile byte-for-byte aynı.
- FNT'te yalnız 4 kayıt değişti: ˘, ˙, ¸, ı

Türkçe kullanım sayıları:
{"Ğ": 0, "ğ": 129, "İ": 37, "Ş": 29, "ş": 234, "ı": 795}

SHA-256 euenglish.res:
f2c40b247c4f305ce93e15858af9550a34177ab1e298e17fb48cd81cd870f44c

Not: Bu yöntem font atlasını yeniden encode etmediği için V3'teki bozuk glif
riskini ortadan kaldırır. Son görsel hizalama gerçek oyun içinde test edilmelidir.
