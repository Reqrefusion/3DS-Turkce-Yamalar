#!/usr/bin/env python3
from __future__ import annotations
import csv, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from msbt_toolkit import control_signature

# v4: manually curated after a second line-by-line multilingual audit.
# Every override was checked against EN + at least JP/ZH and, where useful, FR/DE/IT/ES.
OV = {
# Episode 1
('episode1.csv',2): "İşte geldik!\nBaker'ın bürosu ikinci katta.\nBaker'la görüştüğünde benimle konuşabildiğini\nsöylemesen iyi olur.",
('episode1.csv',191): "Burmy, pelerinini yaparken\n{{CTRL:0000:0003:FF4B4BFF}}çevresindeki malzemeleri kullanır{{CTRL:0000:0003:FDFDFDFF}}.\n{{CTRL:0000:0003:FF4B4BFF}}Kullandığı malzemeye göre{{CTRL:0000:0003:FDFDFDFF}} pelerini\n{{CTRL:0000:0003:FF4B4BFF}}üç türden biri{{CTRL:0000:0003:FDFDFDFF}} olur: Bitki,\nKum ya da Çöp Pelerini.",
('episode1.csv',227): "Buradaki Taillowların tüyleri koyu renkli. Ama\nbu tüy onlardan daha kirli görünüyor.\nTaillowlar sık sık tüylerini temizlediği için, ardından\netrafta {{CTRL:0000:0003:FF4B4BFF}}bir sürü tüy kalır{{CTRL:0000:0003:FDFDFDFF}}.",
('episode1.csv',270): "{{CTRL:0000:0003:FF4B4BFF}}Bu olaya karıştığını gösteren{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}bir kanıt{{CTRL:0000:0003:FDFDFDFF}} bulamazsak onunla konuşmamıza\nizin vermeyecek misin?",
('episode1.csv',366): "Çöp Pelerini yapmak için gereken çöpü nereden\nbulmuş olabilir? {{CTRL:0000:0003:FF4B4BFF}}Çöp deyince akla temizlik gelir{{CTRL:0000:0003:FDFDFDFF}}, değil mi?\nMutlaka {{CTRL:0000:0003:FF4B4BFF}}bu işten anlayan biri{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}vardır{{CTRL:0000:0003:FDFDFDFF}}. Etrafa soralım.",
('episode1.csv',464): "Murkrow doğru söylüyorsa,\n{{CTRL:0000:0003:FF4B4BFF}}Aipom'un bulunduğu yerin yakınındaki{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}ağaçta{{CTRL:0000:0003:FDFDFDFF}} Burmyler varmış.",
('episode1.csv',504): "Demek hep şuradaki\n{{CTRL:0000:0003:FF4B4BFF}}çiçek tarhlarında ve{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}çalılıkların arasında{{CTRL:0000:0003:FDFDFDFF}} oynuyor, öyle mi?",
('episode1.csv',759): "Hâlâ anlamadın mı?\nBen babanın—\nDedektif Harry Goodman'ın—ortağıyım.\nŞimdi Baker Dedektiflik Bürosu'nda\nkalıyorum.{{CTRL:0001:0006:}}\nHarry'yle de orayla birlikte çalışırdık.",
('episode1.csv',825): "Yeni bir şey öğrenmişsin.\n{{CTRL:0000:0003:FF4B4BFF}}Daha önce konuştuğun kişilerle{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}yeniden konuşmak{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}çok önemlidir{{CTRL:0000:0003:FDFDFDFF}}.",
('episode1.csv',1072): "Evet, burada bir püf noktası var. {{CTRL:0000:0003:FF4B4BFF}}Çöp deyince{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}akla temizlik gelir{{CTRL:0000:0003:FDFDFDFF}}, değil mi? Mutlaka {{CTRL:0000:0003:FF4B4BFF}}bu işten{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}anlayan biri{{CTRL:0000:0003:FDFDFDFF}} vardır. Etrafa soralım.",
# Episode 2
('episode2.csv',47): "Haklısın galiba. Bir yerlerde keyifle\nkahvesini içiyordur.",
('episode2.csv',222): "Yok, bence yemeği kapmak için yalan söylüyorlar.\nHangisinin doğru söylediğini anlamak için\n{{CTRL:0000:0003:FF4B4BFF}}ifadelerini toplayıp{{CTRL:0000:0003:FDFDFDFF}} karşılaştıralım.",
('episode2.csv',570): "Küreği burada yapmamız gerekecek. Sence\ngerekli malzemeleri bulabilir miyiz?",
('episode2.csv',763): "Şey... normal şartlarda\nsana vazgeç derdim.",
('episode2.csv',910): "Arkadaki Litwickleri uyandırmadan\ndaha ileri gidemeyiz.\n{{CTRL:0000:0003:FF4B4BFF}}Donmuş Drifloon'u{{CTRL:0000:0003:FDFDFDFF}} kurtarıp\n{{CTRL:0000:0003:FF4B4BFF}}ondan yardım istemeye{{CTRL:0000:0003:FDFDFDFF}} ne dersin?",
# Episode 3
('episode3.csv',420): "Bize güvenmiyor musun? Peki güvenini\nnasıl kazanacağız? Aa, {{CTRL:0000:0003:FF4B4BFF}}Shuckle sana{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}meyve suyu yaparsa bize güveneceksin{{CTRL:0000:0003:FDFDFDFF}}, öyle mi?\nİlaç değil, normal meyve suyu istiyorsun?",
('episode3.csv',1597): "Aferin!\nTesisin haritasını bulmuşsun. Bakalım...\n{{CTRL:0000:0003:FF4B4BFF}}Kırmızı üçgen{{CTRL:0000:0003:FDFDFDFF}} şu an bulunduğumuz yeri gösteriyor.",
('episode3.csv',1649): "İşte bu! Son ipucunu da hemen yakaladın.\nArtık gerçek suçluyu ortaya çıkarabiliriz!",
('episode3.csv',1838): "O değil.",
('episode3.csv',1846): "Hayır! O değil!",
('episode3.csv',1852): "Harry Goodman'ın oğlu mu?",
('episode3.csv',2157): "Aradığımız şişe bu değil.",
# Episode 4
('episode4.csv',3): "Harika değil mi!\nBu tekne tam dört yüz beygir gücünde.{{CTRL:0001:0006:}}",
('episode4.csv',8): "Amanda...\nBiraz yavaşlayabilir misin?",
('episode4.csv',288): "Böyle hassas bilgileri açıklayamayacağımı\nbiliyorsun...\nHımm?",
('episode4.csv',300): "Hah, buldum! Bu Spritzee'nin kokusu.\nSana fazla yoğun geliyor; o yüzden hapşırıyorsun!",
('episode4.csv',547): "Ha, şimdi hatırladım.\nBaban {{CTRL:0000:0003:FF4B4BFF}}Fine Park{{CTRL:0000:0003:FDFDFDFF}}'ı araştırdığını söylemişti.",
('episode4.csv',565): "Hımm... Aslına bakarsan,\nR'yi sormaya gelen ikinci kişi sensin.",
('episode4.csv',567): "Sanırım iki ay kadar önceydi.\nBir adam bana aynı şeyi sormuştu.\nHatırladığım kadarıyla yanında da, tıpkı senin gibi,\nbir Pikachu vardı.",
('episode4.csv',744): "Kesinlikle. Bir anda ne kadar da heybetli oldu!\nDarısı bana; ben de yakında iyi bir\nPokémon Korucusu olurum umarım!",
('episode4.csv',1174): "Evet. Araştırırken\ndikkatli olalım.",
('episode4.csv',1222): "Milo, Feebas'ı tanıyor musun?",
('episode4.csv',1381): "Bu taraftan gittiğimize emin misin?",
('episode4.csv',1445): "İnsanlar burayı geliştirmeye başladığından beri\nçevre çok değişmiş.\nHatta {{CTRL:0000:0003:FF4B4BFF}}su kalitesi bile{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}eskisinden bambaşka{{CTRL:0000:0003:FDFDFDFF}} olmuş, diyor.",
('episode4.csv',1549): "*homurdanır* Benim bacaklarım seninkinden daha kısa,{{CTRL:0001:0006:}}\nunutma!",
('episode4.csv',1879): "Evet, pek iyi fikir değil. Sis o kadar\nyoğun ki önümüzü bile göremeyiz.",
('episode4.csv',1923): "Evet. Buna bakarsak geçen hafta\nTimburr'un taşıdığı yüklerle ilgili daha fazla\nbilgi edinebiliriz.",
('episode4.csv',1967): "Eh, bu kadarı bir\nPokémon Korucusunun görevi!",
('episode4.csv',1969): "Bilmiyor musun?\nPokémon Korucuları\nPokémonlara yardım eder,\ndoğayı korur.",
('episode4.csv',2053): "Ah, geliştirme projesiyle ilgili bir sorun çıktı.\nBelki de kendimi fazla kaptırdım ama\nbu projenin başarısız olmasına izin veremem...",
# Episode 5
('episode5.csv',467): "Aa, bize yardımcı olabilecek Pokémonları mı\nçağıracaksın? Harika! Göründüğünden{{CTRL:0001:0006:}}\ndaha iyiymişsin!",
('episode5.csv',478): "Bankın altı yağmurdan korunmak için\nideal bir yer gibi.",
('episode5.csv',645): "Bir yerde saklanıyor olabilir. Litten'in olabileceği\nbir yer fark edersen, {{CTRL:0000:0003:FF4B4BFF}}bana haber ver{{CTRL:0000:0003:FDFDFDFF}}.\nDikkatimi nasıl çekeceğini biliyorsun, değil mi?\n{{CTRL:0000:0003:FF4B4BFF}}Sinyalimi fark ettiğinde yaptığınla{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}aynı şekilde{{CTRL:0000:0003:FDFDFDFF}}.",
('episode5.csv',834): "Arkadaşın yağmurdan korunabileceği bir yere\nkaçtı, öyle mi?",
('episode5.csv',1006): "Hah, Harry için mi endişeleniyorsun?\nDüşünmen yeter, sağ ol. Ama merak etme.\nPeşine kim düşmüş olursa olsun Harry kesin iyidir.\nSonuçta o Tim'in babası!",
# Episode 6
('episode6.csv',302): "Hadi ama, ne yapacağını biliyorsun.\nGitmediğin bir yer kaldı mı?\nMesela {{CTRL:0000:0003:FF4B4BFF}}stüdyo{{CTRL:0000:0003:FDFDFDFF}}, {{CTRL:0000:0003:FF4B4BFF}}alt kontrol odası{{CTRL:0000:0003:FDFDFDFF}} ya da\n{{CTRL:0000:0003:FF4B4BFF}}oyuncuların kulisleri{{CTRL:0000:0003:FDFDFDFF}}...",
('episode6.csv',494): "{{CTRL:0000:0003:FF4B4BFF}}Programda yer alan herkesin{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}alibisini{{CTRL:0000:0003:FDFDFDFF}} kontrol edelim.\nBulduklarımızı Vaka Notları'ndan\nher zaman kontrol edebilirsin.",
('episode6.csv',605): "Evet, yerel TV kanallarının ayakta kalması\nkolay değilmiş. GNN'nin de açığını kapatmak için\nelinden geleni yaptığını duydum.",
('episode6.csv',1185): "{{CTRL:0000:0003:FF4B4BFF}}Kapıyı çaldığında içeriden{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}sana bağırıldığını{{CTRL:0000:0003:FDFDFDFF}} söylüyorsun...\n'Çekil yolumdan!' diye mi bağırdılar?",
('episode6.csv',1357): "Sorma. Bu kadın\nne yapıyor da bu kadar gecikiyor?",
('episode6.csv',1361): "Aa, aklıma geldi!\n{{CTRL:0000:0003:FF4B4BFF}}Yanma kameralarını{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}bizzat denemek{{CTRL:0000:0003:FDFDFDFF}} ister misin?",
('episode6.csv',1377): "Cık! O değil, bu Chatot!\nBugünkü konuğumuz ise—",
('episode6.csv',1459): "Kricketune'un performansı seni etkiledi mi?\nHaklısın; biz kollarımızı birbirine sürtsek de\nöyle güzel bir ses çıkaramayız.",
# Episode 7
('episode7.csv',512): "Bu bir kalite kontrolü olmalı. Bir şeyleri\nyerine koymadan önce kusurlu olanları ayırıyorlar.",
('episode7.csv',513): "Evet, anlaşılan kusurlu olan epey çok.",
('episode7.csv',880): "*iç çeker* Sorma!\n*homurdanır* Seni uyandırdığım için üzgünüm. Ama galiba\nbir şeyi unutuyorum—verdiğim bir sözü.",
('episode7.csv',973): "*homurdanır* Off... Sonunda geldik.\nAma hakkını vereyim... fena iş çıkarmadın!",
# Episode 8
('episode8.csv',1141): "Evet, az önce öyle biri buradaydı.\nTam şurada durup\naşağıya bakıyordu.",
('episode8.csv',1199): "Bir de içecek sayısı! Sana bir, bana bir; yani iki.\nHepsini yazdıysan sipariş formunu\nFrillish'e ver, Tim!",
('episode8.csv',1269): "İşte bu, Tim! Sipariş formunu Frillish'e ver.",
('episode8.csv',1486): "Bu, içecekler için sipariş formu.\nFrillish'e verirsen,\nyazdıklarını getirir.",
('episode8.csv',1736): "Ne diyorsun sen? Nerem şüpheliymiş?!\nHiç de öyle değil. Çok kabasın!",
# Episode 9
('episode9.csv',136): "Bakalım... Hem çok sayıda olup hem de\nkadrajda görünecek balonlar hangileri?\n{{CTRL:0000:0003:FF4B4BFF}}Brad'in karşısındaki{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}dörtlü balon demeti{{CTRL:0000:0003:FDFDFDFF}} şüpheli görünüyor.",
('episode9.csv',249): "Aa, Pokémonların ödülü!\nGeçit töreninin sonunda atıştırmalıklarla dolu bir vagon\ngeliyor. Onları Pokémonlara dağıtıp\nonları yakından görebiliyorsun!",
('episode9.csv',263): "Teşekkürler, Meiko. Seni duyabiliyorum, haberin olsun.",
# Stream
('stream.csv',118): "Şurada!\n{{CTRL:0000:0003:1EFF00FF}}(En önde Charizard'dan iyisi düşünülemez!{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:1EFF00FF}}Bu yılki geçidin temasının{{CTRL:0000:0003:FDFDFDFF}}{{CTRL:0001:0006:}}\n{{CTRL:0000:0003:1EFF00FF}}...){{CTRL:0000:0003:FDFDFDFF}}",
('stream.csv',163): "{{CTRL:0000:0003:1EFF00FF}}(En önde Charizard'dan iyisi düşünülemez!{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:1EFF00FF}}Bu yılki geçidin teması...{{CTRL:0001:0006:}}{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:1EFF00FF}}){{CTRL:0000:0003:FDFDFDFF}}",
# Pikachu sign / inner monologue snippets
('mpika.csv',8): "Bazen en çok gereken şey,\nsabırla adım adım ilerlemektir.",
('mpika.csv',57): "Hadi ama!\nO değil...{{CTRL:0001:0006:}}\nBugün sen Tim Ottman’sın!\nAnladın mı? Ottman!",
('mpika.csv',257): "İşte bu! Kutunun içindeki pençe izleri\nağaçlardaki izlerle aynı.\nDemek biri Crawdaunt'u o kutuya koyup\nburaya kadar taşımış.",
('mpika.csv',309): "Hımm...\nBir zamanlar Feebas olduğuna kim inanır?\nDemek insan da Pokémon da gerçekten isterse\ndeğişebiliyor.{{CTRL:0001:0006:}}",
('mpika.csv',337): "Evet ya, bu da aslında{{CTRL:0001:0006:}}\nhiç fena olmazdı, değil mi?",
('mpika.csv',356): "Tim! Hazır mısın?\nSeni beklemekten ağaç oldum!\nBen hazırım; nasıl hareket edeceğimi de\nkafamda kurdum. Önce bir bak!",
('mpika.csv',447): "Vay, bu yük gemisi gerçekten devasa!\nDünyanın dört bir yanından gelen yükler\nbu limana taşınıyor.",
('mpika.csv',462): "Sandığımdan daha güvenilirsin, ha.\nTabii hepsi benim eğitimim sayesinde!",
('mpika.csv',507): "Bu gemide Emilia'yla karşılaşacağımız\nkimin aklına gelirdi?{{CTRL:0001:0006:}}\nİşte buna kader derim!",
}

# Additional v4.1 idiom/literal-calque pass.
OV_EXTRA = {
('episode4.csv',1453): "Feebas'la Milo biraz birbirine benziyor, değil mi?",
('episode9.csv',681): "Oh, Volbeat'lerin peşinden uçup onları mı çekeceksin?\nBu, geçidin kendisini izlemekten bile\ndaha eğlenceli olacak gibi!",
('episode7.csv',106): "Dur... Bu binayı tanıyorum.\nBurası Ryme Rıhtımı.",
('episode7.csv',260): "Hey, lafı bile olmaz! Bence Machamp'ler onun hakkında\nbenden daha çok şey biliyor olabilir. Son geldiğinde\nbir süre ona bakıp durmuşlardı.\nKaslarına göz dikmiş olmalılar.",
('episode7.csv',618): "Sabırsızlanıyorum.\nO var ya... gerçekten çok hoş...",
('episode2.csv',17): "Babam da kahveyi çok severdi.\nBu konuda ona epey benziyorsun.",
('episode3.csv',1356): "Harry'nin yanındayken\nsıradan bir Pikachu gibi görünüyordu.",
('episode3.csv',1390): "Evet... daha işimiz bitmedi.\nBundan sonra da sana güveniyorum.\nİkimiz şaşırtıcı derecede iyi bir ikiliyiz, ha.",
('episode3.csv',1451): "Bence Baker da\naraştırmamızdan çoktan haberdar...",
('stream.csv',128): "Ha? Şu hareket...{{CTRL:0001:0006:}}\nKeith olabilir mi...",
('episode6.csv',269): "Şimdi düşününce, Yanma kameralarının\nhareketleri de biraz tuhaftı...",
('episode6.csv',1372): "Şimdi düşününce, onu koridorda görmüş olabilirim...\nAsansörü kullanmış olamaz; o yüzden\nhâlâ bu katta bir yerlerde olmalı.",
('episode6.csv',1540): "Kulis odasına dönüp kestirdin, öyle mi?\nOlga da seni güzelce taramış; tüylerin\npırıl pırıl olmuş... Hımm, ben pek fark göremedim.",
('episode1.csv',1137): "Ha? Neden birden bunu soruyorsun? Dün akşamdı.\nBurada aceleyle not alırken düşürdüm.\nYoksa bir ipucu mu buldun?",
('episode8.csv',1667): "Aa? Bu maskeyi haberlerde görmüştüm.\nÇalındığını söylüyorlardı!",
('episode8.csv',1840): "Tim! Ben araştırayım. Röportajlar için\nyanımda bir elbise getirmiştim.",
('episode2.csv',813): "Şimdi ne demek istediğimi anladın mı?\nBence Harry kazayı buradan dönerken\ngeçirdi.",
('mpika.csv',308): "Hımmm... *çığlık* Iyy, yapış yapışsın!\nBak! Görüyor musun? Elim yapış yapış oldu! İğrenç!",
('mpika.csv',310): "Bana sorarsan Brad tam bir pısırık! *güler*\nHa? Ne demek mi istiyorum?\nBoş ver, sizin gibi çocukların{{CTRL:0001:0006:}}\nbilmesi gereken şeyler değil bunlar.",
('episode6.csv',1215): "Fark etmedin mi?\nGerçi bu çizime bakılırsa fark etmemen normal...",
('episode8.csv',930): "Evet...\nBence o salon kesinlikle şüpheli.\nÜstelik kimse gösteriyi hiç görmemiş!",
('episode5.csv',910): "Tabii, sayende ben az kalsın\ncanımdan oluyordum ama!",
('episode1.csv',307): "O değil!",
('mpika.csv',100): "Hayır, o değil.",
('mpika.csv',128): "Hımmm... Sanırım o değil.\nVaka Listene\nbir kez daha bak istersen.",
('episode4.csv',656): "Ona... bunun doğru olmadığını söyle!",
}
OV.update(OV_EXTRA)

# Explicit notes for key semantic choices.
NOTES = {
('episode1.csv',2): 'JP/ZH/DE singular Baker office; literal “offices” replaced with Baker’ın bürosu; hedge removed.',
('episode1.csv',191): 'Control-repaired sentence restructured; JP/ZH confirm Burmy uses surrounding material and has three cloak types.',
('episode1.csv',227): 'Control-repaired but syntactically broken line rewritten; FR/DE/IT/ES/JP/ZH agree on Taillow preening and dropped feathers.',
('episode1.csv',270): 'Control-repaired word order was broken; all languages mean “proof it was involved in the incident”.',
('episode1.csv',759): 'Goodman suffix fixed; JP/ZH emphasize Pikachu is Harry’s partner and currently stays/works with Baker agency.',
('episode2.csv',222): 'JP/ZH “collect testimony and verify”; Turkish changed from singular imperative to collaborative natural phrasing.',
('episode2.csv',910): 'Technical repair left duplicated “frozen” phrase; JP/FR/DE confirm help frozen Drifloon and borrow its help.',
('episode3.csv',1838): 'FR/DE/IT/ES explicitly “not that one”; puzzle rejection is “O değil”, not factual “Bu doğru değil”.',
('episode3.csv',1846): 'FR/DE/IT/ES explicitly “not that one”; puzzle rejection localized naturally.',
('episode3.csv',2157): 'JP/FR/DE/ES: wrong target vial/type; natural Turkish “Aradığımız şişe bu değil”.',
('episode4.csv',3): 'JP/FR/DE/IT/ES treat “you know” as discourse emphasis, not a literal question.',
('episode4.csv',8): 'JP/FR/DE/IT/ES contain only a hesitant request to slow down; literal “Biliyor musun?” removed.',
('episode4.csv',547): 'JP/FR/DE/IT/ES: simple recollection marker; literal “Biliyor musun?” removed.',
('episode4.csv',565): 'JP/ZH say directly that Tim is the second person to ask about R; English filler omitted.',
('episode4.csv',567): 'JP/FR/DE/IT/ES: recollection about man with Pikachu; English filler omitted.',
('episode4.csv',744): 'JP/ZH avoid literal Pokémon-style evolution for a human; Turkish keeps the parallel naturally and standardizes Pokémon Korucusu.',
('episode4.csv',1445): 'Original Turkish had broken time relation; JP/ZH/FR/DE/IT/ES agree water quality is now different from the old days.',
('episode4.csv',1967): 'Pokémon Ranger terminology standardized as Pokémon Korucusu; English discourse filler omitted.',
('episode4.csv',2053): 'JP/ZH/FR/IT/ES: project stress/overfocus, not literally “a point I got stuck at”.',
('episode5.csv',1006): 'JP/ZH/FR/DE/IT/ES: Pikachu is confident Harry must be safe; “iyi olmak zorunda” was a semantic calque.',
('episode6.csv',494): '“involved in the show” means participants/people connected to the program, not “gösteriye karışan”.',
('episode6.csv',605): 'JP/ZH/FR/DE explicitly refer to operating losses/red figures; “zarar etmeyi bırakmak” replaced with natural “açığını kapatmak”.',
('episode6.csv',1185): 'Control-repaired text still contained duplicated “kapı”; JP/ZH and EU languages confirm a shout came from inside after knocking.',
('episode6.csv',1357): 'JP/ZH/FR/IT/ES idiom is “what is she doing/taking so long”; literal causal phrasing removed.',
('episode6.csv',1377): 'FR/DE/IT/ES/JP indicate correction of a mistaken answer (“not that; it is Chatot”), not truth-value statement.',
('episode6.csv',1459): 'JP/ZH/FR/DE explain rubbing arms cannot make that beautiful sound; expanded to preserve the joke.',
('episode7.csv',512): 'Typo “küsur” corrected to “kusur”; JP context is inspection/quality checking.',
('episode7.csv',513): 'Typo “küsur” corrected to “kusur”; JP/EN agree many defective items.',
('episode7.csv',880): 'FR/DE/IT/ES idiom “tell me about it” = agreement/commiseration; Turkish “Sorma!” is idiomatic.',
('episode7.csv',973): 'JP/ZH tone is teasing praise (“you’re pretty good”); Turkish made more Pikachu-like.',
('episode8.csv',1141): 'All languages say she was looking down; previous Turkish incorrectly said “bir şeye aşağıdan bakıyordu”.',
('episode8.csv',1199): 'JP/ZH/DE/ES use order sheet/form; standardized “sipariş formu”, not receipt.',
('episode8.csv',1269): 'Order-sheet terminology standardized across repeated interaction.',
('episode8.csv',1486): 'Order-sheet terminology standardized; subject agreement made natural.',
('episode9.csv',136): 'Control-repaired line had modifier order inverted; JP/ZH confirm four-balloon bundle opposite Brad.',
('episode9.csv',249): 'Removed “yakından yaklaşmak” redundancy; all languages mean get/see Pokémon up close.',
('stream.csv',118): 'Technical repair left duplicated/incomplete parade phrase; rebuilt as broadcast fragment while preserving all control codes.',
('stream.csv',163): 'Technical repair left duplicated/incomplete parade phrase; rebuilt as broadcast fragment while preserving all control codes.',
('mpika.csv',257): 'JP “そうか!” / FR “Mais oui!” are realization markers; “Ne biliyor musun?!” was a literal mistranslation.',
('mpika.csv',309): 'JP expresses general realization that people/Pokémon can change; English fillers removed.',
('mpika.csv',356): 'JP says Pikachu has been waiting and is fully prepared; Turkish “Beni beklettiğini biliyorsun” was unnatural.',
('mpika.csv',507): 'JP/FR frame this as “destiny”; English filler localized as emphatic “İşte buna kader derim!”.',
}

NOTES_EXTRA = {
('episode4.csv',1453): 'FR/DE/IT/ES/JP/ZH cümleyi “birbirine benziyor, değil mi?” şeklinde kuruyor; İngilizcedeki dolgu “you know” kaldırıldı.',
('episode9.csv',681): 'JP/ZH/FR/DE/IT/ES doğrudan çekimin geçitten daha seyirlik/eğlenceli olacağını söylüyor; “Biliyor musun” dolgusu kaldırıldı.',
('episode7.csv',106): 'JP/ZH/FR/DE/ES yapıyı tanıma/hatırlama anlamında; literal “Biliyor musun” yerine doğal fark ediş kullanıldı.',
('episode7.csv',260): 'JP/ZH ve Avrupa dilleri Machamp’lerin kaslara bakıp adam hakkında daha çok şey bilebileceğini söylüyor; konuşma dolgusu kaldırıldı.',
('episode7.csv',618): 'JP/ZH ve Avrupa dilleri beklenen kişi/varlığa sevgi dolu bir övgü veriyor; literal “Biliyor musun” kaldırıldı.',
('episode2.csv',17): 'JP/ZH/FR/DE/IT/ES Tim’in babasının da kahveyi sevdiğini ve Pikachu ile bu yönden benzediğini doğrudan söylüyor; dolgu ifade kaldırıldı.',
('episode3.csv',1356): 'JP/ZH/FR/IT/ES Harry ile birlikteyken Pikachu’nun sıradan/normal göründüğünde birleşiyor; “Biliyor musun” gereksizdi.',
('episode3.csv',1390): 'JP/ZH “bundan sonra da sana güveniyorum” ve “uyumlu ikiliyiz” nüansını taşıyor; Pikachu’nun sıcak ama takılmalı sesi güçlendirildi.',
('episode3.csv',1451): 'FR/DE/IT/ES ve ZH Baker’ın araştırmadan haberdar olduğunu; JP ise bu gidişle öğreneceğini söylüyor. Türkçe ortak sonucu doğal biçimde verdi.',
('stream.csv',128): 'JP/ZH/DE/IT/ES yalnızca hareketin Keith’e benzediğini fark ediyor; “Biliyor musun” kaldırıldı.',
('episode6.csv',269): 'JP/ZH/FR/DE/IT “şimdi düşününce” türü hatırlama bağlantısı kuruyor; literal konuşma dolgusu buna çevrildi.',
('episode6.csv',1372): 'JP/ZH/FR/DE/IT/ES hatırlama geçişi + asansör kullanamayacağı çıkarımında birleşiyor; “Biliyor musun” kaldırıldı.',
('episode6.csv',1540): 'DE/IT açıkça “tüylerinde fark göremiyorum” diyor; JP/ZH da belirsizlik veriyor. “Biliyor musun” ve “dümdüz” ifadesi düzeltildi.',
('episode1.csv',1137): 'JP/ZH/FR/DE/IT/ES son soruyu “bir ipucu mu buldun?” anlamında veriyor; “Biliyor musun bir şey?” yanlış yapısı düzeltildi.',
('episode8.csv',1667): 'JP/ZH/FR/DE/ES maskeyi haberlerden tanıma ve çalındığını hatırlama anlamında; “Biliyor musun” dolgusu kaldırıldı.',
('episode8.csv',1840): 'JP/ZH doğrudan Emilia’nın araştırmayı üstlenmesini ve röportaj elbisesini söylüyor; gereksiz “Biliyor musun?” kaldırıldı.',
('episode2.csv',813): 'Tüm Avrupa dilleri “ne demek istediğimi anladın mı?” yapısını destekliyor; asıl hata “kazayı yaptı” idi, doğal “kazayı geçirdi” olarak düzeltildi.',
('mpika.csv',308): 'JP/ZH/FR/DE/IT yapışkanlık tepkisini tekrar ederek komediyi kuruyor; meta “ne demek istediğimi görüyor musun?” yerine fiziksel tepki öne çıkarıldı.',
('mpika.csv',310): 'JP/ZH “ne demek mi?” diye karşılık verip çocuğun anlamayacağını söylüyor; literal “ne demek istediğimi bilmiyor musun?” doğal diyaloğa çevrildi.',
('episode6.csv',1215): 'JP/ZH/FR/DE çizimin kötü olmasını vurguluyor; İngilizcedeki “sketch” burada skeç değil çizim. Yanlış anlam düzeltildi.',
('episode8.csv',930): 'JP/ZH/FR/DE/IT/ES salonun şüpheli olduğu ve hiç kimsenin gösteriyi görmediği noktasında birleşiyor; gereksiz “Yani” kaldırıldı.',
('episode5.csv',910): 'JP/ZH/DE/ES Pikachu’nun risk yüzünden çok çektiğini vurguluyor; mevcut “hiç sorun değil” çevirisi anlamı tersine çeviriyordu.',
('episode1.csv',307): 'FR/IT/ES/JP/ZH bunun yanlış kanıt/seçenek reddi olduğunu gösteriyor; “Bu doğru değil” yerine “O değil!” kullanıldı.',
('mpika.csv',100): 'FR/IT/ES/JP/ZH kısa yanlış-seçim reddi; Türkçe “Hayır, o değil” olarak doğallaştırıldı.',
('mpika.csv',128): 'FR/DE/IT/ES/JP/ZH çözümün yanlış olduğuna ve Vaka Listesi’ni yeniden kontrol etmeye yönlendiriyor; diyalog doğallaştırıldı.',
('episode4.csv',656): 'FR/DE/IT/ES İngilizceyle birlikte “ona bunun doğru olmadığını söyle” anlamını veriyor; Türkçe söz dizimi düzeltildi.',
}
NOTES.update(NOTES_EXTRA)

# Additional ambiguity/typo pass found while auditing the unchanged rows.
OV_MORE = {
('episode6.csv',1270): "S-şey... güzel. Chatot çizimin tam...\nsenlik.",
('episode6.csv',1946): "Beni düşündüğün için sağ ol...\nHâlâ biraz sarsılmış durumdayım ama\niyi olacağım.",
('episode8.csv',1528): "Pek bir şey diyemem...\nSanırım şuradaki kafenin baristası\nFrillish hakkında benden daha çok şey biliyordur.",
('episode8.csv',1563): "Demek Gino bileti ele geçirmek için bavulu çaldı?\nPeki biletin o bavulda olduğunu\nnereden biliyordu?",
('episode8.csv',1564): "Bence asıl ihtimal, bavulun zaten\nGino'ya ait olması.\nBelki de bu hırsızlık, kendi eşyalarını\ngeri almasından ibaretti.\nGino'nun neyin peşinde olduğunu öğrenelim.\nÖnce {{CTRL:0000:0003:FF4B4BFF}}Emilia ve Graham'a soralım{{CTRL:0000:0003:FDFDFDFF}}.",
('episode8.csv',1905): "Hayır, gemi personeline teslim etmiştim.\nGemiye bindikten sonra resepsiyondan aldım;\nSnubbull da odama kadar taşıdı.\nEn sevdiğim diz örtüsünü çıkarmak istedim ama\nbavulu açınca içinde o maske vardı.\nBenim bavulum nereye gitmiş olabilir?",
('episode2.csv',393): "Demek bunun nedeni\nMeiko'yla diğerleri değilmiş.",
('episode4.csv',751): "Demek onun da\niyi yanları varmış.",
('episode4.csv',1226): "İlk gördüğümde çok şaşırmıştım.\nKanatları bildiğin yeşil yapraklardan oluşuyor!",
('episode8.csv',1113): "Sandık taşıyan adamlar mı?\nHayır, hiç görmedim.",
('episode8.csv',1130): "Bu geminin yolcuları önemli kişiler, bu yüzden\nrahatsız olmasınlar diye yükler normalde gece taşınır.\nAma bugün daha gündüz vakti\nsandık taşıyan adamların ortalıkta dolaştığını gördüm...",
('episode8.csv',1132): "Anlaşılan yükleri içeri taşımayı bitirmişler.\nAcaba bütün o hareketliliğin sebebi neydi?",
('episode8.csv',1290): "Sandık taşıyan adamlar mı? Hayır efendim,\ngörmedim.\nAma bu çok tuhaf. Normalde yolcular dinlenmeye\nçekildikten sonra yüklerin yalnızca gece\ntaşınmasına izin veririz.",
('episode8.csv',1384): "Yük taşımak senin işin mi?\nŞu incecik kollarınla ha...",
}
OV.update(OV_MORE)
NOTES_MORE = {
('episode6.csv',1270): 'FR/DE/IT/ES/JP/ZH “sketch” sözcüğünü çizim/karikatür/portre olarak veriyor; ayrıca “very you” = Max’e özgü. “Şenlik” anlamsızlığı “tam senlik” olarak düzeltildi.',
('episode6.csv',1946): 'JP/ZH/FR/DE/IT/ES karakterin zihnen sarsılmış/şokta olduğunu ama toparlanacağını söylüyor; “karmaşığım” yanlış ve doğal olmayan bir calque idi.',
('episode8.csv',1528): 'FR/DE/IT/ES barista/kafe görevlisini, JP/ZH kafe sahibini gösteriyor; “barışta” açık yazım/anlam hatasıydı.',
('episode8.csv',1563): 'Tüm diller Gino’nun bilet için bavulu çalmış olabileceği ve biletin bavulda olduğunu nasıl bildiği sorusunda birleşiyor; “çanta/bavul” tutarsızlığı giderildi.',
('episode8.csv',1564): 'JP/ZH/FR/DE/IT/ES bavulun aslında Gino’ya ait olabileceğini ve hırsızlığın kendi eşyalarını geri almak olabileceğini söylüyor; bozuk Türkçe söz dizimi tamamen yeniden kuruldu.',
('episode8.csv',1905): 'FR/DE/IT/ES ve JP/ZH “front desk/reception” anlamını doğruluyor; “ön maşa” yazım hatası ve cümlenin mekanik yapısı düzeltildi.',
('episode2.csv',393): 'JP/ZH doğrudan Meiko ve diğerlerinin Glalie’nin davranışının nedeni olmadığını söylüyor; çift olumsuz ve yapay Türkçe giderildi.',
('episode4.csv',751): 'JP/ZH/FR/DE/IT/ES Brad’in beklenmedik biçimde iyi bir yanı olduğunu söylüyor; “Yani, demek ki” gereksiz tekrarı kaldırıldı.',
('episode4.csv',1226): 'JP/ZH ve Avrupa dilleri kanatların yeşil yaprak gibi/yeşil yapraklardan olduğunu vurguluyor; “Yani, kanatları yeşil yaprak” eksik cümlesi doğallaştırıldı.',
('episode8.csv',1113): 'DE/IT/ES açıkça Kiste/cassa/caja = sandık/kasa diyor; JP/ZH daha genel “yük” kullanıyor. Sahnedeki kişiler “bavullu” değil “sandık taşıyan” olarak düzeltildi.',
('episode8.csv',1130): 'FR/DE/IT/ES gündüz sandık/kasa taşıyan adamları; JP/ZH genel yük taşımayı doğruluyor. “Bavul” dar anlamı kaldırılıp yük/sandık ayrımı korundu.',
('episode8.csv',1132): 'IT/JP/ZH genel kargo/yük taşınmasının bittiğini söylüyor; “bavullar” yerine bağlama uygun “yükler” kullanıldı.',
('episode8.csv',1290): 'FR/DE/IT/ES ilk cümlede sandık/kasa taşıyan adamlardan söz ediyor; JP/ZH ise genel yük. İki nüans Türkçede birlikte korundu.',
('episode8.csv',1384): 'JP/ZH “yük taşıma”, Avrupa dilleri bagaj/valiz görevini veriyor; genel görev için “yük taşımak” daha kapsayıcı ve bağlama uygun.',
}
NOTES.update(NOTES_MORE)

# Orthography/naturalness findings from audit pass.
OV_AUDIT_FIX = {
('episode1.csv',1182): "Son zamanlarda şakaları azalmış ama\nyaptıkları da gitgide daha beter olmuş, öyle mi?",
('episode4.csv',1938): "Üç resim var, altında da birtakım açıklamalar yazıyor.\nBunlar gizli yolun ipuçları mı?",
('episode8.csv',1567): "Umarım Bayan Milton'ın bavulunu bulursunuz.\nRöportajım biter bitmez araştırmana yardım edeceğim.\nBay Graham'dan da izin aldım.",
}
OV.update(OV_AUDIT_FIX)
NOTES_AUDIT_FIX = {
('episode1.csv',1182): 'JP/ZH/FR/DE/IT/ES şakaların sayısının azaldığını ama kalanların giderek daha ağır/kötü olduğunu söylüyor; “kötü niyetli olanlarını arttırmış” hem yazım hem anlatım açısından düzeltildi.',
('episode4.csv',1938): 'JP/ZH/FR/DE/IT/ES metinde üç resim ve açıklamalar bulunduğunu söylüyor; “bir takım talimatlar” yerine doğru “birtakım açıklamalar” ve doğal soru yapısı kullanıldı.',
('episode8.csv',1567): 'JP/ZH/IT Emilia’nın röportaj sonrası Tim’in araştırmasına yardım edeceğini ve Graham’dan izin aldığını doğruluyor; “Milton’in” eki ve mekanik “yardım etmeye çalışacağım” yapısı düzeltildi.',
}
NOTES.update(NOTES_AUDIT_FIX)

# Consistency replacements after manual verification.
TERM_REPL = [
    ("Goodman'in", "Goodman'ın", 'Yazım: proper-name suffix harmony'),
    ("Louise'nin", "Louise'in", 'Yazım: Louise + genitive suffix'),
    ("DNA'sinin", "DNA'sının", 'Yazım: DNA + genitive suffix'),
    ("daimâ", "daima", 'Yazım standardizasyonu'),
    ("ipuçlarim", "ipuçlarım", 'Yazım: ı harfi'),
    ("Koruculari", "Korucuları", 'Yazım: ı harfi'),
]
# Multilingual terminology: Japanese/Chinese/Italian call 破壊の遺伝子 / destruction gene.
BERSERK_REPL = [
    ("'Berserk Gene'ye", "Yıkım Geni'ne"),
    ("Berserk Gene'ye", "Yıkım Geni'ne"),
    ("Berserk Geninden", "Yıkım Geni'nden"),
    ("Berserk Genini", "Yıkım Geni'ni"),
    ("Berserk Geni", "Yıkım Geni"),
    ("Çılgın Gen'i", "Yıkım Geni"),
]

def transform(fn, idx, row):
    before=row['Turkish_Revised_v3']
    out=before; notes=[]
    key=(fn,idx)
    if key in OV:
        out=OV[key]
        notes.append(NOTES.get(key,'Çok-dilli satır bazlı incelemeyle doğal Türkçe yeniden yazım.'))
    # apply safe global consistency after override
    for a,b,n in TERM_REPL:
        if a in out:
            out=out.replace(a,b); notes.append(n)
    # Berserk term only when source text actually refers to Berserk Gene
    if re.search(r'Berserk Gene|破壊の遺伝子', row.get('English','')+' '+row.get('JPN',''), re.I):
        old=out
        for a,b in BERSERK_REPL: out=out.replace(a,b)
        if out!=old:
            notes.append('Terminoloji: JP/ZH/IT “destruction gene” doğrultusunda Yıkım Geni standardize edildi.')
    if control_signature(out)!=control_signature(row['English']):
        raise ValueError(f'CONTROL MISMATCH {fn}:{idx}\nEN={row["English"]!r}\nOUT={out!r}\n{control_signature(row["English"])} != {control_signature(out)}')
    return out, '; '.join(dict.fromkeys(notes))

def main(src_dir, dst_dir):
    src=Path(src_dir); dst=Path(dst_dir); dst.mkdir(parents=True,exist_ok=True)
    changes=[]; manifest=[]
    for p in sorted(x for x in src.glob('*.csv') if not x.name.startswith('_')):
        with p.open(encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f)); fields=list(rows[0].keys())
        if 'Turkish_Revised_v4' not in fields: fields += ['Turkish_Revised_v4','V4_Notes']
        n=0
        for r in rows:
            out,note=transform(p.name,int(r['Index']),r)
            r['Turkish_Revised_v4']=out; r['V4_Notes']=note
            if out!=r['Turkish_Revised_v3']:
                n+=1
                changes.append({'File':p.name,**r})
        with (dst/p.name).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
        manifest.append([p.name,len(rows),n])
    with (dst/'_manifest_v4.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f); w.writerow(['File','Rows','V4AdditionalChanges']); w.writerows(manifest)
    if changes:
        fields=['File']+[k for k in changes[0].keys() if k!='File']
        with (dst/'_v4_changes.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(changes)
    print('files',len(manifest),'rows',sum(x[1] for x in manifest),'v4 additional',sum(x[2] for x in manifest))

if __name__=='__main__':
    main(sys.argv[1],sys.argv[2])
