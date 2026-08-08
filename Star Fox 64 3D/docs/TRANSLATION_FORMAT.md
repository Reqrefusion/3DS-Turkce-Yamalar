# Çeviri JSONL Biçimi

`translations/tr_TR.jsonl` dosyasında her fiziksel satır tek bir JSON kaydıdır.

Alanlar:

- `file`: hedef MSBT dosya kimliği
- `index`: metnin MSBT TXT2 indeksi
- `label`: kaynak label bilgisi
- `source_sha256`: orijinal kaynak metnin SHA-256 değeri; metnin kendisi repoda tutulmaz
- `source_line_count`: kaynak metindeki satır sayısı
- `source_max_visible_chars`: kontrol tokenları hariç kaynak en uzun satır karakter sayısı; CI bunun üzerine en fazla +8 karakter tolerans verir
- `control_tokens`: korunması gereken MSBT kontrol tokenları
- `translation`: Türkçe metin

Katkıcıların normalde yalnızca `translation` alanını değiştirmesi gerekir. Meta alanlarını elle değiştirmeyin.
