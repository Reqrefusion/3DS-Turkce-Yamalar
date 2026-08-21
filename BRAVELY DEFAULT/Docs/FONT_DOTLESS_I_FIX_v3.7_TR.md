# Noktasız ı düzeltmesi — v3.7

Kullanıcı geri bildirimine göre önceki `ı` şekli doğru görünmüyordu. v3.7 herhangi bir glyph'i çevirmiyor/aynalamıyor. Her iki CFNT'de de kaynak küçük `i` hücresi alınır, bağlantısız üst nokta bileşeninin bulunduğu satırlar şeffaflaştırılır ve gövdeye dokunulmaz. Elde edilen hücre hem gerçek U+0131 `ı` glyph'ine hem runtime uyumluluk slotu U+00FE `þ` glyph'ine yazılır. Genişlik bilgisi de kaynak `i` ile eşitlenir.
