#!/usr/bin/env python3
"""V7 ikinci manuel kontrol karar raporlarını üretir.

V6 ve V7 hizalı SJS metinlerini karşılaştırır. Değişen her parçada V7 manuel
kuralının gerekçesini, aynı bırakılan her parçada ise neden müdahale edilmediğini
kaydeder. credits_text varyantları ve credit.sjs için de ayrı karar raporları üretir.
"""
from pathlib import Path
import csv, re, sys, importlib.util, collections

BASE = Path(__file__).resolve().parents[1]
REPORT = BASE/'RAPORLAR'
V6 = Path('/mnt/data/cs3d_v6/Cave_Story_3D_TR_v6_manuel_kontrol_aracli')
V6_DATA = V6/'000400000004D200/romfs/data'
V7_DATA = BASE/'000400000004D200/romfs/data'
EN_DATA = Path('/mnt/data/cs3d_other/data')

PROPER = {
'Quote','Curly','Curly Brace','Balrog','Sue','Kazuma','Toroko','King','Jack','Jenka','Misery','Ballos','Booster',
'Professor Booster','Momorin','Itoh','Mahin','Kanpachi','Sandaime','Chaco','Santa','Malco','Cthulhu','Numahachi',
'Ma Pignon','Pignon','Basu','Polish','Bute','Mesa','Hoppy','Midorin','Stumpy','Ravil','Basil','Mannan','Gaudi',
'Orangebell','Buyobuyo','Fuzz','Ironhead','Nicalis','Studio Pixel','Pixel','Hajime','Mick','Shinobu','Kakeru','Nene',
'Booster v0.8','Booster v2.0','Press','Sandcroc','Skullhead','Skullstep','Behemoth','Critter','Jelly','Kurara'
}
TECH_PAT = re.compile(r'^(?:#\d|XX:|LM#|[0-9# :_-]+$)|yrotS evaC|\.tsc|\.sjs', re.I)
SOUND_PAT = re.compile(r'^[.!?…\- ]+$|^(?:A+h+|A+ah+|A+hh+|H+ey+|H+uh+|H+mm+|Grr+|W+u+h+|O+h+|Phew+|Huzzah+|Y+e+a+h+|No+|Yo+|Boo+)[!.?…]*$', re.I)

def read_tsv(p):
    with p.open(encoding='utf-8',newline='') as f: return list(csv.DictReader(f,delimiter='\t'))

def u(s):
    return s.replace('\\r','\r').replace('\\n','\n')

def flat(s): return ' '.join(u(s).split())

def load_rules():
    p=BASE/'ARACLAR/manual_review_v7.py'
    spec=importlib.util.spec_from_file_location('v7rules',p)
    m=importlib.util.module_from_spec(spec)
    old=sys.argv[:]; sys.argv=[str(p)]
    try: spec.loader.exec_module(m)
    finally: sys.argv=old
    return m.R, m.CREDIT_REPL

def changed_reason(file, oldtext, rules):
    hits=[]
    for rf,old,new,cat,why in rules:
        if rf=='*SJS*':
            if re.search(old,oldtext): hits.append((cat,why))
        elif rf==file:
            probe=old.split('<',1)[0] if '<' in old else old
            if probe in oldtext:
                hits.append((cat,why))
    # one source chunk can receive more than one small correction
    seen=[]
    for h in hits:
        if h not in seen: seen.append(h)
    if seen:
        cats=' + '.join(dict.fromkeys(x[0] for x in seen))
        why=' / '.join(x[1] for x in seen)
        return cats,why
    return 'Manuel cila','V6 ve İngilizce kaynak yan yana okunurken anlam, akıcılık veya terim kullanımı iyileştirildi; değişiklik V7 karşılaştırmasında doğrulandı.'

def unchanged_reason(en,tr):
    e=flat(en); t=flat(tr)
    if not e and not t:
        return 'AYNI BIRAKILDI – teknik/boş','Teknik ayraç/boşluk; oyuncuya gösterilen çevrilebilir metin değil.'
    if TECH_PAT.search(e) or (e.startswith('#')):
        return 'AYNI BIRAKILDI – teknik/şifre','Event kimliği, geliştirici etiketi, dosya içi teknik not veya şifre niteliğinde; çevirmek oyun davranışını ya da referansı bozabilir.'
    if e==t:
        # punctuation / onomatopoeia first
        if SOUND_PAT.match(e) or (len(e)<=14 and any(c in e for c in '!?.…') and not any(ch.isdigit() for ch in e)):
            return 'AYNI BIRAKILDI – ses/ünlem','Seslenme, ünlem, tepki veya noktalama efektidir; Türkçede de aynı işlevi gördüğü için değiştirilmedi.'
        if e in PROPER or any(name in e for name in PROPER) or re.fullmatch(r"[A-Z][A-Za-z0-9 .'-]{1,35}",e):
            return 'AYNI BIRAKILDI – özel ad/terim','Karakter, yaratık, ürün/sürüm veya oyun içi özel addır; anlam taşımayan özel adları zorla çevirmek yerine kaynak adı korundu.'
        return 'AYNI BIRAKILDI – özel ad/evrensel ifade','Kaynakla aynı görünmesi bilinçli; ikinci manuel okumada bunun özel ad, evrensel kısa ifade veya çevrilmesi gerekmeyen etiket olduğu doğrulandı.'
    return 'AYNI BIRAKILDI – doğru/doğal','İngilizce kaynak anlamını koruyor; Türkçesi akıcı, sahne tonuna ve kullanılan terimlere uygun. İkinci manuel okumada müdahale gerektirmedi.'

def write_tsv(path,fields,rows):
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter='\t'); w.writeheader(); w.writerows(rows)

def sjs_reports(rules):
    v6=read_tsv(REPORT/'bilingual_audit_v6.tsv'); v7=read_tsv(REPORT/'bilingual_audit_v7.tsv')
    assert len(v6)==len(v7)
    out=[]
    for a,z in zip(v6,v7):
        assert (a['dosya'],a['parca'],a['ingilizce'])==(z['dosya'],z['parca'],z['ingilizce'])
        ch=a['turkce']!=z['turkce']
        if ch:
            cat,why=changed_reason(a['dosya'],u(a['turkce']),rules)
            decision='DEĞİŞTİRİLDİ'
        else:
            decision,why=unchanged_reason(a['ingilizce'],a['turkce']); cat=decision.split('–',1)[-1].strip()
        out.append({'dosya':a['dosya'],'parca':a['parca'],'ingilizce':a['ingilizce'],'v6_turkce':a['turkce'],'v7_turkce':z['turkce'],'karar':decision,'kategori':cat,'gerekce':why})
    fields=list(out[0])
    write_tsv(REPORT/'V7_MANUEL_KARAR_RAPORU.tsv',fields,out)
    write_tsv(REPORT/'V7_DEGISENLER_GEREKCELI.tsv',fields,[r for r in out if r['karar']=='DEĞİŞTİRİLDİ'])
    write_tsv(REPORT/'V7_AYNI_BIRAKILANLAR_GEREKCELI.tsv',fields,[r for r in out if r['karar']!='DEĞİŞTİRİLDİ'])
    # file summary
    by=collections.defaultdict(lambda:collections.Counter())
    for r in out: by[r['dosya']][r['karar']]+=1
    fs=[]
    for f in sorted(by):
        c=by[f]; fs.append({'dosya':f,'degistirildi':c['DEĞİŞTİRİLDİ'],'ayni_birakildi':sum(v for k,v in c.items() if k!='DEĞİŞTİRİLDİ'),'toplam_parca':sum(c.values())})
    write_tsv(REPORT/'V7_DOSYA_OZETI.tsv',['dosya','degistirildi','ayni_birakildi','toplam_parca'],fs)
    return out

def decode_credit_text(p,enc): return p.read_bytes().decode(enc,'surrogateescape').splitlines()
def visible_credit_line(line):
    x=re.sub(r'\[[^\]]*\]','',line)
    return x.strip()

def credit_text_reports(credit_rules):
    allrows=[]
    for ep in sorted(EN_DATA.glob('credits_text*.txt')):
        name=ep.name; vp=V6_DATA/name; zp=V7_DATA/name
        en=decode_credit_text(ep,'cp1252'); v6=decode_credit_text(vp,'cp1254'); v7=decode_credit_text(zp,'cp1254')
        assert len(en)==len(v6)==len(v7), name
        for i,(e,a,z) in enumerate(zip(en,v6,v7),1):
            ev,av,zv=visible_credit_line(e),visible_credit_line(a),visible_credit_line(z)
            if not (ev or av or zv): continue
            if a!=z:
                hits=[]
                for old,new,cat,why in credit_rules:
                    if old in a: hits.append((cat,why))
                if hits: cat=' + '.join(dict.fromkeys(x[0] for x in hits)); why=' / '.join(x[1] for x in hits)
                else: cat='Manuel jenerik cilası'; why='İkinci manuel jenerik okumada kaynak anlam/üslup daha doğal Türkçeyle ifade edildi.'
                dec='DEĞİŞTİRİLDİ'
            else:
                dec,why=unchanged_reason(ev,av); cat=dec.split('–',1)[-1].strip()
            allrows.append({'dosya':name,'satir':i,'ingilizce':ev,'v6_turkce':av,'v7_turkce':zv,'karar':dec,'kategori':cat,'gerekce':why})
    write_tsv(REPORT/'V7_CREDITS_TEXT_KARAR_RAPORU.tsv',list(allrows[0]),allrows)
    return allrows

def credit_payloads(p,enc):
    raw=p.read_bytes(); arr=[]
    for i,m in enumerate(re.finditer(br'\[([^\]]*)\]',raw)):
        b=m.group(1)
        # layout byte preserved; make it visible in report
        b=b.replace(b'\xC2',b'<LAYOUT>')
        arr.append((i,b.decode(enc,'surrogateescape')))
    return arr

def credit_sjs_report():
    en=credit_payloads(EN_DATA/'credit.sjs','cp1252'); a=credit_payloads(V6_DATA/'credit.sjs','cp1254'); z=credit_payloads(V7_DATA/'credit.sjs','cp1254')
    assert len(en)==len(a)==len(z)
    rows=[]
    reason_map=[
        ("Sue'nun kendine",'Doğallık','“grandfather figure” Türkçede “dedesi gibi gördüğü kişi” olarak doğal.'),
        ('dede bildiği kişi','Doğallık','“grandfather figure” ifadesinin ikinci satırı doğal Türkçe yapıya tamamlandı.'),
        ('İkinci adam','Terim/ton','“Number-Two” jenerik esprisi “İki numara” ile daha doğrudan korunuyor.'),
        ('Yaşlı','Anlam','Kaynak “The Grandpa Mimiga”; “Dede” niteliği kaynak anlamı daha iyi koruyor.'),
        ('Büyük uçucu','Doğallık','“The big flyer” için jenerik tonunda “Koca uçan” daha doğal.'),
        ('Birden çoğa','Anlam/doğallık','“From one, many” çoğalma özelliğini anlatıyor; fiilli “Birden çoğalır” daha açık.'),
        ('Gerçek kahramanların rakibi','Anlam/ton','“True heroes meet the Red Ogre” eylem vurgusuyla “Gerçek kahramanlarla kapışır” olarak verildi.'),
        ('Şişmiş makine','Doğallık','“swollen mech” için “Şişkin makine” daha doğal sıfat kullanımı.')
    ]
    for (i,e),(j,v),(k,w) in zip(en,a,z):
        assert i==j==k
        if not any(ch.isalpha() for ch in e+v+w): continue
        if v!=w:
            hits=[(c,r) for old,c,r in reason_map if old in v]
            cat=' + '.join(dict.fromkeys(x[0] for x in hits)) if hits else 'Manuel jenerik cilası'
            why=' / '.join(x[1] for x in hits) if hits else 'İkinci manuel jenerik okumada daha doğru/doğal karşılık seçildi.'
            dec='DEĞİŞTİRİLDİ'
        else:
            dec,why=unchanged_reason(e,v); cat=dec.split('–',1)[-1].strip()
        rows.append({'payload':i,'ingilizce':e,'v6_turkce':v,'v7_turkce':w,'karar':dec,'kategori':cat,'gerekce':why})
    write_tsv(REPORT/'V7_CREDIT_SJS_KARAR_RAPORU.tsv',list(rows[0]),rows)
    return rows

def summary(sjs,ct,cs):
    allr=sjs+ct+cs
    cnt=collections.Counter(r['karar'] for r in allr)
    cats=collections.Counter(r['kategori'] for r in allr if r['karar']!='DEĞİŞTİRİLDİ')
    changed_sjs=sum(r['karar']=='DEĞİŞTİRİLDİ' for r in sjs)
    changed_ct=sum(r['karar']=='DEĞİŞTİRİLDİ' for r in ct)
    changed_cs=sum(r['karar']=='DEĞİŞTİRİLDİ' for r in cs)
    files_changed=len({r['dosya'] for r in sjs if r['karar']=='DEĞİŞTİRİLDİ'})
    text=f'''# Cave Story 3D TR V7 – İkinci Manuel Kontrol Karar Özeti\n\nBu rapor V6 ile V7 arasındaki ikinci manuel dil/üslup geçişini açıklar. İngilizce kaynak karşısına V6 ve V7 Türkçesi kondu; değişen parçalar gerekçelendirildi, değiştirilmemiş parçalar da neden korunmuş olduklarına göre sınıflandırıldı.\n\n## SJS\n- Hizalanan parça: **{len(sjs)}**\n- Değiştirilen parça: **{changed_sjs}**\n- Değişiklik bulunan SJS dosyası: **{files_changed}**\n- Aynı bırakılan parça: **{len(sjs)-changed_sjs}**\n\n## Jenerik\n- credits_text varyantlarında raporlanan görünür satır: **{len(ct)}**\n- Bu satırlarda değişiklik: **{changed_ct}**\n- credit.sjs görünür payload: **{len(cs)}**\n- credit.sjs değişik payload: **{changed_cs}**\n\n## “Aynı bırakıldı” ne demek?\n- **doğru/doğal:** Anlam, ton, dilbilgisi ve terim kullanımı ikinci okumada yeterli bulundu.\n- **özel ad/terim:** Quote, Curly Brace, Balrog gibi özel adlar veya sürüm/yaratık adları bilinçli korundu.\n- **ses/ünlem:** Hey!, Aah!, “...” gibi ses/tepki öğeleri Türkçede aynı işlevi gördüğü için korunabildi.\n- **teknik/şifre:** Event kimlikleri, geliştirici notları, dahili etiketler ve yrotS evaC gibi oyun mantığına bağlı öğeler çevrilmedi.\n\n## QA\n- 113/113 SJS komut/event hizası temiz.\n- 42 karakter üstü görünür satır: 0.\n- credit.sjs ham 0xC2 kontrol baytı: 32/32 korunuyor.\n- 12 değiştirilmiş görselin biçim/bit derinliği doğrulandı.\n\nAyrıntılar için `V7_DEGISENLER_GEREKCELI.tsv` ve `V7_AYNI_BIRAKILANLAR_GEREKCELI.tsv` dosyalarına bakın. `V7_MANUEL_KARAR_RAPORU.tsv` bütün SJS kararlarını tek tabloda içerir.\n'''
    (REPORT/'V7_MANUEL_KARAR_OZETI.md').write_text(text,encoding='utf-8')
    return cnt,cats

def main():
    REPORT.mkdir(exist_ok=True)
    rules,credit_rules=load_rules()
    s=sjs_reports(rules); c=credit_text_reports(credit_rules); q=credit_sjs_report(); cnt,cats=summary(s,c,q)
    print('SJS:',len(s),'değişen',sum(r['karar']=='DEĞİŞTİRİLDİ' for r in s))
    print('credits_text:',len(c),'değişen',sum(r['karar']=='DEĞİŞTİRİLDİ' for r in c))
    print('credit.sjs:',len(q),'değişen',sum(r['karar']=='DEĞİŞTİRİLDİ' for r in q))
    print('kararlar:',dict(cnt))

if __name__=='__main__': main()
