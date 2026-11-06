# Professor Layton and the Miracle Mask Türkçe yama

## Kurulum

Kurulum hedefi ve gereken girdiler için aşağıdaki kullanım belgesine bakın.

Ana hedef EUR, `00040000000A8600` değeridir. Hazır kurulum ağacı bu klasörde bulunmuyorsa kendi temiz oyun arşivinizden çıktı üretmeniz gerekir.

## Çeviri ve araçlar

Ana çeviri projesi `ceviri/layton_tr.jsonl`; CSV çalışma tablosu `ceviri/layton_tr.csv` dosyasıdır. Hazır senaryo girdileri `kaynaklar/hazir_xs/` altındadır.

Oyun klasöründe, temiz oyun arşivinizi kullanarak:

```text
python araclar/layton5_tool.py fa-replace <temiz_lt5_uk.fa> kaynaklar/hazir_xs <cikti_lt5_uk.fa> --report <rapor.json>
```

Üretilen dosya oyun içinde `romfs/lt5/arc/lt5_uk.fa` yoluna yerleştirilir. Özgün girdinin üzerine yazmayın. Kaynak doğrulaması ve doğrudan JSONL aktarımı için [kullanım notlarına](belgeler/kullanim_notlari.md) bakın.

[Yamanın kaynak sayfası](https://gamebanana.com/mods/701527)

## Açıklamalar

- [FORMAT TR](belgeler/FORMAT_TR.md)
- [REFERENCES](belgeler/REFERENCES.md)
- [kullanim notlari](belgeler/kullanim_notlari.md)
