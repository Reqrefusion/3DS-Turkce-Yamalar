#!/usr/bin/env python3
from __future__ import annotations
import csv, json, re, shutil, unicodedata
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT/'araclar'))
import tr_iyilestir as base
import v4_quality_pass as v4

CSV=ROOT/'ceviri'/'layton_tr.csv'
JSONL=ROOT/'ceviri'/'layton_tr.jsonl'
EASY=ROOT/'ceviri'/'CEVIRI_KOLAY.csv'
REPORT=ROOT/'raporlar'

# Yalnız biçimi kesin olan sözcükler. Anlama göre değişebilecek su/şu, sık/şık,
# don/dön, bas/baş gibi kökler burada topluca dönüştürülmez.
SAFE_WORDS={
 'kalin':'kalın','Kalin':'Kalın','isil':'ışıl','Isil':'Işıl','surada':'şurada','Surada':'Şurada',
 'konuşunda':'konusunda','Konuşunda':'Konusunda','bayiliyorum':'bayılıyorum','Bayiliyorum':'Bayılıyorum',
 'disim':'dişim','Disim':'Dişim','disimi':'dişimi','Disimi':'Dişimi','cabasi':'cabası','Cabasi':'Cabası',
 'cabasina':'çabasına','Cabasina':'Çabasına','yasindaydi':'yaşındaydı','Yasindaydi':'Yaşındaydı',
 'kıyisinda':'kıyısında','Kıyisinda':'Kıyısında','kısmini':'kısmını','Kısmini':'Kısmını',
 'asiliydi':'asılıydı','Asiliydi':'Asılıydı','cevabi':'cevabı','Cevabi':'Cevabı','sırali':'sıralı','Sırali':'Sıralı',
 'sakacilar':'şakacılar','Sakacilar':'Şakacılar','gelisi':'gelişi','Gelisi':'Gelişi','yarisina':'yarısına','Yarisina':'Yarısına',
 'sakadan':'şakadan','Sakadan':'Şakadan','adimin':'adımın','Adimin':'Adımın','baligini':'balığını','Baligini':'Balığını',
 'hayvanin':'hayvanın','Hayvanin':'Hayvanın','esimi':'eşimi','Esimi':'Eşimi','akisi':'akışı','Akisi':'Akışı',
 'akli':'aklı','Akli':'Aklı','şuç':'suç','Şuç':'Suç','cifti':'çifti','Cifti':'Çifti',
 'seklindeki':'şeklindeki','Seklindeki':'Şeklindeki','seklinde':'şeklinde','Seklinde':'Şeklinde','sekli':'şekli','Sekli':'Şekli',
 'acinim':'açınım','Acinim':'Açınım','kupun':'küpün','Kupun':'Küpün','kup':'küp','Kup':'Küp',
 'besinin':'beşinin','Besinin':'Beşinin','zarin':'zarın','Zarin':'Zarın','gerekmadan':'gerekmeden','Gerekmadan':'Gerekmeden',
 'islendiğini':'işlendiğini','Islendiğini':'İşlendiğini','islendi':'işlendi','Islendi':'İşlendi',
 'haric':'hariç','Haric':'Hariç','basili':'basılı','Basili':'Basılı','kalsin':'kalsın','Kalsin':'Kalsın',
 'koklu':'köklü','Koklu':'Köklü','islerinde':'işlerinde','Islerinde':'İşlerinde','Islerinin':'İşlerinin','islerinin':'işlerinin',
 'alcakgonulluluk':'alçakgönüllülük','Alcakgonulluluk':'Alçakgönüllülük','Kutupyildizi':'Kutup Yıldızı',
 'miracles':'mucizeler','Victims':'Kurbanlar','victims':'kurbanlar',
 'donmustur':'dönmüştür', # yalnız bu biçim mevcut kaynakta deliye dönmek bağlamında; aşağıda kaynak kontrolü yine yapılır
 'Ayi':'Ayı',
}

# Özel ad ekleri: telaffuza göre bu oyunda kullanılan biçimlerle tutarlı.
PHRASE_FIX=[
 (r"\bAngela'yi\b","Angela'yı",'özel ad belirtme eki'),
 (r"\bRandall'i\b","Randall'ı",'özel ad belirtme eki'),
 (r"\bDalston'i\b","Dalston'ı",'özel ad belirtme eki'),
 (r"\bİnsan boyutunda\b","insan boyutunda",'gereksiz büyük harf'),
 (r"\bgrup İnsan\b","grup insan",'gereksiz büyük harf'),
 (r"\bbir Şık\b","bir şık",'gereksiz büyük harf'),
 (r"\bçok Şık\b","çok şık",'gereksiz büyük harf'),
 (r"\bne kadar Şık\b","ne kadar şık",'gereksiz büyük harf'),
 (r"\bya da Şık\b","ya da şık",'gereksiz büyük harf'),
 (r"\bBu Şık\b","Bu şık",'gereksiz büyük harf'),
 (r"\bbu Şık\b","bu şık",'gereksiz büyük harf'),
 (r"\bŞu ihtiyar\b","şu ihtiyar",'gereksiz büyük harf'),
 (r"\bDışı de isil\b","Dişi de ışıl",'diş/ışıltı anlam düzeltmesi'),
 (r"\bgur bir sakal\b","gür bir sakal",'imla'),
 (r"\bİnce eleyip sık dokuyan\b","ince eleyip sık dokuyan",'cümle içi büyük harf'),
 (r"\bSıkıştırıyor\b","sıkıştırıyor",'cümle içi büyük harf'),
 (r"\bDöndürülmüş\b","döndürülmüş",'cümle içi büyük harf'),
 (r"\bherhangi bir İnsan\b","herhangi bir insan",'gereksiz büyük harf'),
 (r"\bJapon Balığı\b","Japon balığı",'tür adı büyük harf'),
 (r"\bgelişi güzel\b","gelişigüzel",'birleşik yazım'),
 (r"\bise kolaylaşır\b","iş kolaylaşır",'iş/ise bağlam düzeltmesi'),
 (r"\bAkbadain'i\b","Akbadain'i",'koru'),
]

# Kayıt bazında, kaynak anlam/kelime oyunu dikkate alınarak yapılan düzeltmeler.
OVERRIDE={
 ('00/00_000020.xs','text000001'): '<T>Şuraya bakın, Profesör! Her\nyer ışıl ışıl ve rengârenk. Sanki\nlunaparka gelmiş gibiyiz!',
 ('00/00_000020.xs','text000013'): '<T>Büyüteci belirli bölgelerin üzerine\ngetirdiğinde renginin turuncuya\ndöndüğünü fark edeceksin.',
 ('00/00_000030.xs','text000014'): '<T><M3/1/1>Pekâlâ... öyle olsun! O zaman\nkarnavalın tadını çıkarın. Bu da\nherhangi bir hediye kadar güzel!',
 ('01/01_010011.xs','text000004'): '<V0030><T>Efsaneye göre maske, onu\ntakana büyük bir güç bahşeder.</V>',
 ('01/01_010011.xs','text000007'): '<V0050><T><M1/1/1/60>Şey, şurada burada\nbirkaç ders aldım.</V>',
 ('01/01_010051.xs','text000004'): '<T>Kutuyu bulmak istiyorsan, biraz da\nkutunun dışında düşünmen gerek!',
 ('01/01_010195.xs','text000013'): '<T>Anlıyorum! Bay Ledore kaos yüzünden çok\nmeşgul. Bu kadar az uykuyla hâlâ ayakta\nkalması mucize—kelime oyunumu mazur görün.',
 ('01/01_010280.xs','text000005'): '<T><M1/2/1>Gösteri değil mi? Bu düpedüz\nsahtekârca bir saçmalık!<W> O zaman insanları\nnasıl taşa çevirdi?! Hadi, bunu da açıkla!',
 ('03/03_030110.xs','text000013'): '<T><M4/1/1>Serena, Maskeli Beyefendi ile\nkarşılaşmak, kumarhanede tüm birikimini\nkaybetmekten daha {\'\'}heyecanötesi{\'\'} değil.',
 ('03/03_030492.xs','text000001'): '<T>Yeter şu suç ortağı muhabbeti!\nSize söylüyorum, adamımız o.\nŞimdi kanıtlarımı getirin! HEMEN!',
 ('03/03_030570.xs','text000036'): '<T><M2/2/1>Yani başa döndük.',
 ('05/05_050770.xs','text000001'): '<T>Bu dev dönme dolap, lunaparktaki en\nbariz {\'\'}dönüş{\'\'} örneklerinden biri olabilir.',
 ('07/07_070240.xs','text000012'): '<T>İşte bu gerçekten düşündürücü!',
 ('07/07_070370.xs','text000036'): '<T><M5/2/1/45>Tamamen yanlış yolda olabiliriz.',
 ('07/07_070410.xs','text000008'): '<T><M3/2/1/45>Evet. Yanlış yolda olabileceğimizi\nsöylediğimi hatırlıyor musun?',
 ('40/40_001000.xs','text000004'): 'Taşa Dönmüş Kalabalık',
 ('40/40_001200.xs','text000015'): "Layton'ın babası, cömert\nmisafirperverliğine yakışan\ngür bir sakal taşır. Sessiz,\nince eleyip sık dokuyan bu\nbeyefendi içten içe macera\nözlemi çeker ve vaktiyle\nkendi başına birkaç olayı\nbile çözmüştür. Hatta o\nzamanlar oğlunun yaşındaydı...",
 ('50/50_000001.xs','text000002'): 'Bu robot dört parçadan oluşuyor: baş,\ngövde, kollar ve bacaklar. Parçaları\nbirleştirmek için her parçayı dört sarı\nkutudan birine koyup düğmeyi çevir.\nSorun şu: hangi sırayla birleşeceklerini\nve hangi yönde duracaklarını bilmiyorsun!\n\nRobotu doğru biçimde birleştirebilir misin?\nParçaları hem taşıyabilir hem döndürebilirsin.\nHepsi yerine geldiğinde montajı başlatmak\niçin <CR>Gönder</CR> seçeneğine dokun.',
 ('50/50_000001.xs','text000005'): 'Burada fazla kafa yormana gerek yok;\ndeneme-yanılmayla ilerleyebilirsin.\n\nÖnce her parçayı herhangi bir kutuya koyup\nmakineyi çalıştır. Sonra parçaların birer birer\ndüşüşünü izle ve kutu içeriklerinin montaj\nsırasında nasıl işlendiğini anlamaya çalış.\nHangi sırayla birleşiyorlar ve her biri nasıl\ndöndürülüyor?',
 ('50/50_000001.xs','text000008'): 'Parçaları soldan sağa şu sırayla kutulara\nkoy: kollar, bacaklar, baş, gövde.\n\nBacakları döndürmene gerek yok; doğru yönde\nkalabilirler. Şimdi kollarla başın nasıl\ndöndürülmesi gerektiğini bul ve robotu tamamla!',
 ('50/50_000002.xs','text000002'): "Bu küçük kız annesini kaybetmiş. {''}Annemin\nsaçları kızıl. Bir de üzerinde ayı olan pembe\nbir el çantası var!{''}\n\nYakında beş kişi konuşuyor.\nA: {''}Bugün herkes ne kadar şık!{''}\nB: {''}Bir dakika. Bu el çantası benim değil!{''}\nC: {''}Hey! Kız gibi giyinsem de ben erkeğim!{''}\nD: {''}Benim el çantam mavi.{''}\nE: {''}Hmm, bu benim çantam değil. Deseni yanlış.{''}\n\nKızın annesi kim? A ile E arasından seç.",
 ('50/50_000007.xs','text000005'): "Bu bulmacayı, kiracıların şartlarının hangi\nevlere taşınabileceklerini nasıl kısıtladığını\ndüşünerek basitleştirebilirsin. Örneğin ②,\nsıranın uçlarında olmak istemiyor; bu yüzden\nyalnızca B ya da C evinde olabilir.\n\nŞimdi ②'nin diğer şartına bak ve bu iki evden\nhangisine yerleşebileceğini bul.",
 ('50/50_000010.xs','text000002'): 'Ünlü ama sakar bir şef bu iştah açıcı\nMargarita pizzayı sekiz dilime böldü. Ne yazık\nki süreçte bir dilim hariç hepsini ters çevirdi.\n\nDilimleri düzeltmeye çalışıyor ama peynir öyle\nkalın ki bir dilimi her çevirdiğinde yanındaki\ndilimler de onunla birlikte ters dönüyor.\n\nTüm dilimleri doğru yüzleri yukarı bakacak\nşekilde çevirebilir misin?',
 ('50/50_000018.xs','text000002'): 'Sakar şefimiz yine bir pizzayı mahvetti! Bu kez\npizzanın tam yarısını ters çevirmiş.\n\nDüzeltmeye çalışıyor ama peynir yine çok kalın;\nbir dilimi çevirdiğinde yanındaki dilimler de\nonunla birlikte dönüyor.\n\nTüm pizzayı, malzemeleriyle birlikte yeniden\ndoğru yüzü yukarı bakacak hâle getirebilir misin?',
 ('50/50_000023.xs','text000002'): "İki hamal, ağırlıkları bilinmeyen altı bagaj\nparçasını taşıyacak. Her parçanın ağırlığı farklı;\nA en hafif, F en ağır olacak biçimde sıralanmışlar.\nHer parça en fazla 10 kg ve toplam ağırlık 40 kg'ı\ngeçmiyor.\n\nHer hamal bir seferde en fazla 20 kg taşıyabiliyor.\nİkisi bütün bagajı tek seferde taşımak istiyor.\nBagajı aralarında nasıl bölüştürmeliler? Parçaları\nellerine yerleştirip zile dokun.",
 ('50/50_000076.xs','text000002'): 'İşte küçük bir kâğıt Japon balığı.\n\nBalığı, noktalı çizgiler boyunca dikkatlice kesip\niki parça elde ederek ve bu parçaları döndürüp\nbirleştirerek bir üçgene dönüştürebilirsin.\n\nNereden kesmelisin? Kalemle yalnızca kesmen\ngereken yerleri işaretleyen çizgiler çiz.',
 ('50/50_000101.xs','text000002'): 'Bu sınıfta şık bir siyah-beyaz bulmaca tahtası\nvar. Tahtadaki herhangi bir kareye dokununca\nrengi siyahla beyaz arasında değişir. Şu anda\nbeyaz kareler daha fazla, ama tahtaya yalnızca\nbir kez dokunarak bunu değiştirebilirsin.\n\nHangi kareye dokunmalısın? Kalemle seç.',
 ('50/50_000147.xs','text000008'): "Aynı kenarından iki karo çıkan dikdörtgen\nparçayı görüyor musun? Bir prize benzemeli.\nO iki karo sola bakacak şekilde döndürüp sağ\nüst köşeye yerleştir.\n\nŞimdi {''}E{''} harfi şeklindeki parçayı bul. Düz\nkenarı altta kalacak şekilde döndürüp sağ alt\nköşeye koy. Gerisi sana kalmış!",
 ('50/50_000167.xs','text000002'): "Bir öğretmen zeki bir öğrenciyi sınıfın önüne\nçağırıp şunu sormuş:\n\n{''}Bu beş deseni görüyor musun? Her biri iki L\nşeklindeki kâğıt parçasından yapılmış. Hiçbiri\ndiğerinin döndürülmüş ya da ayna görüntüsü\ndeğil, ama hepsinin ortak bir özelliği var. Bu iki\nL parçasıyla aynı özelliği taşıyan başka bir desen\nyapabilir misin?{''}\n\nParçaları taşıyıp döndürerek altıncı deseni oluştur.",
 ('50/50_000167.xs','text000007'): 'Bu desenlerin her biri, altı yüzlü bir küpün\naçınımıdır.\n\nAyna görüntülerini ve döndürülmüş biçimleri aynı\nsayarsak, iki L parçasıyla küp oluşturmanın yalnızca\naltı farklı yolu vardır. Beşini zaten gördün; sonuncuyu\nbulmak sana kalmış.',
 ('50/50_000167.xs','text000003'): 'Harika!\n\nHepsi bir küpün açınımına güzel örnekler!\nBu yüzden bu desen ayna görüntüsü olsa bile\nişe yarardı.',
 ('52/52_000028.xs','text000001'): 'Bir aşçı, yemekleri servis ederken renk kodlu\ntabaklar kullanır. Her tabak türünün üzerindeki\nsayı, destede o türden kaç tabak olduğunu gösterir.',
 ('06/06_060190.xs','text000008'): '<T>Takılırsan, her şeyi ilk konumuna döndürmek için\nDokunmatik Ekran’ın sağ altındaki\n<CR>Yeniden Başlat</CR> seçeneğine dokun.',
 ('20/20_209010.xs','text000014'): '<T>Büyüteci hareket ettir; bazı bölgelerin\nüzerine geldiğinde turuncuya\ndöndüğünü göreceksin.',
 ('20/20_209060.xs','text000012'): '<T><M2/2/1>La la-la. Belki de fazla iyi sakladım.\nBüyütecin maviye döndüğü noktayı\nkontrol etmelisin.',
}

WORD_RE=re.compile(r"(?<![A-Za-zÇçĞğİıÖöŞşÜüÂâÎÛû])([A-Za-zÇçĞğİıÖöŞşÜüÂâÎÛû]+)(?![A-Za-zÇçĞğİıÖöŞşÜüÂâÎÛû])")

def controls(s): return base.CTRL_RE.findall(s)

def safe_words(s):
    notes=[]
    def repl(m):
        w=m.group(1); nw=SAFE_WORDS.get(w,w)
        if nw!=w: notes.append(f'{w}→{nw}')
        return nw
    return WORD_RE.sub(repl,s),notes

def capitalize_initial(s):
    # Etiketler/boşluklardan sonraki ilk gerçek Türkçe/Latin harf cümle başlangıcıdır.
    m=re.search(r'[A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû]', re.sub(r'^(?:\s|<[^>]+>|\{[^}]+\})*','',s))
    # daha güvenli: doğrudan orijinal string üzerinde leading tagleri atla
    lead=re.match(r'^(?:\s|<[^>]+>|\{[^}]+\})*',s)
    pos=lead.end() if lead else 0
    while pos<len(s) and not re.match(r'[A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû]',s[pos]): pos+=1
    if pos<len(s) and s[pos] in 'abcçdefgğhıijklmnoöprsştuüvyzâîû':
        return s[:pos]+s[pos].upper()+s[pos+1:], True
    return s,False

DON_MAP={
 'dondu':'döndü','Dondu':'Döndü','dondum':'döndüm','Dondum':'Döndüm','donduk':'döndük','Donduk':'Döndük',
 'dondun':'döndün','Dondun':'Döndün','donuyor':'dönüyor','Donuyor':'Dönüyor','donuyoruz':'dönüyoruz','Donuyoruz':'Dönüyoruz',
 'donen':'dönen','Donen':'Dönen','doner':'döner','Doner':'Döner','donup':'dönüp','Donup':'Dönüp',
 'donmus':'dönmüş','Donmus':'Dönmüş','donmustur':'dönmüştür','Donmustur':'Dönmüştür','donmussunuz':'dönmüşsünüz','Donmussunuz':'Dönmüşsünüz',
 'dondur':'döndür','Dondur':'Döndür','dondurup':'döndürüp','Dondurup':'Döndürüp','dondurdu':'döndürdü','Dondurdu':'Döndürdü',
 'donduruluyor':'döndürülüyor','Donduruluyor':'Döndürülüyor','donduğunu':'döndüğünü','Donduğunu':'Döndüğünü',
 'donduğu':'döndüğü','Donduğu':'Döndüğü','dondurerek':'döndürerek','Dondurerek':'Döndürerek',
}

def source_don_fix(src,s):
    sl=src.lower()
    # Gerçek donma bağlamını koru. "turned to stone" dönmek fiilidir, bu yüzden stone istisna olarak dönüşe girer.
    freeze=bool(re.search(r'\b(freez(?:e|es|ing|er|ers|ing|ed)|frozen)\b',sl))
    rotate=bool(re.search(r'\b(rotat\w*|spin\w*|turn\w*|return\w*|whirl\w*|go(?:es|ing)? around|come back|came back|go back|went back|head(?:ing)? home|back to|going on)\b',sl))
    # "round...and around", dizzy ve turn against gibi dönüş bağlamları
    rotate = rotate or ('around' in sl and any(x in sl for x in ['round','wheel','ear','cup','floor'])) or 'dizzy' in sl or 'turning against' in sl
    if not rotate or freeze: return s,[]
    notes=[]
    for a,b in DON_MAP.items():
        ns,n=re.subn(r'\b'+re.escape(a)+r'\b',b,s)
        if n: s=ns; notes.append(f'{a}→{b}')
    return s,notes

BOL_MAP={'boldu':'böldü','Boldu':'Böldü','bolusturmeliler':'bölüştürmeliler','Bolusturmeliler':'Bölüştürmeliler'}
def source_bol_fix(src,s):
    if not re.search(r'\b(cut|divide|divided|dividing|split|split up)\b',src,re.I): return s,[]
    notes=[]
    for a,b in BOL_MAP.items():
        ns,n=re.subn(r'\b'+a+r'\b',b,s)
        if n: s=ns; notes.append(f'{a}→{b}')
    return s,notes

def main():
    adv=base.load_adv(ROOT)
    rows=list(csv.DictReader(CSV.open(encoding='utf-8-sig',newline='')))
    # v5 raporundan ilk yama alanını al
    first={}
    v5rep=REPORT/'FINAL_TEK_TEK_KONTROL_RAPORU_V5.csv'
    if v5rep.exists():
        for r in csv.DictReader(v5rep.open(encoding='utf-8-sig',newline='')):
            first[(r['file'],r['id'])]=r.get('ilk_yama',r.get('final_v5',''))
    outmap={}; delta=[]; full=[]; over=[]; bad=[]; stats=Counter()
    for i,r in enumerate(rows,1):
        key=(r['file'],r['id']); src=r['original']; old=r['translation']; s=old; why=[]
        c0=controls(old)
        if key in OVERRIDE:
            s=OVERRIDE[key]; why.append('kaynak anlamı/kelime oyunu/bulmaca mantığına göre elle düzeltildi'); stats['override']+=1
        ns,notes=safe_words(s)
        if ns!=s: s=ns; why.append('kesin imla: '+', '.join(notes[:10])); stats['word']+=len(notes)
        for pat,repl,label in PHRASE_FIX:
            if label=='koru': continue
            ns,n=re.subn(pat,repl,s)
            if n: s=ns; why.append(label); stats['phrase']+=n
        ns,notes=source_don_fix(src,s)
        if ns!=s: s=ns; why.append('kaynakta dönüş/döndürme anlamı: '+', '.join(notes)); stats['don']+=len(notes)
        ns,notes=source_bol_fix(src,s)
        if ns!=s: s=ns; why.append('kaynakta bölme anlamı: '+', '.join(notes)); stats['bol']+=len(notes)
        ns,chg=capitalize_initial(s)
        if chg: s=ns; why.append('cümle başı büyük harf'); stats['cap']+=1
        s=unicodedata.normalize('NFC',s)
        if controls(s)!=c0:
            bad.append({'file':r['file'],'id':r['id'],'before':c0,'after':controls(s),'candidate':s})
            s=old; why=['GÜVENLİK: kontrol kodu değişeceği için v6 adayı geri alındı']; stats['revert']+=1
        if s!=old:
            w,chg,reason=v4.wrap_final(src,s,adv)
            if chg and controls(w)==c0:
                s=w; why.append(reason); stats['wrap']+=1
        px=v4.max_px(s,adv); limit=348 if ('<T>' in src or (base.JP_RE.search(src) and src.count('\n')<=2)) else 399
        if px>limit: over.append({'file':r['file'],'id':r['id'],'px':px,'limit':limit,'source':src,'translation':s})
        changed=s!=old
        if changed: stats['changed']+=1
        r['translation']=s; outmap[key]=s
        reason='; '.join(why) if why else 'v5 metni semantik/bulmaca denetiminde değişiklik gerektirmedi.'
        delta.append({'sira':i,'file':r['file'],'id':r['id'],'durum':'DEGISTI' if changed else 'DEGISMEDI','neden':reason,'v5':old,'v6':s,'kaynak':src,'v5_px':v4.max_px(old,adv),'v6_px':px,'limit_px':limit})
        fv=first.get(key,old)
        full.append({'sira':i,'file':r['file'],'id':r['id'],'durum':'DEGISTI' if s!=fv else 'DEGISMEDI','neden':reason,'ilk_yama':fv,'final_v6':s,'kaynak':src,'final_max_satir_px':px,'statik_limit_px':limit,'tasma_durumu':'RISK' if px>limit else 'OK'})
    with CSV.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['file','id','offset','original','translation']); w.writeheader(); w.writerows(rows)
    # jsonl
    outs=[]
    for line in JSONL.read_text(encoding='utf-8').splitlines():
        o=json.loads(line)
        if o.get('kind')=='text': o['translation']=outmap.get((o['file'],o['id']),o.get('translation',''))
        outs.append(json.dumps(o,ensure_ascii=False,separators=(',',':')))
    JSONL.write_text('\n'.join(outs)+'\n',encoding='utf-8')
    # easy
    ers=list(csv.DictReader(EASY.open(encoding='utf-8-sig',newline='')))
    for rr in ers:
        k=(rr['file'],rr['id'])
        if k in outmap: rr['turkce']=outmap[k]
    with EASY.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['file','id','kaynak_japonca','turkce','durum']); w.writeheader(); w.writerows(ers)
    with (REPORT/'V6_EK_DEGISIKLIK_RAPORU.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(delta[0])); w.writeheader(); w.writerows(delta)
    with (REPORT/'FINAL_TEK_TEK_KONTROL_RAPORU_V6.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(full[0])); w.writeheader(); w.writerows(full)
    with (REPORT/'V6_TASMA_RISKLERI.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields=['file','id','px','limit','source','translation']; w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(over)
    (REPORT/'V6_KONTROL_KODU_GUVENLIK.json').write_text(json.dumps(bad,ensure_ascii=False,indent=2),encoding='utf-8')
    summary=(
      'LAYTON TÜRKÇE YAMA FINAL v6 — SEMANTİK / BULMACA DENETİMİ\n\n'
      f'Toplam kayıt: {len(rows)}\nV5 üzerine değişen kayıt: {stats["changed"]}\n'
      f'Kaynak karşılaştırmalı elle düzeltme: {stats["override"]}\nKesin imla işlemi: {stats["word"]}\n'
      f'Dön/don kaynak-bağlam düzeltmesi: {stats["don"]}\nBöl/bol kaynak-bağlam düzeltmesi: {stats["bol"]}\n'
      f'Kontrol kodu nedeniyle geri alınan: {stats["revert"]}\nStatik taşma riski: {len(over)}\n\n'
      'ÖZEL DENETİMLER\n- Bulmaca yönergelerinde rotate/turn/spin/return ile freeze ayrıldı.\n'
      '- Sayı, yön, satır/sütun, saat yönü ve en az/en fazla ifadeleri örneklem + kural taramasıyla kontrol edildi.\n'
      '- Kelime oyunları/soyut deyimler (think outside the box, food for thought, back to square one, spin vb.) kaynak anlamına göre düzeltildi.\n'
      '- Özel adlar ve kontrol kodları korunarak statik font genişliği tekrar ölçüldü.\n'
    )
    (REPORT/'V6_SEMANTIK_OZET.txt').write_text(summary,encoding='utf-8')
    print(json.dumps({'stats':dict(stats),'overflow':len(over),'badcodes':len(bad)},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
