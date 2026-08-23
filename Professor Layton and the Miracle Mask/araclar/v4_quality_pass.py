#!/usr/bin/env python3
from __future__ import annotations
import csv, json, re, ctypes, math, unicodedata
from pathlib import Path
from collections import Counter, defaultdict
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'araclar'))
import tr_iyilestir as base

WORD_RE=re.compile(r"[A-Za-zÇçĞğİıÖöŞşÜüÂâÎîÛû]+(?:'[A-Za-zÇçĞğİıÖöŞşÜüÂâÎîÛû]+)?")
LATIN_WORD_RE=re.compile(r"[A-Za-zÇçĞğİıÖöŞşÜüÂâÎîÛû]+")
JP_RE=re.compile(r'[\u3040-\u30ff\u3400-\u9fff]')

PROPER=set(x.lower() for x in base.PROPER_BASES) | {
    x.lower() for x in '''
Luke Layton Randall Henry Hershel Angela Emmy Dalston Ledore Tingly Beaufort Yukkles Ludmilla Stellar Grosky Gloria Mordaunt Alphonse Norwell Descole Murphy Hannibal Aldus Sharoa Saroa Sheffield Scotland Youngland Bloom Lionel Jean Roland Lucille Akbadain Ascot Bunny Randy Hersh Waltham Collins StreetPass Reunion Touch SD
Nuden Gonzales Dandleman Bonnie Peachy Montsarton Stansbury Monte London Chatea u Chateau Remi Stachenscarfen Alphonse Alphonse
'''.split()
}

# TDD Hunspell sözlüğü. Sadece aynı ASCII katlamasına sahip, tek ve geçerli
# Türkçe varyant bulunduğunda otomatik düzeltme yapıyoruz.
LIB='/lib/x86_64-linux-gnu/libhunspell-1.7.so.0'
DIC=Path('/mnt/data/tr_TR.dic')
AFF=Path('/mnt/data/tr_TR.aff')
lib=ctypes.CDLL(LIB)
lib.Hunspell_create.argtypes=[ctypes.c_char_p,ctypes.c_char_p];lib.Hunspell_create.restype=ctypes.c_void_p
lib.Hunspell_spell.argtypes=[ctypes.c_void_p,ctypes.c_char_p];lib.Hunspell_spell.restype=ctypes.c_int
lib.Hunspell_destroy.argtypes=[ctypes.c_void_p]
H=lib.Hunspell_create(str(AFF).encode(),str(DIC).encode())
SPELL_CACHE={}
VAR_CACHE={}
TO_TR={'c':'ç','g':'ğ','i':'ı','o':'ö','s':'ş','u':'ü','C':'Ç','G':'Ğ','I':'İ','O':'Ö','S':'Ş','U':'Ü'}

def spell_ok(w:str)->bool:
    v=SPELL_CACHE.get(w)
    if v is None:
        v=bool(lib.Hunspell_spell(H,w.encode('utf-8')))
        SPELL_CACHE[w]=v
    return v

def unique_diacritic_variant(w:str)->str|None:
    if w in VAR_CACHE:return VAR_CACHE[w]
    if len(w)<=1 or spell_ok(w):
        VAR_CACHE[w]=None; return None
    pos=[(i,TO_TR[ch]) for i,ch in enumerate(w) if ch in TO_TR]
    if not pos or len(pos)>10:
        VAR_CACHE[w]=None; return None
    good=[]
    for mask in range(1,1<<len(pos)):
        a=list(w)
        for j,(i,r) in enumerate(pos):
            if mask>>j & 1:a[i]=r
        cand=''.join(a)
        if spell_ok(cand):
            good.append(cand)
            if len(good)>1:
                VAR_CACHE[w]=None; return None
    VAR_CACHE[w]=good[0] if good else None
    return VAR_CACHE[w]

def source_has_exact_token(source:str, tok:str)->bool:
    return bool(re.search(r'(?<![A-Za-z])'+re.escape(tok)+r'(?![A-Za-z])',source))

def spell_fix_text(source:str,text:str)->tuple[str,int,list[tuple[str,str]]]:
    n=0; pairs=[]
    def fix_word(word:str)->str:
        nonlocal n
        # Apostrof sonrası Türkçe ekleri ayrıca düzelt; tabanı özel ad olarak koru.
        if "'" in word:
            b,s=word.split("'",1)
            nb=b
            if b.lower() not in PROPER and not source_has_exact_token(source,b):
                v=unique_diacritic_variant(b)
                if v: nb=v
            vs=unique_diacritic_variant(s)
            ns=vs or s
            out=nb+"'"+ns
            if out!=word:n+=1;pairs.append((word,out))
            return out
        if word.lower() in PROPER:return word
        # Kaynak İngilizcede aynı token birebir varsa ad/UI/terim olma ihtimali yüksek.
        if source_has_exact_token(source,word):return word
        v=unique_diacritic_variant(word)
        if v:
            n+=1;pairs.append((word,v));return v
        return word
    def repl(m):return fix_word(m.group(0))
    return unicodedata.normalize('NFC',WORD_RE.sub(repl,text)),n,pairs

# Kaynağa bakılarak çözülen, sözlükçe iki biçimi de geçerli olabilen sözcükler.
def semantic_context_fix(source:str,text:str)->tuple[str,int,list[str]]:
    s=text; n=0; notes=[]; sl=source.lower()
    def sub(pat,repl,label,flags=re.I):
        nonlocal s,n
        s2,c=re.subn(pat,repl,s,flags=flags)
        if c:n+=c;notes.append(f'{label} ({c})');s=s2
    # Eski otomatik kuralın anlamsal hatası: costume -> koştum.
    if re.search(r'\bcostume(?:s)?\b',sl):
        sub(r'\b[Kk]oştum\b',lambda m:'Kostüm' if m.group(0)[0].isupper() else 'kostüm','costume→kostüm')
    # Masked Gentleman için yanlış "Mucize Beyefendi" kullanımı.
    if 'masked gentleman' in sl:
        sub(r'\bMucize Beyefendi\b','Maskeli Beyefendi','Masked Gentleman terimi')
    # Şu / su ayrımı.
    waterish=bool(re.search(r'\b(water|liquid|drink|fountain|river|lake|sea|pool|wet)\b',sl)) or bool(re.search(r'[水泉湖川海]',source))
    demonstrative=bool(re.search(r'\b(this|that|these|those|look at|over there|here is|here are|there is|there are|such)\b',sl)) or bool(re.search(r'(この|その|あの|これ|それ|あれ|こちら|そちら|あちら|向こう)',source))
    if demonstrative and not waterish:
        sub(r'\bSu\b','Şu','su/şu bağlamı')
        sub(r'\bsu\b','şu','su/şu bağlamı')
    for a,b in [
        (r'\bsu an\b','şu an'),(r'\bsu anda\b','şu anda'),(r'\bsu ana kadar\b','şu ana kadar'),
        (r'\bsu şekilde\b','şu şekilde'),(r'\bsu noktada\b','şu noktada')]:
        sub(a,b,'kalıp su→şu')
    # taş / tas ayrımı.
    if re.search(r'\b(stone|stones|rock|rocks|statue|statues|petrif|turned to stone)\b',sl) or re.search(r'[石岩像]',source):
        sub(r'\bTas\b','Taş','tas→taş')
        sub(r'\btas\b','taş','tas→taş')
        sub(r'\bTasa\b','Taşa','tasa→taşa')
        sub(r'\btasa\b','taşa','tasa→taşa')
    # tür / tur ayrımı.
    if re.search(r'\b(kind|type|sort|species|variety)\b',sl) or re.search(r'(種類|種別)',source):
        sub(r'\bTur\b','Tür','tur→tür');sub(r'\btur\b','tür','tur→tür')
    # sakin / sakın ayrımı.
    if re.search(r"\b(don't|do not|never|mustn't|must not)\b",sl):
        sub(r'\bSakin\b','Sakın','sakin→sakın');sub(r'\bsakin\b','sakın','sakin→sakın')
    elif re.search(r'\b(calm|quiet|peaceful|tranquil|oasis)\b',sl):
        # burada sakin zaten doğru; önceki yanlış "sakın" oluşmuşsa geri çevir.
        sub(r'\bSakın\b','Sakin','sakın→sakin');sub(r'\bsakın\b','sakin','sakın→sakin')
    # sık / şık ve türevleri.
    sub(r'\bSikint','Sıkınt','sıkıntı kökü'); sub(r'\bsikint','sıkınt','sıkıntı kökü')
    sub(r'\bSikist','Sıkışt','sıkış kökü'); sub(r'\bsikist','sıkışt','sıkış kökü')
    sub(r'\bSikil','Sıkıl','sıkıl kökü'); sub(r'\bsikil','sıkıl','sıkıl kökü')
    sub(r'\bSikici','Sıkıcı','sıkıcı'); sub(r'\bsikici','sıkıcı','sıkıcı')
    sub(r'\bSikica\b','Sıkıca','sıkıca'); sub(r'\bsikica\b','sıkıca','sıkıca')
    if re.search(r'\b(elegant|fancy|stylish|chic|fine)\b',sl):
        sub(r'\bSik\b','Şık','sık/şık bağlamı');sub(r'\bsik\b','şık','sık/şık bağlamı')
    elif re.search(r'\b(often|frequent|frequently|tight|tightly|regularly)\b',sl):
        sub(r'\bSik\b','Sık','sık/şık bağlamı');sub(r'\bsik\b','sık','sık/şık bağlamı')
    # kör/kor, şok/sok, ölüm/olum, ön/on gibi iki geçerli biçimli sözcükler.
    if re.search(r'\bblind\b',sl):sub(r'\bKor\b','Kör','kor→kör');sub(r'\bkor\b','kör','kor→kör')
    if re.search(r'\bshock(?:ed|ing)?\b',sl):
        sub(r'\bSok\b','Şok','sok→şok');sub(r'\bsok\b','şok','sok→şok');sub(r'\bSoktu\b','Şoktu','soktu→şoktu');sub(r'\bsoktu\b','şoktu','soktu→şoktu')
    if re.search(r'\b(death|dead|died|die|dying)\b',sl):
        sub(r'\bOlum\b','Ölüm','olum→ölüm');sub(r'\bolum\b','ölüm','olum→ölüm')
    if re.search(r'\bfront\b',sl):
        sub(r'\bOn kap','Ön kap','ön kapı');sub(r'\bon kap','ön kap','ön kapı')
        sub(r'\bOn taraf','Ön taraf','ön taraf');sub(r'\bon taraf','ön taraf','ön taraf')
    # Yaygın kabul edilen ama ASCII kalmış kalıplar.
    sub(r'\bHimm\b','Hımm','ünlem');sub(r'\bhimm\b','hımm','ünlem')
    sub(r'\bHih\b','Hıh','ünlem');sub(r'\bhih\b','hıh','ünlem')
    sub(r'\bPekala\b','Pekâlâ','imla');sub(r'\bpekala\b','pekâlâ','imla')
    sub(r'\b[Yy]egane\b',lambda m:'Yegâne' if m.group(0)[0].isupper() else 'yegâne','yegâne')
    sub(r'\b[Iİiı]se yar',lambda m:('İşe yar' if m.group(0)[0].isupper() else 'işe yar'),'işe yarar kalıbı')
    sub(r'\b[Gg]uc(?=[uüıi]?(?:n|m|y|d|l|s|\b))',lambda m:'Güc' if m.group(0)[0].isupper() else 'güc','güç kökü')
    sub(r'\b[Iİiı]htiyaçimiz\b',lambda m:'İhtiyacımız' if m.group(0)[0].isupper() else 'ihtiyacımız','ihtiyacımız')
    sub(r'\b[Mm]eydani\b',lambda m:'Meydanı' if m.group(0)[0].isupper() else 'meydanı','meydanı')
    sub(r'\b[Kk]isilik\b',lambda m:'Kişilik' if m.group(0)[0].isupper() else 'kişilik','kişilik')
    sub(r'\b[Kk]isinin\b',lambda m:'Kişinin' if m.group(0)[0].isupper() else 'kişinin','kişinin')
    sub(r'\b[Dd]urust\b',lambda m:'Dürüst' if m.group(0)[0].isupper() else 'dürüst','dürüst')
    sub(r'\b[Ss]oyluyorlar\b',lambda m:'Söylüyorlar' if m.group(0)[0].isupper() else 'söylüyorlar','söylüyorlar')
    sub(r'\b[Cc]ıkarin\b',lambda m:'Çıkarın' if m.group(0)[0].isupper() else 'çıkarın','çıkarın')
    sub(r'\b[Yy]asima\b',lambda m:'Yaşıma' if m.group(0)[0].isupper() else 'yaşıma','yaşıma')
    sub(r'\b[Aa]zranlarin\b',lambda m:'Azranların' if m.group(0)[0].isupper() else 'azranların','Azranların')
    sub(r'\b[Bb]asim(?= (?:fena )?derde)',lambda m:'Başım' if m.group(0)[0].isupper() else 'başım','başım derde kalıbı')
    sub(r'\b[Dd]alston[’\']in\b',lambda m:"Dalston'ın" if m.group(0)[0].isupper() else "dalston'ın",'Dalston iyelik eki')
    if re.search(r'\b(business|businesses|work|job|jobs)\b',sl):
        sub(r'\b[Iİiı]sleri\b',lambda m:'İşleri' if m.group(0)[0].isupper() else 'işleri','işleri')
    return unicodedata.normalize('NFC',s),n,notes


def post_context_fix(source:str,text:str)->tuple[str,int,list[str]]:
    """İlk güvenli geçişin özellikle iki geçerli sözlük biçimi yüzünden bıraktığı
    ASCII Türkçe kalıntılarını, kök ve kaynak bağlamı ile temizler."""
    s=text; n=0; notes=[]; sl=source.lower()
    def sub(pat,repl,label,flags=re.I):
        nonlocal s,n
        s2,c=re.subn(pat,repl,s,flags=flags)
        if c:
            s=s2;n+=c;notes.append(f'{label} ({c})')
    def cap(word,lo):
        return lo[:1].upper()+lo[1:] if word[:1].isupper() else lo

    # Kökü/biçimi Türkçede açık olan yaygın ASCII kalıntıları.
    exact_pairs={
      'olustur':'oluştur','vahsi':'vahşi','sandik':'sandık','uclu':'üçlü','buyutec':'büyüteç',
      'ilginc':'ilginç','ogrenci':'öğrenci','savas':'savaş','sans':'şans','durust':'dürüst',
      'yasarmis':'yaşarmış','yasardik':'yaşardık','yasadik':'yaşadık','yasandi':'yaşandı',
      'yasandiği':'yaşandığı','yasadiginiz':'yaşadığınız','yasinda':'yaşında','yasi':'yaşı',
      'kilic':'kılıç','kopegi':'köpeği','kopek':'köpek','kosedeki':'köşedeki','kosede':'köşede',
      'kose':'köşe','sakli':'saklı','bolum':'bölüm','bolume':'bölüme','bolumde':'bölümde',
      'siranin':'sıranın','sıranin':'sıranın','batisinda':'batısında','bulunmasi':'bulunması',
      'bulmasinda':'bulmasında','konuşmasi':'konuşması','olmasini':'olmasını','sayısini':'sayısını',
      'baslamayi':'başlamayı','baslatiyoruz':'başlatıyoruz','baslasin':'başlasın','basladim':'başladım',
      'basladin':'başladın','basardin':'başardın','basardiniz':'başardınız','basari':'başarı',
      'kostu':'koştu','dusmus':'düşmüş','dustu':'düştü','dustuk':'düştük','dusuyor':'düşüyor',
      'dusurdu':'düşürdü','dusurmek':'düşürmek','dusunce':'düşünce','dusun':'düşün',
      'ustalik':'ustalık','Yasasin':'Yaşasın','yasasin':'yaşasın','Ilginc':'İlginç','Ince':'İnce',
      'Insani':'İnsanı','insani':'insanı','Sansimiz':'Şansımız','sansimiz':'şansımız',
      'sansim':'şansım','sansima':'şansıma','sansimi':'şansımı','sansimizin':'şansımızın',
      'arabasi':'arabası','arabasini':'arabasını','karisinin':'karısının','kurbani':'kurbanı',
      'takimim':'takımım','masasinda':'masasında','canin':'canın','samanlikta':'samanlıkta',
      'repertuvarinizdayken':'repertuvarınızdayken','masalarinizi':'masalarınızı','saclarin':'saçların',
      'tasindim':'taşındım','girmis':'girmiş','kurmus':'kurmuş','onlugun':'önlüğün',
      'asit':'asit',
    }
    # Uzun sözcüklerden önce: tam sözcük değişimleri.
    for a,b in sorted(exact_pairs.items(),key=lambda kv:-len(kv[0])):
        sub(r'\b'+re.escape(a)+r'\b',lambda m,b=b: cap(m.group(0),b),f'{a}→{b}')

    # Üretken ve güvenli kök düzeltmeleri.
    sub(r'\b([Bb])asla(?=[a-zçğıöşüâîû]*)',lambda m:'Başla' if m.group(1)=='B' else 'başla','başla- kökü')
    sub(r'\b([Kk])isi(?=(?:yi|nin|ler|lere|leri|lerden|lik|liğ|siniz|dir|yd|ym|yle)\b)',lambda m:'Kişi' if m.group(1)=='K' else 'kişi','kişi kökü')
    sub(r'\b([Bb])asim(iz|iza|izi|izda|izdan|in|i|a)?\b',lambda m:('Başım' if m.group(1)=='B' else 'başım')+(m.group(2) or '').replace('iza','ıza').replace('izi','ızı').replace('izda','ızda').replace('izdan','ızdan'),'başım/başımız kökü')
    sub(r'\b([Bb])asin(dan|a|i|in)\b',lambda m:('Başın' if m.group(1)=='B' else 'başın')+{'dan':'dan','a':'a','i':'ı','in':'ın'}[m.group(2)],'başın kökü')
    sub(r'\b([Gg])uce\b',lambda m:'Güce' if m.group(1)=='G' else 'güce','güce')
    sub(r'\b([Gg])ucu\b',lambda m:'Gücü' if m.group(1)=='G' else 'gücü','gücü')
    sub(r'\b([Gg])ucunu\b',lambda m:'Gücünü' if m.group(1)=='G' else 'gücünü','gücünü')
    sub(r'\b([Gg])ucunun\b',lambda m:'Gücünün' if m.group(1)=='G' else 'gücünün','gücünün')
    sub(r'\b([Gg])ucler',lambda m:'Güçler' if m.group(1)=='G' else 'güçler','güçler')
    sub(r'\b([Ss])utun',lambda m:'Sütun' if m.group(1)=='S' else 'sütun','sütun kökü')
    sub(r'\b([Kk])ose',lambda m:'Köşe' if m.group(1)=='K' else 'köşe','köşe kökü')
    sub(r'\b([Bb])olum',lambda m:'Bölüm' if m.group(1)=='B' else 'bölüm','bölüm kökü')
    sub(r'\b([Ss])ekil',lambda m:'Şekil' if m.group(1)=='S' else 'şekil','şekil kökü')
    sub(r'\b([Bb])olgel',lambda m:'Bölgel' if m.group(1)=='B' else 'bölgel','bölge kökü')
    sub(r'\b([Oo])lustur',lambda m:'Oluştur' if m.group(1)=='O' else 'oluştur','oluştur kökü')
    sub(r'\b([Vv])ahsi',lambda m:'Vahşi' if m.group(1)=='V' else 'vahşi','vahşi kökü')
    sub(r'\b([Ss])avas',lambda m:'Savaş' if m.group(1)=='S' else 'savaş','savaş kökü')
    sub(r'\b([ŞSs])ans',lambda m:'Şans' if m.group(0)[0].isupper() else 'şans','şans kökü')
    sub(r'\b([Dd])urust',lambda m:'Dürüst' if m.group(1)=='D' else 'dürüst','dürüst kökü')
    sub(r'\b([ÖOo])grenci',lambda m:'Öğrenci' if m.group(0)[0].isupper() else 'öğrenci','öğrenci kökü')
    sub(r'\b([Kk])ilic',lambda m:'Kılıç' if m.group(1)=='K' else 'kılıç','kılıç kökü')
    sub(r'\b([Bb])uyutec',lambda m:'Büyüteç' if m.group(1)=='B' else 'büyüteç','büyüteç')

    # "yarıs-" (half) ile "yarış-" (race) kaynak bağlamından ayrılır.
    if re.search(r'\b(half|halves)\b',sl) or re.search(r'(半分|半数)',source):
        sub(r'\b([Yy])aris',lambda m:'Yarıs' if m.group(1)=='Y' else 'yarıs','yarısı bağlamı')
    elif re.search(r'\b(race|racing|racecourse|racetrack|chariot|contest)\b',sl) or re.search(r'(競走|競馬|レース|戦車)',source):
        sub(r'\b([Yy])aris',lambda m:'Yarış' if m.group(1)=='Y' else 'yarış','yarış bağlamı')

    # taş/tas: taşlaşma, kaya ve bulmaca karoları kaynakta açıksa taş.
    if re.search(r'\b(stone|rock|tile|slab|block|petrif|statue|boulder|piece)\b',sl) or re.search(r'[石岩像]',source):
        sub(r'\b([Tt])as(?=[a-zçğıöşüâîû]*)',lambda m:'Taş' if m.group(1)=='T' else 'taş','taş bağlamı')

    # tür/tur: cins/tip anlamı, ayrıca doğal Türkçe kalıpları.
    if re.search(r'\b(kind|type|sort|species|variety|category|what kind|all kinds)\b',sl) or re.search(r'(種類|種別)',source):
        sub(r'\b([Tt])ur\b',lambda m:'Tür' if m.group(1)=='T' else 'tür','tür bağlamı')
    sub(r'\b([Hh])er tur\b',lambda m:('Her tür' if m.group(1)=='H' else 'her tür'),'her tür')
    sub(r'\b([Nn])e tur\b',lambda m:('Ne tür' if m.group(1)=='N' else 'ne tür'),'ne tür')
    sub(r'\b([Bb])u tur (?!(?:daha|attır|at|tur))',lambda m:('Bu tür ' if m.group(1)=='B' else 'bu tür '),'bu tür')

    # su/şu: gösterme kalıpları; su mandası/su kaynağı gibi gerçek su ifadelerine dokunma.
    for pat in [r'\bsu an\b',r'\bsu anda\b',r'\bsu anki\b',r'\bsu izlenim',r'\bsu erkek',r'\bsu küçük',r'\bsu delikanlı',r'\bsu suç',r'\bsu mucize',r'\bsu zırval',r'\biyi kısmı su\b']:
        sub(pat,lambda m:m.group(0).replace('su','şu').replace('Su','Şu'),'şu kalıbı')
    sub(r'\bSu(?=\.\.\.\s*su Kaos)', 'Şu','şu Kaos')
    sub(r'(?<=\.\.\.\s)su(?= Kaos)', 'şu','şu Kaos')

    # şık/sık: stil bağlamı ve kalıp; sıklık kalıplarında "sık".
    if re.search(r'\b(stylish|elegant|fashion|fancy|chic|smart|fine-looking|dress sense|with style)\b',sl):
        sub(r'\b([Ss])ik\b',lambda m:'Şık' if m.group(1)=='S' else 'şık','şık bağlamı')
    sub(r'\bsik (?=(?:bir )?(?:takım|takim|yer|otel|hava|şapka|bot|kravat|mozaik|oyuncak|bey|beyler))', 'şık ','şık isim kalıbı')
    sub(r'\bSik (?=(?:Kravat|Bot|Şapka))','Şık ','şık başlık')
    sub(r'\bsik dokuyan\b','sık dokuyan','sık dokumak')
    sub(r'\bsik uğran','sık uğran','sık uğranmak')

    # süre: oyunda süre/zaman anlamındaki yaygın çekimler.
    if re.search(r'\b(time|duration|while|soon|shortly|long|minute|hour|second|week|month|year)\b',sl):
        sub(r'\b([Ss])ure(?=(?:de|den|dir|si|sini|sinin|yle|li|siz|\b))',lambda m:'Süre' if m.group(1)=='S' else 'süre','süre bağlamı')

    # Doğrudan kalıp düzeltmeleri.
    sub(r'\bic acici\b','iç açıcı','iç açıcı')
    sub(r'\bİc acici\b','İç açıcı','iç açıcı')
    sub(r'\btek basima\b','tek başıma','tek başıma')
    sub(r'\bkendi basima\b','kendi başıma','kendi başıma')
    sub(r'\bkendi basimiza\b','kendi başımıza','kendi başımıza')
    sub(r'\baklimi basimda\b','aklımı başımda','aklımı başımda')
    sub(r'\bAklimizi basimizda\b','Aklımızı başımızda','aklımızı başımızda')
    sub(r'\bbaşimi dondur', 'başımı döndür','başımı döndürmek')
    sub(r'\bBasimi dondur', 'Başımı döndür','başımı döndürmek')
    sub(r'\btaslas', 'taşlaş','taşlaşma')
    sub(r'\bTaslas', 'Taşlaş','taşlaşma')
    # İlk kök düzeltmesinden sonra kalan karışık 'güc...' çekimleri.
    for a,b in {
      'gücunu':'gücünü','gücuyle':'gücüyle','gücunun':'gücünün','gücune':'gücüne',
      'gücun':'gücün','gücunle':'gücünle','gücumu':'gücümü','gücunde':'gücünde',
      'gücumuze':'gücümüze','gücume':'gücüme','gücunuz':'gücünüz'
    }.items():
        sub(r'\b'+a+r'\b',b,'güç çekimi')
    sub(r'\bkisiligi\b','kişiliği','kişiliği')
    sub(r'\bKisiligi\b','Kişiliği','kişiliği')
    # düş- fiilinin ASCII kalan çekimleri (yalın \"dus\" sözcüğüne dokunma; duş ile karışabilir).
    sub(r'\b([Dd])us(?=[a-zçğıöşüâîû]+)',lambda m:'Düş' if m.group(1)=='D' else 'düş','düş- kökü')
    # Gösterme sıfatı/kalıbı olduğu açık olan kalan şu örnekleri.
    for pat in [r'\bSu at iz',r'\bSu canlı',r'\bSu dey',r'\bSu ana kadar',r'\bSu tatlı',r'\bSu dedikodu',r'\bSu saçma',
                r'\bsu saçma',r'\bsu delikanlı',r'\bsu ayak takım',r'\bsu hissi',r'\bsu anahtarı']:
        sub(pat,lambda m:m.group(0).replace('Su','Şu').replace('su','şu'),'şu gösterme kalıbı')
    # Şık/sık için kalan açık kalıplar.
    sub(r'\bsik sik\b','sık sık','sık sık')
    sub(r'\bSik sik\b','Sık sık','sık sık')
    sub(r'\bsik (?=(?:bir şekilde|bir <CR>şapka|mozai|otel|hizmet))','şık ','şık kalıbı')
    sub(r'\bçok sik\b','çok şık','çok şık')
    sub(r'\bdaha sik\b','daha şık','daha şık')
    # Tür/tur için tur=round anlamına gelmeyen açık kalıplar.
    sub(r'\bbu tur numara','bu tür numara','bu tür numara')
    sub(r'\bbir tur alegori','bir tür alegori','bir tür alegori')
    sub(r'\bbir tur kontrol mekanizması','bir tür kontrol mekanizması','bir tür kontrol')
    # Yarış/yarısı için Türkçe çevrenin anlamı tekilleştirdiği kalan örnekler.
    sub(r'\byolun yarisindayiz\b','yolun yarısındayız','yarısındayız')
    sub(r'\bdaha yarisina\b','daha yarısına','yarısına')
    sub(r'\bgece yarisini\b','gece yarısını','gece yarısı')
    sub(r'\bAt yarisini\b','At yarışını','at yarışı')
    sub(r'\büçüncülük yarisini\b','üçüncülük yarışını','yarış')
    # Sık görülen ek/ünlü uyumu kalıntıları.
    for a,b in {
      'Insan':'İnsan','Insanı':'İnsanı','insanı':'insanı','üstu':'üstü',
      'Baligin':'Balığın','baligin':'balığın','Baligi':'Balığı','baligi':'balığı',
      'sırasi':'sırası','sırasini':'sırasını','sırasiyla':'sırasıyla','sırasina':'sırasına','Sırayi':'Sırayı',
      'soyleyeyim':'söyleyeyim','soyleme':'söyleme','sakladiği':'sakladığı','sakladiğini':'sakladığını',
      'yasiyor':'yaşıyor','olustur':'oluştur','olusur':'oluşur','olusuyor':'oluşuyor','olasilik':'olasılık',
      'kosu':'koşu','basli':'başlı','basliyor':'başlıyor','basliyoruz':'başlıyoruz','basardi':'başardı','basardik':'başardık',
      'kizil':'kızıl','cilginca':'çılgınca','sayısiz':'sayısız','satirlar':'satırlar','sasirmis':'şaşırmış','sasirdim':'şaşırdım',
      'koymus':'koymuş','olmasinin':'olmasının','olmasi':'olması','bulmasi':'bulması','çıkmasi':'çıkması','almasi':'alması',
      'disini':'dışını','olmustur':'olmuştur','gecince':'geçince','sandim':'sandım','Dolayisiyla':'Dolayısıyla',
      'sacli':'saçlı','ziyaretci':'ziyaretçi','yasindaki':'yaşındaki','igrenc':'iğrenç','icerisi':'içerisi','kapisi':'kapısı',
      'çıkisin':'çıkışın','acisindan':'açısından','acidan':'açıdan','salina':'salına'
    }.items():
        sub(r'\b'+re.escape(a)+r'\b',b,'yaygın çekim/imla')
    sub(r'\bsalına salına\b','salına salına','salına salına')
    sub(r'\bafis asiyorum\b','afiş asıyorum','afiş asıyorum')
    sub(r'\bAsiyorum\b','Asıyorum','asmak')
    sub(r'\basiyorum\b','asıyorum','asmak')
    if re.search(r'\b(love|loves|loved|in love|sweetheart)\b',sl):
        sub(r'\b([Aa])sik\b',lambda m:'Âşık' if m.group(1)=='A' else 'âşık','âşık')
    if re.search(r'\b(corncob|corn cob|ear of corn)\b',sl):
        sub(r'\b([Kk])ocanin\b',lambda m:'Koçanın' if m.group(1)=='K' else 'koçanın','koçan')
    # donmuş/dönmüş ve olmuş/ölmüş kaynak anlamına göre ayrılır.
    if re.search(r'\b(return|returned|returning|back home|go back|come back)\b',sl):
        sub(r'\b([Dd])onmus\b',lambda m:'Dönmüş' if m.group(1)=='D' else 'dönmüş','dönmüş')
    elif re.search(r'\b(frozen|freeze|froze|ice)\b',sl):
        sub(r'\b([Dd])onmus\b',lambda m:'Donmuş' if m.group(1)=='D' else 'donmuş','donmuş')
    if re.search(r'\b(died|dead|death|killed)\b',sl):
        sub(r'\b([Oo])lmustu\b',lambda m:'Ölmüştü' if m.group(1)=='O' else 'ölmüştü','ölmüştü')
    else:
        sub(r'\b([Oo])lmustu\b',lambda m:'Olmuştu' if m.group(1)=='O' else 'olmuştu','olmuştu')
    # yarısı/yarışı karışık ünlü eki.
    if re.search(r'\b(half|halves|midnight|halfway)\b',sl):
        sub(r'\b([Yy])arısini\b',lambda m:'Yarısını' if m.group(1)=='Y' else 'yarısını','yarısını')
    elif re.search(r'\b(race|racing|racecourse|contest)\b',sl):
        sub(r'\b([Yy])arısini\b',lambda m:'Yarışını' if m.group(1)=='Y' else 'yarışını','yarışını')
    # döndürülmüş/dondurulmuş kaynak fiiline göre.
    if re.search(r'\b(rotate|rotated|turn(?:ed)?|rotation)\b',sl):
        sub(r'\bDondurulmus\b','Döndürülmüş','döndürülmüş')
        sub(r'\bdondurulmus\b','döndürülmüş','döndürülmüş')
    return unicodedata.normalize('NFC',s),n,notes

VOWELS='aeıioöuüâîû'
def tr_lower(s):return base.tr_lower(s)
def last_vowel(w):
    for c in reversed(tr_lower(w)):
        if c in VOWELS:return c
    return ''

def q_base(prev):
    v=last_vowel(prev)
    if v in 'aıâ':return 'mı'
    if v in 'eiî':return 'mi'
    if v in 'ouû':return 'mu'
    if v in 'öü':return 'mü'
    return 'mi'

def harmonize_tail(basev,shape):
    # shape soru ekinden sonraki sessiz iskelet; aşağıdaki sınıflar oyunda görülen biçimlerdir.
    v={'mi':'i','mı':'ı','mu':'u','mü':'ü'}[basev]
    forms={
      '':'', 'sin':'s'+v+'n', 'siniz':'s'+v+'n'+v+'z',
      'yim':'y'+v+'m','yiz':'y'+v+'z',
      'ydi':'yd'+v,'ydin':'yd'+v+'n','ydiniz':'yd'+v+'n'+v+'z',
      'ymis':'ym'+v+'ş','ymisin':'ym'+v+'ş'+v+'n','ymisiniz':'ym'+v+'ş'+v+'n'+v+'z',
      'yse':'yse','yken':'yken'
    }
    return basev+forms.get(shape,'')

# Ham soru eki biçimlerini sessiz iskelete indir.
Q_FORMS={}
for stem in ['mi','mı','mu','mü']:
    for raw,shape in [('', ''),('sin','sin'),('sın','sin'),('sun','sin'),('sün','sin'),
                      ('siniz','siniz'),('sınız','siniz'),('sunuz','siniz'),('sünüz','siniz'),
                      ('yim','yim'),('yım','yim'),('yum','yim'),('yüm','yim'),
                      ('yiz','yiz'),('yız','yiz'),('yuz','yiz'),('yüz','yiz'),
                      ('ydi','ydi'),('ydı','ydi'),('ydu','ydi'),('ydü','ydi'),
                      ('ydin','ydin'),('ydın','ydin'),('ydun','ydin'),('ydün','ydin'),
                      ('ydiniz','ydiniz'),('ydınız','ydiniz'),('ydunuz','ydiniz'),('ydünüz','ydiniz')]:
        Q_FORMS[stem+raw]=shape

def question_fix(text:str)->tuple[str,int]:
    n=0
    pat=re.compile(r"([A-Za-zÇçĞğİıÖöŞşÜüÂâÎîÛû]+)(\s+)(m[ıiuü](?:s[ıiuü]n(?:[ıiuü]z)?|y[ıiuü]m|y[ıiuü]z|yd[ıiuü](?:n(?:[ıiuü]z)?)?)?)\b",re.I)
    def repl(m):
        nonlocal n
        raw=m.group(3); key=tr_lower(raw)
        shape=Q_FORMS.get(key)
        if shape is None:return m.group(0)
        nb=q_base(m.group(1)); new=harmonize_tail(nb,shape)
        if raw[:1].isupper():new=base.turkish_title(new)
        if new!=raw:n+=1
        return m.group(1)+m.group(2)+new
    return pat.sub(repl,text),n

# Taşma ve anlam için elle yeniden yazılmış yüksek etkili kayıtlar.
MANUAL={
('01/01_010053.xs','text000005'): '<T>Ah, az kalsın unutuyordum! Dünyayı artık\nayrıntılı görmek istemezseniz, normale dönmek için\n<CR>Zoom Out</CR> seçeneğine dokunun!',
('01/01_010195.xs','text000013'): '<T>Anlıyorum! Bay Ledore bu kaos yüzünden\nbaşını kaşıyacak vakit bulamıyor. Bu kadar az uykuyla\nayakta kalması mucize; kelime oyunumu bağışlayın.',
('02/02_020230.xs','text000015'): '<T>Pff, sanırım Ascot sana Bulmaca Hastalığı\nbulaştırmış. Umursamıyorsun gibi yapıyorsun ama\naslında hoşuna gidiyor. Senin de, Angela’nın da.',
('03/03_030260.xs','text000001'): '<T>Ahh! <W>Siyaha asla bahis yapma. ASLA!\nNe zaman öğreneceğim?<W> Görünüşe göre bu hafta\nyine fasulye ve tost yiyeceğim...',
('03/03_030560.xs','text000014'): '<T>Hıh, öyle olduğunu düşünmek isterim.\nBulmaca çözecek kadar zekiyim sanıyordum ama\nbunda tıkandım. Yardım eder misin?',
('05/05_050590.xs','text000008'): '<T><M1/1/1>Muhasebeci olduğumu biliyorsunuzdur, değil mi?<W30>\nHayır mı?<W30> Ben Murphy; Bay Dalston ile Ledore’ların\nmuhasebesini tutarım.',
('06/06_067020.xs','text000008'): '<T>Ah, şu sinir bozucu mumyalar! Etkinleşince\nsen hareket ettikçe onlar da hareket eder.\nHiçbir şey yapmazsan onlar da durur.',
('07/07_071120.xs','text000025'): '<T><M2/1/2>Demek onu hiç bulamamışlar... <W>Bir vahanın\nyanında üs kurduklarını söylüyor; demek ki Monte d’Or\no zamanlar henüz şehir bile değildi.',
('17/17_170110.xs','text000020'): '<T>Merhaba,<W30> iyi akşamlar,<W30> geciktim, özür dilerim!\n<W>Muhasebeyle neşeli bir gece daha, değil mi?\n{\'\'}Tally{\'\'}-ho? Ha ha ha!',
('19/19_190450.xs','text000001'): '<T>Ledore’ların evinde Layton, Henry’yi yine\nkısa ve sert bulur; ayrıca onu bekleyen\nşaşırtıcı bir karşılaşma vardır.',
('20/20_200200.xs','text000002'): '<T><M4/1/1>Doğrusu, şövalyeliğiniz beni gözyaşlarına\nboğdu!<M1/2/1> <W>Hem de gerçekten, <M4/2/1>gözyaşlarım\nyüzümden sel gibi aktı!',
('81/81_000300.xs','text000005'): '<T>Bir ürünü tutarken reyonun bazı bölümleri kararır.\nYa ürün o alana sığmıyordur ya da orada\nonu taşıyacak bir destek yoktur.',
# Günlük/özet ekranlarında kapasiteyi aşan birkaç paragraf aynı anlamı daha kısa veriyor.
('40/40_001000.xs','text000021'): 'Karnaval gece boyunca sürmüş gibi görünüyor; çünkü\nuyandığımızda dinç ve zinde, sokakları yine kalabalık\nbulduk.\n\nDünkü olayları gözden geçirip son gelişmeleri Henry’den\ndinlemek üzere Ledoreların malikanesine yeniden yola\nçıkmaya hazırlandık. Beni bir başka buluşma bekliyor,\nama bu kez pek sıcak karşılanmayacağımızdan\nkorkuyorum.',
('40/40_001000.xs','text000163'): 'Randall son 18 yılda değişmiş. Kaybolmuş ve\nsavunmasızken, Henry ile Stansbury’nin akıbeti hakkında\nduyduğu acımasız söylentilere inanmak dışında pek\nseçeneği yoktu; öfkesini anlamak zor değil.\n\nYaptıklarını kolayca bağışlayamam. Yine de ona biraz\nhuzur vermeyi umuyorum. Şehir artık güvende olduğuna\ngöre bildiğim her şeyi anlatacağım; umarım\nyanılgılarını tamamen giderebilirim.',
('40/40_001000.xs','text000169'): 'Bu kez Randall’ı kurtarmayı başardım. Yalnızca\naltımızda açılan yarıktan değil, 18 yıl önce düştüğü\nderin duygusal uçurumdan da. Monte d’Or gerçekten bir\nmucizeler şehri; dostların, aradaki uçurum ne kadar\nbüyük olursa olsun, yeniden buluştuğu bir yer. Randall\nkayıp yıllarını geride bırakıp hayata yeniden\nbaşlayabilir.\n\nLondra’ya dönünce Monte d’Or’daki eski dostlarıma\nyazmak için sabırsızlanıyorum. Onlara çok şey\nborçluyum; özellikle de beni arkeolojiyle tanıştırdıkları için!',
('40/40_001010.xs','text000005'): 'Bay Collins’in dersleri genelde keyiflidir ve bir\nöğretmene göre epey rahattır. Peki Randall neden hep\naraya girip karmaşık sorular soruyor? Geri kalanımız\noturup onu dinlemek zorunda kalıyoruz. Keşke bazen\nbiraz daha az budala olsa.\n\nBugün öğleden sonra antrenmanı kısa keseceğiz; ona\ndersini vermem gelecek haftayı bulacak. Belki de\nonunla eve kadar yarışırım.',
('40/40_001010.xs','text000057'): 'Stansbury’ye dönünce Angela’nın ya da Henry’nin\ngözlerinin içine bakamadım. Suçlulukla eve kapandım.\nAnneyle baba beni karşılamaya geldi; hayatımın en sert\nazarını çekip ardından sımsıkı sarıldılar. Şimdi yeniden\nokuldayım ama her şey Randall’ı hatırlatıyor. Göğsümde\nkocaman bir boşluk varmış gibi hissediyorum.\n\nRandall’ı harabelerde aramak için ekip gönderdiler,\nama uçurum çok derindi... Böyle bir düşüşten biri sağ\nçıkabilir mi?',
('40/40_001100.xs','text000063'): 'Henry’nin Monte d’Or’daki malikanesini koruyup\ngenişletmesinin nedeni, Randall döndüğünde her şeyin\nkusursuz olmasını istemesiydi.',
}

# Statik genişlik taramasında kalan kayıtlar: anlam korunarak daha kısa/doğal yazım.
# Bu tablo mevcut MANUAL girdilerini de bilinçli olarak geçersiz kılabilir.
MANUAL.update({
('00/00_000020.xs','text000016'): '<T><M2/1/1>Sanırım. Etrafa bakmak için kalemi Dokunmatik\nEkranda kaydırıp <M1/1/1>incelemek istediğimiz yere\nkısaca dokunacağız, öyle mi?',
('01/01_010050.xs','text000001'): '<T><M4/1/1>Yine karşılaştık, dostlarım! Kader bizi yine\nbuluşturdu, değil mi? <W>Bu geceki karnaval\nne kadar heyecanlı!',
('01/01_010195.xs','text000013'): '<T>Anlıyorum! Bay Ledore kaos yüzünden çok meşgul.\nBu kadar az uykuyla ayakta kalması mucize;\nkelime oyunumu mazur görün.',
('01/01_010320.xs','text000004'): "<T><M2/1/1/80>Ahh, tahmin edeyim. Monte d'Or'a ilk gelişiniz,\ndeğil mi? <W>Merhaba! Ben Juggles, mahallenin\nsevimli palyaçosu. Ya siz?",
('01/01_010320.xs','text000013'): "<T>Şu büyük taş levhayı görüyor musunuz? Ünlü\nanıtımız o. Monte d'Or'un tüm tarihi üzerinde!\n<W30>Fotoğraf çekmek için de harika!",
('01/01_010335.xs','text000009'): '<T><M2/1/1>Sen mi?<W> Sıradan bir çocuk, sirk müdürü olarak\nbenim bile eğitemediğim şu umutsuz hayvanlardan\nbirini eğitebileceğini mi sanıyor?',
('01/01_010370.xs','text000013'): "<T><M5/2/1/45>Gerçek Kaos Maskesi'yle uğraştığımızdan bile\nşüpheliyim. <W>O maskenin yıllar önce bir\nuçuruma düştüğünü gördüm.",
('02/02_020030.xs','text000007'): '<T><M1/2/1>Pompitous, farklı alanlardan pek çok kanıta\ndayanarak bu medeniyet hakkında kökten yeni\nfikirler ortaya attı.',
('02/02_020230.xs','text000015'): '<T>Pff, sanırım Ascot sana Bulmaca Hastalığı\nbulaştırmış. Umursamaz görünüyorsun ama aslında\nhoşuna gidiyor. Angela’nın da öyle.',
('03/03_030260.xs','text000016'): '<T>Önce haftalığımı kaybettim, şimdi de şu aptal\nmucizeler hakkında elimdeki tek işe yarar\nbilgiden vazgeçmem gerekecek...',
('03/03_030410.xs','text000010'): "<T><M3/1/2>Ben de yapabilir miyim acaba... Belki büyüyünce\nbelediye başkanı olurum! 'Başkan Luke Triton'\nkulağa nasıl geliyor?",
('03/03_030470.xs','text000006'): 'Bu olayın anahtarı, kendine Maskeli Beyefendi\ndiyen suçlunun şehirde yarattığı tuhaf olayların\nhilelerini çözmekte yatıyor.',
('03/03_030492.xs','text000012'): '<T>Teşekkürler. Her zamanki gibi şehrimizi koruyoruz.\n<W>Yardım için süslü bir Scotland Yard\nbürokratına ihtiyacımız yok.',
('03/03_030581.xs','text000004'): '<T>Ay ay ay! Hangi çıkartmanın oraya geleceğini\nbulamazsam öyle paniklerim ki çalışamam!\nSonra da başım fena derde girer!',
('03/03_030585.xs','text000004'): '<T><M2/1/1>Güzel sanattan anlamıyor musunuz? Kusursuz\nburnuma, muhteşem çeneme... ve şu zahmetsiz\nsırıtışıma bakın! Aha!',
('04/04_040175.xs','text000008'): '<T><M2/2/2>Keyfini çıkarın çocuklar. Söyleyeceğim tek şey bu.\nBenim yaşıma gelince her şey kural ve\nsorumluluktan ibaret oluyor.',
('05/05_050110.xs','text000001'): '<T>Alphonse Dalston tutuklanmış. Ruhsatsız mucize\nyapıyormuş, diyorlar. Zaten hep şüpheli biri\nolduğunu düşünürdüm.',
('05/05_050210.xs','text000001'): '<T>Merhaba, Layton! Vay be! Planı kuranın en\ndürüst vatandaşlarımızdan biri olacağını kim\ndüşünürdü? Dünya tuhaf.',
('05/05_050300.xs','text000003'): '<T><M2/2/1>Bay Dalston bir hipodromdan söz etti;\nbaşmüfettiş de müdürle konuştuğunu ve hiçbir\nşeyin eksik olmadığını söyledi.',
('05/05_050330.xs','text000005'): '<T><M2/1/1>Memnuniyetle yardım ederim, efendim. Ancak bir\nşartım var: <M3/1/1>yakın zamanda hazırladığım\nbir bulmacayı çözmelisiniz.',
('05/05_050340.xs','text000003'): '<T><M5/2/1>Suçlunun sıradan araba yerine atlı yarış arabası\nseçmesini anlıyorum. Sağlam görünüyorlar;\nağır yük taşımaya uygunlar.',
('05/05_050630.xs','text000067'): "<T><M2/1/1>Ustaca arabuluculuktu efendim. Bay Ledore'un\nbüyüyen dertlerine bir de tek kişilik kumarhane\nisyanı eklemek istemezdim.",
('06/06_060140.xs','text000007'): '<T>Yine de tek başıma olsam takılırdım. İki kişi\nolduğumuz için şanslıyız! <W><M4/2/2>Belki bu da ekip\nçalışmasını kullanmamızı hatırlatıyor.',
('06/06_068010.xs','text000004'): '<T>Bu harabelerin keşfini dünyaya duyurunca,\nistediğin gibi bir arkeolog olarak çarpıcı bir\nçıkış yapacaksın.',
('07/07_070180.xs','text000004'): "<T>Tembel bir pazar sabahı yatakta Eggs Benevolent\nyerken hizmetkârlarımın bana 'mistremoiselle'\ndediğini hayal etmeyi severim.",
('07/07_070210.xs','text000001'): '<T>Annem kaybolursam nerede bekleyeceğimi söyledi.\nBen de bunu biraz...<W30>dolaşmama...<W30>izin var\ndiye anladım.',
('07/07_070480.xs','text000014'): '<T><M3/1/1>Senden şüphelendiğim için özür dilerim, Dalston.\nDikkatli olmalıydım ama Hannibal kısa sürede\nmasum olduğuna beni ikna etti.',
('07/07_071060.xs','text000004'): "<T><M1/1/1>Aynen öyle! Ah, hiç söylemedim, değil mi? <W>Bay\nLedore'a karşı birçok görevimin yanında bu otelin\nmüdürlüğünü de yapıyorum.",
('07/07_071070.xs','text000002'): "<T>Monte d'Or'un en büyük oteliyiz; en çok oda da\nbizde. Yönünüzü bulmak için yardıma ihtiyacınız\nolursa sormanız yeter.",
('07/07_071120.xs','text000018'): '<T>Şimdilik şansımız yok ama Henry Ledore’un var.\nSöylentiye göre burada altın bulmuş! Hem de\ngözleri fal taşı gibi açtıracak kadar büyük\nbir hazine yığını.',
('07/07_071120.xs','text000025'): "<T><M2/1/2>Demek onu hiç bulamamışlar... <W>Bir vahanın yanında\nüs kurduklarından söz ediyor. Demek ki Monte d'Or\no zamanlar henüz şehir değildi.",
('07/07_071160.xs','text000004'): '<T>Yakındaki tabelada {\'\'}Cesur maceracı, beni\nalabilirsin!{\'\'} yazısını gören arkadaşlar hazineyi\naldılar ve eşitçe paylaştılar.',
('07/07_071250.xs','text000001'): '<T>Bir varmış bir yokmuş, hareketli bir kasabada\nçok fakir bir adam yaşarmış.\n\nKasabalılar çok iyi kalpliymiş. Adamın adı sanı\nolmasa da hiçbir şeyden mahrum kalmamasını\nsağlarlarmış.',
('08/08_080020.xs','text000033'): "<V0300><T><M2/1/1>Planımın her aşaması yerine oturdukça, <L3.05>ben de\ngeri döndüğümü hissediyordum. <L5.65>Beni hayata\ndöndüren Maskeli Beyefendi'ydi.</V>",
('09/09_092070.xs','text000006'): '<T><M2/2/1>Evet, haklısın.<W> Ben sadece onun hayalini\ngerçekleştirmek istiyorum, baba. O yapamaz...\nAma ben doğru şekilde yapmak istiyorum.',
('20/20_020920.xs','text000005'): '<T><M3/2/1>Hem de çok heyecanlı! Sıradan sihirbazlık\nnumaralarından bambaşka. Kıyaslanamaz bile;\naralarında dağlar kadar fark var.',
('20/20_020930.xs','text000005'): '<T><M3/2/1>Hem de çok heyecanlı! Sıradan sihirbazlık\nnumaralarından bambaşka. Kıyaslanamaz bile;\naralarında dağlar kadar fark var.',
('20/20_200200.xs','text000001'): '<T><M1/2/1>Yine mi geldiniz efendim? Beni kandıramazsınız.\nGözlerinizdeki bakış, devedikeni arayan aç\nbir eşeğinki gibi.',
('20/20_200200.xs','text000027'): '<T>Aman! Daha önce yeterince açık olmadıysam özür\ndilerim ama bayrakları toplamanız gerekiyor;\nonlardan kaçınmanız değil!',
('40/40_001000.xs','text000009'): "Her zamanki gibi öğüt vermeye hevesli eski bir dostla\nkarşılaştıktan sonra çadıra devam ettik. Festival\nartıkları arasında perişan bir palyaço balonu gördük;\nkendi hâline ağlıyor gibiydi. Oysa ses, panikte annesini\nkaybeden ve yardım isteyen genç bir kızdan geliyordu.\nAnneyle çocuk kavuşunca Ledore malikanesine doğru\nyola çıktık. Yolda bir sanat galerisinin önünden geçtik,\nama önceki bir olay yüzünden kapalıydı: Maskeli\nBeyefendi'nin bir başka mucizesi.",
('40/40_001000.xs','text000011'): "Yerleşim bölgesine giderken başımızdan epey macera\ngeçti. Emmy'ye sevimli, el yapımı bir kurmalı robot\nhediye edildi; bize saatlerce eğlence sağlayacaktır.\n\nLedore arazisinin kapılarına yaklaşırken sokakta\nsevimsiz bir tip yolumuzu kesti. İkinci bir adam\ntartışmayı yatıştırmak için araya girdi, ama ikisinin\nortak çalıştığından kuvvetle şüpheleniyorum. Demek ki\nyalnız Maskeli Beyefendi'ye karşı değil, başka\ntehlikelere karşı da dikkatli olmalıyız.",
('40/40_001000.xs','text000037'): "Müfettiş Grosky ve saygın Dedektif Bloom, Maskeli\nBeyefendi davasında yerel Başmüfettiş Sheffield'a\nyardım için Scotland Yard'dan gelmişler.\n\nBelediye başkanı iki müfettiş arasında eski bir\nhusumetten söz etmişti; Sheffield ile Bloom'un arası\ngerçekten gergin görünüyor. Yine de sorunlarını bir\nkenara bırakabilirlerse görev gücünün olumlu sonuçlar\nvereceğine inanıyorum. Birazdan strateji toplantılarına\nkatılacağım.",
('40/40_001000.xs','text000095'): "Tingly Tower'a çıkmak üzereyken Henry ile Angela gelip\nBeyefendi'yi yakalamamıza yardım teklif etti. Kısa bir\nkonuşmadan sonra kuleye bizimle gelmeye karar verdiler.\nHenry gerçekten endişeli görünüyor, ama Angela'nın da\nkendini tehlikeye atmasına izin vermesi ona pek\nbenzemez...\n\nHer neyse, vaktimiz kalmadı. Beyefendi Tingly Town'un\nelektriğini kesmeden onu durdurmalıyız!",
('40/40_001000.xs','text000099'): "Maskeli Beyefendi elimizden kaçtı ve sonraki mucizesinin\nşehrin her yerinden görüleceğini söyleyen uğursuz bir\nduyuru bıraktı. Ölçeği benzeri görülmemiş olmalı!\n\nLunapark kalabalığı yeniden belirdiğinde çok rahatladık;\naz önce tamamen yok olduklarından haberleri bile yoktu.\nŞimdiye dek Beyefendi'nin tüm mucizelerinin birer numara\nolduğunu gösterdik. Peki bunu nasıl açıklayacağız?",
('40/40_001000.xs','text000105'): "Ch{^a}teau Dalston'a vardığımızda Maskeli Beyefendi'nin\nTingly Town'da görüldüğü söylentileri hızla yayılmıştı.\nDalston tamamen aklanmış değil, ama polis şimdilik gerçek\nMaskeli Beyefendi'yi yakalamaya odaklanacak.\n\nDalston doğal olarak bu işe bozuldu, ama elinden geldiğince\nbize destek olmayı kabul etti. Aslında ona minnettarız;\ndün geceki mucizeyi çözmemize farkında olmadan yardım etti.",
('40/40_001000.xs','text000111'): "Tingly Tower'dan ayrılırken mali danışman Murphy yanımıza\ngeldi. Belli ki bir şey anlatmak istiyordu; söyledikleri\ngerçekten önemliydi. Dalston'ın tutuklanmasından beri\nHenry'nin işleri ciddi bir üstünlük elde etmiş.\n\nŞunu düşünmeden edemiyorum: Henry yakın zamanda şehir\nplanlamasına büyük paralar yatırdı. İkinci Tingly Town'u\nyaratan o olabilir mi?",
('40/40_001000.xs','text000169'): "Bu kez Randall'ı kurtardım. Yalnız altımızda açılan\nyarıktan değil, 18 yıl önce düştüğü duygusal uçurumdan\nda. Monte d'Or gerçekten mucizeler şehri; dostları,\naradaki uçurum ne kadar büyük olursa olsun, yeniden\nbuluşturuyor. Randall kayıp yıllarını geride bırakıp\nhayata yeniden başlayabilir.\n\nLondra'ya dönünce Monte d'Or'daki eski dostlarıma\nyazacağım. Onlara çok şey borçluyum; özellikle de beni\narkeolojiyle tanıştırdıkları için!",
('40/40_001010.xs','text000017'): "Randall'ın evine giden yokuşta Angela'yla karşılaştım.\nBabasını uyarmamak için her zamanki gizli girişten geçtik.\nEn son ön kapıyı denediğimizde Bay Ascot, Randall'a bir\nhafta ek çalışma vermişti! Sanki okul ödevleri yetmiyor.\n\nYine de Henry vardığımızda bizi hep bekliyor gibi. Demek\nki sandığımız kadar sessiz değiliz.",
('52/52_000038.xs','text000004'): "Hangi lambaları yakacağını seçince <CR>Gönder</CR>'e dokun.\nÇözüm işe yarıyor mu bak; düzeltilmesi gerekenleri\nkontrol et.",
})



def control_codes(s):return base.CTRL_RE.findall(s)

def wrap_final(source:str,text:str,adv)->tuple[str,bool,str]:
    old=text
    # Diyalog: İngilizce/Japonca kaynakta gözlenen pratik üst sınır 348 px.
    # Kaynak 1-2 satırsa Türkçe daha uzunsa 3 satıra kadar çıkabilir.
    # Her adayda gerçek font advance genişliğini ölçüp sığan en az satır sayısını seç.
    if '<T>' in source or (JP_RE.search(source) and source.count('\n')<=2):
        sp=source.split('\n\n'); tp=text.split('\n\n')
        if len(sp)!=len(tp):return text,False,'paragraf yapısı farklı'
        outs=[]
        for a,b in zip(sp,tp):
            srcn=a.count('\n')+1
            if srcn>=3:
                cand=base.wrap_n_lines(b,srcn,adv)
            else:
                best=None;bestpx=10**9
                for n in range(max(1,srcn),4):
                    c=base.wrap_n_lines(b,n,adv)
                    p=max_px(c,adv)
                    if p<bestpx:best,bestpx=c,p
                    if p<=348:
                        best=c;break
                cand=best
            outs.append(cand)
        text='\n\n'.join(outs)
        return text,text!=old,'diyalog genişliğine göre satır dengeleme'
    # Günlük/yardım metinlerinde kaynak paragraf satır sayısını koru.
    text2,chg,_=base.reflow_like_source(source,text,adv)
    return text2,chg,'kaynak satır sayısına göre dengeleme'


def max_px(text,adv):return max([base.visible_width(x,adv) for x in text.split('\n')] or [0])

def main():
    adv=base.load_adv(ROOT)
    csvp=ROOT/'ceviri'/'layton_tr.csv'
    rows=list(csv.DictReader(csvp.open(encoding='utf-8-sig',newline='')))
    original_v2={ (r['file'],r['id']):r for r in csv.DictReader((ROOT/'raporlar/orijinal_yedek/layton_tr_v2.csv').open(encoding='utf-8-sig',newline='')) }
    # V3 raporundaki gerekçeleri koru.
    v3_reason={}
    v3rp=ROOT/'raporlar'/'V3_TEK_TEK_DEGISIKLIK_RAPORU.csv'
    if v3rp.exists():
        for r in csv.DictReader(v3rp.open(encoding='utf-8-sig',newline='')):
            v3_reason[(r['file'],r['id'])]=(r['durum'],r['neden'])

    key_to_new={}; v4delta=[]; finalreport=[]
    stats=Counter(); unresolved=[]; control_bad=[]
    for idx,r in enumerate(rows,1):
        key=(r['file'],r['id']); source=r['original']; old=r['translation']; s=old; reasons=[]
        oldcodes=control_codes(s)
        if key in MANUAL:
            s=MANUAL[key]; reasons.append('elle anlam/akıcılık ve/veya taşma düzeltmesi');stats['manual']+=1
        s,c,pairs=spell_fix_text(source,s)
        if c: reasons.append(f'Hunspell ile güvenli Türkçe karakter restorasyonu ({c} sözcük)');stats['spell_rows']+=1;stats['spell_tokens']+=c
        s,c,notes=semantic_context_fix(source,s)
        if c: reasons.append('bağlama göre düzeltme: '+', '.join(notes));stats['semantic_rows']+=1;stats['semantic_edits']+=c
        s,c,notes=post_context_fix(source,s)
        if c: reasons.append('ikinci bağlamlı imla geçişi: '+', '.join(notes));stats['post_rows']+=1;stats['post_edits']+=c
        s,c=question_fix(s)
        if c: reasons.append(f'soru eki ünlü uyumu ({c})');stats['question_rows']+=1;stats['question_edits']+=c
        # Kontrol kodlarını bozmadan satırları yeniden dengele.
        s2,chg,why=wrap_final(source,s,adv)
        if chg:
            s=s2;reasons.append(why);stats['rewrap_rows']+=1
        s=unicodedata.normalize('NFC',s)
        newcodes=control_codes(s)
        if oldcodes!=newcodes:
            control_bad.append({'file':r['file'],'id':r['id'],'before':oldcodes,'after':newcodes})
            # Kontrol kodu değişmişse güvenlik için eski metne geri dön.
            s=old;reasons=['GÜVENLİK: kontrol kodu dizisi değişeceği için v4 değişikliği geri alındı'];stats['control_reverted']+=1
        # Taşma statik kontrolü
        px=max_px(s,adv)
        limit=348 if ('<T>' in source or (JP_RE.search(source) and source.count('\n')<=2)) else 399
        if px>limit:
            unresolved.append({'file':r['file'],'id':r['id'],'px':px,'limit':limit,'source':source,'translation':s})
        key_to_new[key]=s
        r['translation']=s
        if s!=old:stats['v4_changed']+=1
        v4delta.append({'sira':idx,'file':r['file'],'id':r['id'],'durum':'DEGISTI' if s!=old else 'DEGISMEDI','neden':'; '.join(reasons) if reasons else 'v3 sonrası ek kontrolde güvenli bir ek değişiklik saptanmadı.','v3':old,'v4':s,'kaynak':source,'v3_max_satir_px':max_px(old,adv),'v4_max_satir_px':px})
        orig=original_v2.get(key,{}).get('translation',old)
        v3d,v3n=v3_reason.get(key,('DEGISMEDI','Önceki turda güvenli değişiklik saptanmadı.'))
        if s!=orig:
            why=[]
            if v3d=='DEGISTI':why.append('v3: '+v3n)
            if reasons:why.append('v4: '+'; '.join(reasons))
            if not why:why=['Son metin, ilk yamadan farklı; önceki iyileştirme korunmuştur.']
            status='DEGISTI'
        else:
            status='DEGISMEDI';why=[v3n if v3d=='DEGISMEDI' else 'Yapılan denemeler son metni ilk sürümle aynı bıraktı.']
        finalreport.append({'sira':idx,'file':r['file'],'id':r['id'],'durum':status,'neden':' | '.join(why),'ilk_yama':orig,'final_v4':s,'kaynak':source,'ilk_max_satir_px':max_px(orig,adv),'final_max_satir_px':px,'statik_limit_px':limit,'tasme_durumu':'RISK' if px>limit else 'OK'})

    if control_bad:
        # Bu, geri alma sonrası bile rapora kaydedilir; final doğrulamada ayrıca sıfır olması beklenir.
        pass
    # CSV ana proje
    with csvp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['file','id','offset','original','translation']);w.writeheader();w.writerows(rows)
    # JSONL ana proje
    jp=ROOT/'ceviri'/'layton_tr.jsonl'; out=[]
    for line in jp.read_text(encoding='utf-8').splitlines():
        o=json.loads(line)
        if o.get('kind')=='text':
            k=(o['file'],o['id']);o['translation']=key_to_new.get(k,o['translation'])
        out.append(json.dumps(o,ensure_ascii=False,separators=(',',':')))
    jp.write_text('\n'.join(out)+'\n',encoding='utf-8')
    # kolay CSV
    kp=ROOT/'ceviri'/'CEVIRI_KOLAY.csv'
    krows=list(csv.DictReader(kp.open(encoding='utf-8-sig',newline='')))
    for rr in krows:
        k=(rr['file'],rr['id'])
        if k in key_to_new:rr['turkce']=key_to_new[k]
    with kp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['file','id','kaynak_japonca','turkce','durum']);w.writeheader();w.writerows(krows)
    # Raporlar
    rp=ROOT/'raporlar'/'V4_EK_DEGISIKLIK_RAPORU.csv'
    with rp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(v4delta[0]));w.writeheader();w.writerows(v4delta)
    frp=ROOT/'raporlar'/'FINAL_TEK_TEK_KONTROL_RAPORU.csv'
    with frp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(finalreport[0]));w.writeheader();w.writerows(finalreport)
    urp=ROOT/'raporlar'/'V4_TASMA_RISKLERI.csv'
    with urp.open('w',encoding='utf-8-sig',newline='') as f:
        fields=['file','id','px','limit','source','translation'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(unresolved)
    crp=ROOT/'raporlar'/'V4_KONTROL_KODU_GUVENLIK.json'
    crp.write_text(json.dumps(control_bad,ensure_ascii=False,indent=2),encoding='utf-8')
    total=len(rows);final_changed=sum(1 for x in finalreport if x['durum']=='DEGISTI')
    summary=ROOT/'raporlar'/'V4_IYILESTIRME_OZETI.txt'
    summary.write_text(
        'LAYTON TÜRKÇE YAMA v4 — KURTARILAN ÇALIŞMA / SON KALİTE GEÇİŞİ\n\n'
        f'Toplam kayıt: {total}\n'
        f'İlk yamaya göre değişen kayıt: {final_changed}\n'
        f'İlk yamaya göre değişmeyen kayıt: {total-final_changed}\n'
        f'v3 üzerine ek değişen kayıt: {stats["v4_changed"]}\n'
        f'Hunspell güvenli karakter restorasyonu: {stats["spell_tokens"]} sözcük / {stats["spell_rows"]} kayıt\n'
        f'Bağlama göre ek düzeltme: {stats["semantic_edits"]} işlem / {stats["semantic_rows"]} kayıt\n'
        f'İkinci bağlamlı imla geçişi: {stats["post_edits"]} işlem / {stats["post_rows"]} kayıt\n'
        f'Soru eki uyumu düzeltmesi: {stats["question_edits"]} işlem / {stats["question_rows"]} kayıt\n'
        f'Elle anlam/akıcılık/taşma düzenlenen kayıt: {stats["manual"]}\n'
        f'Yeniden satır dengelenen kayıt: {stats["rewrap_rows"]}\n'
        f'Kontrol kodu değişimi nedeniyle geri alınan v4 değişikliği: {stats["control_reverted"]}\n'
        f'Statik genişlik kontrolünde kalan risk: {len(unresolved)} kayıt\n\n'
        'FONT\n'
        '- v3 font dosyaları korundu; 18 Türkçe/şapkalı glif doğrulaması zaten başarılıydı.\n'
        '- v4 esas olarak metinlerde kalmış ASCII/yanlış Türkçe harfleri tamamlar.\n\n'
        'YÖNTEM\n'
        '- Her kayıt tek tek satır bazında işlendi ve FINAL_TEK_TEK_KONTROL_RAPORU.csv dosyasına yazıldı.\n'
        '- Otomatik imla düzeltmesinde yalnız mevcut biçim Hunspell tarafından reddedilip, yalnız bir tane aynı ASCII-katlamalı Türkçe biçim kabul edildiğinde değişiklik yapıldı.\n'
        '- su/şu, sık/şık, sakin/sakın, tur/tür, tas/taş gibi iki biçimi de sözlükte geçerli olabilen kelimeler kaynak İngilizce/Japonca bağlama göre ele alındı.\n'
        '- Kontrol kodu dizisi değişen hiçbir v4 metni kabul edilmedi; güvenlik için otomatik geri alındı.\n'
        '- Taşma kontrolü nrm font advance değerleriyle statik piksel hesabına dayanır; gerçek cihaz/emülatör görsel testi yapılamadı.\n',encoding='utf-8')
    print(json.dumps({'stats':stats,'unresolved':len(unresolved),'control_code_attempts_reverted':len(control_bad),'final_changed':final_changed,'reports':[str(rp),str(frp),str(urp),str(summary)]},ensure_ascii=False,default=dict))

if __name__=='__main__':
    try:main()
    finally:lib.Hunspell_destroy(H)
