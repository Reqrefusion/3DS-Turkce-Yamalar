MLSS UI TÜRKÇELEŞTİRME ARACI
============================

Bu klasör grafik olarak çizilen arayüz yazılarını yeniden üretmek için kullanılan
araçları ve çeviri tablosunu içerir.

DOSYALAR
--------
mlss_ui_tool.py
- Obj/EU altındaki BUI.dat, FUI.dat, KUI.dat ve MGUI.dat arşivlerini okur.
- _CA_INFO_ eşlemesini çözer.
- Dil varyantlarını karşılaştırarak yerelleştirilmiş sprite parçalarını bulur.
- Türkçe metni sprite grafiklerine işler.
- Backwards LZ77 verisini yeniden sıkıştırır.
- BG4 arşivini yeniden paketler ve değişen kayıtları doğrular.

ui_translations.csv
- Grafik UI çevirilerinin düzenlenebilir tablosudur.
- archive: hedef UI arşivi
- asset: dil bağımlı kaynak adı
- animation: ilgili animasyon/etiket indeksi
- english: İngilizce karşılık
- turkish: Türkçe karşılık
- style: çizim stili
- enabled: satırın build'e katılıp katılmayacağı

requirements_ui.txt
- UI aracının ihtiyaç duyduğu Python paket adlarını içerir.

KULLANIM
--------
1. Python ortamında gerekli paketleri kurun:
   pip install -r requirements_ui.txt

2. Oyundan çıkarılmış Obj/EU klasörünü hazırlayın. Bu klasörde en az:
   BUI.dat
   FUI.dat
   KUI.dat
   MGUI.dat
   bulunmalıdır.

3. Windows:
   UI_BUILD.bat "C:\oyun\romfs\Obj\EU" "C:\cikti\Obj\EU"

   Linux/macOS:
   ./ui_build.sh "/oyun/romfs/Obj/EU" "/cikti/Obj/EU"

4. Elle komut:
   python mlss_ui_tool.py "Obj/EU" ui_translations.csv "cikti/Obj/EU" --preview "onizleme"

NOTLAR
------
- Araç yalnızca dil bağımlı grafik kayıtlarını değiştirir.
- Kaynak oyunun dosyaları bu araç klasöründe bulunmaz.
- UI çizimi için sistemde bulunan Türkçe karakter destekli bir font kullanılır;
  font dosyası pakete eklenmemiştir.
- Hazır yama için bu aracı çalıştırmanız gerekmez. Yama/romfs altında oluşturulmuş
  BUI.dat, FUI.dat, KUI.dat ve MGUI.dat zaten bulunur.
