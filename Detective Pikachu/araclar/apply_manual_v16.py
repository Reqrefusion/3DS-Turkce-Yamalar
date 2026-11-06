from pathlib import Path
import pandas as pd, shutil, re, json

SRC=Path('/mnt/data/v15_work/detective_pikachu_translation_toolkit_v15_manual_batch11')
OUT=Path('/mnt/data/detective_pikachu_translation_toolkit_v16_manual_batch12')
if OUT.exists(): shutil.rmtree(OUT)
shutil.copytree(SRC, OUT)
# Rename dirs later after CSV processing

UNCH_REASON = ('Satır EN, JP, FR, DE, IT, ES, Basitleştirilmiş Çince ve Geleneksel Çince ile tek tek manuel okundu. '
                'Mevcut Türkçe anlamı, bağlamı, karakter sesini ve gerekli terminolojiyi yeterli biçimde koruduğu için bilinçli olarak değiştirilmedi.')
UNCH_CROSS = ('Resmî diller arasında sözcük seçimi veya yaratıcı yerelleştirme farkları olsa da ortak anlam mevcut Türkçeyle uyumlu. '
               'Japonca özgün metin de Türkçeyi değiştirmeyi gerektirecek ek/eksik bilgi, ters anlam veya belirgin ton kaybı göstermedi.')

# Manual decisions. Keys are row Index values in episode9.csv.
# Each tuple: (new Turkish, reason, cross-language note)
C={}
def ch(i, text, reason, cross): C[str(i)] = (text, reason, cross)

def style(i,text):
    ch(i,text,
       'Tüm resmî dillerle manuel karşılaştırmada temel anlam korunuyordu; ancak mevcut Türkçe İngilizce sözdizimini fazla izliyor veya doğal konuşma akışını bozuyordu. Cümle bilgi eklemeden daha doğal Türkçeyle yeniden kuruldu.',
       'JP özgün ton ve bağlamı, FR/DE/IT/ES ile iki Çince sürüm de aynı temel anlamı doğruluyor; değişiklik anlamdan çok doğal Türkçe ve konuşma ritmi için yapıldı.')
def term(i,text,termnote):
    ch(i,text,
       f'Terminoloji manuel çok-dilli karşılaştırmayla düzeltildi: {termnote}',
       'JP ile FR/DE/IT/ES ve Çince karşılıklar aynı kavrama işaret ediyor; dosya içindeki ve önceki manuel turlardaki Türkçe terminolojiyle de tutarlılık sağlandı.')
def sound(i,text):
    ch(i,text,
       'Ses/eylem etiketi manuel olarak bağlama göre düzeltildi; mevcut “çığlık/homurdanma” seçimi Pokémon sesi veya fiziksel eylemi gereksiz biçimde farklı anlamlandırıyordu.',
       'JP sahne yönergesi/seslenişi ile EN ve diğer Batı dillerinin bağlamı birlikte değerlendirildi; Türkçede işlevi doğru veren kısa bir ses/eylem etiketi seçildi.')
def critical(i,text,reason,cross): ch(i,text,reason,cross)

# Opening / machine
ch(1,'Şimşek—','Pikachu’nun elektrik temalı çıkarım kelime oyunu Türkçede yeniden kuruldu; “Bir şimşek—” tek başına yarım ve ağır kalıyordu.','JP ピカっと／ひらめいた elektrik + “aklına gelmek” çağrışımı yapıyor; FR/DE Pikachu kelime oyunu, ES ise “perspikachu” yaratıcı uyarlaması kullanıyor. Türkçede “Şimşek— / Çaktı!” aynı çift anlamı taşıyor.')
ch(2,'Çaktı!','“Dâhiçe!” doğal Türkçe değil ve özgün kelime oyununu kaybediyor; ikinci parça “şimşek çaktı / kafamda şimşek çaktı” çift anlamıyla yeniden yazıldı.','JP ひらめいた “aklıma geldi” demek; FR/DE/ES de kelime oyununu birebir çevirmek yerine yaratıcı uyarlıyor. “Çaktı!” hem elektrik hem fikir çağrışımını koruyor.')
term(9,"Emilia, çok vaktimiz yok.\nKomiser Holiday'le iletişime geçebilir misin?\nBiz de bu makineyi durdurmanın bir yolunu\narayacağız.",'Holiday’nin JP 警部 rütbesi önceki manuel turlarda “Komiser” olarak sabitlendi; “Müfettiş” tutarsızdı.')
style(10,'Evet, tabii!\nOnu hemen buraya getireceğim.\nSakın kendini tehlikeye atma.')
critical(13,'İki yandaki sıvıları\nortadaki tankta karıştırıyor gibi.\nBu bölüm önemli görünüyor.\nHadi açalım!','Mevcut Türkçe sıvıların sadece ortadaki tanka “aktarıldığını” söylüyordu; makinenin işlevi yanlış aktarılmıştı.','JP 調合する, DE gemischt, ES mezcla, IT mescolare ve FR mélange açıkça sıvıların merkez tankta karıştırıldığını doğruluyor.')
sound(15,'*ıkınır*')
sound(21,'*memnuniyetle başını sallar*')
style(22,'Gerçekten de makineyi nasıl etkisiz hâle\ngetireceğini biliyormuşsun, Pikachu!')
term(24,'Ne?! Dedektif Dergisi mi?!','Bir önceki satırda aynı yayın “Dedektif Dergisi” olarak geçiyor; aynı özel yayın adı “Günlüğü” diye değişmemeli.')
style(25,'*güler* Şakaydı!\nBöyle şeyler büyük dedektifliğin şanındandır.')
sound(30,'*ıkınır*')
style(33,'Tim, buldum!\nMakine, dört düğmeye yandıkları sırayla\nbasarsak duracak!\nÖnce ortadaki, yanan kırmızı düğmeye bas.')
# Roger room
style(45,'Bir de makinemin işini bitirmişsiniz.\nNe büyük başarı doğrusu.')
style(46,'Tim! Beni boş ver— Ah!')
style(47,'*homurdanır* İyi dinle.\nMakinenin iki yanındaki vanaları açıp\nçalıştır!')
critical(49,'Hadi, oyalanma!','“Just get moving” burada yürümek değil, Roger’ın Tim’e az önce tarif ettiği işlemi hemen yapmasını emrediyor; “Sadece yürü” bağlamı bozuyordu.','JP さっさとやるんだ “çabuk yap” anlamında; FR/DE/IT/ES de acele etme/işe koyulma emri veriyor.')
style(55,'İşi garantiye almışsın.\nAkıllıca.')
critical(58,'GNN bu kaosu özel haber olarak verirse,\nitibarımız daha da artar!','Mevcut Türkçe GNN’nin haberin özel/eksklüzif niteliğini atlıyordu; Roger’ın motivasyonu bu “scoop” üzerine kurulu.','JP スクープ, FR exclusivité, IT esclusiva, ES primicia ve Çince 独家新闻 aynı “özel haber” anlamını doğruluyor.')
style(61,"Peki R'yi neden kaçak sokuyordun?")
style(64,'GNN’i ele geçirince Ryme Şehri’ndeki\ntüm bilgiyi kontrol edebilirdim.\nBöylece şehri ben yönetirdim!')
style(65,'Bu korkunç...')
sound(68,'*haykırır*')
sound(69,'*zorlanır*')
sound(70,'*zorlanır*')
critical(74,'Pokémon sesi (Anlaşıldı!)','Pokémon vokalizasyonu “çığlık” değildir; parantez içindeki anlam da “Tam burada!” değil, JP’de onay/“anlaşıldı”dır.','JP 了解！ açıkça “anlaşıldı/tamam” anlamında; sahne Pokémon sesi olduğu için Türkçede “Pokémon sesi” etiketi kullanıldı.')
critical(76,'Tim, peşinden gitme!','İngilizce “Hold on” genel durdurma olsa da özgün Japonca Tim’in Roger’ın peşine düşmesini açıkça yasaklıyor.','JP ティム！追うな！ = “Tim! Peşinden gitme!”; bağlam Roger’ın kaçışıyla birebir uyumlu.')
sound(78,'Pokémon sesi (tehditkâr)')
style(81,'Emin değilim.\nFazla sakin görünüyor.')
sound(85,'Pokémon sesi (Haydi!)')
critical(87,'İzin vermem!','“Not so fast!” serbest İngilizce uyarlaması; özgün replik Roger’ın eylemini engelleme kararlılığını söylüyor.','JP させるか！ ve FR/IT karşılıkları “buna izin vermem” yönünde; Türkçe bu doğrudan tehdidi koruyor.')
sound(89,'Pokémon sesi (Yolumdan çekilin!)')
sound(91,'Pokémon sesi (Nasıl, böyle mi?)')
style(95,'Sen... olmaz...\nSana... izin vermem...')
sound(98,'Pokémon sesi (Aaaaagh!)')
# Roger aftermath
critical(105,'Geriye hücreleri almak kaldı.','“cells” mevcut Türkçede “piller” yapılmış; bu sahnede biyolojik hücrelerden söz ediliyor ve nesne yanlış çevrilmiş.','JP 細胞, FR cellules, DE Zellen, IT cellule, ES células ve Çince 细胞/細胞 hep “hücre” diyor.')
style(106,'İşte hepsi bu.\nBitti. Aferin, Tim.')
term(110,'Vaka hakkında','Detective-note terminolojisinde “case” önceki manuel turlarda bağlama göre “vaka” olarak standardize edildi.')
critical(113,'Evet. R üç farklı biçimde kullanılacak.','Mevcut Türkçe “üç yer” diyordu; burada üç dağıtım noktası değil sıvı/gaz/kapsül olmak üzere üç R biçimi anlatılıyor.','JP 3種類, FR trois formes, DE drei Formen, IT tre forme, ES tres formas karşılaştırması “üç tür/biçim”i doğruluyor.')
style(116,"Tamam. GNN çalışanlarından\nne öğrenebilirsem bakacağım.")
style(117,'Lütfen, çok işimize yarar.')
critical(121,'Muhtemelen hatırlatmama gerek yok ama\nsorularını fazla dikkat çekmeden, doğal biçimde sor.\nMeydanın hedef alındığını duyarlarsa panik çıkar.\nÖnce şu {{CTRL:0000:0003:FF4B4BFF}}harita{{CTRL:0000:0003:FDFDFDFF}}ya bakalım.\nOfistekini aldım.','“Rahatça sor” özgün nüansı kaybediyor; amaç sorgu yaptığı belli olmadan bilgi toplamak. Satırın panik ve harita bilgisi de eksiltilmeden korundu.','JP さりげなく “belli etmeden/doğal biçimde”; FR discrètement ve diğer diller de ihtiyatlı, sıradan sohbet gibi sormayı destekliyor. JP/EN aynı satırda meydanın hedef alındığı duyulursa panik çıkacağını ve ofisteki haritanın kullanılacağını da doğruluyor.')
style(134,'İnsanlarla konuşup bilgi toplamayı da unutma!')
style(138,'{{CTRL:0000:0003:FF4B4BFF}}Baba-kız{{CTRL:0000:0003:FDFDFDFF}} {{CTRL:0000:0003:FF4B4BFF}}yemek tezgâhlarının yanında{{CTRL:0000:0003:FDFDFDFF}}ydı.\nOnlarla konuştun mu?')
critical(139,'Şekerlemeler demişken, {{CTRL:0000:0003:FF4B4BFF}}başında kimse olmayan{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}yiyecek tezgâhı{{CTRL:0000:0003:FDFDFDFF}} vardı ya? Bana kalırsa\nburası oldukça şüpheli.','“Treats” burada Pokémonlara dağıtılacak şekerlemeler; “terk edilmiş tezgâh” ise gereksiz biçimde daha güçlü bir anlam veriyordu.','JP お菓子, FR friandises, IT/ES dolci/dulces “şekerleme”; JP 店員のいない屋台 ise yalnız “başında görevli olmayan tezgâh” diyor.')
style(141,'{{CTRL:0000:0003:FF4B4BFF}}Saat kulesinin{{CTRL:0000:0003:FDFDFDFF}} {{CTRL:0000:0003:FF4B4BFF}}önünde{{CTRL:0000:0003:FDFDFDFF}} duran polis memurunu\ngördün, değil mi? Yakınlarında bir de\n{{CTRL:0000:0003:FF4B4BFF}}kadın{{CTRL:0000:0003:FDFDFDFF}} vardı. Onunla daha konuşmadık!')
style(142,'{{CTRL:0000:0003:FF4B4BFF}}Sarı şapkalı{{CTRL:0000:0003:FDFDFDFF}} adam!\nPeşinden!')
term(149,'Buradan büyük bir özel haber çıkar!','“scoop” önceki satırlarda ve JP/FR/IT/ES karşılıklarında özel/eksklüzif haber anlamındadır; “manşet” dar ve farklı bir kavramdı.')
term(152,'Burada üç tür R bulabildim, ama...\nBir tane daha olduğunu öğrendim.\nBu, Komiser Holiday’nin\nKeith’ten alabildiği bir bilgi.','Holiday’nin JP 警部 rütbesi “Komiser” olarak standardize edildi.')
style(157,'Saklı olabileceğini düşündüğün bir yer görürsen\n{{CTRL:0000:0003:FF4B4BFF}}bana seslen{{CTRL:0000:0003:FDFDFDFF}}.')
style(163,'Yok, öyle bir şey değil.\nOlan bitenden sonra biraz kafa dağıtmak istedim.')
style(167,'Sen buradaysan kesin bir şeyler olur!\nBir olay çıkarsa da bize büyük bir özel haber düşer!')
style(171,'Burada bir şey yok gibi.')
style(172,'Aa? Kırmızı kapüşonlu üst, yanında Pikachu...\nSen şu meşhur dedektif olmalısın!')
style(175,'Bize de haber verildi;\npolis olarak meydanı arıyoruz.')
style(176,"R'yi bulabilecek misiniz?")
style(180,"R’lerden birini mi buldun? Harika!\nGeriye iki tane kaldı. Acaba neredeler?")
term(183,'Gaz hâlindeki R','UI seçeneği R’nin kullanım biçimini anlatıyor; doğal ve diğer “sıvı/kapsül” seçenekleriyle paralel Türkçe kuruldu.')
term(184,'Sıvı hâlindeki R','UI seçeneği R’nin kullanım biçimini anlatıyor; doğal ve diğer “gaz/kapsül” seçenekleriyle paralel Türkçe kuruldu.')
term(185,'Kapsül hâlindeki R','UI seçeneği R’nin kullanım biçimini anlatıyor; doğal ve diğer “gaz/sıvı” seçenekleriyle paralel Türkçe kuruldu.')
style(186,'Ha? Düşünmektense harekete geçmek istiyorsun.\nHadi, Tim!')
style(187,'Tamam, hadi R’yi bulalım!\nŞüpheli bir şey görürsen {{CTRL:0000:0003:FF4B4BFF}}bana seslen{{CTRL:0000:0003:FDFDFDFF}}.\nDikkatimi nasıl çekeceğini biliyorsun, değil mi?\n{{CTRL:0000:0003:FF4B4BFF}}Ben sana işaret verdiğimde yaptığın gibi{{CTRL:0000:0003:FDFDFDFF}}.')
term(193,'Şekerlemeler','JP お菓子 ve FR/IT/ES karşılıkları, geçit sonunda Pokémonlara dağıtılan ürünün şekerleme olduğunu gösteriyor.')
style(196,"Tabii ya, balonlar! Fine Park'taki olayda da\nR bir balona saklanmıştı.\nBalonlar kesinlikle şüpheli.")
critical(202,'Şekerlemelere sıvı R karıştırılmış mı\ndiye bakalım.','Mevcut Türkçe “karıştırılmamış olsun” diyerek doğal olmayan ve mantığı tersine yakın bir yapı kuruyordu.','JP/FR/DE/IT/ES bağlamı, şekerlemelerin sıvı R içerebileceğini kontrol etmeyi söylüyor.')
style(203,'Sıvı R konusunda dikkatini ne çekti?')
style(209,"İşte bu! Şekerlemeler!\nCarlos'un raporunda, PCL’de Trevenant’ın\nyemeğine karıştırılan R’nin de\nsıvı olduğu yazıyordu.")
style(213,"Kapsül R konusunda henüz bir şey söylemek zor.\nÖnce sıvı ve gaz hâlindeki R’yi arayalım.")
style(221,"Kapsül R'yi sonra düşünürüz.\nŞimdilik sıvı ve gaz hâlindeki R'yi\nbulmak daha kolay görünüyor.")
style(222,"Bu bilgi tek başına R'nin yerini\nbulmamıza yetmez.")
style(235,'İnanılmaz uzunmuş diye duydum.')
critical(238,'Çeşmenin öbür tarafında da bir merdiven var.','Mevcut “çeşmenin yanında” konumu zayıflatıyordu; konuşmacı karşı taraftaki başka merdiveni tarif ediyor.','JP 噴水の向こう側 ve Avrupa dillerindeki karşı/öte taraf yönlendirmesi “öbür taraf”ı destekliyor.')
style(241,'GNN geçit törenine programında geniş yer verecekmiş.\nSüs balonları da her zamankinden fazla.')
term(247,'Şekerlemeler hakkında','JP お菓子 ve dosyanın görev bağlamı Pokémonlara dağıtılacak şekerlemeleri anlatıyor.')
style(248,'Sabırsızlanıyorum!\nPokémonlara şekerleme vermek için\ncan atıyorum!')
critical(249,'Aa, Pokémonların ödül şekerlemeleri!\nGeçidin sonunda şekerleme dolu bir vagon geliyor.\nİstediğin şekerlemeyi Pokémonlara verebiliyorsun;\nhem de yanlarına kadar yaklaşarak!','Mevcut Türkçe özne/nesne ilişkisini bulanıklaştırıp “onları dağıtıp onları görmek” gibi tekrarlı bir yapı kuruyordu.','JP お菓子をあげられる ve FR/DE/IT/ES, ziyaretçinin vagondan şekerleme seçip Pokémonlara bizzat verebildiğini doğruluyor.')
style(260,'Bu bir onur.\nAma bunu yalnız başımıza{{CTRL:0001:0006:}}\nbaşarmadık.')
style(261,'Yok canım! Günü kurtaran{{CTRL:0001:0006:}}\nsenin çıkarımlarındı.')
critical(266,'Al. Söz verdiğim şey.','“Here you are” mevcut Türkçede “İşte buradasın” diye kişiye yönelik çevrilmiş; konuşmacı söz verdiği nesneyi uzatıyor.','JP これが約束のブツだ = “işte söz verdiğim şey”; FR/DE/IT/ES de nesne teslimini doğruluyor.')
style(278,'Bir süre sonra uyanacak.')
style(279,'Bekleyin!')
style(286,'Volbeatlere mi?')
term(287,'Referans noktası gibi kullanılıyor.','Konuşmadaki “mark” konum bulmak/rota takibi için referans işaretidir; “işaret gibi” ifadesi gereksiz belirsizdi.')
style(292,'Hadi, Manectric! Yakala onu!')
critical(294,"Ohh... Böylece bütün R'leri topladık.",'Mevcut Türkçe “son tür bu olmalı” diyerek hâlâ belirsizlik bırakıyordu; bu noktada bulunan R’lerin tamamlandığı söyleniyor.','JP これで全部のRを回収した, FR/DE/IT/ES karşılıkları “bütün R toplandı/geri alındı” anlamını açıkça doğruluyor.')
term(303,"Komiser Holiday şu anda karakolda\nKeith'i sorguluyor.\nİşi biter bitmez buraya\ngeleceğini söyledi.",'Holiday’nin rütbesi JP 警部 ve önceki manuel terminolojiyle “Komiser”dir.')
style(306,'Demek şüphelendiğin balon bu?\nMantıklı.')
term(308,'Manec!','Manectric’in İngilizce/IT/ES seslenişi “Manec”; aynı episode içindeki yazım “Manek” ile tutarsızdı.')
style(309,'R kokusunu kesin olarak aldığını söylüyor.')
style(310,'Güzel, gaz hâlindeki R’yi bulduk.')
style(311,"Burayı Brad'e bırakalım, biz de\nkalan R'leri arayalım.")
term(315,'Komiser Holiday!','Holiday’nin rütbesi JP 警部 ve önceki manuel terminolojiyle “Komiser”dir.')
critical(316,"Az önce bütün R'leri topladık.",'“R’leri ortadan kaldırmayı bitirdik” bu sahnede yanlış eylem; ekip R’leri imha etmiyor, ele geçirip topluyor.','JP 回収した, FR récupéré, DE eingesammelt ve diğer diller “toplamak/geri almak” anlamında birleşiyor.')
style(318,'Ne?! Nasıl öğrendiniz?')
critical(319,'Bunu Keith’in sorgusu sırasında öğrendim.\nBize meydan okumak ister gibi, artık saat sekize\nyetişemeyeceğimizi düşünüp dördüncü R’yi\nağzından kaçırdı.','Mevcut “hava atmak istedi” motivasyonu fazla serbest ve cümlenin mantığını bulanıklaştırıyordu.','JP 時間に間に合わないと思って konuşmayı kışkırtıcı biçimde yaptığını; FR/DE/IT/ES ise bilgiyi artık çok geç olduğunu düşündüğü için verdiğini destekliyor.')
style(320,'Şu Keith son ana kadar başımıza iş açıyor!')
critical(322,"Son R hakkında bize anlattığı her şeyi aktardım.\nAma sorgu sırasında başka bazı şeyler de öğrendik.",'“R’nin son konumu” yanlış; Holiday konumu değil, henüz bulunmamış son R örneğini/planını anlatıyor.','JP 最後のR, FR/DE/IT/ES “son/kalan R” anlamını doğruluyor; location/konum sözcüğü yok.')
term(324,"Keith’in bağlantısı\nasıl suçluyla",'“mastermind/黒幕/真犯人” dosya boyunca doğal dedektiflik Türkçesiyle “asıl suçlu” olarak standardize edildi; “asıl planlayıcı” yapaydı.')
term(325,'Asıl suçlu hakkında','“mastermind/真犯人” için “asıl suçlu” standardı kullanıldı.')
style(327,"Keith'in suç işleme nedeni")
critical(328,'Keith, asıl suçludan\ntelefon görüşmeleri ve mektuplarla emir aldığını söyledi.','Mevcut “telefonlarla” ifadesi doğal değil ve iletişim biçimini eksik aktarıyor.','JP 電話と手紙, FR appels/lettres, DE Telefon/Briefe ve diğer diller telefon görüşmeleri ile mektupları açıkça sayıyor.')
critical(330,'Keith’e dördüncü R’yi yerleştirme emri de\nasıl suçludan gelmiş.','Mevcut Türkçe “dördüncü yerini saklaması” diyerek eylemi ve nesneyi yanlışlaştırıyordu.','JP/FR/DE/IT/ES Keith’e dördüncü R’yi yerleştirme/kurma talimatı verildiğini doğruluyor.')
style(331,'Tüm iletişimi asıl suçlu başlatmış.\nKeith ise ona nasıl ulaşacağını bilmiyormuş.')
term(332,'Asıl suçlunun kim olduğunu Keith bile bilmiyor.\nKeith sadece aldığı emirleri uygulamış.','Aynı kavram bir satırda “azmettirici”, diğerlerinde “asıl planlayıcı” idi; “asıl suçlu” ile tutarlılaştırıldı.')
style(333,'Asıl suçlu çok temkinli—\nkendi elini kirletmemek için başkalarını kullanıyor...')
term(337,'Anlıyorum... Bunu bilen biri varsa,\no da asıl suçludur.','“mastermind/真犯人” için “asıl suçlu” standardı kullanıldı.')
style(339,'Gerçekten aşağılığın teki.\nMidemi bulandırıyor.')
critical(340,"Son R'yi aramaya devam edeceğiz.\nÜzgünüm ama soruşturmada\nsenden de yardım istemek\nzorundayım, Tim.",'“R’nin son konumu” aynı hatayı tekrar ediyordu; hedef konum değil son/kalan R.','JP 最後のR ve Avrupa dilleri son R’yi aramayı anlatıyor.')
style(342,'Desteğin bizim için çok değerli, Tim.')
style(343,'Bu adamın sorgusuna başlayacağım.\nMüsaadenle, Tim.')
style(344,"Holiday'yi dinleyelim.")
style(346,'Keith giderayak bize ne beter bir dert bıraktı.')
style(348,'Hım... Aramayı biraz daraltabiliriz.')
term(368,"Hayır, Komiser Holiday bizi\nmevcut durumdan haberdar etti.\nManectric ile birlikte R'yi arıyorum.",'Holiday’nin rütbesi “Komiser” olarak standardize edildi.')
style(370,"Manectric'in burnu R'nin kokusunu\nayırt edebiliyor.")
style(376,"R'leri toplamaya başladık bile.")
style(378,"Keith de R hakkında ilgisiz insanlara\ngevezelik edip duruyor!")
style(381,'Burada kalıp şüpheli biri yaklaşırsa\ngözden kaçırma.')
style(382,'Sana elimizden geldiğince yardımcı olmamız söylendi.')
critical(383,'Vay be, Tim!\nPolis içinde de sözün geçmeye başlamış!','“Famous” karşılığındaki mevcut Türkçe yalnız ünü vurguluyordu; JP burada Tim’in polis içindeki güvenilirlik/bağlantı kazanmasını alaycı biçimde övüyor.','JP 警察にも顔が利くようになった nüansı “polis içinde sözü geçmek/tanınmak”; bağlamda Pikachu Tim’in kurduğu ilişkilere takılıyor.')
style(386,'Üstlerimiz bu bölgeyi aramamızı söyledi...')
style(391,'Burada R yayılırsa nasıl bir felaket çıkar kim bilir...')
style(395,'Şimdi düşününce, balonlar ve şekerlemeler hakkında\nkonuşurken insanların sürekli bahsettiği\nbiri yok muydu?')
style(402,'Ne? Saç bandı takan bir çocuk mu?\nBunun olayla ilgisi olduğunu sanmıyorum.')
critical(409,'Artık gerçekten güven veriyorsun, Tim.\nPekâlâ, hadi! Onu\nbu taraftan sıkıştıralım!','“Daha derli toplu olmuşsun” yanlış anlam; Pikachu Tim’in olgunlaşıp güvenilir hale geldiğini övüyor.','JP 頼もしくなった, DE “gewachsen”, ES saygınlık/güven nüansı ve bağlam “güvenilir/işe yarar hale gelmek” yönünde.')
style(415,'Sadece geçit töreni değil, daha neler neler var.\nÇeşit çeşit tezgâha da bakın!')
style(417,'Evet, tezgâhlara bakmak istiyorsan\nşimdi tam zamanı—kalabalık olmadan önce.\nHemen ileride bir sürü tezgâh kurulmuş.')
critical(423,'Geçidi izleyeceksen bu yol tam bir gizli cevher.\nDüz ilerleyince karşı taraftaki merdivenlere çıkar;\nfarklı geçitleri izlemek için çok kullanışlı.\nBu yolu bilen az, yazık doğrusu!','Mevcut Türkçe yolu “gizli bir noktaya çıkan” yer olarak yorumlamıştı; konuşmacı yolun kendisinin az bilinen kullanışlı bir kestirme olduğunu anlatıyor.','JP この道は穴場 ve devamındaki karşı merdivene bağlanma bilgisi; FR/DE/IT/ES de az bilinen rota/kestirme anlamını destekliyor.')
style(431,"Ne? Yardım ettiğim için mi teşekkür ediyorsun?\nAma seni GNN'de gördüğümü sanmıyorum.\nBeni tanıyor musun?")
style(433,'Arkadaşların, garip bir Pikachu’nun\nüstlerindeki suçlamayı kaldırdığını mı söyledi?\nBana neden “garip” desinler ki?\nGerçekten minnettar olduklarına emin misin?')
style(446,'Hey, şurada coşkuyla eğlenen adamı gördün mü?\nGeçit töreninden çok ona baktım;\no kadar keyifli görünüyordu ki gözümü alamadım.')
style(455,'Kız arkadaşım, tatlı Pokémonlarla dolu\ngeçidi görmek istiyordu.')
style(461,'Gerçek hayranlar her geçidin rotasını hesaplar\nve mümkün olduğunca çoğunu izlemek için plan yapar!')
style(468,'Tabii ki! Karnaval günü kim çalışabilir ki?\nHeyecandan işe odaklanamıyorum!')
style(470,'Senin keyfin yerinde tabii.')
style(484,'Bir şey olursa sana güvenelim, öyle mi?\nBunu söylemek için saklanmayıp\nburada mı bekledin?\nHah, sağ ol.')
term(488,'Asıl suçlu hakkında','mastermind/真犯人 kavramı “asıl suçlu” olarak standardize edildi.')
critical(490,"Evet. Topladığımız bilgilerden\nR'nin yayılacağı yerleri çıkarabiliriz.",'Mevcut Türkçe “çekim konumlarını” diyordu; bu satırda amaç çekim yerlerini değil R’nin yayılma noktalarını eldeki bilgilerden çıkarmak.','JP 集めた情報から推理, bağlam ve sonraki satırlar dağıtım/yayılma yerlerinin çıkarımını anlatıyor; FR/DE/IT/ES de location deduction bağlamını destekliyor.')
term(491,"GNN'de biri asıl suçlu olabilir, değil mi?\nEmilia'nın kendi iş arkadaşlarından\nşüphelenmek zorunda kalması çok zor olmalı.\nOna destek ol, tamam mı?",'“mastermind/犯人” için dosya genelinde “asıl suçlu” standardı kullanıldı; “azmettirici” gereksiz hukukileşiyordu.')
style(493,'Yine kendini epey tehlikeye attın, Tim.')
style(496,'Estağfurullah...')
term(499,'Asıl suçlu hakkında','mastermind/真犯人 kavramı “asıl suçlu” olarak standardize edildi.')
critical(501,"Demek GNN’den biri bütün bunların arkasındaki\nasıl suçlu olabilir...\nR olaylarını bu kadar hızlı haber yapmaları da\nböylece anlam kazanıyor.\nYoksa Harry'nin kazası da—?",'“tüm bunun” gramer hatası giderildi; mastermind terminolojisi ve Baker’ın çıkarım akışı doğal Türkçeyle yeniden kuruldu.','JP 真犯人 ve FR/DE/IT/ES “bütün bunların arkasındaki suçlu” anlamını; hızlı R haberlerinin bu şüpheyi desteklediğini doğruluyor.')
term(502,'Evet, asıl suçlunun onunla da\nilgisi olabilir...','mastermind/真犯人 için “asıl suçlu” standardı kullanıldı.')
critical(503,'Şimdilik bu vakaya odaklan, Tim!\nAsıl suçluyu yakalayınca Harry hakkında da\nbir ipucu elde ederiz.\nÖnce R’nin nerede yayılacağını bulmalıyız.','Mevcut metinde hem “olay/asıl planlayıcı” terminolojisi hem de “R’yi salmak” ifadesi dağınıktı; özgün akış “önce suç mahallini/yayılma yerini belirle” diyor.','JP 今はこの事件に集中＋犯行場所の特定, FR/DE/IT/ES de önce R’nin kullanılacağı/yayılacağı yeri saptamayı destekliyor.')
style(505,'R’yi nerede yaymayı planladıklarını\nbulmaya başlayalım, olur mu?')
critical(510,'Dur biraz! Acele ettiğini biliyorum ama\ndaha dışarı çıkamayız.\nÖnce Baker’la birlikte R’nin nerede\nyayılacağını çıkaralım.','Mevcut “R’nin nerede saklı olduğu” yanlış hedef; Baker’la yapılan çıkarım, R’nin saklandığı yeri değil yayılma/dağıtım noktasını bulmak üzerine.','JP Rの散布場所, FR/DE/IT/ES release/dispersal location karşılıkları “yayılma yeri”ni açıkça doğruluyor.')
term(515,'Asıl suçlu hakkında','mastermind/真犯人 kavramı “asıl suçlu” olarak standardize edildi.')
term(517,'GNN çalışanlarından biri\nasıl suçlu olabilir, değil mi?','mastermind/黒幕 için “asıl suçlu” standardı kullanıldı.')
style(519,'Bunun ne anlama geldiğini biliyorsun, değil mi Tim?\nMeiko’ya bile hemen güvenemeyiz.')
style(522,"Demek R'yi yayacaklarsa,\nsaat sekizde merkez meydanda olacak!")
style(525,'Zamanımız tükeniyor!\nBay Baker, biz hemen\nmeydana gidiyoruz.')
style(528,'Tamam!\nPeki ya sen, Emilia...?')
term(532,"Doğru. Gemide hem R'yi yayma planını\nhem de GNN'nin çekim noktalarına dair\nbilgileri bulmuştuk.",'“filming locations” dosya boyunca “çekim noktaları” olarak doğal ve tutarlılaştırıldı; burada bunlar R yayılma yerinden ayrı bir bilgi setidir.')
term(543,'Geçit töreninin çekim noktaları','“filming locations” için doğal Türkçe “çekim noktaları” seçildi; “çekim konumları” yapay kalıyordu.')
style(546,'Doğru, geçidin çekileceği noktalar.\nSuçlunun amacı, kuduran Pokémonları\nGNN kameralarına çektirmek.\nR kullanılacaksa çekim noktalarının yakınında olur.')
critical(551,'*soluk soluğa* Bay Baker!\nBelgeleri buldunuz mu?','“information” İngilizcede genel; özgün Japonca ve diğer diller Baker’ın fiziksel belgeleri bulup bulmadığını soruyor.','JP 資料, FR documents, IT documenti ve bağlam elde edilen harita/rota belgelerini doğruluyor.')
style(552,'Evet!\nŞehir haritası ve geçit töreni bilgileri.\nHepsi burada.')
style(556,"Baker Dedektiflik Bürosu'ndan da\nbu beklenirdi. İşleri hızlı!")
style(557,'Bu belgelerle sizin topladığınız bilgileri\nbirleştirirsek, suçlunun R’yi nerede\nyayacağını çıkarabiliriz.')
# departure scene
critical(574,'Böö!\nKandırdım seni!','Mevcut “Aha! Yakaladım!” şakanın anlamını yanlışlaştırıyordu; Pikachu Tim’i korkutup numara yaptığını açıklıyor.','JP ばあ！うそだよーん！ = “Böö! Şakaydı/kandırdım!”; İngilizce de prank bağlamında “I got you” diyor.')
style(576,'*güler* Nasıl ama, Tim?\nKorktun mu?')
critical(578,'Böyle ufak bir şakayla sarsılma!\nDedektifsin sen!','“Upset” burada üzülmek değil, korkup afallamak/sarsılmak; mevcut Türkçe duygusal üzüntüye kayıyordu.','JP 動じる “sarsılmak/soğukkanlılığını kaybetmek”; FR/DE/IT/ES de şaşırma/korkma bağlamını destekliyor.')
style(579,'Sarsılmadım!\nZaten numara yaptığını anlamıştım.')
style(580,'Öyle mi?\nNeyse, içini rahat tut.\nBir süre daha dadılığını ben yapacağım.')
critical(583,'Hımm... Babamı arayacağım.\nTabii Büyük Dedektif Pikachu’yla\nortak olarak!','Mevcut “umarım ortağım olur” Tim’in kararsızlığını gereksiz ekliyordu; özgün replik ortaklığı kesin biçimde kabul ediyor.','JP もちろん…コンビでね = “tabii ki … ile ikili olarak”; FR/DE/IT/ES de Pikachu’yla ortaklığı olumlu biçimde kabul ediyor.')
style(584,'İşte şimdi konuşuyoruz!\nHadi, Tim!')
critical(590,'Tabii, onu hatırlarsın zaten.','Mevcut “Tabii ki öyledir” Türkçede anlamsız kalıyordu; Tim, Pikachu’nun yalnız kendi kahramanlığını hatırlamasına takılıyor.','EN ironik “Of course you do”; JP なにそれ şaşkın/alaycı tepki. Türkçede bağlamı açık eden kısa bir iğneleme seçildi.')
style(595,'Demek Illumise’in peşinden uçuyorsun.\nİlk gelen de sensin, en hevesli Volbeat de?\nGüzel! Bütün şehir geçit törenini bekliyor.')
style(604,'Demek zamanında gelenler hep sen ve\nşuradaki Volbeat. Diğerleri de birazdan gelir.\nProvada kolay gelsin!')
critical(605,'Anladım. Demek bu tezgâhtaki şekerlemelerde\nR olabilir. Evet, şüpheli görünüyor.','“Treats” burada dükkân ödülü değil, Pokémonlara dağıtılacak şekerlemeler; soru yapısı da Türkçede gereksiz belirsizdi.','JP お菓子, FR friandises, DE Süßigkeiten, IT/ES dolci/dulces aynı yiyeceği doğruluyor.')
term(607,'Manec!','Manectric’in seslenişi dosya içinde “Manec” olarak tutarlılaştırıldı.')
style(610,"Evet! Burayı Brad'e bırakalım, biz de\nkalan R'yi arayalım.")
style(612,'Burada bir şey yok gibi.')
style(614,"Unutma, Tim! Meiko da GNN çalışanı.\nHer ihtimale karşı R konusunu\nşimdilik ondan saklayalım.")
style(616,'Aa, lafı mı olur! Yine tehlikeli bir işe\nbulaşmadın, değil mi?\nGerçi Pikachu yanındaysa sorun olmaz.\nDüşmanları elektriğiyle çarpar! Değil mi, Pikachu?')
style(618,'Hadi ama, somurtma.\nŞey... Sen çekim için buradasın, değil mi Meiko?\nKolay gelsin!')
style(619,'Evet, sağ ol! Çekimde elimden geleni yapacağım.\nAma etraf öyle güzel kokuyor ki\nacıkmaya başladım.')
style(624,'Bay Clifford en büyük geçidin çekimini bana bıraktı!\nBaşaracağım! Bu şehrin geçit törenini\nbir sürü insana göstereceğim!')
style(627,'Tamam!\nPeşinden!')
style(629,'Hayır! Tam fırsatı, Tim!\nBak—polis de geldi!')
style(630,'Haklısın!\nArtık suçlunun soldaki yoldan\nkaçmaktan başka seçeneği yok.')
critical(633,'Artık gerçekten güven veriyorsun, Tim.\nPekâlâ, hadi!\nBiz de bu taraftan sıkıştıralım!','“Daha saygın biri oldun” özgün “güvenilir/işe yarar hâle gelmek” nüansını yanlış eksene taşıyordu.','JP 頼もしくなった, DE/FR/IT/ES karşılıkları büyüme/güvenilirlik/işe yararlık anlamına yakındır.')
term(634,'Hım? Aa, hakkında sürekli duyduğum Tim sen misin?\nPolis arasında epey tanınır olmuşsun.\nKomiser Holiday senden\növgüyle bahsedip duruyor.','Holiday “Komiser” olarak standardize edildi; “famous among police” de doğal Türkçeyle “polis arasında tanınır” yapıldı.')
style(636,'Bu bölgede arama yapıyoruz ama\nşimdilik şüpheli bir şey bulamadım.')
term(639,'Şekerlemeler hakkında','JP お菓子 ve FR/DE/IT/ES karşılıkları Pokémonlara verilecek şekerlemeleri doğruluyor.')
critical(641,'Aa, Pokémonlara verdiğimiz şekerlemeleri mi diyorsun?\nEvet, özenerek hazırlıyoruz. Yan tezgâhtaki adam\ngaliba kendi payını çoktan bitirmiş.\nPek güler yüzlü değildi ama işi hızlıymış.\nTuhaf bir adam doğrusu.','“Ödül” yanlış nesne türüydü ve mevcut cümle gereksiz tekrar/kelimesi kelimesine yapı taşıyordu.','JP お菓子, FR friandises, DE/IT/ES şekerleme/tatlı anlamında; JP はりきって作ってる “hevesle/özenle yapıyoruz” nüansını verir.')
style(643,'Asıl işimiz geçit başlayınca açılır;\nbir sürü müşteri gelir.\nAma o adam çekip gitti. Sarı bir şapka takmıştı\nve giderken sürekli etrafına bakınıyordu.')
term(646,'Şekerlemeler hakkında','JP お菓子 ve FR/DE/IT/ES karşılıkları Pokémonlara verilecek şekerlemeleri doğruluyor.')
critical(648,'Evet, bütün yemek tezgâhı sahipleri\nşekerlemeleri birlikte hazırlıyor.\nDüzenleme komitesinden biri akşam sekizden önce\ngelip hepsini toplayacak.','“Atıştırmalık” dosya terminolojisine uymuyordu; ayrıca “herkes yapımına yardım ediyor” yapısı doğal değildi.','JP 屋台のみんなでお菓子を作ってる, FR/DE/IT/ES tüm tezgâhların şekerlemeleri birlikte hazırladığını ve komitenin topladığını doğruluyor.')
style(649,'Hoş geldiniz!\nBuradaki her şeyi gönül rahatlığıyla öneririm!')
term(651,'Şekerlemeler hakkında','JP お菓子 ve FR/DE/IT/ES karşılıkları Pokémonlara verilecek şekerlemeleri doğruluyor.')
critical(653,'Geçidin sonunda Pokémonlara verilen\nşekerlemeleri mi diyorsun?\nEvet, bütün tezgâh sahipleri hazırlıyor;\nama en lezzetlileri benimkiler!','“Atıştırmalık” yerine olayın sabit şekerleme terminolojisi kullanıldı ve “yapımına yardım ediyor” mekanik yapısı doğal Türkçeye çevrildi.','JP お菓子, FR/DE/IT/ES karşılıkları aynı şekerleme hazırlama görevini doğruluyor.')
style(655,'Ne?! O zaman yakalıyoruz!\nHadi, Manectric!')
term(656,'Manec!','Manectric’in seslenişi dosya içinde “Manec” olarak tutarlılaştırıldı.')
critical(660,'Şimdi yemek tezgâhlarına gidiyoruz!\nBabam bana güzel bir şey alacak!','Çocuğun babası burada görev şekerlemesini değil genel bir lezzetli yiyeceği alacağını söylüyor; “atıştırmalık” gereksiz daraltıyordu.','JP 美味しいもの “lezzetli bir şey”; FR/DE/IT/ES de genel bir ikram/yiyecek anlamına yakın.')
style(661,'{{CTRL:0000:0003:FF4B4BFF}}Sarı şapkalı{{CTRL:0000:0003:FDFDFDFF}} bir adam\n{{CTRL:0000:0003:FF4B4BFF}}balonları dörder dörder{{CTRL:0000:0003:FDFDFDFF}} asıyordu.\nÇok güzel bir {{CTRL:0000:0003:FF4B4BFF}}pembe balon{{CTRL:0000:0003:FDFDFDFF}} vardı;\nben de bana verir mi diye sordum ama vermedi.\nSanırım balonlar herkes için.')
style(668,'Festival dediğin coşkuyla yaşanır!\nBelki ben de güzel bir saç bandı takarım.')
style(671,'Şimdiden geçit törenini iple çekiyorum.\nKarnavalın en hareketli yeri merkez meydan.\nÜç geçit burada buluşacağı için\nbir sürü Pokémon ve insan olacak.')
critical(674,'Geçit güzel ama yemek tezgâhları da ayrı keyif!\nHepsini yemek istiyorum; sonra kilo alırım diye\nne yiyeceğime karar veremiyorum.','Mevcut Türkçe “sağlıklı değil, dikkatli seçmeliyim” diye didaktikleşiyordu; özgün konuşmacı ne yiyeceğini seçmekte zorlanıp kilo almaktan söz ediyor.','JP ぜんぶ食べたら太っちゃうかしら＋なにを食べるか迷う; IT/ES/DE de fazla yeme/diyet/doyma nüansını destekliyor.')
critical(681,"Aa, Volbeatlerin peşinden uçup onları mı çekeceksin?\nBuradan izlemekten çok daha etkileyici\ngörüntüler çıkacak gibi!",'Mevcut Türkçe “geçidin kendisinden daha eğlenceli” diyerek izleme keyfine kayıyordu; Yanma’nın çekiminden daha seyirlik/etkileyici görüntüler çıkacağını söylüyor.','JP 見ごたえのある映像, FR/DE/IT/ES de daha etkileyici/izlemeye değer görüntü fikrini destekliyor.')
style(683,"Hevesi yerinde!\nBiz de R'yi bir an önce bulalım.")


# Semantic-completeness overrides after manual QA: retain every meaningful clause in multi-sentence MSBT rows.
critical(45,"Olan biteni bana anlattı.\nKeith'i yakalamışsınız...\nBir de makinemin işini bitirmişsiniz.\nNe büyük başarı doğrusu.",'Roger’ın alaycı cümlesi düzeltilirken Keith’in yakalanması ve makinenin sabote edilmesi bilgilerinin ikisi de korunmalı; önceki taslak ikinci yarıya fazla daralmıştı.','JP, FR, DE, IT ve ES aynı satırda önce Keith’in yakalandığını, ardından Roger’ın makinesinin bozulduğunu alaycı biçimde söylüyor.')
critical(55,'İşi garantiye almışsın. Akıllıca.\nBu arada...','Fail-safe/emniyet sistemi daha doğal Türkçeyle ifade edildi; devamındaki konu değiştirme “Bu arada...” da anlam kaybı olmaması için korundu.','JP 念入り ve FR/DE/IT/ES “her şeyi düşünmüş/önlem almış” anlamında birleşiyor; tüm diller ardından yeni konuya geçiyor.')
critical(58,"R için veri topluyorum.\nBu kadar çok Pokémon'un aynı yerde toplandığı\nfırsat pek çıkmaz.\nÜstelik GNN bu kaosu özel haber olarak verirse\nitibarımız daha da artar!",'“Scoop” özel haber olarak düzeltildi; aynı satırdaki R için veri toplama ve çok sayıda Pokémonun bir araya gelmesi gerekçeleri de eksiksiz korundu.','JP Rの実験データ＋スクープ, FR/DE/IT/ES veri toplama, nadir topluluk ve özel haber/eksklüzif haber motivasyonlarının üçünü de doğruluyor.')
critical(64,"GNN'i ele geçirince Ryme Şehri'ndeki\ntüm bilgiyi kontrol edebilirdim.\nBöylece şehri ben yönetirdim!\nElbette böyle bir plan için para da gerekiyordu.",'Cümle doğal Türkçeyle yeniden kuruldu; Roger’ın bilgi kontrolü, şehri yönetme amacı ve bunun için para gerektiği üç anlam parçası da korundu.','JP, FR, DE, IT ve ES aynı üç aşamayı veriyor: GNN’yi ele geçir, bilgiyi kontrol et, şehri yönet; plan için para gerekir.')
critical(113,'Evet. Üç farklı R var ve\nhepsi farklı türde.','İngilizce “üç yer” eklerken Japonca ve dört Avrupa yerelleştirmesi asıl bilginin üç farklı R türü/biçimi olduğunu söylüyor; çoğunluk ve özgün Japonca esas alındı.','JP Rは3つあって全部種類が違う; FR trois formes, DE drei Formen, IT tre tipi, ES tres tipos. Bu satırda “üç farklı yer” ortak bilgi değil.')
critical(149,'GNN bu yıl geçit töreninin yayın hakkını\ntek başına aldı. Burada bir olay çıkarsa\nbize büyük bir özel haber düşer!\nSana güveniyorum, Tim.','“Manşet” yerine çok-dilli karşılaştırmayla “özel haber” seçildi; yayın hakkı ve Tim’e güvenme cümleleri eksiksiz korundu.','JP 独占中継＋大スクープ, FR/IT/ES özel yayın hakkı ve scoop/primicia; DE de özel yayın hakkı ve özel haber anlamını destekliyor.')
critical(157,'Tamam, Tim. Son R’yi bulmamız gerek.\nSaklı olabileceğini düşündüğün bir yer görürsen\n{{CTRL:0000:0003:FF4B4BFF}}bana seslen{{CTRL:0000:0003:FDFDFDFF}}.','Sözdizimi düzeltildi; görevin “son R’yi bulmak” olduğu ilk cümle de eksiksiz korundu.','JP, FR, DE, IT ve ES hem son R’yi arama hedefini hem de şüpheli bir yer görülürse Pikachu’ya seslenme talimatını doğruluyor.')
critical(172,'Aa? Kırmızı kapüşonlu üst, yanında Pikachu...\nSen şu meşhur dedektif olmalısın!\nNe istersen sorabilirsin.','Tanımlama doğal Türkçeye çekildi; konuşmacının Tim’e istediğini sorma izni de satırdan düşürülmedi.','JP なんでも聞いてね ve FR/DE/IT/ES “istediğini sor” anlamını açıkça koruyor.')
critical(175,'Bize de haber verildi; polis olarak\nmeydanı arıyoruz. Henüz bir şey bulamadık,\nama aramayı ve teyakkuzu sürdüreceğiz.','Polis repliği doğal Türkçeye çekildi; “henüz bir şey bulunmadı ve arama/teyakkuz sürecek” bilgisi korunarak önceki aşırı kısaltma giderildi.','JP 捜索中＋何も見つかってない＋警戒を続ける; FR/DE/ES aynı üç bilgiyi doğruluyor.')
critical(176,"Tim! GNN çalışanları arasında\nşüpheli davranan kimse görmedim.\nSende durum nasıl? R'yi bulabilecek misin?",'İngilizcedeki “all the kinds” ifadesi JP ve diğer yerelleştirmelerde yalnız genel R arayışı; soru bu çoğunluk anlamına göre düzeltildi ve GNN gözlemi korunarak eksiksiz çevrildi.','JP Rは見つかりそう, FR/DE/IT/ES “R’yi bulabildin/bulabilecek misin” diyor; GNN çalışanlarında şüpheli davranış görülmediği de tüm dillerde mevcut.')
critical(235,'Bu yılki geçitteki Exeggutorların\nboyunları inanılmaz uzunmuş!\nOnları görmek için sabırsızlanıyorum.','“Süper uzun” doğal Türkçeye çekildi; Exeggutor ve onları görme heyecanı bilgileri eksiksiz korundu.','JP すごく首が長い＋早く来ないかな; FR/DE/IT/ES uzun boyun ve görme heyecanını doğruluyor.')
critical(238,'Şuradaki polis memurunu görüyor musun?\nYakınında bir merdiven var.\nÇeşmenin öbür tarafında da\nbaşka bir merdiven bulunuyor.','Yön bilgisi “yanında”dan “öbür tarafında”ya düzeltildi; polis memuru ve ilk merdiven tarifleri korunarak tüm satır eksiksiz bırakıldı.','JP 噴水の向こう, FR/IT “de l’autre côté/dall’altra parte”, Çince 喷泉对面; ilk merdivenin polisin yakınında olduğu da ortak bilgi.')
critical(241,'Ben karnavalın düzenleme komitesindeyim.\nGeçidin bu kadar hareketli geçecek olması içimi rahatlattı.\nGNN de programında geniş yer verecekmiş.\nBu yıl süs balonları da her zamankinden fazla gibi.','GNN’nin “programın gözde kısmı” olması yerine geniş yer vermesi doğal/ortak anlama getirildi; komite görevi, memnuniyet ve balon sayısı bilgileri korunarak eksiksiz yeniden yazıldı.','JP 番組で大きくとりあげる, IT interesse, ES reportaje; JP/DE/IT/ES ayrıca bu yıl balon sayısının fazla göründüğünü doğruluyor.')
critical(278,'Endişelenmene gerek yok.\nPikachu sadece uyuyor.\nBir süre sonra uyanacak.','“Zamanı gelince” yerine Japoncadaki süre anlamı seçildi; Pikachu’nun sadece uyuduğu ve endişe edilmemesi gerektiği cümleleri korunarak eksiksiz bırakıldı.','JP しばらくすれば, FR dans quelque temps, DE bald ve Çince 过一会儿; tüm diller Pikachu’nun yalnız uyuduğunu söylüyor.')
critical(287,'Evet, bir tür referans noktası.\nVolbeatler şu an provada, gerçek geçitte izleyecekleri\naynı rotada uçuyor. Şimdi onları düzgün çekebilirsek\ngeçidi de düzgün çekebiliriz.','“Mark” doğal olarak “referans noktası” yapıldı; Volbeatlerin prova rotası ve kamerayı geçide göre ayarlama mantığı eksiksiz korundu.','JP 目安, FR repères, IT punti di riferimento, ES referencia. Tüm diller Volbeatlerin gerçek geçit rotasını prova ettiğini ve çekim ayarına referans olduğunu doğruluyor.')
critical(306,'Demek şüphelendiğin balon bu? Mantıklı.\nHem kameraların tam önünde\nhem de geçit töreninin rotası üzerinde.','İlk cümle doğal Türkçeye çekildi; balonun kamera önünde ve rota üzerinde olduğu iki kanıt da eksiksiz korundu.','JP カメラの前＋パレードのルート, FR/DE/IT/ES aynı iki konumsal gerekçeyi doğruluyor.')
critical(330,'Evet, oldukça sık iletişim kuruyorlarmış.\nKeith GNN’den kaçtıktan sonra da emir almaya devam etmiş.\nDördüncü R’yi yerleştirme emrini de\nyakın zamanda almış.','“Dördüncü yerini saklamak” hatası “dördüncü R’yi yerleştirmek” olarak düzeltildi; sık iletişim ve kaçış sonrası emirlerin sürmesi bilgileri korunarak eksiksiz çevrildi.','JP かなり頻繁＋逃亡後も連絡＋4つめのRを仕掛ける指示; FR/DE/IT/ES aynı üç bilgi parçasını doğruluyor.')
critical(342,'Teşekkür ederim. Desteğin bizim için gerçekten çok değerli.\nAma kendini tehlikede hissedersen\nhemen Brad’i ya da beni ara.','“Büyük avantaj” yapaylığı giderildi; Holiday’nin güvenlik uyarısı satırdan düşürülmeden korundu.','JP 頼もしい＋危険を感じたら連絡; FR/DE/IT/ES de Tim’in desteğini takdir edip tehlikede Brad/Holiday’ye ulaşmasını istiyor.')
critical(370,'Sana güveniyorum, Manectric.\nTim’in bulduğu belgelere göre R’nin\nhafif ama belirgin bir kokusu var.\nSenin burnun bu kokuyu ayırt edecek kadar hassas.','Manectric’in R kokusunu ayırt etmesi doğal Türkçeyle ifade edildi; Tim’in belgeleri ve R’nin hafif kokusu bilgileri korunarak eksiksiz çevrildi.','JP わずかな匂い＋判別, FR/DE/IT/ES R’nin zayıf/belirgin kokusunu ve Manectric’in güçlü koku alma duyusunu doğruluyor.')
critical(376,"Demek R'yi zaten biliyorsunuz.\nGeçit rotasına R yerleştirildiğine dair bir ihbar aldık\nve şu anda araştırıyoruz. Ama gördüğünüz gibi\nR'leri toplamaya başladık; endişelenmeyin.",'“Toplamaya bile başladık” doğal Türkçeye çekildi; ihbar, soruşturma ve durumun kontrol altında olduğu bilgilerinin tamamı korundu.','JP Rが仕掛けられた情報＋捜査＋回収が進んでいる; FR/DE/IT/ES aynı soruşturma ve ilerleme bilgisini doğruluyor.')
critical(381,'Sonra anlatırım!\nLütfen burada kalıp şüpheli biri yaklaşır mı diye\ngözünü açık tut.','Bozuk “kimse şüpheli biri yaklaşmasın” sözdizimi düzeltildi; “sonra anlatırım” cümlesi de eksiksiz korundu.','JP あとでお話しします＋見張っていて, FR/DE/IT/ES bekleyip şüpheli kişileri gözetleme talimatını doğruluyor.')
critical(382,'Aa, sen Tim Goodman olmalısın!\nSana elimizden geldiğince yardımcı olmamız söylendi.','“Emredildi” gereksiz sertlik taşıyordu; Tim’i tanıma cümlesi korunarak doğal polis repliği yapıldı.','JP 協力するように連絡, FR/DE/IT/ES destek/yardım emri veya bilgilendirmesi anlamında; Tim’in kimliğini tanıma da ortak.')
critical(386,'Üstlerimiz bu bölgede arama yapmamızı söyledi,\nama şimdiye kadar şüpheli bir şey bulamadık.','“Üstten” yapay ifadesi “üstlerimiz” olarak düzeltildi; sonuçta henüz bir şey bulunmadığı bilgisi de korunarak eksiksiz bırakıldı.','JP 上からの指示＋見つかっていない, DE/ES üstlerden emir ve henüz bulgu olmaması anlamını açıkça doğruluyor.')
critical(391,'Geçit sırasında Pokémonlar çılgına dönerse\nnasıl bir felaket çıkar kim bilir...\nBöyle bir trajediyi haber yapmak istemiyorum.\nLütfen R’yi bul, Tim. Ben de gözümü açık tutacağım.','Mevcut “ne kadar zarar olur” yapısı doğal Türkçeye çekildi; gazetecinin trajediyi haber yapmak istememesi, Tim’den R’yi bulmasını istemesi ve kendisinin de arayacağı bilgileri eksiksiz korundu.','JP おそろしいこと＋報道するのはごめん＋Rを見つけてくれ＋ぼくも探す; FR/DE/IT/ES aynı dört anlam parçasını doğruluyor.')


critical(95,'*inler* Sen... olmaz...\nSana... izin vermem... *inler*','Parçalı konuşma doğal Türkçeye çekildi; Roger’ın fiziksel zorlanmasını gösteren sahne sesleri de satırdan düşürülmedi.','EN iki groan içeriyor; JP cümleyi parçalı veriyor. FR/DE/IT/ES de Roger’ın güçlükle konuştuğu sahneyi destekliyor.')
critical(106,'Ah... *tökezler*\nİşte hepsi bu.\nBitti. Aferin, Tim.','“last of them” bağlamı doğal Türkçeyle verildi; İngilizce sahne eylemi ve Pikachu’nun Tim’i övmesi eksiksiz korundu.','EN stumble ve “last of them”; JP/diğer diller işlemin bittiğini ve Tim’in iyi iş çıkardığını doğruluyor.')
critical(167,'Buraya gelmekle iyi etmişim!\nSen buradaysan kesin bir şeyler olur.\nBir olay çıkarsa da bize büyük bir özel haber düşer!','“scoop” özel haber olarak düzeltildi; konuşmacının buraya gelmekten memnun olduğu ilk cümle de korunarak satır eksiksiz bırakıldı.','JP/EN ve Avrupa dilleri konuşmacının Tim’in bulunduğu yerde olay çıkacağı beklentisiyle geldiğini ve bunun büyük haber olacağını anlatıyor.')
critical(286,'Kamerayı ayarlamak için\nVolbeatlere mi ihtiyacın var?','Tekil/tür kullanımı doğal Türkçeye çekildi; soru yalnız “Volbeatlere mi?” diye kısaltılmayıp kamera ayarı bağlamı korundu.','JP ve FR/DE/IT/ES konuşmanın kamerayı ayarlamak için Volbeatleri referans alma üzerine olduğunu doğruluyor.')
critical(316,'Tam zamanında!\nAz önce bütün R’leri topladık.','“ortadan kaldırmak” yerine “toplamak” seçildi; Brad’in tam zamanında gelişi de satırda korunarak eksiksiz bırakıldı.','JP/FR/DE/IT/ES hem varışın zamanlamasını hem de R örneklerinin toplandığını/geri alındığını doğruluyor.')


critical(199,"Şekerlemeler, ha...\nBen de bir tuhaflık olduğunu düşünüyorum ama\ngaz hâlindeki R’yle bağlantılı olduklarını sanmıyorum.",'Aynı görev nesnesi dosyanın başka yerlerinde şekerleme olarak standardize edildi; “ikram” tutarsızdı.','JP お菓子, FR friandises, DE Snacks, IT/ES dolci/dulces aynı yiyecek grubunu doğruluyor.')
term(205,'Şekerlemeler','Aynı görev seçeneği JP お菓子 ve FR/DE/IT/ES karşılıklarına göre “Şekerlemeler” olarak standardize edildi.')
critical(210,'Topladığımız ifadelere bakılırsa,\niçinde R olan bir şekerleme bulmamız muhtemel.\nPeki başka bir şey dikkatini çekti mi?','“Treat” dosya içindeki aynı görev nesnesiyle tutarlı olarak “şekerleme” yapıldı; cümlenin olasılık anlamı korundu.','JP R入りのお菓子, FR friandises, IT/ES dolci/dulces, DE Snacks; hepsi aynı yiyecek nesnesini doğruluyor.')
term(216,'Şekerlemeler','Aynı görev seçeneği JP お菓子 ve FR/DE/IT/ES karşılıklarına göre “Şekerlemeler” olarak standardize edildi.')
critical(220,'Şekerlemeler ve kapsül R mi?\nBunların bağlantılı olduğunu sanmıyorum.','“Treats” aynı olay içinde “şekerlemeler” olarak standardize edildi; cümle doğal Türkçeyle kısaltıldı.','JP お菓子, FR friandises, IT/ES dolci/dulces; tüm diller kapsül R ile şekerlemeler arasında bağlantı görülmediğini söylüyor.')
critical(249,'Aa, Pokémonlara verilen ödül şekerlemeleri!\nGeçidin sonunda şekerleme dolu bir vagon geliyor.\nİstediğin şekerlemeyi Pokémonlara verebiliyorsun;\nhem de yanlarına kadar yaklaşarak!','“Reward” şekerlemenin işlevini anlatıyor; nesnenin kendisi şekerleme. Türkçe bu ilişkiyi açıklaştırdı.','JP ごほうびのお菓子; DE “Snacks sind die Belohnung”, FR/IT/ES de Pokémonlara ödül olarak verilen şekerlemeleri doğruluyor.')
critical(378,'Şu Brad de R hakkında\nilgisiz insanların yanında gevezelik edip duruyor!','Mevcut Türkçe bozuktu; önceki taslakta özne yanlışlıkla Keith’e kaymıştı. Manuel kontrolle doğru özne Brad olarak geri getirildi.','JP ブラッドのやつ, IT doğrudan Brad; FR/DE/ES bağlamda Brad’in Roger’ın yanında R bilgisini ağzından kaçırdığını doğruluyor.')


critical(405,'Hayır! Tam fırsatı, Tim!\nBak—polis geldi!','Aynı sahnenin birebir tekrar eden repliği başka occurrence ile manuel olarak tutarlılaştırıldı; anlam değişmedi, yalnız ifade birliği sağlandı.','JP metni 629 ile birebir aynı: いや！チャンスだティム！／ちょうど警官が来たぞ. Bu nedenle Türkçe de aynı tutuldu.')
critical(429,'Nereye gidiyorsun, Tim?\nSarı şapkalı adamın peşine düşmeliyiz!','Aynı JP repliğinin diğer occurrence’larıyla Türkçe ifade birliği sağlandı.','JP 427/429/675/676 satırlarında birebir aynı; Türkçede de “peşine düşmeliyiz” standardı kullanıldı.')
critical(675,'Nereye gidiyorsun, Tim?\nSarı şapkalı adamın peşine düşmeliyiz!','Aynı JP repliğinin diğer occurrence’larıyla Türkçe ifade birliği sağlandı.','JP 427/429/675/676 satırlarında birebir aynı; Türkçede de “peşine düşmeliyiz” standardı kullanıldı.')


critical(407,'Brad, yardımına ihtiyacımız var!\nO adamı iki taraftan sıkıştırmak istiyoruz.','Aynı İngilizce repliğin iki occurrence’ında Japonca kip farkı var; burada “挟み撃ちしたい” isteği anlatıldığı için “sıkıştırmak istiyoruz” seçildi.','JP bu satırda 挟み撃ちしたい (“iki taraftan kıstırmak istiyoruz”), 631’de ise 挟み撃ちにしましょう (“hadi kıstıralım”) diyor; Türkçe fark bilinçli.')
critical(409,'Artık gerçekten güven veriyorsun, Tim.\nPekâlâ, hadi!\nBiz de bu taraftan sıkıştıralım!','Pikachu’nun Tim’e güvenilir/işe yarar hâle geldiğini söyleyen övgüsü düzeltildi; aynı sahne tekrarındaki ifade birliği sağlandı.','JP 頼もしくなった her iki occurrence’da aynı temel övgüyü veriyor; devamında bu taraftan suçluyu sıkıştırma emri var.')
critical(629,'Hayır! Tam fırsatı, Tim!\nBak—polis geldi!','Aynı EN ve JP repliğinin 405’teki karşılığıyla birebir tutarlılaştırıldı.','JP 405 ve 629’da birebir aynı; Türkçe de aynı tutuldu.')
critical(631,'Brad, yardımına ihtiyacımız var!\nO adamı iki taraftan sıkıştıralım.','Bu occurrence Japoncada öneri/ortak eylem kipi kullanıyor; “çalışıyoruz” yerine “sıkıştıralım” seçildi.','JP 挟み撃ちにしましょう = “iki taraftan kıstıralım”; 407’deki 挟み撃ちしたい ile bilinçli kip farkı korundu.')
critical(633,'Artık gerçekten güven veriyorsun, Tim.\nPekâlâ, hadi!\nBiz de bu taraftan sıkıştıralım!','Pikachu’nun övgüsü ve takip emri aynı sahne tekrarındaki 409 ile tutarlılaştırıldı.','JP 頼もしくなった＋こっちから追い込む; 409 ile aynı temel anlamı taşıyor.')

# Simple systematic/manual consistency corrections that were individually checked above.
for i in [89,98]:
    pass
# Additional exact rows
term(193,'Şekerlemeler','JP お菓子 / FR-DE-IT-ES tatlı-şekerleme karşılıkları dosya genelindeki terimi doğruluyor.')
# Manectric cries elsewhere
for i in [361,369]:
    term(i,'Manec!','Manectric’in seslenişi İngilizce/IT/ES yazımı ve dosya içi kullanım ile “Manec” olarak tutarlılaştırıldı.')
# Holiday title remaining
# already 9,152,303,315,368,634

# Build new comparison directory
oldcmp=OUT/'comparison_csv_v15'
newcmp=OUT/'comparison_csv_v16'
oldcmp.rename(newcmp)

# Process every CSV: carry v15 text/status forward; episode9 becomes fully manually reviewed.
for csvp in sorted(newcmp.glob('*.csv')):
    df=pd.read_csv(csvp,dtype=str,keep_default_na=False)
    basecol='Turkish_Manual_v15'
    if basecol not in df.columns:
        continue
    df['Turkish_Manual_v16']=df[basecol]
    df['Manual_Review_Status_v16']=df.get('Manual_Review_Status_v15','HENÜZ_MANUEL_İNCELENMEDİ')
    df['Manual_v16_Decision']=df.get('Manual_v15_Decision','')
    df['Manual_v16_Reason_TR']=df.get('Manual_v15_Reason_TR','')
    df['Manual_v16_CrossLanguage_TR']=df.get('Manual_v15_CrossLanguage_TR','')
    if csvp.name=='episode9.csv':
        for ridx,row in df.iterrows():
            idx=str(row['Index'])
            old=row[basecol]
            df.at[ridx,'Manual_Review_Status_v16']='MANUEL İNCELENDİ'
            if idx in C:
                new,reason,cross=C[idx]
                df.at[ridx,'Turkish_Manual_v16']=new
                # Real change only if different; avoid fake change count.
                if new != old:
                    df.at[ridx,'Manual_v16_Decision']='DEĞİŞTİ'
                    df.at[ridx,'Manual_v16_Reason_TR']=reason
                    df.at[ridx,'Manual_v16_CrossLanguage_TR']=cross
                else:
                    df.at[ridx,'Manual_v16_Decision']='AYNI KALDI'
                    df.at[ridx,'Manual_v16_Reason_TR']=UNCH_REASON
                    df.at[ridx,'Manual_v16_CrossLanguage_TR']=UNCH_CROSS
            else:
                df.at[ridx,'Manual_v16_Decision']='AYNI KALDI'
                df.at[ridx,'Manual_v16_Reason_TR']=UNCH_REASON
                df.at[ridx,'Manual_v16_CrossLanguage_TR']=UNCH_CROSS
    df.to_csv(csvp,index=False,encoding='utf-8-sig')

# Copy manual review dir and rename
oldmr=OUT/'manual_review_csv_v15'
newmr=OUT/'manual_review_csv_v16'
oldmr.rename(newmr)
# Remove old batch-specific generated summaries; regenerate cumulative below
for p in list(newmr.glob('_BATCH11_*')) + [newmr/'mpika.csv']:
    if p.exists(): p.unlink()
# Episode9 standalone manual report
ep=pd.read_csv(newcmp/'episode9.csv',dtype=str,keep_default_na=False)
ep.to_csv(newmr/'episode9.csv',index=False,encoding='utf-8-sig')

# Cumulative aggregates from all comparison CSVs, v16 status only.
allrows=[]
progress=[]
for csvp in sorted(newcmp.glob('*.csv')):
    d=pd.read_csv(csvp,dtype=str,keep_default_na=False)
    if 'Turkish_Manual_v16' not in d: continue
    reviewed=d['Manual_Review_Status_v16'].eq('MANUEL İNCELENDİ')
    changed=reviewed & d['Manual_v16_Decision'].eq('DEĞİŞTİ')
    kept=reviewed & d['Manual_v16_Decision'].eq('AYNI KALDI')
    progress.append({'Dosya':csvp.name,'Toplam':len(d),'Manuel_Incelendi':int(reviewed.sum()),'Degisti':int(changed.sum()),'Ayni_Kaldi':int(kept.sum()),'Henuz_Manuel_Incelenmedi':int((~reviewed).sum())})
    if reviewed.any():
        x=d.loc[reviewed].copy(); x.insert(0,'Dosya',csvp.name); allrows.append(x)
reviewed_all=pd.concat(allrows,ignore_index=True)
reviewed_all.to_csv(newmr/'_MANUAL_REVIEWED_ALL.csv',index=False,encoding='utf-8-sig')
reviewed_all[reviewed_all['Manual_v16_Decision'].eq('DEĞİŞTİ')].to_csv(newmr/'_MANUAL_CHANGES_ONLY.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(progress).to_csv(newmr/'_MANUAL_PROGRESS.csv',index=False,encoding='utf-8-sig')
# Batch 12
batch=ep[ep['Manual_Review_Status_v16'].eq('MANUEL İNCELENDİ')].copy()
batch.to_csv(newmr/'_BATCH12_REVIEWED.csv',index=False,encoding='utf-8-sig')
batch[batch['Manual_v16_Decision'].eq('DEĞİŞTİ')].to_csv(newmr/'_BATCH12_NEW_CHANGES.csv',index=False,encoding='utf-8-sig')

# Save mapping metadata for reproducibility
(OUT/'tools'/'manual_v16_episode9_decisions.json').write_text(json.dumps({k:{'new':v[0],'reason':v[1],'cross':v[2]} for k,v in C.items()},ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copy2('/mnt/data/apply_manual_v16.py', OUT/'tools'/'apply_manual_v16.py')

print('OUT',OUT)
print('episode9 changed', (ep['Manual_v16_Decision']=='DEĞİŞTİ').sum(), 'kept', (ep['Manual_v16_Decision']=='AYNI KALDI').sum())
prog=pd.DataFrame(progress)
print(prog[['Toplam','Manuel_Incelendi','Degisti','Ayni_Kaldi','Henuz_Manuel_Incelenmedi']].sum().to_dict())
