# Oyun İçi Test Rehberi

Otomatik doğrulama binary ve metin yapısını korur; ekran/font davranışını tamamen simüle etmez. PR testlerinde mümkünse şunları kontrol edin:

- metin kutusunda taşma veya kesilme
- Türkçe karakterlerin (`çğıöşüÇĞİÖŞÜ`) doğru görünmesi
- satır kırılımlarının doğal olması
- buton/kontrol simgelerinin doğru yerde kalması
- diyalog ile seslendirme/zamanlama arasında aşırı uzunluk farkı olmaması
- menü seçeneklerinin seçilebilir ve okunabilir olması
- aynı terimin farklı ekranlarda tutarlı kullanılması

Sorun bildirirken bölüm/görev, görünen Türkçe metin, beklenen metin ve mümkünse ekran görüntüsü ekleyin. Orijinal oyun dosyalarını issue'a yüklemeyin.
