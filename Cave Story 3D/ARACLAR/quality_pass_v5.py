#!/usr/bin/env python3
"""Cave Story 3D TR v5 - kaynak İngilizceye göre manuel kalite geçişi.

Amaç:
- SJS komutlarını değiştirmeden yalnız görünür metin parçalarını düzeltmek.
- Eski ASCII-Türkçe yazımları temizlemek.
- İngilizce ROMFS ile karşılaştırmada saptanan anlam/üslup hatalarını düzeltmek.
- credit.sjs'ye dokunmamak (özel ikili düzen baytları içerir).

Kodlama: cp1254 + surrogateescape; tanımsız/ikili baytlar byte-byte korunur.
"""
from pathlib import Path
import argparse, collections, re

CMD_RE = re.compile(r'<[A-Z0-9+\-]{3}(?:[0-9:+\-]+)?')
WORD_RE = re.compile(r"(?<![A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû])[A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû]+(?![A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû])")

# Yalnızca tek-anlamlı, bağlamdan bağımsız yazım düzeltmeleri.
WORD_FIXES = {
    'gecmen':'geçmen','caliligin':'çalılığın','bagiriyormus':'bağırıyormuş',
    'hazirlansan':'hazırlansan','sardin':'sardın','hirsimin':'hırsımın','buyum':'büyüm',
    'calismiyorsun':'çalışmıyorsun','yuzlestim':'yüzleştim','gecemiyorsun':'geçemiyorsun',
    'gecebilirdik':'geçebilirdik','yuzundenmis':'yüzündenmiş','siginaktayim':'sığınaktayım',
    'odadayim':'odadayım','hakliysa':'haklıysa','actirmaliyiz':'açtırmalıyız',
    'kiriliyorlar':'kırılıyorlar','yakalayamiyorum':'yakalayamıyorum',
    'mimigalarını':'Mimigalarını', # case is handled below; source typo often Mimigalarıni
    'tatliymissin':'tatlıymışsın','tikistirdin':'tıkıştırdın','tanistin':'tanıştın',
    'buyugunde':'büyüğünde','tasirsin':'taşırsın','ilerlemeliyiz':'ilerlemeliyiz',
    'ceviriyorsun':'çeviriyorsun','sanmamistim':'sanmamıştım','saklanamazsin':'saklanamazsın',
    'ciddilesiyorum':'ciddileşiyorum','cakildin':'çakıldın',
    'kurtulamayacagimizi':'kurtulamayacağımızı','konusursun':'konuşursun',
    'asiliydi':'asılıydı','karmakarisikti':'karmakarışıktı','parcalarim':'parçalarım',
    'olmezsem':'ölmezsem','tarafindayim':'tarafındayım','yenilmeyecegim':'yenilmeyeceğim',
    'tarafindasin':'tarafındasın','yaklasamiyorum':'yaklaşamıyorum','sominede':'şöminede',
    'harlaniyor':'harlanıyor','kilicinla':'kılıcınla','buyuyle':'büyüyle','cevrildim':'çevrildim',
    'senmissin':'senmişsin','kilicmis':'kılıçmış','bitmisim':'bitmişim','basiyorsun':'basıyorsun',
    'ciddilesiyorum':'ciddileşiyorum','dehsetten':'dehşetten','barbarin':'barbarın',
    'odlegin':'ödleğin','mimigalarıni':'mimigalarını',
}

# Türkçe büyük/küçük harf biçimini koru.
TR_UP = str.maketrans({'i':'İ','ı':'I','ş':'Ş','ğ':'Ğ','ü':'Ü','ö':'Ö','ç':'Ç'})
TR_LOW = str.maketrans({'İ':'i','I':'ı','Ş':'ş','Ğ':'ğ','Ü':'ü','Ö':'ö','Ç':'ç'})
def tr_upper(s): return s.translate(TR_UP).upper()
def tr_lower(s): return s.translate(TR_LOW).lower()
def shape(src, dst):
    if src.isupper(): return tr_upper(dst)
    if src[:1].isupper(): return tr_upper(dst[:1]) + dst[1:]
    return dst

# Tüm betiklerde güvenli ve elle doğrulanmış ifade düzeltmeleri.
GLOBAL = [
    ("Jenka'nin", "Jenka'nın"),
    ("Kutup Yıldızı'nin", "Kutup Yıldızı'nın"),
    ("Kutup Yıldızı'ni", "Kutup Yıldızı'nı"),
    ("Her Derde Deva'yi", "Her Derde Deva'yı"),
    ('SIZ İKİSİ BENİ DİNLİYOR MUSUNUZ', 'SİZ İKİNİZ BENİ DİNLİYOR MUSUNUZ'),
    ('SİZ İKİSİ BENİ DİNLİYOR MUSUNUZ', 'SİZ İKİNİZ BENİ DİNLİYOR MUSUNUZ'),
    ('ASANSÖR INDIRILSIN MI?', 'ASANSÖR İNDİRİLSİN Mİ?'),
    ('Bu halim korkunç mu?', 'Bu hâlim korkunç mu?'),
    ('Hih!', 'Hıh!'),
]

# Dosya bazlı, İngilizce orijinalle yan yana okunarak hazırlanmış manuel düzeltmeler.
FILE_FIXES = {
'armsitem.sjs': [
    ('Füzeatarın ciddi biçimde geliştirilmiş hâli.', 'Füzeatarın çok daha güçlü bir sürümü.'),
    ('Yumurta No. 06’nın içinde bulunan kimlik kartı.', "Yumurta No. 06'nın içinde bulunan\r\nbir kimlik kartı."),
    ('Kapıları havaya uçurmak için yapılmış bir bomba.', 'Kapıları havaya uçurmak için\r\nyapılmış bir bomba.'),
    ('Canını tamamen yeniler, ama yalnızca\r\nbir kez kullanılabilir. Şimdi kullanılsın mı?',
     'Canını tamamen yeniler, ama yalnızca\r\nbir kez kullanılabilir.\r\nŞimdi kullanılsın mı?'),
    ('Canını tamamen yeniler, ama yalnızca\nbir kez kullanılabilir. Şimdi kullanılsın mı?',
     'Canını tamamen yeniler, ama yalnızca\nbir kez kullanılabilir.\nŞimdi kullanılsın mı?'),
],
'head.sjs': [
    ('Sistemi kapatma ve Nintendo 3DS\nOyun Kartını çıkarma.',
     'Sistemi kapatmayın ve Nintendo 3DS\nOyun Kartını çıkarmayın.'),
    ('Azami füze sayısı <NUM0000.', 'Azami füze sayısı <NUM0000 arttı.'), # command-aware fallback below
],
'stage/almond.sjs': [
    ('Dış kabuğu\r\ninanılmaz zarar görmüş.', 'Dış gövdesi\r\nağır hasar görmüş.'),
    ('Bu zırhlı kapı...\r\nYarı açık kalmış...', 'Bu patlama kapısı...\r\nYarı açık kalmış...'),
    ('Yine mi dışarıda???', 'Yine mi baygın???'),
    ("Çekme Halatını Curly'ye sardin.", "Çekme Halatını Curly'ye sardın."),
    ('Bir şeyin\r\nkurtulduğunu duyuyorsun...', 'Bir şeyin yerinden\r\nkoptuğunu duyuyorsun...'),
    ('Anne gibi davranma!', 'Annemmişsin gibi davranma!'),
    ('Aptal ahmak!!', 'Aptalın tekisin!!'),
    ('Çekirdeği Hemen laboratuvara götür!', 'Çekirdeği HEMEN laboratuvara götür!'),
    ('Bilinç... kayboluyor...', 'Bilincimi... kaybediyorum...'),
    ("Biliyor muydun, Jenka adındaki kadının \r\nJenka'nin küçük bir kardeşi mi\r\nvardı?",
     "Biliyor muydun, Jenka'nın\r\nküçük bir erkek kardeşi vardı."),
],
'stage/ballo1.sjs': [
    ('Çok, çok önce, büyü gücüne\r\nolan hirsimin\r\ncezasından korkmadan',
     'Çok, çok uzun zaman önce,\r\nbüyü gücüne duyduğum hırsın\r\nsonuçlarından korkmadan'),
    ('kontrolsüzce büyümesine izin verdim.', 'dizginlerinden boşanmasına izin verdim.'),
    ('...ateşi yuttu\r\nbeni seven çocuğu,', '...alevleri bana hayran olan\r\nçocuğu yuttu,'),
    (' ve\r\nbeni seven karımı...', ' ve\r\nbeni seven eşimi...'),
    ('Onlar alevlerinde boğuldu\r\nve korkunç acı çekti.', 'Alevler onları yuttu;\r\nkorkunç acılar çektiler.'),
    ('Gözlerim açık kaldı ve\r\no alevli dehsetten\r\nbakışımı çeviremedim...',
     'Gözlerimi ayıramadım;\r\no alevli dehşeti\r\nseyretmek zorunda kaldım...'),
    ('Jenka beni mühürledi. Ama\r\nbuyum her dakika\r\ndaha da kudurdu.',
     'Jenka beni mühürledi.\r\nAma büyüm her dakika\r\ndaha da azgınlaştı.'),
    ('Bu muazzam büyü öfkesine\r\nson verecek kişiyi\r\nbekledim...',
     'Büyümün bu korkunç öfkesine\r\nson verecek kişiyi...'),
],
'stage/cent.sjs': [
    ('Sakin\r\naptalca bir şey yapma.', 'Sakın\r\naptalca bir şey yapma.'),
    ('Ama sen ve ben farkliydik.', 'Ama sen ve ben farklıydık.'),
    ('yok etmeye gonderildik.', 'yok etmeye gönderildik.'),
    ('Yeryüzünden gelecek\r\nsaldırıya karşı kırmızı\r\nçiçek yetiştiriyoruz.',
     'Yeryüzüne yapılacak\r\nsaldırı için kırmızı\r\nçiçek yetiştiriyoruz.'),
    ('Doktor hakliysa...\r\nçiçekleri bir an önce\r\nactirmaliyiz.',
     'Doktor doğru söylüyorsa...\r\nçiçekleri bir an önce\r\naçtırmalıyız.'),
    ('Çabuk büyü, kırmızı çiçek!', 'Çabuk aç, küçük kırmızı çiçek!'),
    ('Yaşasın Doktor!', 'Yaşasın yüce Doktor!'),
    ('Niye calismiyorsun...', 'Niye çalışmıyorsun...'),
    ('Sakin aptalca bir şey yapma.', 'Sakın aptalca bir şey yapma.'),
    ('ama çok kolay kiriliyorlar.', 'ama çok kolay kırılıyorlar.'),
    ('Bugün hiçbir şey yakalayamiyorum...', 'Bugün hiçbir şey yakalayamıyorum...'),
    ('Yakalandı...', 'Yakalandın...'),
    ('bu adanın Mimigalarıni kırmızı\r\nçiçek yetiştirmek için kullanıyor.',
     'bu adanın Mimigalarını kırmızı\r\nçiçek yetiştirmek için kullanıyor.'),
    ('Buna benzer şeyler\r\ngeçmişte de ölmüş...', 'Geçmişte de buna benzer\r\nolaylar olmuş...'),
    ('Bu kız kaynak yakınına düştü.', 'Bu kız pınarın yakınına düştü.'),
    ('Şimdi hurda metal olmuştur herhalde.', 'Şimdiye hurdaya dönmüştür herhalde.'),
    ('Tatliymissin...', 'Tatlıymışsın...'),
    ("Curly'nin ağzına tikistirdin.", "Ma Pignon'u Curly'nin ağzına tıkıştırdın."),
    ('Onunla yuzlestim ve', 'Onunla yüzleştim ve'),
],
'stage/chako.sjs': [
    ('Ateşi gecemiyorsun.', 'Ateşi geçemiyorsun.'),
    ('En buyugunde var.', 'En büyüğünde var.'),
    ("Şu ödlek Santa'yla tanistin mi?", "Şu ödlek Santa'yla tanıştın mı?"),
    ('bir kavanoz Denizanası Suyu tasirsin', 'bir kavanoz Denizanası Suyu taşırsın'),
],
'stage/drain.sjs': [
    ('Şu ızgaralar olmasa gecebilirdik.', 'Şu ızgaralar olmasa geçebilirdik.'),
    ('Devam etmek zorundayız. Ilerlemeliyiz.', 'Devam etmek zorundayız. İlerlemeliyiz.'),
    ('Ceviriyorsun.', 'Çeviriyorsun.'),
],
'stage/fall.sjs': [
    ('Gerçekten yapacağını sanmamistim.', 'Gerçekten yapacağını sanmamıştım.'),
    ('Dur, sen bize nefret etmiyor musun?', 'Dur, sen bizden nefret etmiyor musun?'),
    ('Seni kötü biri sanmıştım,\r\nama meğer sadece\r\nŞeytan Tacı yuzundenmis?',
     'Seni kötü biri sanmıştım;\r\nmeğer hepsi Şeytan Tacı\r\nyüzündenmiş, öyle mi?'),
],
'stage/gard.sjs': [('o kilicinla', 'o kılıcınla')],
'stage/itoh.sjs': [('Buyuyle Mimiga\'ya cevrildim!', "Büyüyle Mimiga'ya çevrildim!")],
'stage/jenka2.sjs': [('senmissin', 'senmişsin')],
'stage/little.sjs': [('kilicmis', 'kılıçmış')],
'stage/lounge.sjs': [('Bitmisim...', 'Bitmişim...')],
'stage/mazem.sjs': [('Basiyorsun.', 'Basıyorsun.')],
'stage/momo.sjs': [
    ('erkekler barbarın tekidir.', 'erkekler tam birer barbardır.'),
    ('o da dışarıdaki fiskiyelerdir.', 'o da dışarıdaki fıskiyelerdir.'),
    ('Bu fiskiyenin pilleri', 'Bu fıskiyenin pilleri'),
    ("Sen Sue'nun bahsettiği\r\nsavaşçı olmalısın.", "Sen Sue'nun bahsettiği\r\nkahraman olmalısın."),
    ("Şansımı Doktor'un\r\ntarafındayken denedim.", "Doktor'un yanında çalışarak\r\nşansımı denedim."),
    ('Kadınlara saygısız davranan\r\nerkekler barbarin tekidir.', 'Kadınlara saygısız davranan\r\nerkekler barbarın tekidir.'),
    ('Ama belli ki\r\nyeterli parça yok.', 'Ama belli ki roket için\r\nhâlâ yeterli parçam yok.'),
    ('Roketi tamamlamak için\r\ngerekli parçalar hâlâ yeterli değil.', 'Roketi tamamlamak için\r\nhâlâ yeterli parçam yok.'),
    ('onlarla rahatça konusursun.', 'onlarla rahatça konuşursun.'),
    ('Ama odlegin tekidir.', 'Ama tam bir korkaktır.'),
],
'stage/jenka1.sjs': [
    ('Balrog değil misin.', 'Aa, Balrog, sen misin.'),
    ('Neyden söz\r\nediyorsun, Balrog.', 'Neden bahsettiğini\r\nbilmiyorum, Balrog.'),
    ("Kırmızı Çiçek'i yemenin\r\nyasak etkisiyle...", 'Yasak kırmızı çiçeği\r\nyedikleri için...'),
    ('Peki sonra\r\nböyle öfkeyle dolmuş\r\nMimiga\'ya ne olur...', "Peki sonra\r\nböyle öfkeyle dolmuş\r\nbir Mimiga'ya ne olur..."),
    ('Bir söylenti duydum.\r\nSözde inmişler...\r\nyüzeye...', 'Bir söylenti duydum.\r\nSözde yüzeye kadar\r\ninmişler...'),
    ('Insanların yaşadığı yere.', 'İnsanların yaşadığı yere.'),
    ('Çılgına dönmüş\r\nMimigaların yüzeye\r\nyüzeye...', 'Çılgına dönmüş Mimigaların\r\nyeryüzüne kadar inmesi...'),
],
'stage/mimi.sjs': [
    ('Toroko güvende değilse seni parcalarim!', 'Toroko güvende değilse seni parçalarım!'),
    ('Doktor, kırmızı çiçeği kullanıp\r\nhepinizi\r\ninsanlara saldırmak istiyor.',
     'Doktor, kırmızı çiçeği kullanıp\r\nhepinizi insanlara\r\nsaldırtmayı planlıyor.'),
    ("Doktor'un adamları\r\nbeni başka bir Mimiga sanıp\r\nonu kaçırdılar.",
     "Doktor'un adamları başka bir\r\nMimiga'yı benimle karıştırıp\r\nonu kaçırdılar."),
],
'stage/pens1.sjs': [
    ('Ama gerçekten kurtulamayacagimizi sandım.', 'Ama gerçekten kurtulamayacağımızı sandım.'),
    ("Korkarım ki \r\nDoktor'un adamlarını\r\nbuluruz herhalde.", "Korkarım oraya Doktor'un\r\nadamları gidecek."),
    ("En azından Sue'yu\r\nadadan kaçırırdım.", "En azından Sue'nun\r\nadadan kaçmasını sağlardım."),
    ('Uzun zamandır\r\nbu adaya gelmeye\r\ndirenmişti.', 'Uzun süre bu adaya\r\ngelmek istemedi.'),
    ("Sue'yu son bir kez görürsen,\r\nlütfen onu al ve...\r\nkaç... adadan.",
     "Sue'yu son bir kez görürsen,\r\nlütfen onu yanına al ve...\r\nadadan... kaç."),
],
'stage/curly.sjs': [
    ('Ben Mimigaların tarafindayim, sana yenilmeyecegim!!', 'Ben Mimigaların tarafındayım, sana yenilmeyeceğim!!'),
    ('Sen de Mimiga tarafindasin, öyle mi?', 'Sen de Mimigaların tarafındasın, öyle mi?'),
],
'stage/ring3.sjs': [
    ('Çekirdekten uzak dur.\r\nYoksa bunun canı gider.', 'Onun canını önemsiyorsan\r\nÇekirdekten uzak dur.'),
    ('Yeni kralın\r\nsenin elinden düşmesi...', 'Demek yeni kralı\r\nsen yendin...'),
    ('Sanki bir\r\ninsanüstü oldum!', 'Sanki insanüstü bir\r\nvarlığa dönüştüm!'),
    ('Efendisini unutacak kadar aptal olan\r\nözgür iradeye ihtiyaç duymaz.', 'Efendisini unutacak kadar aptal\r\nolanların özgür iradeye ihtiyacı yok.'),
    ('Olduğun güne dek,\r\nBENİM kuklam olacaksın.', 'Öldüğün güne dek,\r\nBENİM kuklam olacaksın.'),
],
'stage/mazes.sjs': [
    ('O zaman su kayayı kenara çekelim.', 'O zaman şu kayayı kenara çekelim.'),
    ('Biraz daha uca\r\ntutamaz mısın?', 'Biraz daha ucundan\r\ntutamaz mısın?'),
    ('Size yardım etmem.\r\nARAMIZDA KALSIN!', 'Size yardım ettiğim...\r\nARAMIZDA KALSIN!'),
],
'stage/shelt.sjs': [
    ('Kazuma: içi bomboş bir siginaktayim\r\nhiçbir şey yok', 'Kazuma: içi bomboş bir sığınaktayım;\r\nburada hiçbir şey yok'),
    ('Kazuma: hâlâ sığınak gibi bir\r\nodadayim', 'Kazuma: hâlâ sığınak gibi bir\r\nodadayım'),
],
'stage/cemet.sjs': [('goturursun', 'götürürsün')],
'stage/ring2.sjs': [('Biraz ünlü gibi hissediyorum.', 'Kendimi biraz ünlü gibi hissediyorum.')],
'stage/mazeo.sjs': [
    ("Panzehiri doktora verdin.", "Her Derde Deva'yı doktora verdin."),
    ('Seninle gelirdim ama bu hâlimle\r\nbu hâlimle yardım değil,\r\nyük olurum.', 'Seninle gelirdim ama bu hâlimle\r\nyardımdan çok yük olurum.'),
],
'stage/mazed.sjs': [("Her Derde Deva'yi aldın.", "Her Derde Deva'yı aldın.")],
'stage/pixel.sjs': [('Guvenliktesin!', 'Güvenliktesin!')],
'stage/pole.sjs': [('Hih!', 'Hıh!')],
'stage/mapi.sjs': [('Tuh!', 'Tüh!')],
'stage/santa.sjs': [
    ("Chako'nun evindeki şömineden\r\ngecmen gerek.", "Chako'nun evindeki şömineden\r\ngeçmen gerek."),
    ('geçersen caliligin öbür\r\ntarafına', 'geçersen çalılığın öbür\r\ntarafına'),
    ('Sonra da biri bagiriyormus gibi', 'Sonra da biri bağırıyormuş gibi'),
    ("Santa'nın sominesinde kömür yanıyor.", "Santa'nın şöminesinde kömür yanıyor."),
],
'stage/comu.sjs': [('Sominede alevler harlaniyor.', 'Şöminede alevler harlanıyor.')],
'stage/eggr.sjs': [('yaklasamiyorum', 'yaklaşamıyorum')],
'stage/eggx.sjs': [('Şimdi ciddilesiyorum!', 'Şimdi ciddileşiyorum!')],
}

# Gum Base terminolojisi tüm ilgili dosyalarda tek biçim.
for _rel in ('armsitem.sjs','stage/malco.sjs','stage/frog.sjs','stage/weed.sjs'):
    FILE_FIXES.setdefault(_rel, []).extend([
        ('Sakız Bazı', 'Sakız Mayası'), ('Sakız bazı', 'Sakız mayası'),
        ('Sakız bazasi', 'Sakız mayası'),
    ])


def split_parts(text):
    out=[]; pos=0
    for m in CMD_RE.finditer(text):
        out.append([False,text[pos:m.start()]])
        out.append([True,m.group(0)])
        pos=m.end()
    out.append([False,text[pos:]])
    return out


def apply_word_fixes(seg, counts):
    def repl(m):
        w=m.group(0)
        # Turkish-aware lowercase, then ASCII key shape.
        low=tr_lower(w)
        key=(low.replace('ç','c').replace('ğ','g').replace('ı','i')
                .replace('ö','o').replace('ş','s').replace('ü','u'))
        dst=WORD_FIXES.get(key)
        if not dst: return w
        nw=shape(w,dst)
        if nw!=w: counts['word:'+key]+=1
        return nw
    return WORD_RE.sub(repl,seg)


def apply_pairs(seg, pairs, counts, prefix):
    for a,b in sorted(pairs,key=lambda x:len(x[0]),reverse=True):
        n=seg.count(a)
        if n:
            seg=seg.replace(a,b); counts[f'{prefix}:{a[:55]}']+=n
    return seg


def process_script(path, rel, counts):
    raw=path.read_bytes(); text=raw.decode('cp1254','surrogateescape')
    parts=split_parts(text)
    local=FILE_FIXES.get(rel,[])
    for p in parts:
        if p[0]: continue
        s=p[1]
        s=apply_pairs(s,GLOBAL,counts,'global')
        s=apply_pairs(s,local,counts,'manual')
        s=apply_word_fixes(s,counts)
        # İkinci tur: kelime düzeltmesinden sonra eşleşebilen manuel ifadeler.
        s=apply_pairs(s,GLOBAL,counts,'global2')
        s=apply_pairs(s,local,counts,'manual2')
        p[1]=s
    new=''.join(x[1] for x in parts)

    # Özel animasyon: komut dizisi değişmeden ekrana "sıkıca tutun!!" yazdır.
    if rel=='head.sjs':
        for old,newtxt in [
            ('<GIT0006Azami füze sayısı <NUM0000.<NOD','<GIT0006Azami füze sayısı <NUM0000 arttı.<NOD'),
            ('<GIT0011Azami füze sayısı <NUM0000.<NOD','<GIT0011Azami füze sayısı <NUM0000 arttı.<NOD'),
        ]:
            if old in new:
                new=new.replace(old,newtxt); counts['manual:head_azami_fuze_artisi']+=1

    if rel=='stage/fall.sjs':
        old=('Tamam,\r\n<ANP0230:0020:0002s<WAI0010i<WAI0010k<WAI0010i<WAI0010 '
             '<WAI0010c<WAI0010a<WAI0010 <WAI0010t<WAI0010u<WAI0010t<WAI0010u<WAI0010n<WAI0010!!')
        fixed=('Tamam,\r\n<ANP0230:0020:0002s<WAI0010ı<WAI0010k<WAI0010ı<WAI0010c'
               '<WAI0010a<WAI0010 <WAI0010t<WAI0010u<WAI0010t<WAI0010u<WAI0010n<WAI0010<WAI0010!!')
        if old in new:
            new=new.replace(old,fixed); counts['manual:fall_sıkıca_tutun_animasyonu']+=1

    if new!=text:
        path.write_bytes(new.encode('cp1254','surrogateescape'))
        return True
    return False


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('root',help='Yerelleştirilmiş data kökü')
    ap.add_argument('-o','--output',default='quality_pass_v5.txt')
    a=ap.parse_args(); root=Path(a.root); counts=collections.Counter(); changed=[]
    for p in sorted(root.rglob('*.sjs')):
        rel=p.relative_to(root).as_posix()
        if rel=='credit.sjs': continue
        if process_script(p,rel,counts): changed.append(rel)
    lines=[
        'Cave Story 3D TR v5 - doğal çeviri kalite geçişi',
        f'Değişen SJS dosyası: {len(changed)}',
        f'Toplam uygulanan düzeltme: {sum(counts.values())}',
        '', 'Değişen dosyalar:', *changed, '', 'Düzeltmeler:'
    ]
    lines += [f'{k}\t{v}' for k,v in counts.most_common()]
    Path(a.output).write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'değişen={len(changed)} düzeltme={sum(counts.values())} rapor={a.output}')

if __name__=='__main__': main()
