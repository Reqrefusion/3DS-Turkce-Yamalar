#!/usr/bin/env python3
"""Cave Story 3D TR v7 - ikinci manuel dil/üslup kontrolü.

V6'yı temel alır. İngilizce kaynakla görünür metinler yeniden tek tek okunarak
verilen kararları uygular. Her değişiklik için gerekçe tablosu bu dosyada tutulur.
Oyun komutlarına/event kimliklerine dokunulmaz.
"""
from pathlib import Path
import re, sys, csv

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / '000400000004D200/romfs/data'

# (dosya, eski, yeni, kategori, gerekçe)
R = []
def add(file, old, new, cat, why): R.append((file, old, new, cat, why))

# Sistem mesajı: Türkçede iyelik eki gerekiyor.
add('*SJS*', r'Azami can (\d+) arttı\.', r'Azami canın \1 arttı.', 'Dilbilgisi', '“Azami can” oyuncuya ait bir değeri anlatıyor; sayı artışında iyelik ekiyle “Azami canın … arttı” doğal Türkçedir.')

# armsitem
add('armsitem.sjs', 'Daha gelmedik mi?', 'Daha varmadık mı?', 'Doğallık', '“We there yet?” yolculuk bağlamında Türkçede doğal olarak “Daha varmadık mı?” denir.')

# cent
add('stage/cent.sjs', 'Daha erken...', 'Henüz çok erken...', 'Anlam/ton', '“You’re too early” yalnızca “erken” değil, “henüz çok erken” anlamı taşır.')
add('stage/cent.sjs', 'Kırmızı çiçek olursa\r\no katil robotlar ne ki!\r\nHepsini ezer geçeriz!', 'Kırmızı çiçekler elimizdeyken\r\no katil robotları yenmek\r\nçocuk oyuncağı!', 'Anlam/doğallık', 'Kaynak “with the red flowers in our possession” diyor; mevcut cümle koşul anlamı veriyor ve yapay kalıyordu.')
add('stage/cent.sjs', 'Robotlara karşı savaş\r\nmasal değilmiş.', 'Robotlara karşı verilen savaş\r\nsadece bir efsane değilmiş.', 'Anlam', '“wasn’t just a legend” ifadesindeki “sadece” ve “efsane” anlamı geri getirildi.')
add('stage/cent.sjs', 'Onunla yüzleştim ve\r\nonu yenmeye çalıştım.', 'Onunla yüzleştim;\r\nonu yenmek için elimden geleni yaptım.', 'Ton/anlam', '“tried my best” yalnız “denedim” değil, “elimden geleni yaptım” vurgusunu taşır.')
add('stage/cent.sjs', 'Tacın sahibi,\r\no sırada ikimizin de\r\nsaldırısından yaralanmıştı.', 'Tacı takan adam,\r\no sırada ikimizin de\r\nsaldırılarıyla yaralanmıştı.', 'Açıklık', '“crown bearer” soyut “tacın sahibi” yerine sahnedeki kişiyi açıkça anlatan “tacı takan adam” olarak verildi.')
add('stage/cent.sjs', 'Kırık Fıskiye alındı.', 'Bozuk Fıskiye alındı.', 'Terim tutarlılığı', 'Eşya adı armsitem.sjs içinde “Bozuk Fıskiye”; aynı eşya burada da aynı adla görünmeli.')

# pens1
add('stage/pens1.sjs', 'Çalılık bağlantısı hazırlanıyor...', 'Çalılıklar ile bağlantı\r\nhazırlanıyor...', 'Terim/doğallık', 'Bölgenin adı “Çalılıklar”; “Çalılık bağlantısı” yanlış tekilleştiriyordu.')
add('stage/pens1.sjs', 'Çalılık bağlantısı hazır.', 'Çalılıklar ile bağlantı kuruldu.', 'Terim/doğallık', '“Connection … complete” için doğal ve bölge adıyla tutarlı karşılık.')
add('stage/pens1.sjs', 'Nasıl gidiyor?!', 'Nasılsınız?!', 'Bağlam', 'Sue aynı anda Kazuma ve Booster’la karşılaşıyor; çoğul hitap daha uygun.')
add('stage/pens1.sjs', "Doktor'un planı\r\nplanladığı gibi ilerliyor.", "Doktor'un planı\r\naynen istediği gibi ilerliyor.", 'Doğallık', '“planı planladığı gibi” Türkçede gereksiz tekrar oluşturuyordu.')
add('stage/pens1.sjs', 'Bisiklet hurdaya dönmüş,\r\nama bir şekilde başardık..<NOD<END', 'Bisiklet hurdaya dönmüş,\r\nama bir şekilde başardık...<NOD<END', 'Noktalama', 'Üç nokta standardize edildi. Kural komut sınırıyla birlikte tanımlandı; ikinci çalıştırmada yeni metnin içine tekrar eşleşmez.')
add('stage/pens1.sjs', 'Görünen o ki sana\r\nbir borcum daha var.', 'Görünüşe göre sana\r\nyine borçlandım.', 'Doğallık', '“owe you yet another one” Türkçede “yine borçlandım” biçiminde daha doğal.')
add('stage/pens1.sjs', 'Aslında, hayır.', 'Aslında... hayır.', 'Ton/noktalama', 'Kaynağın tereddütlü “Actually. no.” duraksaması korunuyor.')

# jenka1
add('stage/jenka1.sjs', 'Hımm!', 'Aa!', 'Ünlem/ton', '“Oh, oh!” şaşırma/fark etme ünlemi; “Hımm” düşünme anlamına kayıyordu.')
add('stage/jenka1.sjs', 'Bu kez, yüzey\r\nsonunda bizim olacak!', 'Bu kez yeryüzü\r\nsonunda bizim olacak!', 'Terim tutarlılığı', '“surface” oyun boyunca “yeryüzü” olarak kullanılıyor.')
add('stage/jenka1.sjs', 'Mimigaları savunmaya çalışan\r\ncesur insanları da\r\nöldürdüler.', 'Mimigaları savunmaya çalışan\r\ncesur kadın ve erkeklerin\r\nölümünden de onlar sorumluydu.', 'Anlam', 'Kaynak “brave men and women” diyor ve ölüm sorumluluğunu vurguluyor.')
add('stage/jenka1.sjs', 'Evet.', 'Kesinlikle.', 'Ton', '“Definitely.” basit “Evet”ten daha güçlü bir kesinlik taşır.')
add('stage/jenka1.sjs', 'Bu benim.', 'O benimki.', 'Bağlam/doğallık', 'Jenka uzaktaki köpeği tanımlıyor; “That one’s mine” için “O benimki” daha doğru.')
add('stage/jenka1.sjs', 'Sözde yüzeye kadar\r\ninmişler...', 'Sözde yeryüzüne kadar\r\ninmişler...', 'Terim tutarlılığı', '“surface” → “yeryüzü” terminolojisi.')
add('stage/jenka1.sjs', 'Anlıyor musun?', 'Şimdi anlıyor musun?', 'Ton', '“Do you yet realize it?” önceki açıklamanın sonucuna işaret ediyor.')
add('stage/jenka1.sjs', "Kırmızı Çiçek'in\r\nne kadar tehlikeli olduğunu biliyor\r\nmusun?", "Kırmızı Çiçek'in aslında\r\nne kadar tehlikeli olduğunun\r\nfarkında mısın?", 'Anlam/doğallık', '“realize how dangerous” bilgi sormaktan çok farkındalık vurgusudur.')
add('stage/jenka1.sjs', 'aptalca olur,\r\no eski felaketi\r\nyeniden yaşatır...', 'geçmişteki trajedinin\r\nyeniden yaşanmasına\r\naptalca izin vermek olur...', 'Anlam/doğallık', '“foolishly allowing an encore of the same tragedy” daha doğrudan ve doğal aktarıldı.')
add('stage/jenka1.sjs', 'Sen yüzeyden gelen\r\nbir askersin.', 'Sen yeryüzünden gelen\r\nbir askersin.', 'Terim tutarlılığı', '“surface” → “yeryüzü”.')

# momo
add('stage/momo.sjs', 'Doktor’un yanında çalışmayı\r\ngöze aldım.', "Doktor'un yanında çalışarak\r\nşansımı denedim.", 'Anlam', '“I took my chance working…” risk almak değil “şansını denemek” anlamında.')
add('stage/momo.sjs', 'Ama çiçek tohumları\r\nbulununca, Doktor için\r\nişe yaramaz oldum.', "Ama çiçek tohumlarının yeri\r\nbulununca Doktor'un\r\nbana ihtiyacı kalmadı.", 'Anlam/doğallık', '“after the flower seeds were located / I was of no use” neden-sonuç ilişkisi daha doğal kuruldu.')
add('stage/momo.sjs', 'Beni apar topar adadan aşağı attılar.\r\nPek nazikçe sayılmaz...', 'Beni apar topar adadan aşağı attılar.\r\nPek nazikçe değildi...', 'Doğallık', '“Pek nazikçe sayılmaz” dilbilgisel olarak yapaydı.')
add('stage/momo.sjs', 'Plantasyonda çalışan Mimigaların', "Plantasyon'da çalışan Mimigaların", 'Yazım', 'Özel bölge adına gelen ek kesmeyle ayrıldı.')
add('stage/momo.sjs', 'Roketi bitirebilmem için\r\nen azından biraz elektriğe ihtiyacım var.', 'Roketi bitirmek için\r\nbelli miktarda elektriğe ihtiyacım var.', 'Anlam/doğallık', '“minimum amount of electricity” için “belli miktarda elektrik” daha doğru; “en azından biraz” konuşma dili açısından gevşekti.')
add('stage/momo.sjs', 'Plantasyondaki\r\nfıskiyelerden birini alabilirsem,\r\nbelki yeter.', "Plantasyon'daki fıskiyelerden\r\nbirini bulabilirsem,\r\nbelki yeter.", 'Yazım/doğallık', 'Özel ad eki düzeltildi; “get one” burada bir fıskiyeyi edinmek/bulmak anlamında.')
add('stage/momo.sjs', 'Kırık Fıskiyeyi göster.', 'Bozuk Fıskiyeyi göster.', 'Terim tutarlılığı', 'Eşya adı “Bozuk Fıskiye” olarak sabit.')
add('stage/momo.sjs', 'Kendine ukalaca\r\n"ünlü teknisyen" der.', 'Kendini ukalaca\r\n"ünlü teknisyen" diye tanıtır.', 'Doğallık', 'Türkçede kişinin kendine unvan vermesi “kendini … diye tanıtmak” şeklinde doğal.')

# curly
add('stage/curly.sjs', "Büyükanne Jenka eskiden\r\nKum Bölgesi'yle taaa çok uzun zaman\r\nönce\r\ntüm köpekleriyle ilgilenirdi.", "Büyükanne Jenka, taaa eskiden\r\nbütün köpekleriyle birlikte\r\nKum Bölgesi'ne göz kulak olurdu.", 'Anlam/doğallık', '“look after the Sand Zone … with all her puppies” daha doğru sözdizimiyle aktarıldı.')
add('stage/curly.sjs', 'Bu küçüklerle\r\nhatırladığım zamandan beri\r\nbirlikteyim.', 'Kendimi bildim bileli\r\nbu küçüklerle birlikteyim.', 'Doğallık', '“since before I can remember” için Türkçenin yerleşik karşılığı “kendimi bildim bileli”.')
add('stage/curly.sjs', 'Görünüşe göre buna\r\n"hafıza kaybı" deniyor.', 'Görünüşe göre buna\r\n"hafıza kaybı" diyorlar.', 'Doğallık', 'Konuşma dili ve kaynak tondaki “so-called” daha doğal verildi.')
add('stage/curly.sjs', "Kutup Yıldızı'nın bayağı\r\nhırpalanmış.", "Kutup Yıldızı bayağı\r\nhırpalanmış.", 'Doğallık/dilbilgisi', 'Kaynak oyuncunun silahını işaret ediyor. Türkçede eşya adının üzerine zoraki iyelik eki bindirmek yerine bağlamın sahipliği taşımasına izin vermek daha doğal: “Kutup Yıldızı bayağı hırpalanmış.”')
add('stage/curly.sjs', "Benim Makineli Tüfek'le\r\ntakas etmek ister misin?", 'Makineli Tüfeğimle\r\ntakas etmek ister misin?', 'Dilbilgisi/anlam', 'Kaynak “my machine gun”; Türkçede iyelik doğrudan “Makineli Tüfeğimle” ile verilir.')

# ballo1/2
add('stage/ballo1.sjs', 'Çok, çok uzun zaman önce,\r\nbüyü gücüne duyduğum hırsı\r\nhiçbir bedelden korkmadan', 'Çok, çok uzun zaman önce,\r\nbüyü gücüne olan hırsımın,\r\ncezasını düşünmeden', 'Anlam/üslup', 'Kaynakta Ballos hırsının büyümesine izin verdiğini anlatıyor; özne-yüklem ilişkisi düzeltildi.')
add('stage/ballo1.sjs', 'dizginsizce büyüttüm.', 'dizginsizce büyümesine izin verdim.', 'Anlam/üslup', '“allowed my drive … to grow recklessly” doğrudan karşılandı.')
add('stage/ballo1.sjs', 'Bu güç öylesine öfkeli ve\r\ndurdurulamazdı ki...', 'Bu güç öylesine vahşi ve\r\ndurdurulamazdı ki...', 'Üslup', 'Cansız “güç” için “öfkeli” yapaydı; “furious force” bağlamında “vahşi” daha doğal.')
add('stage/ballo1.sjs', 'O zaman elimden yalnızca gülmek geldi...', 'O an yapabildiğim tek şey gülmekti...', 'Doğallık/ton', 'Trajik monologda daha doğal ve ağır bir Türkçe ritmi.')
add('stage/ballo1.sjs', 'Jenka beni mühürledi;\r\nama büyüm geçen her dakika\r\ndaha da şiddetleniyordu.', 'Jenka beni mühürledi;\r\no sırada büyüm her geçen dakika\r\ndaha da şiddetleniyordu.', 'Anlam', 'Kaynakta karşıtlık (“ama”) değil eşzamanlılık var.')
add('stage/ballo1.sjs', 'Bu korkunç büyü öfkeme\r\nson verecek kişiyi...', 'Büyümün korkunç öfkesine\r\nson verecek kişiyi...', 'Dilbilgisi/doğallık', '“büyü öfkesi” tamlaması doğal Türkçeye çevrildi.')
add('stage/ballo2.sjs', 'Negatif güç\r\nonu yenince zayıfladı mı?', 'Ballos yenilince\r\nbu karanlık güç zayıfladı mı?', 'Doğallık/açıklık', '“negative power” için “negatif güç” mekanik kalıyordu; özne de açıklaştırıldı.')
add('stage/ballo2.sjs', 'Başın nasıl?', 'Başın iyi mi?', 'Doğallık', 'Türkçede bir darbe sonrası sağlık sorusu “Başın iyi mi?” şeklinde daha doğal.')

# fall
add('stage/fall.sjs', 'Görünüşe göre sana bir\r\nborcum daha var.', 'Görünüşe göre sana\r\nyine borçlandık.', 'Anlam', 'Kaynak “we owe you”; konuşan taraf çoğul olarak kendisi ve Misery’yi kastediyor.')
add('stage/fall.sjs', 'Görevimiz bitti ya...\r\nSakin bir yerde\r\ngüzel manzarayla yaşamak istiyorum.', 'Görevimiz tamamlandı...\r\nSakin, manzarası güzel\r\nbir yerde yaşamak istiyorum.', 'Doğallık/ton', 'Türkçe sözdizimi ve final sahnesinin sakin tonu iyileştirildi.')

# ring2/ring3
add('stage/ring2.sjs', 'Mimiga, kırmızı çiçeği\r\nilaç olarak verdiğimizde\r\nçılgına dönüyor.', 'Mimigalar, kırmızı çiçeği\r\nilaç gibi verdiğimizde\r\nçılgına dönüyor.', 'Dilbilgisi/doğallık', 'Tür adı çoğul/genel anlamda kullanılıyor; özne-yüklem uyumu düzeltildi.')
add('stage/ring2.sjs', 'Kırmızı çiçek\r\ngizli gücü açığa çıkarır.', 'Kırmızı çiçek onların\r\ngizli yeteneklerini açığa çıkarır.', 'Anlam', '“latent abilities” çoğul “gizli yetenekler” ve Mimigalara aitlik vurgusu taşır.')
add('stage/ring2.sjs', 'Ve ben şimdi onu\r\nayıklayıp güçlendirdim.', 'Şimdi o etken maddeyi\r\nayırıp yoğunlaştırmayı başardım.', 'Anlam/üslup', 'Bilimsel konuşmada “extracted and intensified” için “etken maddeyi ayırıp yoğunlaştırmak” daha doğru.')
add('stage/ring3.sjs', 'Efendisini unutacak kadar aptal\r\nolanların özgür iradeye ihtiyacı yok.', 'Efendisini unutacak kadar aptal\r\nolanlara özgür irade gerekmez.', 'Doğallık', 'Türkçe cümle yapısı daha akıcı ve tehditkâr tona uygun.')

# prefa1
add('stage/prefa1.sjs', "Profesör Booster'in notu.", "Profesör Booster'ın notu.", 'Yazım', 'Booster adına gelen ekin ünlü uyumu düzeltildi.')
add('stage/prefa1.sjs', 'v2.0 ise çok daha kullanışlı olacak.', 'v2.0 ise çok daha önemli olacak.', 'Anlam', '“even more indispensable” yalnız “kullanışlı” değil “daha vazgeçilmez/önemli” anlamında.')

# eggx2
add('stage/eggx2.sjs', 'Doktorun zaferi', "Doktor'un zaferi", 'Yazım', 'Özel ada gelen ek kesmeyle ayrıldı.')
add('stage/eggx2.sjs', 'Artık an meselesi...\r\nMimiga ordusu\r\nyüzeye saldırmaya hazır olacak...', 'Mimiga ordusunun\r\nyeryüzüne saldırmaya hazır olması\r\nartık an meselesi...', 'Doğallık/anlam', 'Kaynağın tek cümlelik “only a matter of time” yapısı doğal Türkçeyle yeniden kuruldu.')
add('stage/eggx2.sjs', 'İhtiyacım olan Uçan Ejderha\r\nsağ salim yumurtadan çıksın diye.', 'İhtiyacım olan Uçan Ejderha\r\ngüvenle yumurtadan çıksın diye.', 'Doğallık', '“hatched safely” için “güvenle” daha doğal.')
add('stage/eggx2.sjs', 'Senin için fazla tehlikeli\r\nbir seçim mi?', 'Böyle bir seçim sana\r\nfazla mı tehlikeli geliyor?', 'Doğallık', 'Türkçede değerlendirme sorusu daha doğal ifade edildi.')

# pole
add('stage/pole.sjs', 'Biraz daha uğraşsaydım, o silah\r\ninanılmaz güçlü bir şeye\r\ndönüşecekti.', 'Üzerinde biraz daha çalışsaydım,\r\ninanılmaz güçlü bir silaha\r\ndönüşecekti.', 'Doğallık/anlam', 'Silah ustasının “work put in” ifadesi “üzerinde çalışmak” olarak doğal karşılandı.')
add('stage/pole.sjs', 'Silahların her zaman\r\n insanın kendi eliyle yapılması\r\n gerektiğine inanarak yetiştim.', 'Silahını insanın kendi yapması\r\ngerektiğine inanarak yetiştim.', 'Doğallık', 'Gereksiz boşluklar ve ağır edilgen yapı temizlendi.')
add('stage/pole.sjs', 'Başkasından gelen güçle\r\nkendini dev sananlar...\r\nEn başta o güç kendilerinin değildi.', 'Kendilerine ait olmayan bir güçle\r\nböbürlenenler...', 'Anlam/üslup', 'Kaynak cümle bir sonraki parçaya bağlanıyor; V6 gereksiz ikinci cümle ekliyordu.')
add('stage/pole.sjs', '...Sonra da kendi eksiklerini\r\nkullandıkları silaha atanlar.', '...sonra da kendi eksiklerinin\r\nsuçunu kullandıkları silaha atanlar.', 'Dilbilgisi/doğallık', '“blaming their own shortcomings on the equipment” doğal Türkçe tamlamayla verildi.')
add('stage/pole.sjs', 'Ama şimdi, silahımı senin\r\nkullandığını görünce,\r\nkendi ellerinle... nedense,\r\nçok duygulandım...', 'Ama şimdi silahımı\r\nsenin ellerinde görünce\r\ngerçekten çok duygulandım...', 'Doğallık/üslup', 'V6’daki kopuk “kendi ellerinle... nedense” ifadesi kaynak anlamı bozmadan akıcılaştırıldı.')
add('stage/pole.sjs', 'Kutup Yıldızı gibi bitmemiş bir\r\nsilahı\r\nbu kadar kullanman...', 'Kutup Yıldızı gibi tamamlanmamış\r\nbir silahı bu kadar iyi kullanman...', 'Anlam/doğallık', '“to this degree” kullanım becerisini vurgular; “bu kadar iyi” daha açık.')
add('stage/pole.sjs', 'Hâlâ çok hassas bir denge var\r\nbu dünyada...', 'Bu dünyada çok hassas\r\nbir denge vardır...', 'Üslup', 'Felsefi monolog için devrik ve konuşma dilindeki yapı daha akıcı hâle getirildi.')
add('stage/pole.sjs', 'Üretenlerle, başkalarının\r\nürettiklerinden yararlananlar arasında.', 'Üretenlerle, başkalarının\r\nürettiklerini deneyimleyenler arasında.', 'Anlam', 'Kaynak “experience the creations of others”; yalnız faydalanma değil, yaratılan şeyi deneyimleme vurgusu var.')
add('stage/pole.sjs', 'Bunun farkında değildim diyemem.\r\nAma hiç yaşamamıştım.', 'Bunun farkındaydım,\r\nama daha önce hiç yaşamamıştım.', 'Doğallık', 'Çifte olumsuzluk sadeleştirildi, anlam korundu.')
add('stage/pole.sjs', 'Bu yüzden, üretmeye devam edeceğim\r\ngücüm yettikçe.', 'Bu nedenle gücüm yettiğince\r\nüretmeye devam edeceğim.', 'Doğallık', 'Devrik yapı düzeltilerek monolog akıcılaştırıldı.')

# comu / hell / maze
add('stage/comu.sjs', 'Toroko da olmasın...', 'Toroko da mı...', 'Doğallık/ton', '“Not Toroko too…” kaygılı bir soru/yarım cümle; “olmasın” yanlış çağrışım yapıyordu.')
add('stage/hell1.sjs', 'Sayacı etkinleştirildi.', 'Sayaç 290 etkinleştirildi.', 'Dilbilgisi/terim', 'Kaynak “The 290 Counter is activated.”; özne eksikti. Metni rakamla başlatmadan tam sayaç adı geri getirildi; böylece SJS sayısal-parametre ayrıştırıcısıyla da çakışmıyor.')
add('stage/tt_hell1.sjs', 'Sayacı etkinleştirildi.', 'Sayaç 290 etkinleştirildi.', 'Dilbilgisi/terim', 'Time Trial kopyasında aynı kaynak anlam ve SJS güvenliği gerekçesiyle aynı düzeltme.')
add('stage/mazea.sjs', 'Neyse, büyütülecek şey değil..', 'Neyse, büyütülecek bir şey değil...', 'Dilbilgisi/noktalama', 'Eksik belirsiz artikel ve noktalama düzeltildi.')
add('stage/mazea.sjs', 'Özür!', 'Kusura bakma!', 'Doğallık', 'Konuşma dilinde “Sorry!” için “Kusura bakma!” daha doğal.')
add('stage/mazeb.sjs', 'Belki de bu şanssızlığın\r\niçinden bir şans doğdu.', 'Belki bu talihsizliğin\r\niyi bir yanı vardır.', 'Doğallık', '“good luck arising from misfortune” kelimesi kelimesine kalmıştı; Türkçe doğal ifade kullanıldı.')
add('stage/mazes.sjs', 'Hadi, inine!', 'Hadi, yaratığın inine gidelim!', 'Açıklık/doğallık', '“onto the lair” cümlesinde kimin ini olduğu ve hareket fiili V6’da eksikti.')
add('stage/mazes.sjs', 'Dinlenmen gerekmez mi,\r\nkaçmaya çalışacağına,\r\nha?', 'Kaçmaya çalışacağına\r\ndinlensen daha iyi değil mi, ha?', 'Doğallık', 'Türkçe söz dizimi yeniden kuruldu.')
add('stage/mazes.sjs', 'Size yardım ettiğim...\r\nARAMIZDA KALSIN!', 'Size yardım ettiğimi...\r\nARAMIZDA KALSIN!', 'Dilbilgisi', '“Me helping you guys” bir sonraki “aramızda kalsın” yüklemine nesne olarak bağlanıyor; -i hâli gerekli.')
add('stage/mazeo.sjs', 'Kendimden hayal kırıklığına uğradım.', 'Kendimden hiç memnun değilim.', 'Doğallık', '“I’m disappointed in myself” için Türkçede daha doğal ifade.')

# diğer tutarlılık/doğallıklar
add('stage/lounge.sjs', 'Evet, yeryüzü robotları bu adaya\r\nsaldırmıştı.', 'Evet, yeryüzünden gelen robotlar\r\nbu adaya saldırmıştı.', 'Doğallık/terim', '“surface robots” Türkçede “yeryüzünden gelen robotlar” olarak daha doğal.')
add('stage/gard.sjs', 'Sen, yüzeyden gelen\r\nşu inatçı askersin!', 'Sen, yeryüzünden gelen\r\nşu inatçı askersin!', 'Terim tutarlılığı', '“surface” → “yeryüzü”.')
add('stage/frog.sjs', 'Sen... yüzeyden gelen\r\no asker değil misin?', 'Sen... yeryüzünden gelen\r\no asker değil misin?', 'Terim tutarlılığı', '“surface” → “yeryüzü”.')
add('stage/cthu.sjs', 'Sen yüzeyden bir askersin,\r\ndeğil mi?', 'Sen yeryüzünden bir askersin,\r\ndeğil mi?', 'Terim tutarlılığı', '“surface” → “yeryüzü”.')
add('stage/pixel.sjs', 'Yüzeyde üretilen robotlar\r\nsuda pek hareket edemez.', 'Yeryüzünde üretilen robotlar\r\nsuda pek hareket edemez.', 'Terim tutarlılığı', '“surface” → “yeryüzü”.')
add('stage/drain.sjs', 'Öte yandan akan su sesi\r\ngeliyor.', 'Öbür taraftan akan su sesi\r\ngeliyor.', 'Doğallık', 'Mekânsal “other side” için “öbür taraftan” daha doğal.')
add('stage/drain.sjs', 'Devam etmek zorundayız.\r\nİlerlemeliyiz.', 'İlerlemeye devam etmek zorundayız.', 'Doğallık', 'Aynı anlamı iki kez söyleyen tekrar kaldırıldı.')
add('stage/priso2.sjs', 'Siyah bir rüzgâr bedeninden geçiyor.', 'Kara bir rüzgâr bedeninden geçiyor.', 'Terim/üslup', 'Hell sahnelerinde aynı ifade “Kara bir rüzgâr” olarak kullanılıyor; atmosferik ve tutarlı.')
add('stage/tt_ballo1.sjs', 'Tebrikler!\r\nKutsal Alan Süre Denemesi Modu!', "Tebrikler!\r\nKutsal Alan Süre Denemesi'ni tamamladın!", 'Doğallık/UI', 'V6 yalnız mod adını ünlemle gösteriyordu; kaynak “beating … Mode” tamamlamayı tebrik ediyor.')

# credits_text varyantları ve credit.sjs için ortak manuel jenerik düzeltmeleri
CREDIT_REPL = [
    ("Sue'nun kendine", "Sue'nun dedesi gibi", 'Doğallık', '“grandfather figure” ifadesinin ilk satırı; Türkçede “dedesi gibi gördüğü kişi” yapısını kurmak için doğal biçime çevrildi.'),
    ('dede bildiği kişi', 'gördüğü kişi', 'Doğallık', '“grandfather figure” ifadesinin ikinci satırı; “dedesi gibi gördüğü kişi” doğal Türkçe kalıbını tamamlıyor.'),
    ('İkinci adam', 'İki numara', 'Terim/ton', 'Jack oyun içinde kendisini köyün “number-two”su olarak tanıtıyor; “iki numara” bu espriyi koruyor.'),
    ('Yaşlı', 'Dede', 'Anlam', 'Bu jenerik satırında kaynak “The Grandpa Mimiga”; yalnız yaşlı değil, “dede” niteliği var.'),
    ('Büyük uçucu: Basu', 'Koca uçan: Basu', 'Doğallık', '“Büyük uçucu” Türkçede mekanik; mizahi jenerik tonunda “Koca uçan” daha doğal.'),
    ('Birden çoğa: Polish', 'Birden çoğalır: Polish', 'Anlam/doğallık', '“From one, many” yaratığın çoğalma özelliğini anlatıyor; fiilli ifade daha açık.'),
    ('Gerçek kahramanların rakibi', 'Gerçek kahramanlarla kapışır', 'Anlam/ton', 'Kaynak “True heroes meet the Red Ogre”; jenerik üslubunda eylem korunarak çevrildi.'),
    ('Şişmiş makine', 'Şişkin makine', 'Doğallık', '“swollen mech” için “şişkin” sıfatı daha doğal.'),
]

# credit.sjs satırları CRLF içinde [] payload; satır içi karşılıklar ayrıca uygulanır.
CREDIT_SJS_REPL = [
    ("[ Sue'nun kendine]0000-0016\r\n[Â  dede bildiği kişi]0000-0016", "[ Sue'nun dedesi gibi]0000-0016\r\n[Â  gördüğü kişi]0000-0016"),
    ('[ İkinci adam]0000-0032', '[ İki numara]0000-0032'),
    ('[ Yaşlı]0000-0016\r\n[Â  Mimiga]0000-0016', '[ Dede]0000-0016\r\n[Â  Mimiga]0000-0016'),
    ('[ Büyük uçucu: Basu]0047-0048', '[ Koca uçan: Basu]0047-0048'),
    ('[ Birden çoğa: Polish]0059-0048', '[ Birden çoğalır: Polish]0059-0048'),
    ('[ Gerçek kahramanların rakibi]0000-0032', '[ Gerçek kahramanlarla kapışır]0000-0032'),
    ('[ Şişmiş makine]0000-0032', '[ Şişkin makine]0000-0032'),
]


def dec(p: Path):
    return p.read_bytes().decode('cp1254', 'surrogateescape')
def enc(s: str): return s.encode('cp1254', 'surrogateescape')

def exact_replace(rel, old, new):
    p=ROOT/rel; s=dec(p)
    n=s.count(old)
    if n==0: return 0
    p.write_bytes(enc(s.replace(old,new)))
    return n

def regex_replace_all(oldpat,newpat):
    total=0
    rx=re.compile(oldpat)
    for p in ROOT.rglob('*.sjs'):
        if p.name=='credit.sjs': continue
        s=dec(p); ns,n=rx.subn(newpat,s)
        if n: p.write_bytes(enc(ns)); total+=n
    return total

def main():
    logs=[]
    for file,old,new,cat,why in R:
        if file=='*SJS*':
            n=regex_replace_all(old,new)
        else:
            n=exact_replace(file,old.replace('\\r\\n','\r\n'),new.replace('\\r\\n','\r\n'))
        logs.append((file,cat,n,why,old,new))
        print(f'{file}: {n} | {cat} | {why}')
    # Credits text variants
    for p in sorted(ROOT.glob('credits_text*.txt')):
        s=dec(p); changed=0
        for old,new,cat,why in CREDIT_REPL:
            o=old.replace('\\r\\n','\r\n'); nn=new.replace('\\r\\n','\r\n')
            c=s.count(o)
            if c:
                s=s.replace(o,nn); changed+=c
                logs.append((p.name,cat,c,why,old,new))
        if changed: p.write_bytes(enc(s))
        print(f'{p.name}: {changed} jenerik düzeltme')
    # credit.sjs özel ikili iskeleti bozmadan yalnız [] içindeki görünür payloadlar
    p=ROOT/'credit.sjs'; s=dec(p); changed=0
    for old,new in CREDIT_SJS_REPL:
        c=s.count(old)
        if c:
            s=s.replace(old,new); changed+=c
    if changed: p.write_bytes(enc(s))
    print('credit.sjs:',changed,'payload düzeltme')

    out=Path(__file__).resolve().parents[1]/'RAPORLAR'/'V7_UYGULAMA_GUNLUGU.tsv'
    out.parent.mkdir(exist_ok=True)
    with out.open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f,delimiter='\t'); w.writerow(['dosya','kategori','adet','gerekce','eski','yeni']); w.writerows(logs)
    print('Günlük:',out)

if __name__=='__main__': main()
