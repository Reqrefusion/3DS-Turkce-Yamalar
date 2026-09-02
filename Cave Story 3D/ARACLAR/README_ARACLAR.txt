Cave Story 3D TR - araçlar (Python 3)
=====================================
Görsel araçları Pillow (PIL) kullanır.

V5 ana araçları:
  quality_pass_v5.py          V4 yerelleştirilmiş data üzerinde 135 manuel/anlam/yazım
                              düzeltmesini komutları koruyarak uygular.
  bilingual_audit_tool.py     İngilizce ve Türkçe SJS görünür metin parçalarını komut
                              sınırlarına göre hizalayıp TSV üretir.
  glossary_qa.py              bilinen eski/yanlış terimlerin geri dönüp dönmediğini tarar.
  text_layout_qa.py           aşırı uzun görünür SJS satırlarını raporlar.
  english_residue_review.py   english_residue_scanner çıktısını özel ad/ünlem/dahili
                              etiket/incele sınıflarına ayırır.

Temel QA:
  python sjs_structure_qa.py <ingilizce_data> <yerellestirilmis_data>
  python english_residue_scanner.py <ingilizce_data> <yerellestirilmis_data> -o residue.tsv
  python english_residue_review.py residue.tsv -o residue_review.tsv
  python glossary_qa.py <yerellestirilmis_data> -o glossary.tsv
  python text_layout_qa.py <yerellestirilmis_data> --limit 42 -o layout.tsv
  python image_format_qa.py <ingilizce_data> <yerellestirilmis_data> -o image_qa.txt
  python bilingual_audit_tool.py <ingilizce_data> <yerellestirilmis_data> -o bilingual.tsv

Türkçe sözlük QA:
  python dictionary_residue_qa.py <yerellestirilmis_data> <utf8_turkce_kelime_listesi> -o dict.tsv
Kelime listesi paketlenmez; ana yamayı kullanmak için bu araç/kelime listesi gerekmez.

Jenerik/görsel araçları:
  credit_sjs_tool.py          credit.sjs özel 0xC2 düzenli dönüştürücü
  credits_text_tool.py        altı credits_text*.txt varyantını işler
  ui_texture_localizer.py     textbox/caret/minimap/pixel gömülü yazılarını üretir
  visual_assets_tool.py       title/loading/splash görsellerini üretir
  image_asset_inventory.py    bitmap/texture envanteri ve contact sheet oluşturur
  image_format_qa.py          boyut ve BMP bit derinliğini doğrular

Eski geçiş araçları da karşılaştırma/geri üretim amacıyla pakette tutulmuştur:
quality_pass_v4.py, word_fixes_v3.py.

=== V6 MANUEL KONTROL ARAÇLARI ===
manual_review_v6.py <romfs/data>
  İngilizce kaynakla tek tek karşılaştırılarak kararlaştırılmış SJS düzeltmelerini uygular.
  SJS komutlarını korur; V6 üzerinde ikinci kez çalıştırıldığında 0 değişiklik üretir.

manual_credits_review_v6.py <romfs/data>
  credit.sjs ve altı credits_text*.txt jenerik varyantındaki manuel kalite düzeltmelerini uygular.
  credit.sjs içindeki 32 adet 0xC2 yerleşim baytını korur.

v6_manual_pipeline.py <romfs/data>
  Yukarıdaki iki manuel geçişi sırayla tek komutla çalıştırır.

v6_final_qa.py <ingilizce_romfs_data> <turkce_romfs_data>
  113 SJS komut/event yapısı, credit.sjs ikili yapısı, 42 karakter satır sınırı,
  jenerik rol kalıntıları ve değiştirilmiş 12 görselin biçimini toplu doğrular.

V7 EK ARAÇLARI
==============
manual_review_v7.py
  V6 -> V7 ikinci manuel dil/üslup kararlarını uygular. Kurallar gerekçe bilgisi taşır.
  Kullanım: python manual_review_v7.py <yerellestirilmis_data>

v7_manual_pipeline.py
  V7 geçişi + temel QA zinciri.
  Kullanım: python v7_manual_pipeline.py <ingilizce_data> <yerellestirilmis_data> --reports <rapor_klasoru>

manual_decision_report_v7.py
  Paket hazırlanırken V6/V7 hizalı karar tablolarını üretmek için kullanılmıştır.
  Çıktılar RAPORLAR/V7_*KARAR* ve V7_*GEREKCELI* dosyalarında hazır gelir.
