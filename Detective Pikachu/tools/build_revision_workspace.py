#!/usr/bin/env python3
from __future__ import annotations
import csv, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from msbt_toolkit import parse_msbt, decode_text, control_signature

LANGS=["English","French","German","Italian","Spanish","JPN","jp_hira","Simp_Chinese","Trad_Chinese"]

# High-confidence hand edits. Every entry was checked against the aligned official-language row.
OVERRIDES={
    ("common_hud.msbt",1): "Vaka Notları Listesi",
    ("common_hud.msbt",4): "Kanıtlar",
    ("common_hud.msbt",5): "İfadeler",
    ("common_hud.msbt",8): "Kanıtlar",
    ("common_hud.msbt",9): "İfadeler",
    ("common_hud.msbt",15): "{{CTRL:0001:0000:00}}: İncele",
    ("common_hud.msbt",17): "{{CTRL:0001:0000:03}}: Çevreni incele",
    ("common_hud.msbt",20): "Işık yanınca {{CTRL:0001:0000:00}} tuşuna bas!",
    ("common_hud.msbt",21): "{{CTRL:0001:0000:00}} tuşuna art arda bas!",
    ("common_hud.msbt",24): "Simgeleri kaldırmak için\nSıfırla'ya dokun.",
    ("common_hud.msbt",26): "Vaka Listeni\naçabilirsin.",
    ("common_hud.msbt",28): "Bölgeyi {{CTRL:0001:0000:03}} ile incele\nve kanıt bul.",
    ("common_hud.msbt",33): "Biraz bilgi topladık.\n{{CTRL:0000:0003:FF4B4BFF}}Vaka Notları{{CTRL:0000:0003:FDFDFDFF}}'nı açıp\nşöyle bir düşünelim!",
    ("common_hud.msbt",34): "Artık {{CTRL:0000:0003:FF4B4BFF}}Vaka Notları{{CTRL:0000:0003:FDFDFDFF}}'nı açıp\nbunu düşünmenin tam zamanı.",

    ("mpika.msbt",1): "Hey, kes şunu!\nGit başımdan! Hadi, öteye!\nMidem hiç iyi değil...",
    ("mpika.msbt",5): "Kurbanı bulduğumuzda,{{CTRL:0001:0006:}}\nbu şekilde poz verilmişti.\nBunu bir düşünelim.\nPekâlâ... En küçük ayrıntıyı bile hesaba katmak\nönemlidir; ama bunu zaten biliyorsun.",
    ("mpika.msbt",8): "Bazen sabırla, adım adım\nuğraşmak gerekir, biliyorsun.",
    ("mpika.msbt",9): "Sence ben niye öteki Pokémonlar gibi\nhamle kullanamıyorum, ha?",
    ("mpika.msbt",12): "Demek mesele pratik!\nTamamdır! Sağ ol, Tim!",
    ("mpika.msbt",13): "Hadi ama!\nKendimi duvar prizine takmamı mı istiyorsun?\nEe, elektrik faturasını sen ödeyeceksen,\nbir deneyebilirim.",
    ("mpika.msbt",17): "Dinle, o kazayla ilgili rüyalar görüyorum.\nYemin ederim bu şişenin kazayla bir ilgisi vardı...\n*inler* Bir türlü hatırlayamıyorum.",
    ("mpika.msbt",18): "Hey! Ortağın burada dertlenip duruyor.\nİnsan bir ‘İyi misin?’ diye sorar, değil mi?",
    ("mpika.msbt",19): "Güzel, fark ettin!\nBen de bir şey fark edersem sana işaret çakarım.\nGözünü açık tut.",
    ("mpika.msbt",20): "İyi dinle, Tim.\nBurada çalışıyormuş gibi yaparken şu şişeyi de ara.\nÇaktırmadan. Bizi gören olmasın.",
    ("mpika.msbt",21): "Aa, güzel çizmişsin!\nİlk deneme için hiç fena değil!\nŞimdi... çizdiğin şemadaki gibi,\nyol bir noktada ikiye ayrılıyor.\nElimizde Aipomların ayrılıp farklı yollara\nkaçtığına dair ifadeler var.\nÖyleyse... kolyeyi taşıyan Aipom\nhangi yöne kaçtı?",
    ("mpika.msbt",24): "Hafızan sağlam, aferin.\nÖyleyse kolyeli Aipom'un izini sürebiliriz!\nÜstelik bunu belirlememizi sağlayacak{{CTRL:0001:0006:}}\nbir ifade de duyduk.\nHadi bakalım, hangisiydi?",
    ("mpika.msbt",26): "Olmadı.\nKanıtlara ve ifadelere bir daha bak.\nKolyeli Aipom hangi yöne kaçmıştı? Hadi!",
    ("mpika.msbt",28): "Bütün bunlar çok kısa bir süre içinde{{CTRL:0001:0006:}}\nyaşandı.\nNeyse ki geride bazı{{CTRL:0001:0006:}}\nizler kalmış.\nYani yapmamız gereken{{CTRL:0001:0006:}}\n{{CTRL:0000:0003:FF4B4BFF}}olay yerini incelemek{{CTRL:0000:0003:FDFDFDFF}}.",
    ("mpika.msbt",29): "Pekâlâ... İlk iş, Aipom'a kimin ya da neyin\nsaldırdığını bulmak.\nSaldırgan kimse, kolye de büyük ihtimalle ondadır.\nOlay yerini incelerken suçluya götürebilecek\nbir ipucu buldun mu?",
    ("mpika.msbt",36): "Yapraklar, ha?\nKeşke iyi bir şey yakaladığını söyleyebilsem...\nAma birkaç yaprak tek başına pek güçlü bir ipucu değil.",
    ("mpika.msbt",43): "Şöyle yapalım.\nParkı dolaşıp bu tüyün sahibini bulalım.\nSoruşturmamızın ilk adımı bu.\nTüylü bir Pokémon gördüğünde de\nhemen not al, tamam mı?",
    ("mpika.msbt",50): "Pekâlâ. Başka bir teori: Bitki Pelerinli bir Burmy,\nAipom'un kavgasına karışınca pelerinini yırttı!\nŞimdi sana bir soru.{{CTRL:0001:0006:}}\nBunu destekleyen kanıt hangisi?",
    ("mpika.msbt",125): "Bir şey mi kafana yatmadı?\nO zaman Vaka Listene bir göz at.",
    ("mpika.msbt",126): "Bir şey mi kafana yatmadı?\nO zaman Vaka Listene bir göz at.",
    ("mpika.msbt",161): "*koklar* Iyy!",
    ("mpika.msbt",306): "*koklar* Bu kokuyu tanıyorum!\nLouise! Ah, yok... Spritzee'ymiş.",
    ("mpika.msbt",307): "*koklar* İksir kokuyor. Evet...\nBurnumu da biraz yakıyor.",
    ("mpika.msbt",328): "Hımm... *koklar* Hâlâ güzel kokuyor...\nAma yağmur mahvetmiş olmalı.",
    ("mpika.msbt",343): "Dedektif Kahve Notu #16:\nKahvede suyu da es geçme!\nAynı çekirdekleri kullansan bile...{{CTRL:0001:0006:}}\nSuyun kalitesi tadı değiştirir!",
    ("mpika.msbt",6): "Hey! Kes şunu!\nBeni nereye götürüyorsun?!{{CTRL:0001:0006:}}\nİndir beni!",
    ("mpika.msbt",23): "Öyle miydi?",
    ("mpika.msbt",41): "Sert bir Pokémon",
    ("mpika.msbt",42): "Evet, hiç şüphe yok.\nBu tüy bir Pokémon'a ait.",
    ("mpika.msbt",44): "Tamam! Hadi başlayalım!\nSakın geride kalma!",
    ("mpika.msbt",46): "Bingo, Tim!\nOlay yerindeki siyah tüy kesinlikle\nbir Murkrow'a ait. Hemen gidip konuşalım.",
    ("mpika.msbt",49): "Aa! Bu mu?!\nYok, değil.\nPidove'un tüyü siyahtan çok gri.",
    ("mpika.msbt",51): "Demek böyle düşünüyorsun, ha?\nŞimdi de Burmy'nin neden Çöp Pelerinine\nbüründüğünü bulmalıyız.\nBitki Pelerinli Burmylerin olduğu yerde{{CTRL:0001:0006:}}\ntuhaf bir şey olmuştu. Fark ettin mi?",
    ("mpika.msbt",54): "Hey! Hadi, adını söyle bakalım.",
    ("mpika.msbt",58): "Güzel! Hazırız.\nUnutma... Biz dedektifler\nhiçbir zaman gardımızı düşürmemeliyiz, tamam mı?",
    ("mpika.msbt",59): "Vay be, ne dağınık oda!\nAma her yer soruşturma malzemesi dolu.\nBu da ne?\nVay canına...{{CTRL:0001:0006:}}\nHarry gerçekten işi sıkı tutmuş!",
    ("mpika.msbt",61): "Kanıtları bir toparlamanın\ntam zamanı değil mi?",
    ("mpika.msbt",62): "Epey ifade birikti.\nHepsini bir gözden geçirsek iyi olmaz mı?",
    ("mpika.msbt",65): "Ketçaplı kuyruk izi!\nBu önemli bir kanıt.\nPeki bilgi nasıl toplanır?\nTabii ki tanıklarla konuşarak!",
    ("mpika.msbt",66): "Bu siyah tüyün sahibi...\nAipom'a saldıran Pokémon!\nHadi kim olduğunu bulalım!",
    ("mpika.msbt",153): "Aferin, Tim!\nBunu kullanıp onu yakalayacağız! Harika!",
    ("mpika.msbt",155): "Heeey!\nBen büyük dedektif Pikachu'yum!\nTim, sen de bağırsana.\nAcayip eğlenceli!",
    ("mpika.msbt",158): "Eyvah!\nHadi, buradan çıkalım!",
    ("mpika.msbt",169): "Hey, Klefki!\nSana bir şey soracağım.\nŞu anahtarı biraz kullanabilir miyim?\nHey!\nYapma, acıyor! *iç çeker*\nVay be... Pazarlık numaralarım bile sökmedi.\nÇetin cevizmişsin!",
    ("mpika.msbt",176): "Doğrusu en akıllıcası bu.\nBilirsin: akıllı adam tehlikeye bulaşmaz.",
    ("mpika.msbt",177): "Dedektif dediğin dayanıklı olur.\nBen de formumu korurum...\ngittiğim her yerde!",
    ("mpika.msbt",181): "Ne güzel hava!\nAma olaylar güzel hava dinlemiyor.\nİnsan denen yaratık tuhaf, Tim.",
    ("mpika.msbt",182): "Reflekslerin pek parlak değil,{{CTRL:0001:0006:}}\ndeğil mi?\nSana sakar demeyeyim ama...{{CTRL:0001:0006:}}\nvay arkadaş!",
    ("mpika.msbt",184): "Sana birkaç dedektiflik tüyosu vereyim!\nHazır mısın?",
    ("mpika.msbt",194): "Öteki Pokémonlarla konuşmak bende.",
    ("mpika.msbt",200): "Yazı",
    ("mpika.msbt",204): "Hadi ama, çekinip durma!\nSinyal vermesem bile\nistediğin zaman benimle konuşabilirsin.",
    ("mpika.msbt",207): "Gengar'ın ortağı, işin arkasındaki asıl planlayıcı.\nKim olduğunu bulmalıyız... Bence araştırmacılardan biri.\nO zaman bize düşen de{{CTRL:0001:0006:}}\nmaskesini düşürmek!",
    ("mpika.msbt",214): "Soruşturmaya başla",
    ("mpika.msbt",222): "Tamam, parşömen elimizde.\nŞimdi gizli yolu nasıl bulacağımızı çözelim.\nÖnce girişi bulalım!",
    ("mpika.msbt",223): "Anıtları arıyoruz.\nÜzerinde iki pul olanı bul.\nGörür görmez bana{{CTRL:0001:0006:}}\nhaber ver!",
    ("mpika.msbt",263): "Timburrlar çörek işaretli bir kutu taşıdıklarını söyledi.\nAma listede böyle bir işaret yoktu!\nGöle dönüp bir kez daha kontrol edelim.",
    ("mpika.msbt",279): "Bunu çözmek için...\npolisin topladığı bütün kanıtlara{{CTRL:0001:0006:}}\nihtiyacımız var.\nGidip bakalım.",
    ("mpika.msbt",381): "İşte bu! Magnemite'nin kafesinin nerede olduğunu biliyoruz.\nDemek Purugly kuliste olmalı!",
    ("mpika.msbt",392): "Kemanın değiştirildiği sırada\nherkesin alibisini ortaya çıkarmamız gerekiyor.",
    ("mpika.msbt",397): "Yani... Carina sahnedeyken\nkeman hâlâ gerçekti.\nHem Carina hem Kricketune bunu doğruladı.\nDemek ki suçlu, Carina'nın performansından sonra\nama ben kemanı taşımadan önce\ndeğişimi yaptı.",
    ("mpika.msbt",399): "Evet! O zaman suçlu...\nBir dakika, ne?!\nBütün şüphelilerin alibisi mi var?!",
    ("mpika.msbt",400): "Carina'nın performansı bittiği anla\nben kemanı taşıyana kadar\nolaya karışabilecek herkesin alibisini inceleyelim.",
    ("mpika.msbt",409): "Keith'le fotoğrafta görünen adamın kim olduğunu\nbulursak depoyu da bulabiliriz.\nHadi soruşturalım!",
    ("mpika.msbt",422): "Dikkatli ol. Araştırırken\nyakalanmamaya bak!",
    ("mpika.msbt",431): "Alt katı incelememiz gerek,\nama nöbetçiler var.\nMerdivenlerden inersek\nanında yakalanırız.",
    ("mpika.msbt",434): "Hımm... Neden öyle düşünüyorsun?",
    ("mpika.msbt",548): "Bu meydanda üç ayrı yere R gizlenmiş.\nHepsini bulalım!",
    ("mpika.msbt",558): "Bence asıl planlayıcı\no üç kişiden biri.\nHangisi olduğunu kesinleştirecek\nbir ifade yok mu?",
    ("mpika.msbt",560): "Sakin ol, Tim. İyice düşün.\nKeith'le asıl planlayıcı arasındaki\nbağ ne olabilir?",
    ("mpika.msbt",240): "Bir Pokémon'un rengini bilmiyorsan,\nVaka Listene bak.",
    ("mpika.msbt",241): "Bir Pokémon'un rengini bilmiyorsan,\nVaka Listene bak.",
    ("mpika.msbt",266): "İşaretli evlere bir göz atalım mı?{{CTRL:0001:0006:}}\nGeçen haftaki teslimatlar doğru yapılmış mı bakar,\nkayıtları da kontrol edip hiçbir şeyi gözden kaçırmayız!",
    ("mpika.msbt",346): "Dedektif Kahve Notu #7:\nSıcak kahven soğumasın istiyorsan...\nFincanı önceden ısıtmayı sakın unutma.{{CTRL:0001:0006:}}",
    ("mpika.msbt",382): "Herkes kazaya Yanma'nın bir hatasının yol açtığını\ndüşünüyor. Ama gerçekten öyle mi?\nHadi gidip Yanmaların ne diyeceğini dinleyelim.",
    ("mpika.msbt",383): "Yanmalar, kendilerine verilen talimatlara göre\nhareket ettiklerini söyledi.\nPeki bu ne anlama geliyor?",
    ("mpika.msbt",385): "Evet, anlaşılan biri kazaya yol açmak için\nsahte bir hareket planı hazırlamış... Ama neden?\nCarina'nın düşmanı olacağını sanmıyorum.\nYine de gidip ona soralım.",
    ("mpika.msbt",388): "Doğru. Anlaşılan biri çarpışmaya yol açmak için\nYanma'nın planıyla oynamış. Ama personel bunu\nnasıl fark etmedi? Bir Yanma'nın neden iki ayrı\nhareket planı olsun? Bunun kaza olduğuna hiç\ninanmıyorum. Bence önümüzde çözülecek yeni bir dava var!",
    ("mpika.msbt",435): "Tamam, anladım!\nPansage gardiyanların dikkatini dağıtacak...\nO sırada Accelgor konveyör bandını çalıştıracak.\nHerkes bununla uğraşırken de Spinarak'ın ipini\nkullanıp aşağıdaki odaya ineceğiz!\nBence taş gibi plan!",
    ("mpika.msbt",512): "Ne diye panikliyorsun?\nSenden bahsetmiyorum. Emilia'yla benden söz ediyorum.",
    ("mpika.msbt",519): "Şu kalabalığa bak!\nR'nin buraya saçılmasına izin veremeyiz. Çabuk!",
    ("mpika.msbt",521): "Kahretsin!\nSuçlu sıradaki olayı nerede çıkaracak?!{{CTRL:0001:0006:}}\nNe pahasına olursa olsun yakalayacağız!",
    ("mpika.msbt",526): "Daha iki tane var.\nMerak etme!\nBirlikteysek mutlaka buluruz!",
    ("mpika.msbt",530): "Ne oldu?\nBenimle o kadar konuşmak istiyorsun demek?\nEh, peki madem!",
    ("mpika.msbt",531): "Biraz ara versen mi?\nBenden söylemesi: yorgun kafadan parlak fikir çıkmaz.",
    ("mpika.msbt",533): "Tim, baksana! Sörf kullanıyorum!{{CTRL:0001:0006:}}\n*güler* *çığlık atar*",
    ("mpika.msbt",534): "Ben de bir Pikachu'yum, unutma!\nİzle şimdi!\nYıldırım!!",
    ("mpika.msbt",541): "Tim, dava kapandı!\nBak sen, gittikçe gerçek bir dedektife benziyorsun!",
    ("mpika.msbt",547): "Sakin ol, Tim. İyice düşün...\nHa! Buldum!",
    ("mpika.msbt",552): "Pekâlâ. Son bir çıkarım yapalım.\nÇözdüğümüz davalardan birinde Keith\ndoğrudan sana zarar vermeye çalışmıştı.\nHangisiydi?",
    ("mpika.msbt",556): "Aynen öyle!\nKeith belli ki{{CTRL:0001:0006:}}\nperde arkasındaki asıl suçluyla bağlantıdaydı!\nBilgimizin sızmasının nedeni de bu.",
    ("mpika.msbt",559): "Hamle kullanamadığımı söylediğimiz tek kişi Keith'ti.\nDemek ki bunu bilen kişi, tüm bu işlerin\narkasındaki asıl suçlu olmalı.",

    ("episode1.msbt",103): "Hatırlamıyorum ama nedense\nonu hep şapşal biri diye hatırlıyorum.",
    ("episode2.msbt",930): "{{CTRL:0000:0003:FF4B4BFF}}Vaka Notları{{CTRL:0000:0003:FDFDFDFF}}'nı açıp\nkazmayı nasıl yapacağımızı planlayalım.",
    ("episode3.msbt",1655): "Evet, hiçbir şey yok...",
    ("episode3.msbt",1872): "İyi yakaladın, Tim!\nVaka Notları'nı açıp bu bilmeceyi çözelim!",
    ("episode4.msbt",272): "Demek bütün o Pokémonların yaralanmasına\nCrawdaunt sebep olmuş?!\nBöyle bir şeyi kim yapmış olabilir...",
    ("episode6.msbt",1997): "Purugly'yi arıyoruz.\nHiçbir yerde gördün mü?",
    ("episode7.msbt",262): "Fotoğrafları inceleyebilmek için Accelgor'u bulalım.\nİnsanlardan uzak bir yerde olmalı; mesela\n{{CTRL:0000:0003:FF4B4BFF}}konteynerlerin kenarında{{CTRL:0000:0003:FDFDFDFF}}.",
    ("episode7.msbt",266): "Adamın uğraştığı konteynerler hakkında epey\nifade topladık. {{CTRL:0000:0003:FF4B4BFF}}Vaka Notları{{CTRL:0000:0003:FDFDFDFF}}'nı açıp\nhepsini bir araya getirelim.",
    ("episode7.msbt",269): "Hangi deponun üs olarak kullanıldığını bulalım!\n{{CTRL:0000:0003:FF4B4BFF}}Vaka Notları{{CTRL:0000:0003:FDFDFDFF}}'nı aç!",
    ("episode7.msbt",481): "{{CTRL:0000:0003:FF4B4BFF}}Vaka Notları{{CTRL:0000:0003:FDFDFDFF}}'nı açıp bir plan yapalım.",
    ("episode7.msbt",931): "R, sıvı ya da gaz hâlinde olmasına göre\nfarklı özellikler gösterir.\nBu da duruma göre en uygun biçimde\nkullanılabilmesini sağlar.\nHer iki hâli de neredeyse kokusuzdur; yalnızca\nkoku alma duyusu çok gelişmiş Pokémonlar\nonu fark edebilir.",
    ("episode6.msbt",854): "Yönetmenlik de zor işmiş.\nŞimdilik gidip bu programdaki {{CTRL:0000:0003:FF4B4BFF}}diğer oyuncularla{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}konuşalım{{CTRL:0000:0003:FDFDFDFF}}.",
    ("episode4.msbt",1088): "Pokémon çığlığı (*koklar* *hapşırır*)",
    ("episode4.msbt",1856): "Aa, doğru ya. Pokémonların koku alma duyusu\nbizimkinden çok daha keskin.",
    ("episode1.msbt",466): "O kadar da değil. Yeni şeyler öğrendik.\nKolyeye adım adım yaklaşıyoruz.",
    ("episode3.msbt",39): "\"Anlaşılan Pokémonları güçlendiren 'R' maddesi\nbu odada geliştirilmiş.\n'R'nin etkisi geçici, yan etkileri ise ağır.\nŞu hâliyle kullanıma uygun değil.",
    ("episode8.msbt",1546): "Çeşit çeşit içeceğimizin yanı sıra\natıştırmalıklar ve hafif yemeklerimiz de var. Frillish\nsipariş ettiğiniz her şeyi getirir. Salonlara servis yaparlar ama\nsiparişinizi güverteye, hatta odanıza bile\ngetirirler.",
    ("episode4.msbt",210): "Hımm, kayıtta isimleri karıştırmış olabilir miyim?\nKeşke {{CTRL:0000:0003:FF4B4BFF}}bu konuyu{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}Timburrlara sorabilsem{{CTRL:0000:0003:FDFDFDFF}}...",
    ("episode4.msbt",800): "Evlerinin önünde {{CTRL:0000:0003:FF4B4BFF}}işaretli bayrak{{CTRL:0000:0003:FDFDFDFF}} bulunan\nkişilere sorup teslim edilen paketlerin\nkayıtlarla uyuşup uyuşmadığını kontrol edelim.",
    ("detective_note_ep1.msbt",185): "\"donmuş otoyol vakası\" hakkında",
    ("detective_note_ep1.msbt",186): "bir şeyler yazıyor ama çok yıpranmış, okuyamıyorum.",
    ("episode3.msbt",1186): "Bir terazi. Üzerinde tamamen su geçirmez\nolduğu yazıyor.",
    ("episode4.msbt",679): "Doğru. Polis her yeri didik didik aramasına rağmen\nhiçbir şey bulamadı. O hâlde aradığın şey,\nbizim bakamayacağımız bir yerde olabilir mi?",
    ("episode4.msbt",1384): "*güler* Endişelenmiyorum! Bulmacaları çözüp\nbu labirenti şipşak aşarım!",
    ("episode4.msbt",1542): "Sık sık tekne gezintisine çıkar mısın?",
    ("episode7.msbt",742): "Bu işe yarayabilir.\nBakalım... Pansage bize seve seve yardım eder.\nSpinarak da birinci kata inmek istiyordu;\no da yardım edebilir.\nBaşka kim var...",
    ("episode7.msbt",881): "İyice tozu alınınca pırıl pırıl olmuş.",
    ("episode9.msbt",51): "*öfkeyle homurdanır*",
    ("episode9.msbt",661): "{{CTRL:0000:0003:FF4B4BFF}}sarı şapka {{CTRL:0000:0003:FDFDFDFF}}takmış bir adam vardı;\n{{CTRL:0000:0003:FF4B4BFF}}balonları dörder dörder{{CTRL:0000:0003:FDFDFDFF}} asıyordu.\nÇok güzel bir {{CTRL:0000:0003:FF4B4BFF}}pembe balon{{CTRL:0000:0003:FDFDFDFF}} vardı; ben de\nisteyebilir miyim diye sordum ama vermedi.\nSanırım balonlar herkes için.",
    ("episode3.msbt",80): "Ortaya çıkan ilacın etkisi\nbeklediğimden farklı.\"",
    ("episode3.msbt",81): "\"Deneylerimi daha istikrarlı koşullarda\nyürütebilmek için bodrumu inşa ettim.\n\nBeklediğim gibi, yer altında sıcaklık daha sabit;\nbu da çalışmalarımı kolaylaştırıyor. Yine de\nne yaparsam yapayım istediğim sonuçları alamıyorum.",
    ("episode3.msbt",82): "\"Amacım, iyileşme güçlerini artırmak için\nPokémonları etkinleştirmekti; fakat etkiler...\nbeklediğimden çok daha güçlü.\nYine de vazgeçmeyeceğim. Bu her derde deva ilacı\nmutlaka tamamlayacağım.\"",
    ("episode3.msbt",83): "\"Bugünkü karışımın etkisi her zamankinden de\ngüçlüydü. Kontrol ettiğimde, numunenin tam bir hafta\nolgunlaşmaya bırakıldığını öğrendim.\nAnlaşılan Simon talimatlarımı yanlış anlamış.",
    ("episode3.msbt",84): "\"Ama bu, ulaşmaya çalıştığım ilacın tam tersi\nbir etki. Etkiyi bir şekilde kararlı hâle\ngetirmeliyim...\"",
    ("episode3.msbt",85): "\"Kandırıldım!\nBana verilen hücreler o Pokémon'a ait değilmiş...",
    ("episode3.msbt",86): "\"Demek ilacın etkisinin bir türlü kararlı hâle\ngelmemesinin nedeni bu. Hücreler meğer...\nona aitmiş—\"",
    ("episode3.msbt",87): "Ne? Kimin hücreleriymiş?!",
    ("episode1.msbt",470): "Kapkara, ha? Belki onundur?\nAma siyah tüylü başka Pokémonlar da var.\nBilmiyorum.",
    ("episode1.msbt",989): "Kapkara, ha? Sanki bir yerde görmüş gibiyim\nama çıkaramadım.",

    ("episode4.msbt",216): "İnanmıyorsan, gidip {{CTRL:0000:0003:FF4B4BFF}}iskele yakınındaki{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}duyuru panosuna{{CTRL:0000:0003:FDFDFDFF}} bak. Kullandığımız tüm\nişaretlerin tablosu ve topladığımız paketlerin\nkaydı orada.",
    ("episode4.msbt",221): "Geçen hafta tekneyle gelen bütün paketleri\nkayda geçirdik. Louise ayırma işinde bana\nyardım etti; hata olması zor.",
    ("episode4.msbt",447): "Hımm, köprünün önündeki yükte de\naynı işaret vardı.",
    ("episode4.msbt",731): "Halka işaretli bayrağı buldun!",
    ("episode4.msbt",1040): "Doğru. Sonra suçlu, şef bakmıyorken\netiketi yeniden yapıştırıp halka işaretini\noluşturdu.",
    ("episode4.msbt",1069): "Aslında halka şeklinde bir etiket hiç olmadı.\nHalka işaretini suçlu kendisi oluşturdu.\nDr. Waals'ın evindeki etiketi,{{CTRL:0001:0006:}}\nönceden hazırladığı başka bir şeyle birleştirdi.",
    ("episode4.msbt",1918): 'Topladıkları paketlerin kaydı.\nŞöyle yazıyor: "2 {{CTRL:0001:0000:13}}, 1 {{CTRL:0001:0000:10}}, 3 {{CTRL:0001:0000:11}}, 1 {{CTRL:0001:0000:0F}}."',
    ("episode4.msbt",1925): "Her paketin nereye gideceğini gösteren\nbir liste gibi. Kutuların üzerindeki işaretler\nbelirli evleri gösteriyor.",
    ("episode4.msbt",2057): "Ha? Hayır, gitmedim. O gün iskelede\nTimburr Taşımacılık ekibine paketleri\nayırmalarında yardım ediyordum. Böyle bir\ntura çıkmaya vaktim yoktu.",
    ("episode4.msbt",2108): "Duyuru panosuna göre göle gönderilmiş\nhiçbir paket yokmuş.",

    ("episode5.msbt",831): "Ha? Normalde yiyecek kıt olduğu için\nyıldırım düşünce sevindin mi? Hayret bir şey—\nBuneary'nin başı dertte, sen hâlâ\nyemeği düşünüyorsun.",

    ("episode8.msbt",547): "Ne? Kravatım mı yamuk?\nGüvenlik gerçekten buna da mı karışıyor?",
    ("episode8.msbt",1690): "Vah!\nTamam, tamam! Gideriz ama bir şey soralım:\nSandık taşıyan iki adam\nbu taraftan geçti mi?",

    ("mpika.msbt",264): "Halka işaretli paketi Timburrlar\nnereye götürüyor, öğrenelim! Hadi!",
    ("stream.msbt",31): "{{CTRL:0000:0003:1EFF00FF}}(Litwick Mağarası.{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:1EFF00FF}}Ve bu mağaranın bu kadar popüler olmasının sebebi—){{CTRL:0000:0003:FDFDFDFF}}{{CTRL:0001:0006:}}\nEvet...",
}


def general_revision(en:str, jp:str, tr:str):
    notes=[]
    out=tr
    if "Case Notes" in en or "case notes" in en:
        n=out.replace("Dava Notları", "Vaka Notları").replace("dava notları", "vaka notları")
        if n!=out:
            out=n; notes.append("Case Notes → Vaka Notları (JP 推理メモ / ZH 推理笔记)")
    if "Case List" in en:
        n=out.replace("Dava List", "Vaka List").replace("dava list", "vaka list")
        if n!=out:
            out=n; notes.append("Case List → Vaka Listesi (JP 捜査リスト / ZH 调查列表)")
    if "Detective Tip" in en:
        n=out.replace("Dedektif İpucu", "Dedektiflik İpucu")
        if n!=out:
            out=n; notes.append("Detective Tip wording standardized")
    if "deduct" in en.lower() and "tümdengelim" in out.lower():
        n=re.sub(r"Tümdengelim", "Çıkarım", out)
        n=re.sub(r"tümdengelim", "çıkarım", n)
        if n!=out:
            out=n; notes.append("deduction: formal 'tümdengelim' → detective-context 'çıkarım'")

    # TV studio: FR loge / DE Garderobe / ES camerino / JP 控室 all confirm
    # a backstage green/dressing room. Preserve Turkish suffix morphology by replacing
    # only the lexical head: “soyunma odası” → “kulis odası”.
    if "dressing room" in en.lower():
        n=out
        for a,b in [("Soyunma Odası","Kulis"),("soyunma Odası","kulis"),
                    ("Soyunma oda","Kulis oda"),("soyunma oda","kulis oda"),
                    ("Soyununma oda","Kulis oda"),("soyununma oda","kulis oda"),
                    ("Makyaj oda","Kulis oda"),("makyaj oda","kulis oda"),
                    ("Giyinme oda","Kulis oda"),("giyinme oda","kulis oda")]:
            n=n.replace(a,b)
        if n!=out:
            out=n; notes.append("TV-studio dressing room → kulis/kulis odası (FR loge / DE Garderobe / ES camerino / JP 控室)")

    # Disambiguate English “move” with the Japanese source. 技 means a Pokémon move/attack;
    # physical movement uses words such as 動く/動き instead.
    if re.search(r"\bmoves?\b", en, re.I) and "技" in jp and "hareket" in out.lower():
        n=out
        pairs=[
            ("hareketlerini","hamlelerini"),("hareketlerine","hamlelerine"),
            ("hareketlerden","hamlelerden"),("hareketlerle","hamlelerle"),
            ("hareketleri","hamleleri"),("hareketiyle","hamlesiyle"),
            ("hareketinin","hamlesinin"),("hareketine","hamlesine"),
            ("hareketini","hamlesini"),("hareketi","hamlesi"),
            ("hareketlere","hamlelere"),("harekete","hamleye"),
            ("hareketler","hamleler"),("hareket","hamle"),
        ]
        for a,b in pairs:
            n=re.sub(a,b,n,flags=re.I)
        if n!=out:
            out=n; notes.append("Pokémon move disambiguated via JP 技 → hamle")

    # English “scale” has two unrelated senses in this episode. Japanese removes
    # the ambiguity: ウロコ = Pokémon/fish scale (pul), はかり = weighing scale (terazi).
    if "scale" in en.lower() and "ウロコ" in jp and "terazi" in out.lower():
        n=out
        pairs=[("terazilerinin","pullarının"),("terazilerini","pullarını"),("terazilere","pullara"),
               ("terazilerle","pullarla"),("teraziler","pullar"),("teraziye","pula"),
               ("terazinin","pulun"),("teraziyi","pulu"),("terazili","pullu"),("terazi","pul"),
               ("Terazilerinin","Pullarının"),("Terazilerini","Pullarını"),("Terazilere","Pullara"),
               ("Terazilerle","Pullarla"),("Teraziler","Pullar"),("Teraziye","Pula"),
               ("Terazinin","Pulun"),("Teraziyi","Pulu"),("Terazili","Pullu"),("Terazi","Pul")]
        for a,b in pairs: n=n.replace(a,b)
        if n!=out:
            out=n; notes.append("scale disambiguated via JP ウロコ → pul (FR écaille / DE Schuppe / ES escama)")

    # Detective-context “alibi” is not a generic excuse. Keep the established legal/detective term.
    if "alibi" in en.lower() and "mazeret" in out.lower():
        n=out
        pairs=[("mazeretlerini","alibilerini"),("mazeretleri","alibileri"),("mazeretinin","alibisinin"),
               ("mazeretine","alibisine"),("mazeretini","alibisini"),("mazeretin","alibin"),
               ("mazereti","alibisi"),("mazeret","alibi"),
               ("Mazeretlerini","Alibilerini"),("Mazeretleri","Alibileri"),("Mazeretinin","Alibisinin"),
               ("Mazeretine","Alibisine"),("Mazeretini","Alibisini"),("Mazeretin","Alibin"),
               ("Mazereti","Alibisi"),("Mazeret","Alibi")]
        for a,b in pairs: n=n.replace(a,b)
        if n!=out:
            out=n; notes.append("alibi: generic 'mazeret' → detective/legal 'alibi'")

    # Keep the recurring villain-role term coherent. JP 黒幕/真犯人 and the Romance
    # languages consistently mean the person orchestrating events, not a literal “brain”.
    if "mastermind" in en.lower() and "beyin" in out.lower():
        n=out
        pairs=[("asıl beyni","asıl planlayıcıyı"),("asıl beynin","asıl planlayıcının"),
               ("asıl beyin","asıl planlayıcı"),("o beyin","asıl planlayıcı"),
               ("beyni","planlayıcıyı"),("beynin","planlayıcının"),("beyin","planlayıcı"),
               ("Asıl beyni","Asıl planlayıcıyı"),("Asıl beynin","Asıl planlayıcının"),
               ("Asıl beyin","Asıl planlayıcı"),("O beyin","Asıl planlayıcı"),
               ("Beyni","Planlayıcıyı"),("Beynin","Planlayıcının"),("Beyin","Planlayıcı")]
        for a,b in pairs: n=n.replace(a,b)
        if n!=out:
            out=n; notes.append("mastermind terminology → asıl planlayıcı (JP 黒幕/真犯人)")

    # Episode 7 cargo: JP 石油 and FR/IT/ES explicitly mean petroleum, not cooking oil.
    if "oil" in en.lower() and "石油" in jp and "yağ" in out.lower():
        n=out
        pairs=[("Yağların","Petrollerin"),("yağların","petrollerin"),("Yağın","Petrolün"),("yağın","petrolün"),
               ("Yağı","Petrolü"),("yağı","petrolü"),("Yağa","Petrole"),("yağa","petrole"),
               ("Yağdan","Petrolden"),("yağdan","petrolden"),("Yağla","Petrolle"),("yağla","petrolle"),
               ("Yağ","Petrol"),("yağ","petrol")]
        for a,b in pairs: n=n.replace(a,b)
        if n!=out:
            out=n; notes.append("oil disambiguated via JP 石油 / FR pétrole / IT petrolio / ES petróleo → petrol")

    # “pitch-black” describes colour here (JP 真っ黒/まっくろ), not darkness.
    if "pitch-black" in en.lower():
        n=out.replace("Zifiri karanlık", "Kapkara").replace("zifiri karanlık", "kapkara").replace("Zifiri siyah", "Kapkara").replace("zifiri siyah", "kapkara")
        if n!=out:
            out=n; notes.append("pitch-black colour → kapkara (JP 真っ黒/まっくろ)")

    # Episode 8: all four Western localizations resolve generic EN “luggage” as a single crate/box.
    if "men with the luggage" in en.lower():
        n=out.replace("Valizli adamlar", "Sandık taşıyan adamlar").replace("valizli adamlar", "sandık taşıyan adamlar")
        n=n.replace("Bavullu adamlar", "Sandık taşıyan adamlar").replace("bavullu adamlar", "sandık taşıyan adamlar")
        if n!=out:
            out=n; notes.append("men with luggage → sandık taşıyan adamlar (FR caisse / DE Kiste / IT cassa / ES caja)")

    if "sniff" in en.lower():
        n=out.replace("*hımm hımm*", "*koklar*").replace("*Hımm hımm*", "*koklar*").replace("*kokla*", "*koklar*")
        if n!=out:
            out=n; notes.append("sniff stage direction normalized → *koklar*")

    # Patch-internal move glossary: pikasigntitle already establishes these names.
    if "Thunderbolt" in en:
        n=out
        for a in ["Yıldırım Şoku", "yıldırım saldırısı", "Yıldırım saldırısı", "Şimşek"]:
            n=n.replace(a, "Yıldırım")
        if n!=out:
            out=n; notes.append("Thunderbolt → Yıldırım (patch glossary consistency)")
    if "Surf" in en and "Sörf yapıyorum" in out:
        n=out.replace("Sörf yapıyorum", "Sörf kullanıyorum")
        if n!=out:
            out=n; notes.append("Surf move phrasing normalized")

    if "sense of smell" in en.lower() and "koku alma duyuşu" in out:
        out=out.replace("koku alma duyuşu", "koku alma duyusu")
        notes.append("sense of smell: koku alma duyusu")

    # Safe orthography fixes.
    typo_pairs=[("hiç bir", "hiçbir"), ("yani sıra", "yanı sıra"), ("Çözdüg", "Çözdüğ"), ("çözdüg", "çözdüğ"),
                ("ipuçlarina", "ipuçlarına"), ("ipucularina", "ipuçlarına"), ("haşat", "hasat")]
    for a,b in typo_pairs:
        if a in out:
            out=out.replace(a,b); notes.append(f"Orthography: {a} → {b}")
    return out, notes


def main():
    if len(sys.argv)!=6:
        print("usage: build_revision_workspace.py ORIGINAL_MESSAGE_DIR ORIGINAL_TURKISH_DIR REPAIRED_TURKISH_DIR OUT_CSV_DIR BASE_COMPARISON_DIR")
        raise SystemExit(2)
    message_dir=Path(sys.argv[1]); current_dir=Path(sys.argv[2]); repaired_dir=Path(sys.argv[3]); out_dir=Path(sys.argv[4]); base_csv=Path(sys.argv[5])
    out_dir.mkdir(parents=True, exist_ok=True)
    files=sorted(p.name for p in (message_dir/'English').glob('*.msbt'))
    summary=[]
    semantic_changes=[]
    technical_repairs=[]
    for fname in files:
        parsed={lang:parse_msbt(message_dir/lang/fname) for lang in LANGS}
        cur=parse_msbt(current_dir/fname); rep=parse_msbt(repaired_dir/fname)
        n=len(parsed['English']['raws'])
        rows=[]
        for i in range(n):
            en=decode_text(parsed['English']['raws'][i]); cur_t=decode_text(cur['raws'][i]); rep_t=decode_text(rep['raws'][i])
            rev, notes=general_revision(en, decode_text(parsed['JPN']['raws'][i]), rep_t)
            status=[]
            if cur_t!=rep_t: status.append('TECH_REPAIRED')
            if (fname,i) in OVERRIDES:
                rev=OVERRIDES[(fname,i)]
                notes.append('Curated multilingual/contextual revision')
                status.append('CURATED')
            elif rev!=rep_t:
                status.append('GLOSSARY')
            if control_signature(rev)!=control_signature(en):
                raise ValueError(f"Control signature mismatch after revision: {fname}:{i} {parsed['English']['labels'].get(i)}\nEN={en}\nREV={rev}")
            row={"Index":i,"Label":parsed['English']['labels'].get(i,f'__INDEX_{i}')}
            for lang in LANGS: row[lang]=decode_text(parsed[lang]['raws'][i])
            row['Turkish_Current']=cur_t
            row['Turkish_Technical_Repaired']=rep_t
            row['Turkish_Revised']=rev
            row['Review_Status']='+'.join(status) if status else 'UNCHANGED'
            row['Review_Notes']='; '.join(notes)
            rows.append(row)
            audit_row={'File':fname, **row}
            if cur_t!=rep_t:
                technical_repairs.append(audit_row.copy())
            if rev!=rep_t:
                semantic_changes.append(audit_row.copy())
        headers=['Index','Label']+LANGS+['Turkish_Current','Turkish_Technical_Repaired','Turkish_Revised','Review_Status','Review_Notes']
        out=out_dir/(Path(fname).stem+'.csv')
        with out.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=headers); w.writeheader(); w.writerows(rows)
        sem=sum(r['Turkish_Revised']!=r['Turkish_Technical_Repaired'] for r in rows)
        tech=sum(r['Turkish_Current']!=r['Turkish_Technical_Repaired'] for r in rows)
        summary.append((fname,n,tech,sem))
    with (out_dir/'_manifest.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['File','Rows','TechnicalRepairRows','SemanticRevisionRows']);w.writerows(summary)

    audit_headers=['File','Index','Label']+LANGS+['Turkish_Current','Turkish_Technical_Repaired','Turkish_Revised','Review_Status','Review_Notes']
    for name,data in [('_semantic_changes.csv',semantic_changes),('_technical_repairs.csv',technical_repairs)]:
        with (out_dir/name).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=audit_headers); w.writeheader(); w.writerows(data)
    print(f'Built {len(files)} review CSVs. technical-repair rows={sum(x[2] for x in summary)}, semantic-revision rows={sum(x[3] for x in summary)}')

if __name__=='__main__': main()
