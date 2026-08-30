from pathlib import Path
import csv, shutil, re, json, subprocess, sys, zipfile

SRC=Path('/mnt/data/detective_pikachu_translation_toolkit_v17_manual_batch13')
OUT=Path('/mnt/data/detective_pikachu_translation_toolkit_v18_manual_batch14')
if OUT.exists(): shutil.rmtree(OUT)
shutil.copytree(SRC, OUT)

# Rename versioned directories.
(OUT/'comparison_csv_v17').rename(OUT/'comparison_csv_v18')
(OUT/'manual_review_csv_v17').rename(OUT/'manual_review_csv_v18')
(OUT/'patch_v17').rename(OUT/'patch_v18')
if (OUT/'qa_v17').exists(): (OUT/'qa_v17').rename(OUT/'qa_v18_old')
if (OUT/'qa_manual_v17').exists(): (OUT/'qa_manual_v17').rename(OUT/'qa_manual_v18_old')

cmpdir=OUT/'comparison_csv_v18'
mrdir=OUT/'manual_review_csv_v18'
for p in list(mrdir.glob('_BATCH13_*'))+[mrdir/'episode2.csv']:
    if p.exists(): p.unlink()

# Manual decisions. No translation is generated algorithmically: helpers only write manually chosen text.
C={}
def put(i,text,kind='style',reason=None,cross=None):
    if reason is None:
        reason={
            'style':'Mevcut Türkçe temel anlamı taşıyordu ancak sözdizimi, hitap, sahne akışı veya konuşma doğallığı zayıftı; satır tüm diller tek tek okunarak doğal Türkçeyle yeniden kuruldu.',
            'term':'Mevcut Türkçedeki terim sahne nesnesine veya önceki manuel terminolojiye uymuyordu; çok-dilli karşılaştırmayla tutarlılaştırıldı.',
            'critical':'Mevcut Türkçede anlamı, özne/nesne ilişkisini, ölçüyü veya oyun mantığını etkileyen bir hata vardı; satır çok-dilli karşılaştırmayla düzeltildi.',
            'sound':'Teknik “Pokémon cry / 鳴き声” etiketi Türkçede gerçek çığlık gibi genellenmişti; sahne zorunlu kılmadığı için nötr “Pokémon sesi” kullanıldı.'
        }[kind]
    if cross is None:
        cross={
            'style':'JP özgün metin ile FR/DE/IT/ES ve iki Çince yerelleştirme aynı temel anlamı destekliyor; değişiklik bilgi eklemeden Türkçe akış ve karakter sesi için yapıldı.',
            'term':'JP terimi ve FR/DE/IT/ES/ZH karşılıkları aynı nesne/kavramı doğruluyor; Türkçe dosya içi terminolojiyle eşitlendi.',
            'critical':'JP özgün metin ve resmî yerelleştirmelerin ortak anlamı yeni Türkçeyi destekliyor; İngilizce tek başına yanıltıcıysa özgün/çoğunluk anlamı esas alındı.',
            'sound':'JP 鳴き声 nötr vokalizasyon etiketi; EN “Pokémon cry” da teknik etiket. Replik gerçek bir çığlık gerektirmiyor.'
        }[kind]
    C[str(i)]={'text':text,'kind':kind,'reason':reason,'cross':cross}

def repl(i,*pairs,kind='style',reason=None,cross=None):
    rows_cache = episode7_rows
    old=rows_cache[str(i)]['Turkish_Manual_v17']
    new=old
    if len(pairs)==2 and all(isinstance(x,str) for x in pairs):
        pairs=(pairs,)
    for a,b in pairs:
        if a not in new:
            raise ValueError(f'row {i}: replacement source not found: {a!r} in {new!r}')
        new=new.replace(a,b)
    put(i,new,kind,reason,cross)

def sound(i, extra=None):
    old=episode7_rows[str(i)]['Turkish_Manual_v17']
    new=old.replace('Pokémon çığlığı','Pokémon sesi')
    if extra:
        for a,b in extra:
            if a not in new: raise ValueError((i,a,new))
            new=new.replace(a,b)
    put(i,new,'sound')

# Load episode7 by Index.
ep_path=cmpdir/'episode7.csv'
with ep_path.open(encoding='utf-8-sig',newline='') as f:
    ep_rows=list(csv.DictReader(f)); ep_fields=list(ep_rows[0].keys())
episode7_rows={r['Index']:r for r in ep_rows}
assert len(ep_rows)==1003 and len(episode7_rows)==1003

# --- Simon / PCL / early factory information ---
put(4,'Çok teşekkür ederim! Ama emin misin?\nBana yardım ettiğini buradakiler öğrenirse—','critical',
    '“Beni yardım ettiğini” gramer olarak bozuktu; ayrıca Simon yardımın ortaya çıkmasının tehlikesini anlatıyor.',
    'JP ぼくに協力してること, IT/ES “bana yardım ettiğini öğrenirlerse” anlamını açıkça doğruluyor.')
put(8,'Önce bir bakalım.\nBunun son sevkiyat olduğunu söylemiştin, değil mi?\nPeki nereye gönderiliyor?')
put(9,'Onu ben de bilmiyorum. Ama gideceği yeri\nbulmak için iyi bir fikrim var.\nHazırlığı ben yaparım; bana bırak.')
put(14,"PCL'ye ilk girdiğimde müdürdü.\nZamanla araştırmalarında ona yardım etmeme izin verdi.\nPCL'deki patlamada benim de payım vardı...\nAma profesör bütün sorumluluğu üstlenip ayrıldı.")
put(16,'Ben de onunla gitmek istedim ama kabul etmedi.','critical',
    '“Takip etmek” fiziksel takip çağrışımı yapıyordu; Simon, Waals ayrılırken onunla birlikte gitmek/işten ayrılmak istediğini söylüyor.',
    'JP 付いていこう, FR suivre, DE/IT/ES birlikte ayrılma/gitme anlamını destekliyor.')
put(20,"Doğru. Bir hata oldu.\nMew sonuçta çok nadir bir Pokémon...\nDr. Waals hücrelerini bulmak için elinden geleni yaptı\nama biri ona sahte hücreler vermiş olmalı.\nNe yazık ki herkes dürüst değil.",'critical')
put(25,"Bunu açıklamak için önce Mewtwo'dan söz etmeliyim.\nMewtwo'nun, Mew'un genleri değiştirilerek\nyaratıldığı söylenir.",'term',
    '“Yeniden birleştirmek” yalnız EN recombining yorumuna fazla bağlıydı; özgün Japonca genlerin değiştirilmesini vurguluyor.',
    'JP 改造 = değiştirmek/modifiye etmek; IT “modificando il DNA”, ES/FR/DE genetik yeniden düzenleme anlamında.')
put(27,'Saldırı yeteneğini en üst düzeye çıkarmak için.\nAmaç, son derece güçlü bir Pokémon yaratmakmış.','critical',
    '“Aşırı saldırganlaştırmak” davranışsal saldırganlık gibi okunuyordu; özgün metin saldırı/savaş kapasitesine odaklanıyor.',
    'JP 攻撃に特化, FR potentiel offensif, DE Kampf, IT attacco, ES combate.')
put(30,'Böyle değiştirilmiş gene “Yıkım Geni” deniyor, öyle mi?','style')
put(32,'Bu fotoğraftaki kişi babam. Onu gördün mü?\nYaklaşık iki ay önce buraya sızmış olmalı.','critical')
put(34,'O kesin babamdı!','style')
put(42,"Wallace'ın laboratuvarındaki kaplara benziyor.",'term',
    'Laboratuvar nesnesi için “konteyner” yanlış bağlam çağrışımı yapıyordu; burada deney kabı/tankı kastediliyor.',
    'JP 容器, FR bocaux, DE Behälter, IT contenitori di vetro, ES tanques = laboratuvar kabı/tankı.')
put(50, "Babam bir dedektif. Pokémonlarla ilgili olayları\naraştırıyordu ama şimdi kayıp.\nGeride bıraktığı belgelerin peşinden gidince\nR'nin varlığını öğrendik.", 'critical')
put(51,'Anladım. Sen de oldukça yetenekli bir dedektif gibisin.\nBu vakayı çözersen bana da büyük iyilik etmiş olursun.\nYaklaşık altı ay önce uzun boylu bir adam beni buraya getirdi;\no zamandan beri bana zorla R ürettiriyor.','critical')
for i in [54]: sound(i)
put(59,'Eyvah! Fabrika müdürü geliyor!','critical',
    'Mevcut “Hayır! Müdür!” hareket bilgisini düşürüyordu.',
    'JP/EN müdürün geldiğini/yaklaştığını açıkça söylüyor.')
put(62,'Hey, Doktor! İşler yolunda mı?\nSöz verdiğimiz vakit yaklaştı.','term',
    '“Söz verilen zaman” mekanikti; teslim/kararlaştırılan vaktin yaklaştığı doğal Türkçeyle verildi.',
    'JP 約束の時間 = kararlaştırılan/söz verilen vakit.')
put(66,'Rahatsız ettim, Doktor. İşine dön.','critical',
    '“Seni işine döndüreyim” özne-eylem ilişkisini bozuyordu.',
    'JP 邪魔したな = “rahatsız ettim”; devamında çalışmaya dönmesi söyleniyor.')
put(74,'Kimyasal depo hakkında','term', reason='Aynı Japonca 药品倉庫 / Chemikaliendepot terimi dosya içinde tutarlılaştırıldı.', cross='JP 薬品倉庫; DE Chemikaliendepot; IT deposito di sostanze chimiche; ZH 药品仓库: kimyasal depo.')
put(75,'Waals’tan da duymuştuk ama ne kadar ironik...\nHer derde deva bir ilaç yapmak isterken\nsonunda o korkunç maddeyi ortaya çıkarmışlar.','term',
    '“Mükemmel ilaç” JP 万能薬 kavramını zayıflatıyordu.',
    'JP 万能薬 = her derde deva/çok amaçlı ilaç; diğer diller de panacea/cure-all yönünde.')
put(79,'Aynen, kimyasal depo!\nHarry R’yi oradan almış.','term')
put(85,'Bu, rıhtımdan taşındığını söyledikleri büyük makine mi?','term',
    'Liman içindeki 埠頭 için “rıhtım” seçilerek liman terminolojisi standardize edildi.',
    'JP 埠頭, FR quai, DE Kai, IT molo, ES muelle = rıhtım/iskele; dosya genelinde rıhtım kullanıldı.')
put(91,'Kimyasal depo hakkında','term')
put(93,'Simon özgür kalacaksa sen burada kalmayı göze alıyorsun, öyle mi?','critical')
put(94,'Ne kadar fedakâr bir Pokémon...','style')

# --- office / Accelgor / photo investigation ---
put(100,'Oraya gidersek sağ salim dönebilecek miyiz, diyorsun?\nEvet, sıkı gözetleniyor ama bir yolunu buluruz.','critical')
put(101,'Madalyonun kamera çıkacağını kim tahmin ederdi?!\nİşte ondan tab ettirdiğimiz fotoğraflar!','critical',
    '“Geliştirdiğimiz fotoğraflar” İngilizce develop sözcüğünü yanlış anlamda aktarıyordu; fotoğraf filmi/tab etme kastediliyor.',
    'JP 現像した写真, FR/DE/IT/ES fotoğrafların banyo/tab edilmesini doğruluyor.')
put(102,'Harry vakanın özünü neredeyse çözmüş.','style')
for i in [114,116,120]: sound(i)
put(117,'Tim, bu Pokémon eskiden epey utangaç değil miydi?\nUmarım sorun olmaz.','critical',
    'Accelgor bir Pokémon olduğu hâlde “bu adam” denmişti.',
    'JP/EN/diğer diller öznenin Accelgor olduğunu açıkça gösteriyor.')
put(126,'Seni sevmiş gibi, Tim. Bana alışması tam bir ay sürmüştü.','critical')
put(130,"Dünyanın dört bir yanından insanlar ve mallar\nRyme Şehri'ne geliyor.",'critical',
    'Mevcut Türkçe EN serbest yorumunu dar aktarıyordu; özgün metin hem insan hem mal akışını anlatıyor.',
    'JP 人やモノ; FR/DE/IT/ES insanlar ve mallar/ürünler/fracht anlamında birleşiyor.')
put(132,'Demek madalyonda gizli bir kamera varmış.\nTam Harry’lik iş!','style')
put(136,'İkinize de iyice alışmış gibi.','style')
put(138,'Eminim size çok yardımcı olur. Çok zeki bir Pokémon.','style')
put(141,'Demek bunca depo bu yüzden var.','style')
put(144,'Baker işleri bayağı iyi götürüyor anlaşılan.','style')
put(148,"Baker'ın çapraz karşısında mı? Pek rahat bir yer sayılmaz...",'critical')
put(155,'Arabayla yaklaşık 15 dakika sürer.','style')
put(167,"Pat diye ortadan kaybolmasana! Biz bir ekibiz, değil mi?\nŞimdi Harry'nin fotoğraflarına bakalım.",'style')
put(174,'Deponun içinin fotoğrafı.','style')
put(176,'Ampuller ve kutunun fotoğrafı.','term',
    'R taşıma kapları daha önce manuel olarak “ampul” şeklinde standardize edildi.',
    'JP/DE Ampulle, FR/IT/ES fiole/fiala/vial aynı küçük ilaç ampulünü doğruluyor.')

# --- port / cargo terminology ---
for i in [184,213,214,215,245,337,370,390,408,430]:
    put(i,'Yükler hakkında','term',
        'JP 荷物 ve FR/DE/IT/ES karşılıkları genel yük/mal anlamında; burada fiziksel konteyner türü değil limandaki yük kategorisi soruluyor.',
        'JP 荷物, FR marchandise, DE Fracht/Frachtgüter, IT merci, ES mercancía = yük/mal.')
put(194,'Hepsini dolaşmaya kalksak akşam olur...','style')
put(195,'Dediğim gibi, bir depo aradığını biliyorum ama\nbu fotoğraf tek başına yetmez.','critical')
put(202,'Fotoğraftaki adamın taşıdığı yük mü?\nHiçbir şey çağrıştırmadı...','term')
put(203,'Buradaki yükler hakkında genel olarak bildiğin bir şey varsa\nbize anlatır mısın?','term')
put(206,'Ne mi yapıyorum? Yük hazır olsun da gemiye haber vereyim\ndiye bekliyorum. Konteyner gemisiyle rıhtım ekibi arasındaki\niletişimden ben sorumluyum.','critical',
    'Mevcut metin “bildirimin gelmesini bekliyorum” diyerek iletişim yönünü tersine çeviriyordu.',
    'JP 積み荷の準備ができたら船のスタッフに伝える = yük hazır olunca gemi personeline haber vermek.')
put(207,'Haber vermek derken nasıl?\nBağırıyor musun, yoksa bir sinyal sistemi mi var?','style')
put(218, 'Burası çok büyük; her bölgede farklı yükler var.\nSanırım A ve B bölgelerinde çoğunlukla\nmakine ve ekipman depolanıyor.', 'critical')
put(227,'Keith buraya ne getirdi acaba?\nKesin R’yle ilgilidir...','critical',
    '“Keith dünyada ne getirmiş olabilir?” İngilizce “what in the world” deyimini kelimesi kelimesine taşıyordu.',
    'JP ve diğer diller yalnız Keith’in ne taşıdığını merak ediyor; “dünyada” anlamı yok.')
put(228,'Fotoğraftaki adamın taşıdığı yük hakkında\ndaha fazlasını mı bilmek istiyorsun?\nOnu yalnız bir kez gördüm, pek bir şey diyemem...','term')
put(229, 'Bu rıhtımda taşınan yükler hakkında\ngenel bir bilgi bile işimize yarar.', 'term')
put(230,'O konuda biraz bilgim var! Renklerine göre ayrılıyorlar.\nMavi konteynerlerde... şey... unuttum.\nGemidekilere sorayım. Hey, Pelipper!','critical')
put(234,'Pelipper dönene kadar biraz daha bekle.','style')
# 237 current terminology is correct actual colored containers; only machinery wording.
repl(237,'yeşiller ise makine için.','yeşiller ise makine ve ekipman için.',kind='term')
put(246, 'Hangi depo olduğunu mu bulmaya çalışıyorsun?\nBu fotoğraf tek başına yetmez...\nEn azından orada ne tür yüklerin\ndepolandığını bilsek işe yarardı.', 'term')
put(248,'Sadece fotoğrafa bakarak pek bilgi toplayamayacağız.','style')
put(249, 'Her bölgede farklı yükler var.\nSanırım A ve C bölgelerinde gıda depolanıyor.', 'critical')
put(253,'Buraya sık sık yük almak için uğruyor.','term')
put(258,'Fotoğraftaki adamın ne tür yüklerle uğraştığını mı soruyorsun?\nHep mavi konteyner kullanır. İçlerinde ne var, bilmiyorum.','term')
put(260, 'Lafı bile olmaz! Aslında Machamplar\nbenden daha çok şey biliyor olabilir.\nSon geldiğinde adama uzun uzun bakmışlardı.\nHerhâlde kaslarına hayran kaldılar.', 'style')
put(263,"Accelgor'un getirdiği fotoğrafları iyice incelemeliyiz.\nBana {{CTRL:0000:0003:FF4B4BFF}}Keith'le{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}sarışın adamın birlikte olduğu fotoğrafı{{CTRL:0000:0003:FDFDFDFF}} gösterebilir misin?",'critical',
    'Mevcut kontrol-kodlu ifade “Keith’in fotoğrafını ve sarışın adamı göster” diye iki farklı nesne gibi bozulmuştu.',
    'JP/FR/DE/IT/ES tek bir fotoğrafta Keith ile sarışın adamın birlikte görüldüğünü doğruluyor.')
put(264,'Şunlar hakkında ifade toplayalım:\n{{CTRL:0000:0003:FF4B4BFF}}depo{{CTRL:0000:0003:FDFDFDFF}} ve {{CTRL:0000:0003:FF4B4BFF}}fotoğraftaki kişiler{{CTRL:0000:0003:FDFDFDFF}}.','critical')
put(265,'{{CTRL:0000:0003:FF4B4BFF}}Depo bölgesi{{CTRL:0000:0003:FDFDFDFF}} ve\n{{CTRL:0000:0003:FF4B4BFF}}yükler{{CTRL:0000:0003:FDFDFDFF}} hakkında soru soralım.','term')
put(266,"Adamın taşıdığı yükler hakkında epey ifade topladık.\n{{CTRL:0000:0003:FF4B4BFF}}Vaka Notları{{CTRL:0000:0003:FDFDFDFF}}'nı açıp hepsini bir araya getirelim.",'term')
put(268,"Machamp'la çalışan adama\n{{CTRL:0000:0003:FF4B4BFF}}yükler{{CTRL:0000:0003:FDFDFDFF}} hakkında sormadık galiba.",'term')
put(275,'Acaba bunlar o adamın yükleri mi?','term')
put(283,'Bu fotoğraf babamın kazasından 10 saat önce çekilmiş!','critical')
put(284,"Burası onların üssünün içi mi? Ne olmuş burada?\nAcaba bu fotoğraftan sonra Keith'e yakalandı mı...?",'critical')
put(290,'Yükler konveyör bandıyla depoya taşınıyor.','term')
put(294,'Konveyöre sığmayan yükleri Machamp taşıyor galiba.','term')
put(295,'Şu Pokémon’a bak... ter kokusu buraya kadar geliyor sanki.','critical')
put(296,'Bu adamın elinde hiçbir şey yok.','style')
put(301,'Keith’i araştırmak için burada gözetleme yapmış olmalı.','critical')
put(303,'Evet, burada da kendini pek bir şey sanıyor.\nGNN’de el pençe divan duran adam bu.','critical',
    'Mevcut çeviri “ödlek” diyerek karakter niteliğini yanlışlaştırıyordu; görüntüde adamın boyun eğen/itaatkâr tavrı anlatılıyor.',
    'JP/çok-dilli bağlam davranış biçimini anlatıyor; korkaklık etiketi zorunlu değil.')
put(307, 'Buna bakınca, yapmam gereken önemli bir şey\nvarmış gibi hissediyorum.', 'style')
put(308,'Babamla birlikte geldiğin zamana ait bir anı mı?','critical',
    'Tim kendi babasından söz ederken “babanla” denmişti; kişi ilişkisi yanlıştı.',
    'JP 父さん, FR “mon père”, IT “mio padre”, ES “mi padre” = Tim’in babası.')
put(316, 'Bu adam bilim insanı mı? R üzerinde çalışan\ntek kişinin Carlos olduğunu sanıyordum;\ndemek başka araştırmacılar da varmış.', 'critical')
put(324,'Bu yük depodan mı çıktı?','term')
put(327,'Depodaki işçilerden biri mi?\nPokémonlara talimat veriyor gibi.','term')
put(330,'Biraz daha bilgi toplayalım.','style')
put(334, 'Gemi gelmediği için sıkıldın mı?\nBir an önce yük taşımak istiyorsun, ha?', 'critical')
put(339,'Görevin gemiden yük indirmek, ha.\nİyi antrenman oluyor mu?','term')
put(341,'Herkes de bundan memnun, öyle mi?','style')
put(342,'Kendi yüklerinle o kadar meşgulsün ki\nçevrendeki hiçbir şeyi fark etmiyorsun, öyle mi?\nPeki sen ne tür yükler taşıyorsun?','term')
put(344,'Kare biçimli mi? Başka ayırt edici özelliği yok mu?','style')
put(346,'Çok ağır ve antrenman için mükemmel mi?\nBir de benim taşımamı öneriyorsun, ha? Yok, kalsın.\nPeki konteynerlerin rengi ne?','term')
for i in [355,357,362]: sound(i)
put(359,"Accelgor'a dedektifliğin inceliklerini öğretiyordum.",'critical')
put(376,'İşine gerçekten çok bağlı.','style')
put(379,'Senden bazı yüklerini taşımanı mı istedi? Gerçekten mi?!','term')
put(385,'Aa, fazla heyecanlanıp yükü düşürdün, öyle mi?\nİçindekiler her yere saçıldı, etraf berbat koktu\nve adam da seni azarladı...','term')
put(392,'İş dediğin eğlenmek mi?\nHa, yük taşımak senin için eğlence yani.','critical')
put(394,'Demek senin için işten çok hobi. Ne güzel.','style')
put(397,'{{CTRL:0000:0003:FF4B4BFF}}Birlikte çalıştığın Machamplardan biriyle{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}konuşmuş{{CTRL:0000:0003:FDFDFDFF}}, öyle mi? Bilgi için teşekkürler.','style')
# 400 container ship is actual: keep.
put(409,'Halata tırmanıp gemiye sızmaya çalışıyorsun ama\nsonuna yaklaşınca hep geri çevriliyorsun, öyle mi?','critical')
put(411,'Aynı yöntemi tekrar tekrar denersen\nsonunda bir yolunu bulursun.','style')
put(419,'Şey, evet... iyi. Gayret et.\nVazgeçmezsen sonunda başarırsın.','style')
# 420 actual nearby shipping containers; keep term but naturalize.
put(420,'Konteynerlerin etrafını bayağı kokluyorsun.\nİlgini çeken bir şey mi var?','style')
put(422,'Ha? Mavi konteyner çok keskin kokuyor, öyle mi?\nO yüzden diğer konteynerlerden de koku geliyor mu diye\nkontrol ediyorsun. O kadar güzel mi kokuyor?!','style')
put(424,'Kötü değil, sadece çok keskin mi?\nKokladıkça hoşuna gidiyor, öyle mi?','style')
put(426,'Vay be, mavi konteynerler gerçekten çok keskin kokuyor olmalı...','critical')
put(432,'Kuryeymiş. Mektupları gagasında gemiye götürüyormuş.','critical')
put(433,'Ta gemiye kadar mı? Zor işmiş.','style')
put(436,'Yük derken mektupları mı kastediyorsun?\nBilmiyorsan sorun değil. Sağ ol.','critical')
put(437,'Şu Accelgor yok mu... Neyse.\nBuraya neden geldiğimizi biliyorsundur umarım.','style')
put(441,'Depoyu araştırmak','term')
put(445,"Harry'nin fotoğrafındaki deponun yerini bulup\naraştırmamız gerekiyor.",'style')
put(449,"Ne?! O zaman doğru dürüst soruşturma yapamayız.\nHımm... {{CTRL:0000:0003:FF4B4BFF}}biz{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}önce Accelgor'u bulmalıyız{{CTRL:0000:0003:FDFDFDFF}}.",'style')
put(457, 'Keith’le fotoğrafta görünen adam\ngerçekten depoyla bağlantılı gibi.', 'style')
put(458,'Evet. Buraya sık sık yük almaya geldiğini söylediler.','term')
put(459,'Aynen. Hangi yüklerle uğraştığını öğrenirsek\ndeponun yerini daraltabiliriz.','term')
put(461,'Pekâlâ! Şimdi {{CTRL:0000:0003:FF4B4BFF}}bu yükler hakkında{{CTRL:0000:0003:FDFDFDFF}} bilgi toplayalım!','term')
put(483,'Simon {{CTRL:0000:0003:FF4B4BFF}}fabrikanın sağ arka tarafındaki odada{{CTRL:0000:0003:FDFDFDFF}}.\nHadi.','critical')

# --- factory infiltration ---
put(487,'Spinarak’a söz verdiğimiz yiyeceği bulalım.\n{{CTRL:0000:0003:FF4B4BFF}}Masanın yanındaki kutudan{{CTRL:0000:0003:FDFDFDFF}} bir koku geliyor...','term')
put(488,'{{CTRL:0000:0003:FF4B4BFF}}İkinci kattaki{{CTRL:0000:0003:FDFDFDFF}} kimyasal depoya gitmeliyiz.\n{{CTRL:0000:0003:FF4B4BFF}}Spinarak{{CTRL:0000:0003:FDFDFDFF}}’tan yardım isteyelim.','term')
put(490,'Şu kutuları kenara çekip kimyasal depoyu inceleyelim.\n{{CTRL:0000:0003:FF4B4BFF}}Bütün{{CTRL:0000:0003:FDFDFDFF}}\n{{CTRL:0000:0003:FF4B4BFF}}kutuları başlangıçtaki yerlerine döndürmek{{CTRL:0000:0003:FDFDFDFF}} istersen bana söyle.','style')
put(492,'Şimdi {{CTRL:0000:0003:FF4B4BFF}}kimyasal depoyu{{CTRL:0000:0003:FDFDFDFF}} inceleyelim!','term')
put(493,'{{CTRL:0000:0003:FF4B4BFF}}Masanın üstünü{{CTRL:0000:0003:FDFDFDFF}} ve\n{{CTRL:0000:0003:FF4B4BFF}}arka taraftaki rafı{{CTRL:0000:0003:FDFDFDFF}} kontrol et.','style')
put(494,'Kesin kanıtı bulduk. {{CTRL:0000:0003:FF4B4BFF}}Simon{{CTRL:0000:0003:FDFDFDFF}}’a dönelim.','critical')
put(498,'Buradaki incelemeyi şimdilik bitirebiliriz.','style')
put(509,'Oh be... Söz dinlemene sevindim.','style')
put(511,'Arka odadan sürekli kutular geliyor.','term')
put(512,'Kalite kontrol yapıyorlar galiba.\nKusurlu kutuları ayırıp kalanları banda geri koyuyorlar.','critical',
    'Mevcut Türkçe fabrika işlem akışını belirsiz bırakıyordu; sahnede ürün/kutular kontrol edilip ayıklanıyor.',
    'JP ile FR/DE/IT/ES kontrol/ayıklama ve kalanları hatta döndürme akışını destekliyor.')
put(516,'Hoş geldin. Önce sana bu fabrikanın nasıl çalıştığını anlatayım.','style')
put(517,'Evet, lütfen anlatın!','style')
put(518,'Bu depo fabrika mıymış? Her neyse, iyi denk geldik.\n{{CTRL:0000:0003:FF4B4BFF}}Şunları dinleyelim bakalım{{CTRL:0000:0003:FDFDFDFF}}.','style')
put(523,'Ne?! Hiç araştırmadan mı geldin?\nBiz sağlıklı gıda üretiyoruz! Reklamı görmüşsündür:\n“Kokusu beter, sağlığa değer!”','style',
    'Resmî yerelleştirmelerin çoğu fabrika sloganını kafiyeli/yaratıcı yerelleştiriyor; mevcut Türkçe düz ve yapaydı.',
    'JP あふれる臭さで いざ健康！; FR/DE/IT/ES de koku + sağlık üzerine slogan/kelime oyunu kuruyor. Türkçede kafiyeli yaratıcı karşılık seçildi.')
put(524,"Aa, biliyorum! Şu berbat... şey, yani\nMax'le Chatot'un şarkı söylediği reklam...",'critical')
put(526,'Hımm... Bayağı kapsamlı bir kamuflaj.\nDemek o kokan yük “sağlıklı gıda”ymış.\nSağlıklıymış değilmiş umurumda değil;\nbu kadar kötü kokan ve tadı berbat bir şeyi neden üretiyorlar?','term')
put(545,'Müdür sadece ne olursa olsun o odadan uzak durmamızı söyledi.','critical')
put(547,'Boş ver! Bu konuyu fazla açma.\nYoksa beni de işimden edersin.','style')
put(552,'Önce kıdemlilerin nasıl çalıştığını izle. Onlardan öğren.','style')
put(554,'Şşşt! Duyacak. Alışsan iyi olur!','style')
put(564,'Vay! Ne oluyor?! Demek dikkatimi çeken senin ipliğinmiş!','critical')
put(567,"Ne demek 'haklı'? Zaten bütün bunlar senin yüzünden oldu!\nSen nasıl bir Pokémon'sun böyle?",'style')
put(577,'Ah, pardon! Spinarak, daha sakin bir yerde konuşalım.\nÜst kata çıkabilir misin?','critical')
put(579,'Buradan görebildiğimiz her şeyi inceledik.','style')
put(583,'Machamp... Sanırım kasaların kapaklarını kapatıyor.','term')
put(584,'İşi ciddiye almışlar.','style')
put(585,'Dört kolunu da sonuna kadar kullanıyor.','style')
put(586,'Şurada bir işçi var.','critical')
put(587,'Pek hevesli görünmüyor. Buradaki Pokémonlar ondan daha istekli.','critical')
put(597,'Yükleri dışarı sevk etmek için açık tutuyorlar sanırım.','term')
put(600,'Yok, bildirecek bir şey yok.','style')
repl(602,'gırsın','girsin',kind='critical',reason='Açık yazım hatası düzeltildi.',cross='Tüm diller anlamın “bir Rattata bile içeri girmesin” olduğunu doğruluyor.')
put(607,'Aa, sana da oradan uzak durmanı söylediler demek.\nBunu benden duyduğunu kimseye söyleme ama...\norada hücre kültürü yapıyorlarmış.','term',
    '“Kuluçkaya yatırmak” hücre biyolojisi bağlamında yanlış terimdi.',
    'JP 培養, FR culture in vitro, DE/IT/ES kültür/yetiştirme = hücre kültürü.')
put(609, 'Ben de tam bilmiyorum; Keith’le müdür\nkonuşurken tesadüfen duydum.\nBuradaki birinin bunu yapabilen tek kişi\nolduğunu söylediler... Kimseye söyleme, tamam mı?', 'style')
put(612,'Hücre kültürü dediler, değil mi?','term')
put(613,'Hücre kültürü, hücreleri çoğaltmak demek, değil mi?\nR’yle bağlantılı böyle bir şey varsa... yoksa...','term')
put(614,'Ben de aynı şeyi düşünüyorum. Mewtwo’nun hücreleri olmalı.\nHücre kültürünü yapan kişi arka odada.\nOh! {{CTRL:0000:0003:FF4B4BFF}}Hâlâ konuşuyorlar{{CTRL:0000:0003:FDFDFDFF}}!','term')
put(619,'Evet, gerçekten içimi ısıtıyor.\nBelki ona yine biraz şekerleme veririm.','term',cross='JP お菓子, FR/DE/IT/ES tatlı/atıştırmalık karşılıklarını doğruluyor; “ödül maması” nesneyi gereksiz Pokémon yemine çeviriyordu.')
put(621,'Şekerlemelerden bahsettiler... Belki bir çocuk?','term')
put(626,'Metanglar yükleri dışarı taşıyor.','term')
put(632,'Son çare de olsa olmaz. Sessiz sedasız ilerlemeliyiz.','critical',
    'İngilizcedeki “resort” kelime oyunu Türkçede anlamsız “tatil yeri”ne dönüşmüştü; özgün Japonca “son çare bile olmaz, sessiz ilerleyelim” diyor.',
    'JP 最後でもダメだよ／おんびんに進めよう; özgün metin açıkça sessiz ilerleme ve “son çare” anlamını veriyor.')
for i in [640,642,655,658,662,665]: sound(i)
put(673,'Şu yiyeceği çabuk getir mi diyorsun?\nKusura bakma; bulacağız. Biraz daha sabret.','term')
put(676,'Ha? Ödül olarak söz verdiğimiz yiyecek nerede mi?','term')
put(682,'Lezzetli yiyecek hakkında','term')
put(685,'Sürekli bahsettiğin bu lezzetli yiyecek tam olarak ne?','term')
put(696,'Bedava olmaz mı? Karşılığında yiyecek mi istiyorsun?\nTam fırsatçısın...','term')
put(697,'Spin!','critical',
    'Mevcut “Döön!” uydurma/yanlış bir seslenişti; Spinarak’ın kısa Pokémon sesi doğal biçimde verildi.',
    'JP/EN bu satırın Spinarak vokalizasyonu olduğunu gösteriyor.')
put(710,'Aynen böyle! Devam et!','style')
put(720,'Başka çaremiz yok, Tim. Şu kasaları yolumuzdan çekelim.\nDepoya giden bir yol açmamız gerek; taşırken iyi düşün.','term')
put(722,'Ben de göremedim. Ama ilginç bilgiler topladık.','critical')
put(725,'Tamam. Dikkat edeceğim.','style')
put(732,'Aynen. Alt kat sıkı gözetim altında.\nAma şöyle düşün: fabrika müdürüyle iki güvenlik görevlisini\natlatmamız yeter.','critical')
put(745,"Accelgor'un hızı çok işimize yarar.\nBir şekilde birinci kata inelim!",'style')
put(750,'Evet...\nEyvah! Tim, kapıyı hemen kapat!','critical')
put(753,'Dur bakalım! Sen kimsin?!','style')
put(755,'Kapıyı aç!','critical')
put(757,'Tam anlamıyla kapana kısılmış Pikachu olduk.','style',
    'EN Rattata benzetmesini, JP Pikachu’ya özgü espriyi kullanıyor; Türkçede sahneye ve karaktere uygun yaratıcı karşılık seçildi.',
    'JP 袋のピカチュウ Pikachu üzerinden kelime oyunu yapıyor; Batı dilleri de “kapana kısılma” esprisini yerelleştiriyor.')
put(767,'Accelgor! Onu oyala!','critical')
for i in [768,770]: sound(i)
put(775,'Yaşasın! Başardık!','style')
put(780,'Bunun beni durduracağını mı sanıyorsun?! *zorlanır* *zorlanır*','style')
put(782,'Neredesin? Seni yakalayacağım!{{CTRL:0001:0006:}}\n*homurdanır*','style')
put(790,'Aa...','style')
# Actual container at 802; improve physical grunt.
put(802,'Oh, harika!\nBurada bir konteyner var.\n*zorlanır* İkinize de tam yetecek kadar büyük.','style')
put(803,'İçeri girin!','critical')
put(805,'Bugün sevk edilen ürünü örgütten adamlar alacak;\nbu da sizi doğrudan{{CTRL:0001:0006:}}\nüslerine götürür.','critical')
put(813,'Peki... Hadi Pikachu.\nPeki ya siz?','style')
put(811,'Pokémon sesi (Tamamdır!)','term', reason='Genel ses etiketi çığlık olarak değil Pokémon sesi olarak standardize edildi.', cross='JP 鳴き声（承知！） doğrudan Pokémon sesi + Tamamdır anlamında; önceki manuel dosyalarla tutarlı.')
put(816,'Sen buradaki Pokémonlardan mısın? Sana bir şey soracağız.','critical')
put(827,'Ne kadar fedakâr bir Pokémon...\nFotoğraftaki adam onun partneri mi?','style')
put(835,'Buraya geldikten sonra Simon mutsuz görünmeye başlamış, öyle mi?\nSen girip çıkabiliyorsun ama Simon aylardır dışarı çıkamıyor?\nNasıl yani?','critical')
put(837,'İri yarı bir adam onu sürekli gözetliyor?\nFabrika müdürü olmalı.','style')
put(841,'O adamı sevmiyorsun; Simon’u sürekli acele ettiriyor\nve çok korkutucu görünüyor, öyle mi?\nPeki Simon’a ne yaptırmaya çalışıyor?','style')
put(843,'Simon’a bir şey ürettiriyorlar?\n“Hücre” diye bir şeyden mi bahsediyorlar?','style')
put(846,"Bize, Mewtwo'nun hücrelerini çoğaltabilen dünyada\nyalnız iki kişi olduğu söylenmişti:\nDr. Waals ve eski asistanı.\nO hâlde Pansage'nin partneri de—",'term',
    'Hücre “kuluçkası” terimi biyolojik olarak yanlıştı; ayrıca “laboratuvar asistanı” değil Waals’ın eski asistanı bilgisi korunmalı.',
    'JP 培養＋ワールスさんの助手だった人, FR/DE/IT/ES aynı iki kişi bilgisini doğruluyor.')
put(854,'Demek o zamanlar araştırma yaparken mutluymuş...\nMerak etme, Pansage. Bu fabrikanın sırrını çözüp\nsizi özgürlüğünüze kavuşturacağız!','style')
put(859,'Seni görünce gülümsüyorlar ve sana şekerleme veriyorlar, öyle mi?','term')
put(862,'Bu “Dedektif Dergisi”.\nBöyle bir dergi olduğunu bilmiyordum.','critical',
    '“Journal” burada günlük değil dergi adı; Japonca açıkça 雑誌 diyor.',
    'JP 雑誌, FR/DE/IT/ES süreli yayın/dergi bağlamını doğruluyor.')
put(863, 'Düşündüğünden daha yararlı.\nHer sayıda ayrı bir dosya var;\nşüpheli takibinden bomba etkisizleştirmeye\nkadar her şeyi anlatıyor!', 'critical')
put(864,'Bütün kıyafetlerin birbirine benziyor.','style')
put(865,'Bu tarzı seviyorum.','style')
put(875,"Hazır mısın, Tim? Baker'ın bürosuna gidelim.\nMadalyonun analizini bitirmiş olmalılar.",'critical',
    'Mevcut “Baker’ın evine” yanlış mekândı; konuşulan yer dedektiflik bürosu.',
    'JP 探偵事務所 ve sahne akışı Baker’ın bürosunu doğruluyor.')
put(880,'Kusura bakma, seni uyandırdım. Ama aklıma takılan bir şey var...\nSanki birine bir söz vermişim.','style')
put(884, 'Şaşırmaya hazır ol...\nSöz verdiğim kişi Mewtwo’ydu!', 'critical')
put(888,'Yıkım Geni’ni geri getireceğime ve\nR vakalarının arkasındaki asıl suçluyu yakalayacağıma söz verdim!','term')
put(890,'Sanırım Harry’yi kurtarması karşılığında\nbenden bunları yapmamı istedi.','style')
put(891,'Ama böyle önemli bir işi neden sana emanet etsin ki...','style')
put(892,'Ne demek o?! Ben büyük bir dedektifim!\nMewtwo ünümü duymuş, güvenmiştir bana.\nGerçi ayrıntıları hatırlamıyorum ama...','style')
put(893,'Bence şu son kısmı uydurdun...','style')
put(894,"Keith'in planını durdurmalıyız!\nBay Baker'a ve Komiser Holiday'e hemen haber verelim!\nYine de... Babamla ilgili bir ipucu bulamadık.",'term',
    'Holiday rütbesi önceki manuel turlarla “Komiser” olarak standardize edildi; “evidence” burada babaya dair ipucu/iz bağlamında.',
    'JP ホリデイ警部 = Komiser Holiday; diğer diller de polise haber verme ve Harry’ye dair iz bulunamamasını doğruluyor.')
put(900, 'Bu tuhaf. Acaba babamla buraya geldiğin\nzamandan kalan bir anı mı?', 'critical', 'Tim kendi babasından söz ederken “babanla” kişi ilişkisini ters çeviriyordu.', 'JP 父さん; FR/IT/ES “mon/mio/mi padre” = Tim’in babası.')
put(901,'Kutunun içindekileri çıkarıp bakabilir misin?','critical')
put(907,'Vay canına, ne belgeler bulduk!\nKeith R’yi daha da tehlikeli hâle getirmeyi planlıyor.\nAma artık ne çevirdiğini biliyoruz.','style')
put(910,'Evet, planlarının ana hatları burada.\nKeith R’yi ihraç etmeyi planlıyor.','term')
put(911,'Ama R dünyanın dört bir yanında kullanılırsa felaket olur!\nBunu durdurmak imkânsız hâle gelir!','style')
put(915,'Satış kanalları hakkında','term')
put(917,"En büyük sorun R'nin yalnız PCL'nin altındaki makinede\nüretilebilmesi. En kısa sürede yeni bir üretim sahası için\narazi satın alıp istikrarlı bir üretim sistemi kurmalıyız.",'critical')
put(919,'Önce ağzı sıkı, varlıklı müşteriler bulmamız gerekiyor.\nŞu anda yeraltı bağlantılarımı kullanarak zengin çevrelere\nulaşmaya çalışıyorum.','critical',
    '“Varlıklı hamî / üst sınıf vatandaşlar” makine çevirisi gibi ve satış bağlamını bozuyordu.',
    'JP 口の堅い上客＋富裕層ネットワーク = ağzı sıkı varlıklı müşteriler ve zengin çevre ağı; Avrupa dilleri de müşteri/patron ağını destekliyor.')
put(921,'Carlos’un R analizi yakında bitecek.','style')
put(923,'Kutunun arkasında bir belge var.','style')
put(924,'Ne? “Deney Sonuçları ve Gelecek Planları” mı?\nR hakkında bir rapor bu. İyi buldun, Tim!','critical')
put(926,'“Deney Sonuçları ve Gelecek Planları”','critical')
put(928,'Gaz hâlinin özellikleri','term')
put(929,'Sıvı hâlinin özellikleri','term')
put(932,"Fine Park'taki olayda kullanılan balon,\nR'nin gaz hâlindeki özelliklerine çok iyi bir örnektir.",'style')
put(933,'Balon patlatılınca R etrafa yayıldı.\nEtki alanı merkezden yaklaşık 1 metreydi;\nbu mesafe yeterliydi.','critical',
    'Mevcut “üç fıt” İngilizce ölçü birimini çevirmeden bırakmış, ayrıca radius “çap” olmuştu.',
    'JP merkezden 1 metre以内; FR/DE/IT/ES de 1 metre yarıçap/mesafe veriyor.')
put(936,'Kırmızı ve yeşil sıvılar yiyeceğe ayrı ayrı enjekte edilirse,\nonu yiyen Pokémon güçlü biçimde etkilenir.\nR’yi uygulamanın en kolay yolu budur.','style')
put(940,"Burada R'nin gelecekteki geliştirme planlarını özetleyeceğim.\nŞu anda R ampullerle taşınıyor.\nAncak ampuller kolay kırılıyor ve iki sıvıyı verimli\nkarıştırmaya elverişli değil. Bu yüzden kapsül biçiminde\nbir prototip üzerinde çalışmaya başladık.",'term',
    '“Şişe” önceki manuel terminolojiyle ve bilimsel nesneyle uyumsuzdu.',
    'JP アンプル, DE Ampullen, FR/IT/ES fioles/fiale/viales = ampul/vial.')
put(941,'R’yi sağlam kapsüllerde saklayarak kırılmayı önleyip\ngüvenli biçimde taşımak mümkün olacak.','style')
put(942,'Ayrıca kapsüle, iki ayrı sıvıyı istenen anda\nkarıştıran bir mekanizma eklemeyi planlıyorum.\nBöylece R her yerde ve her zaman otomatik olarak\nkarıştırılıp hemen dağıtılabilecek.','style')
put(943,'R’yi geliştirmek için daha fazla deney verisi toplamalıyız.\nŞimdiki R’nin iki büyük sorunu var:\netkisi geçici ve R’nin etkisindeki Pokémon\nkullanan kişinin komutlarını dinlemiyor.','critical',
    '“İletişim kurmak imkânsız” fazla genel kalıyordu; özgün metin kullanıcının iradesinin/komutlarının Pokémon’a işlemediğini anlatıyor.',
    'JP R使用者の意志が通じない; FR/DE açıkça kullanıcının komutlarına uymama; IT/ES iletişim kuramama.')
put(944,'Bundan sonraki araştırmalar, Pokémon kullanıcısıyla\niletişim kurmayı sürdürürken R’nin güç artırıcı etkisinin\ndaha uzun süre devam etmesini sağlamaya odaklanacak.','critical')
put(950,'Saklanarak ilerleyelim.','style')
put(951,'Yük çok değerli. Sakın zarar vermeyin!','term')
for i in [952,953,961,962,964,967,971,974,987,988,995]:
    extra=None
    if i==953: extra=[('*homurdanır*','*zorlanır*')]
    sound(i,extra)
put(967,'Pokémon sesi (İyi değil.)\nPokémon sesi (Hah! Zıplarken böyle bağırırım.)','sound')
put(969,'*zorlanır* *zorlanır* *zorlanır*','style')
put(970,'*zorlanır* *zorlanır* *zorlanır*','style')
put(973,'*zorlanır* Off... Sonunda geldik.\nHakkını vereyim, iyi iş çıkardın!','style')
put(975,'Hadi ama! Bütün{{CTRL:0001:0006:}}\nişi yapan bendim!','style')
put(995,'Pokémon sesi (Olur bu iş! Buradan girebiliriz!)','sound')
put(996,'Buradan girebileceğimizi söylüyor.','style')
put(1000,'*zorlanır* Evettt... Bunu yapabiliriz, ortak!\nBen beyin olayım, sen de kas gücü, tamam mı?','style')

# Ensure no accidental fake mappings with identical text are counted as changed.
# Preserve exact control-token sequence for every changed row.
TOKEN_RE=re.compile(r'\{\{(?:CTRL|BYTE):[^}]+\}\}')
def sig(s): return tuple(TOKEN_RE.findall(s))
for idx,v in C.items():
    old=episode7_rows[idx]['Turkish_Manual_v17']
    if sig(old)!=sig(v['text']):
        raise ValueError(f'CONTROL SIGNATURE DIFFERENCE row {idx}: {sig(old)} != {sig(v["text"])}')

UNCH_REASON='Satır EN, JP, FR, DE, IT, ES ve iki Çince sürümle tek tek okundu. Mevcut Türkçe, sahne bağlamını ve temel anlamı doğal biçimde koruduğu için bilinçli olarak değiştirilmedi.'
UNCH_CROSS='Çok-dilli manuel karşılaştırmada anlamı değiştirecek bir kaynak farkı, terminoloji sorunu veya karakter tonu kaybı görülmedi; mevcut Türkçe kabul edildi.'

# Update all comparison CSVs with v18 carry-forward; episode7 becomes fully manually reviewed.
for csvp in sorted(cmpdir.glob('*.csv')):
    with csvp.open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f)); fields=list(rows[0].keys())
    needed=['Turkish_Manual_v18','Manual_Review_Status_v18','Manual_v18_Decision','Manual_v18_Reason_TR','Manual_v18_CrossLanguage_TR']
    for n in needed:
        if n not in fields: fields.append(n)
    for r in rows:
        old=r.get('Turkish_Manual_v17',r.get('Turkish_Current',''))
        r['Turkish_Manual_v18']=old
        r['Manual_Review_Status_v18']=r.get('Manual_Review_Status_v17','HENÜZ_MANUEL_İNCELENMEDİ') or 'HENÜZ_MANUEL_İNCELENMEDİ'
        r['Manual_v18_Decision']=r.get('Manual_v17_Decision','')
        r['Manual_v18_Reason_TR']=r.get('Manual_v17_Reason_TR','')
        r['Manual_v18_CrossLanguage_TR']=r.get('Manual_v17_CrossLanguage_TR','')
        if csvp.name=='episode7.csv':
            idx=r['Index']; r['Manual_Review_Status_v18']='MANUEL İNCELENDİ'
            if idx in C and C[idx]['text']!=old:
                r['Turkish_Manual_v18']=C[idx]['text']
                r['Manual_v18_Decision']='DEĞİŞTİ'
                r['Manual_v18_Reason_TR']=C[idx]['reason']
                r['Manual_v18_CrossLanguage_TR']=C[idx]['cross']
            else:
                r['Manual_v18_Decision']='AYNI KALDI'
                r['Manual_v18_Reason_TR']=UNCH_REASON
                r['Manual_v18_CrossLanguage_TR']=UNCH_CROSS
    with csvp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

# Generate manual reports.
for p in mrdir.glob('_MANUAL_*'):
    p.unlink()
for p in mrdir.glob('_BATCH14_*'):
    p.unlink()
all_reviewed=[]; progress=[]; batch=[]
for csvp in sorted(cmpdir.glob('*.csv')):
    with csvp.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    rev=[r for r in rows if r.get('Manual_Review_Status_v18')=='MANUEL İNCELENDİ']
    ch=[r for r in rev if r.get('Manual_v18_Decision')=='DEĞİŞTİ']
    same=[r for r in rev if r.get('Manual_v18_Decision')=='AYNI KALDI']
    progress.append({'Dosya':csvp.name,'Toplam':len(rows),'Manuel_Incelendi':len(rev),'Degisti':len(ch),'Ayni_Kaldi':len(same),'Henuz_Manuel_Incelenmedi':len(rows)-len(rev)})
    for r in rev:
        x={'Dosya':csvp.name}; x.update(r); all_reviewed.append(x)
    if csvp.name=='episode7.csv': batch=rev

def write_csv(path, rows):
    if not rows:
        path.write_text('',encoding='utf-8-sig'); return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

write_csv(mrdir/'_MANUAL_PROGRESS.csv',progress)
write_csv(mrdir/'_MANUAL_REVIEWED_ALL.csv',all_reviewed)
write_csv(mrdir/'_MANUAL_CHANGES_ONLY.csv',[r for r in all_reviewed if r.get('Manual_v18_Decision')=='DEĞİŞTİ'])
write_csv(mrdir/'_BATCH14_REVIEWED.csv',batch)
write_csv(mrdir/'_BATCH14_NEW_CHANGES.csv',[r for r in batch if r.get('Manual_v18_Decision')=='DEĞİŞTİ'])
# standalone episode7
shutil.copy2(cmpdir/'episode7.csv',mrdir/'episode7.csv')

# stats
stats={k:sum(int(r[k]) for r in progress) for k in ['Toplam','Manuel_Incelendi','Degisti','Ayni_Kaldi','Henuz_Manuel_Incelenmedi']}
batch_changed=sum(r.get('Manual_v18_Decision')=='DEĞİŞTİ' for r in batch)
batch_same=sum(r.get('Manual_v18_Decision')=='AYNI KALDI' for r in batch)
build_stats={'total':stats['Toplam'],'reviewed':stats['Manuel_Incelendi'],'changed':stats['Degisti'],'same':stats['Ayni_Kaldi'],'remaining':stats['Henuz_Manuel_Incelenmedi'],'batch_reviewed':len(batch),'batch_changed':batch_changed,'batch_same':batch_same}
(OUT/'build_stats.json').write_text(json.dumps(build_stats,ensure_ascii=False,indent=2),encoding='utf-8')

# Build MSBTs, replacing v17 patch message files.
tool=OUT/'tools'/'msbt_toolkit.py'
base=OUT/'patch_v18'/'TürkçePatch'/'00040000001C1E00'/'romfs'/'message'/'English'
tmp=OUT/'_rebuilt_v18'
if tmp.exists(): shutil.rmtree(tmp)
subprocess.run([sys.executable,str(tool),'apply-dir',str(base),str(cmpdir),'Turkish_Manual_v18',str(tmp),'--fallback-column','Turkish_Manual_v17'],check=True)
for msbt in tmp.glob('*.msbt'):
    shutil.copy2(msbt,base/msbt.name)
shutil.rmtree(tmp)

# QA heuristic output.
qadir=OUT/'qa_v18'
if qadir.exists(): shutil.rmtree(qadir)
subprocess.run([sys.executable,str(tool),'qa-dir',str(cmpdir),'Turkish_Manual_v18',str(qadir),'--source-column','English'],check=True)

# Structural check: parse each rebuilt MSBT and compare labels/texts with CSV.
sys.path.insert(0,str(OUT/'tools'))
import msbt_toolkit
struct={'msbt_files':0,'rows':0,'text_mismatch':0,'label_mismatch':0,'control_mismatch':0,'bad_utf8_repl':0,'byte_tokens':0}
for csvp in sorted(cmpdir.glob('*.csv')):
    stem=csvp.stem; mp=base/(stem+'.msbt')
    parsed=msbt_toolkit.parse_msbt(mp)
    texts=[msbt_toolkit.decode_text(x) for x in parsed['raws']]
    with csvp.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    struct['msbt_files']+=1; struct['rows']+=len(rows)
    if len(texts)!=len(rows): raise RuntimeError((stem,len(texts),len(rows)))
    for pos,(r,t) in enumerate(zip(rows,texts)):
        if t!=r['Turkish_Manual_v18']: struct['text_mismatch']+=1
        if parsed['labels'].get(pos,'')!=r['Label']: struct['label_mismatch']+=1
        if msbt_toolkit.control_signature(r['Turkish_Manual_v17'])!=msbt_toolkit.control_signature(r['Turkish_Manual_v18']): struct['control_mismatch']+=1
        if '�' in t: struct['bad_utf8_repl']+=1
        if '{{BYTE:' in t: struct['byte_tokens']+=1
if any(struct[k] for k in ['text_mismatch','label_mismatch','control_mismatch','bad_utf8_repl','byte_tokens']):
    raise RuntimeError(struct)

# Save decision mapping.
(OUT/'tools'/'manual_v18_episode7_decisions.json').write_text(json.dumps(C,ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copy2('/mnt/data/apply_manual_v18_episode7.py',OUT/'tools'/'apply_manual_v18_episode7.py')

# Documentation.
report=f'''# Detective Pikachu Türkçe — v18 Manuel Tur 14\n\n## Bu tur\n\n- Dosya: `episode7.csv`\n- Manuel incelenen: **1003 / 1003**\n- Gerçek metin değişikliği: **{batch_changed}**\n- Bilinçli aynı bırakılan: **{batch_same}**\n- Her satır EN, JP, FR, DE, IT, ES, Basitleştirilmiş ve Geleneksel Çince ile tek tek karşılaştırıldı.\n- Karar verme otomatik değildir; script yalnız manuel kararları CSV/MSBT'ye yazar.\n\n## Kümülatif\n\n- Manuel incelenen: **{stats['Manuel_Incelendi']} / {stats['Toplam']}**\n- Manuel değişiklik: **{stats['Degisti']}**\n- Bilinçli aynı: **{stats['Ayni_Kaldi']}**\n- Henüz manuel incelenmeyen: **{stats['Henuz_Manuel_Incelenmedi']}**\n\n## Önemli bulgular\n\n- `three feet` kalıntısı, JP/FR/DE/IT/ES ortak metriğine göre **1 metre** olarak düzeltildi; ayrıca radius/çap ayrımı giderildi.\n- R taşıma kapları JP `アンプル` / DE `Ampullen` doğrultusunda **ampul** olarak standardize edildi.\n- Tim'in kendi babası için yanlış `babanla` kullanımları **babamla** olarak düzeltildi.\n- `incubation` kaynaklı hücre biyolojisi hataları **hücre kültürü / hücreleri çoğaltmak** olarak düzeltildi.\n- Limanda JP `荷物` olan genel mallar **yük**, gerçek JP `コンテナ` nesneleri **konteyner** olarak ayrıştırıldı.\n- `Dedektif Günlüğü` ifadesi JP `雑誌` doğrultusunda **Dedektif Dergisi** oldu.\n- Pokémon teknik vokalizasyon etiketlerindeki gereksiz `çığlık` genellemesi sahneye göre **Pokémon sesi** olarak düzeltildi.\n- Fabrika sloganında diğer dillerin yaratıcı yerelleştirme yaklaşımı izlenerek **“Kokusu beter, sağlığa değer!”** kullanıldı.\n\n## Yapısal QA\n\n- MSBT: **{struct['msbt_files']}/27**\n- Satır: **{struct['rows']}/17653**\n- CSV ↔ MSBT metin farkı: **{struct['text_mismatch']}**\n- Label/index farkı: **{struct['label_mismatch']}**\n- Kontrol-kodu farkı: **{struct['control_mismatch']}**\n- Bozuk UTF-8: **{struct['bad_utf8_repl']}**\n- BYTE artığı: **{struct['byte_tokens']}**\n'''
(OUT/'MANUEL_DENETIM_TUR14_TR.md').write_text(report,encoding='utf-8')
(OUT/'CHANGELOG_TR.md').write_text(f'''# v18 Değişiklik Günlüğü\n\n- `episode7.csv`: 1003/1003 manuel incelendi.\n- {batch_changed} gerçek metin değişikliği, {batch_same} bilinçli aynı.\n- Kümülatif manuel ilerleme: {stats['Manuel_Incelendi']}/{stats['Toplam']}.\n- R/ampul, 1 metre ölçüsü, hücre kültürü, liman yük/konteyner ayrımı, rütbe/özel ad/karakter sesi ve fabrika diyaloğu düzeltmeleri.\n- 27 MSBT strict-control ile yeniden derlendi.\n''',encoding='utf-8')
(OUT/'README_TR.md').write_text(f'''# Detective Pikachu Türkçe Yama — v18 Manuel Tur 14\n\nBu paket kullanıcı tarafından sağlanan Türkçe patch'in çok-dilli manuel kalite denetimidir.\n\n- Bu tur: `episode7.csv` **1003/1003**\n- Bu tur değişti: **{batch_changed}**\n- Bu tur aynı kaldı: **{batch_same}**\n- Kümülatif manuel: **{stats['Manuel_Incelendi']}/{stats['Toplam']}**\n- Henüz manuel incelenmedi: **{stats['Henuz_Manuel_Incelenmedi']}**\n\nKlasörler:\n- `patch_v18/` — kurulabilir Türkçe patch\n- `comparison_csv_v18/` — tüm 27 çok-dilli CSV\n- `manual_review_csv_v18/` — manuel karar ve raporlar\n- `qa_v18/` — heuristik QA\n- `tools/` — MSBT araçları ve manuel karar dosyası\n\nTürkçe font korunmuştur.\n''',encoding='utf-8')
qa_summary=f'''Detective Pikachu TR v18 / Manuel Tur 14 — Yapısal QA Özeti\n\nManuel ilerleme: {stats['Manuel_Incelendi']} / {stats['Toplam']}\nBu tur: episode7.csv 1003/1003\nBu tur değişti: {batch_changed}\nBu tur aynı kaldı: {batch_same}\nKümülatif manuel değişiklik: {stats['Degisti']}\nHenüz manuel incelenmedi: {stats['Henuz_Manuel_Incelenmedi']}\n\nYapısal doğrulama:\n- MSBT: {struct['msbt_files']}/27\n- Satır: {struct['rows']}/17653\n- CSV ↔ MSBT farkı: {struct['text_mismatch']}\n- Label/index farkı: {struct['label_mismatch']}\n- Kontrol-kodu farkı: {struct['control_mismatch']}\n- Bozuk UTF-8 (�): {struct['bad_utf8_repl']}\n- BYTE artığı: {struct['byte_tokens']}\n'''
(OUT/'QA_SUMMARY_MANUAL_V18_TR.txt').write_text(qa_summary,encoding='utf-8')

print(json.dumps({'out':str(OUT),'mapping_entries':len(C),'batch_changed':batch_changed,'batch_same':batch_same,'stats':build_stats,'struct':struct},ensure_ascii=False,indent=2))
