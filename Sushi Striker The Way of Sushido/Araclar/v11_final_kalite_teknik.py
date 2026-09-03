#!/usr/bin/env python3
from pathlib import Path
import csv, re, json

WORK=Path('/mnt/data/sushi_work/review_v11_work')
CSV_DIR=WORK/'CSV'
OUT=Path('/mnt/data/sushi_work/review_v11')
ROUND='v0.11-final'
RESET='\\u000E\\u0000\\u0003\\u0004\\u0000＀'
ITEM='\\u000E\\u0000\\u0003\\u0004ﾑ＞'
PINK='\\u000E\\u0000\\u0003\\u0004쳿Ｏ'
BLUE='\\u000E\\u0000\\u0003\\u0004渀＀'
YELLOW='\\u000E\\u0000\\u0003\\u0004Ü＀'

def load(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

def save(path, fields, rows):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with Path(path).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

files={}; idx={}
for p in sorted(CSV_DIR.glob('*.csv')):
    with p.open(encoding='utf-8-sig',newline='') as f:
        rr=list(csv.DictReader(f)); fields=list(rr[0].keys()) if rr else ['label','index','deu','eng','esp','fra','ita','nld','tur']
    files[p.name]=(fields,rr)
    for r in rr: idx[(p.name,r['label'])]=r

changes=[]
rechecked={}

def setv(fn,lab,new,reason,category='KALİTE'):
    r=idx[(fn,lab)]; old=r['tur']
    rechecked[(fn,lab)]=('DEĞİŞTİ',reason)
    if old==new: return
    r['tur']=new
    changes.append({'round':ROUND,'category':category,'file':fn,'label':lab,
                    'eng':r['eng'],'deu':r['deu'],'esp':r['esp'],'fra':r['fra'],'ita':r['ita'],'nld':r['nld'],
                    'old_tur':old,'new_tur':new,'reason':reason})

def replacev(fn,lab,old,new,reason,category='KALİTE'):
    cur=idx[(fn,lab)]['tur']
    if old not in cur:
        if new in cur:
            rechecked[(fn,lab)]=('DEĞİŞTİ',reason)
            return
        raise ValueError(f'{fn}:{lab}: beklenen parça yok: {old!r}\n{cur!r}')
    setv(fn,lab,cur.replace(old,new),reason,category)

# 1) v0.11 place-name suffix regression introduced by mechanical replacement.
for fn,lab in [('stageEndM062.csv','CharaSerif_06_M'),('chapterBeginM005.csv','CharaSerif_36_M')]:
    replacev(fn,lab,"Fugu Kalesi'ya","Fugu Kalesi'ne",
             "Fort Fugu terimini 'Fugu Kalesi' olarak değiştirirken eski -ya eki mekanik biçimde kalmıştı. 'Kale-si' iyelikli birleşik addır; yönelme hâli doğru olarak 'Fugu Kalesi'ne' olur.",'DİL/çekim+TEKNİK/regresyon')

# 2) Tutorial language: natural Turkish while keeping the exact UI emphasis commands.
for lab in ['tutorial04_01_M','tutorial04_01_F']:
    setv('stageBattleM003.csv',lab,f'Hey, \\u000E\\u0000\\u0003\\u0004\\uD85FｱŞerit Dişlisi{RESET} de ne?!',
         "'What's a lane-drive gear?!' için eski 'Şerit Dişlisi ne?' anlaşılır ama eksiltili/çeviri kokuyor. Türkçedeki doğal şaşkınlık 'Şerit Dişlisi de ne?!'; kaynakta kullanılan özel item vurgu komutu aynen korundu.",'KALİTE+TEKNİK/doğallık-vurgu')
setv('stageBattleM003.csv','tutorial04_02_M',
     f'Hmm. Bir \\u000E\\u0000\\u0003\\u0004\\uD85FｱŞerit Dişlisi{RESET} ile\\n{PINK}şeritlerinin{RESET} {PINK}hızını{RESET} {PINK}kontrol{RESET} edebilirsin!',
     "Kaynak üç kavramı ayrı vurguluyor: lanes / speed / control. Eski Türkçe 'kontrol ederek hızı şeritlerinde ayarlayabilirsin' yapay söz dizimiydi. Aynı üç vurgu korunup doğal Türkçe sıraya alındı.",'KALİTE+TEKNİK/vurgu')

# 3) Reward sentence: remove awkward English order/x5 while using the item highlight used by 5 other official localizations.
setv('stageEndM116.csv','CharaSerif_40_M',f'5 {ITEM}Mutfak Pürmüzü{RESET} aldın!',
     "İngilizce kaynakta 'You got [item] x5' ve iç içe özel biçim kodu var; DE/ES/FR/IT/NL sayıyı cümlenin içine alıp tek item vurgusu kullanıyor. Türkçe 'Aldın ... x5!' hem yabancı söz dizimiydi hem gereksiz karmaşık kontrol yapısını taşıyordu; '5 Mutfak Pürmüzü aldın!' ile sadeleştirildi.",'KALİTE+TEKNİK/kontrol-sadeleştirme')

# 4) Pledge/befriend system terminology: all acquisition notices use the established Bağ vocabulary.
acq=[
 ('stageEndArea06Ex010.csv','CharaSerif_15_M'),
 ('stageEndArea07Ex001.csv','CharaSerif_07_M'),
 ('stageEndArea03Ex008.csv','CharaSerif_04_M'),
 ('stageEndM111_After01.csv','CharaSerif_00_M'),
 ('stageEndM092.csv','CharaSerif_15_M'),
 ('stageEndArea01Ex004.csv','CharaSerif_03_M'),
 ('stageEndM050.csv','CharaSerif_11_M'),
 ('stageEndM008.csv','stageEndM009_20B_M'),
 ('stageEndM008.csv','stageEndM009_20C_M'),
]
for fn,lab in acq:
    cur=idx[(fn,lab)]['tur']
    new=cur.replace(' ile arkadaş oldun!',' ile bağ kurdun!').replace(' ile dost oldun!',' ile bağ kurdun!')
    new=new.replace(' adlı suşi ruhuyla arkadaş oldun!',' adlı suşi ruhuyla bağ kurdun!')
    if lab=='CharaSerif_15_M' and fn=='stageEndArea06Ex010.csv':
        # make syntax match all other acquisition notices
        new=f'Suşi ruhu {ITEM}Anubiva{RESET} ile bağ kurdun!\\nYeteneği {ITEM}Can Takası{RESET}!'
    if fn=='stageEndM092.csv':
        new=new.replace('Yeteneği: ','Yeteneği ')
    setv(fn,lab,new,
         "Bu bildirimlerin İngilizcesi 'befriended', ES/FR/IT ittifak, NL açıkça 'band' kullanıyor. Oyunun Türkçe pledge sistemi artık 'Bağ / bağ kurmak' olarak standardize edildiği için kazanım bildirimlerindeki 'arkadaş/dost oldun' kalıntısı aynı terime çekildi.",'TERİM/bağ-sistemi')

# 5) Canonical skill-name consistency against database_cmn.
replacev('stageBeginM094.csv','CharaSerif_04_M','Lüks Flaş','Lüks Parıltı',
         "Luxury Flash'ın ana yetenek adı database_cmn'de 'Lüks Parıltı'. Diyalogdaki eski 'Lüks Flaş' aynı yeteneği ikinci adla gösteriyordu; kanonik ada çekildi.",'TERİM/yetenek')
# Correct suffix after the renamed vowel-final skill name.
replacev('stageBeginM094.csv','CharaSerif_04_M',f'{ITEM}Lüks Parıltı{RESET}’ıma',f"{ITEM}Lüks Parıltı{RESET}'ma",
         "'Lüks Parıltı' ünlüyle bittiği için birinci tekil iyelik+yönelme eki 'Parıltı'ma' olur; eski Flaş'tan kalan -ıma eki yeni ada taşınamaz.",'DİL/çekim')

# Budget Striker: canonical 'Hesaplı Vurucu'; fix both reward and introduction, avoiding bad suffix on the title.
replacev('stageEndArea04Ex004.csv','CharaSerif_03_M','Bütçe Vurucu','Hesaplı Vurucu',
         "Budget Striker kanonik tabloda 'Hesaplı Vurucu'. 'Bütçe Vurucu' yalnız bu sahnede kalmıştı; DE/IT miktar-kalite, ES 'daha aza daha çok', FR ekonomik tonunu doğruluyor.",'TERİM/yetenek')
setv('stageBeginArea04Ex004.csv','CharaSerif_04_M',
     f'Karşınızda {ITEM}Popokan{RESET}; yeteneği\\n{ITEM}Hesaplı Vurucu{RESET}!',
     "Budget Striker ana tabloda 'Hesaplı Vurucu'. Eski 'Bütçe Vurucu'ın kullanıcısı' hem terim sapması hem de yanlış Türkçe ek taşıyordu; cümle doğal bir sunum kalıbıyla yeniden kuruldu.",'TERİM+KALİTE/yetenek')
replacev('stageBeginM032.csv','CharaSerif_04_M','Ghost suşi','Hayalet Suşi',
         "Ghost Sushi ana yetenek adı 'Hayalet Suşi'. 'Ghost suşi' yarım İngilizce kalmıştı; kanonik ad kullanıldı.",'TERİM/yetenek')
replacev('stageEndArea01Ex004.csv','CharaSerif_03_M','Tabak Zıplayıcısı','Tabak Atlatan',
         "Plate Jumper ana yetenek adı 'Tabak Atlatan'. Ruh kazanım mesajında eski 'Tabak Zıplayıcısı' kalmıştı; kanonik ada çekildi.",'TERİM/yetenek')
for lab in ['stageEndM009_17C_M','stageEndM009_19C_M','stageEndM009_20C_M']:
    replacev('stageEndM008.csv',lab,'ElektroÇarpma','Elektroşok',
             "Electrozap ana yetenek adı 'Elektroşok'. Bu üç seçim/kazanım repliğinde eski 'ElektroÇarpma' kalmıştı; aynı yetenek adı tüm oyunda tekleştirildi.",'TERİM/yetenek')
replacev('stageBeginM007.csv','stageBeginM008_04_M','Çılgın Şerit','Çılgın Şeritler',
         "Runaway Lane bu aktivasyon repliğinde tekil yazılmış olsa da DE/FR/IT/NL kanonik yetenek adını kullanıyor; Türkçedeki ana ad 'Çılgın Şeritler'. Aynı yetenek adıyla tekleştirildi.",'TERİM/yetenek')

# 6) Canonical item-name consistency.
# Renewal Bean family: Yenileme, not Yenilenme; Great tier is Dev.
renewal_rows=[]
for fn,(fields,rr) in files.items():
    for r in rr:
        if 'Yenilenme Fasulyesi' in r['tur']:
            renewal_rows.append((fn,r['label']))
for fn,lab in renewal_rows:
    cur=idx[(fn,lab)]['tur']
    new=cur.replace('Harika Yenilenme Fasulyesi','Dev Yenileme Fasulyesi')
    new=new.replace('Büyük Yenilenme Fasulyesi','Büyük Yenileme Fasulyesi')
    new=new.replace('Küçük Yenilenme Fasulyesi','Küçük Yenileme Fasulyesi')
    new=new.replace('Yenilenme Fasulyesi','Yenileme Fasulyesi')
    setv(fn,lab,new,
         "Renewal Bean ailesinin kanonik adları database_cmn'de 'Yenileme Fasulyesi / Küçük / Büyük / Dev'. 'Yenilenme' ve 'Harika' varyantları aynı eşyayı farklı adlarla gösteriyordu; bütün kullanımlar kanonik aileye çekildi.",'TERİM/eşya')
for lab in ['homeShrine_get_OhudaSkillC_sg_M','homeShrine_get_OhudaSkillC_pl_M']:
    replacev('homeShrine.csv',lab,'Harika Yetenek Tılsımı','Büyük Yetenek Tılsımı',
             "Great Skill Charm'ın kanonik eşya adı 'Büyük Yetenek Tılsımı'. Tapınak ödül mesajındaki 'Harika' varyantı kaldırıldı.",'TERİM/eşya')
replacev('stageEndM078.csv','CharaSerif_40_M','Parti Tılsımları','Parti Tılsımı',
         "Türkçede sayıdan sonra ad çoğul eki almaz: '5 Parti Tılsımı'. Kanonik item adı da tekil 'Parti Tılsımı'. Kontrol kodu korunarak çoğul hatası düzeltildi.",'DİL/çoğul+TERİM')
replacev('stageEndM052.csv','CharaSerif_15_M',"Ausprey'in Anahtarını","Ausprey'nin Anahtarını",
         "Kanonik item adı 'Ausprey'nin Anahtarı'. Ausprey ünlü sesiyle bittiği için ilgi eki -nin; ödül cümlesinde belirtme ekiyle 'Ausprey'nin Anahtarını' olur.",'DİL/çekim+TERİM')

# 7) Whole-patch layout cleanup found by final validator: keep every visible line <=48 chars without dropping meaning or emphasis.
setv('database_tipsInfo.csv','TipsPage3_018',
     f'{BLUE}Çember Çubuğu{RESET}yla {YELLOW}Musashi’yi hareket ettir{RESET};\\n'
     f'önündeki yığını fırlatmak için {BLUE}X Düğmesine{RESET} bas.\\n'
     f'Yığınları hızlıca art arda fırlatmak için\\n'
     f'{BLUE}X Düğmesine{RESET} {YELLOW}art arda bas{RESET}!',
     "Kaynak beş ayrı kavramı vurguluyor (Circle Pad, move Musashi, X Button, repeatedly pressing, X Button). Önceki Türkçe anlam ve vurgu açısından doğruydu ama ilk satır 54 görünür karakterdi; vurgu çiftleri korunarak dört satıra dengelendi.",'TEKNİK/UI-yerleşim')
setv('database_tipsInfo.csv','TipsPage4_025',
     f'-{BLUE}Hazır Eşya{RESET} kullanamazsın.\\n'
     f'-Her ruhun suşisi 30. seviyedeki hâlidir;\\n'
     f'bu yüzden {BLUE}Mutfak Pürmüzü{RESET} gibi eşya etkileri\\n'
     f'hesaba katılmaz.',
     "Kaynak iki Arena kuralı veriyor. Önceki Türkçede ikinci satır 49 görünür karakterdi; anlam, Prepared Item/Mutfak Pürmüzü terimleri ve iki vurgu spanı korunarak satırlar yeniden dengelendi.",'TEKNİK/UI-yerleşim')

# Write CSV files.
for fn,(fields,rr) in files.items(): save(CSV_DIR/fn,fields,rr)

# Patch original v11 script so a clean v0.10 -> v0.11 replay doesn't recreate the Fugu suffix bug.
v11script=WORK/'Araclar'/'v11_ucuncu_kalite_gecisi.py'
s=v11script.read_text(encoding='utf-8')
s=s.replace("r['tur'].replace('Fort Fugu','Fugu Kalesi')",
            "r['tur'].replace(\"Fort Fugu'ya\",\"Fugu Kalesi'ne\").replace('Fort Fugu','Fugu Kalesi')")
v11script.write_text(s,encoding='utf-8')

# ---- update reports idempotently ----
change_fields=['round','category','file','label','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']

def strip_round(path, round_name):
    if not Path(path).exists(): return []
    rr=load(path)
    return [r for r in rr if r.get('round')!=round_name]

# V11 new changes and historical changes.
v11changes=strip_round(OUT/'V11_YENI_DEGISIKLIKLER.csv',ROUND)+changes
save(OUT/'V11_YENI_DEGISIKLIKLER.csv',change_fields,v11changes)
hist=strip_round(OUT/'INCELEME_DEGISIKLIKLERI.csv',ROUND)+changes
save(OUT/'INCELEME_DEGISIKLIKLERI.csv',change_fields,hist)
latest={}
for r in hist: latest[(r['file'],r['label'])]=r
save(OUT/'INCELEME_SON_DURUM_ESSIZ.csv',change_fields,list(latest.values()))

# Master 10,676 status: update final text/reason for changed rows.
master=load(OUT/'TUM_10676_SATIR_DURUMU.csv')
mm={(r['file'],r['label']):r for r in master}
for (fn,lab),(dec,reason) in rechecked.items():
    r=mm[(fn,lab)]; src=idx[(fn,lab)]
    r['review_status']='İNCELENDİ'; r['decision']=dec; r['current_tur']=src['tur']; r['reason']=reason
save(OUT/'TUM_10676_SATIR_DURUMU.csv',list(master[0].keys()),master)

# V11 detailed review: preserve existing rows, update same labels to final text/reason; add newly rechecked rows.
review_path=OUT/'V11_UCUNCU_GECIS_INCELEME.csv'; review=load(review_path)
rm={(r['file'],r['label']):r for r in review}
for (fn,lab),(dec,reason) in rechecked.items():
    src=idx[(fn,lab)]
    ch=[x for x in changes if x['file']==fn and x['label']==lab]
    finalch=ch[-1] if ch else None
    if (fn,lab) in rm:
        rr=rm[(fn,lab)]; rr['decision']=dec; rr['new_tur']=src['tur']; rr['reason']=reason
        if finalch and not rr.get('old_tur'): rr['old_tur']=finalch['old_tur']
    else:
        prev=mm[(fn,lab)]
        rr={'round':'v0.11','file':fn,'label':lab,'index':src.get('index',''),
            'previous_review_status':'İNCELENDİ','previous_decision':prev.get('decision',''),
            'decision':dec,'eng':src['eng'],'deu':src['deu'],'esp':src['esp'],'fra':src['fra'],'ita':src['ita'],'nld':src['nld'],
            'old_tur':finalch['old_tur'] if finalch else src['tur'],'new_tur':src['tur'],'reason':reason}
        review.append(rr);rm[(fn,lab)]=rr
review.sort(key=lambda r:(r['file'],int(r.get('index') or 10**9) if str(r.get('index','')).isdigit() else 10**9,r['label']))
save(review_path,list(review[0].keys()),review)

# cumulative row-level review: append one final record per rechecked row for auditability.
cum_path=OUT/'SATIR_BAZLI_INCELEME_KUMULATIF.csv'; cum=strip_round(cum_path,ROUND)
cum_fields=['round','file','label','index','decision','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
for (fn,lab),(dec,reason) in sorted(rechecked.items()):
    src=idx[(fn,lab)]; ch=[x for x in changes if x['file']==fn and x['label']==lab]
    cum.append({'round':ROUND,'file':fn,'label':lab,'index':src.get('index',''),'decision':dec,
                'eng':src['eng'],'deu':src['deu'],'esp':src['esp'],'fra':src['fra'],'ita':src['ita'],'nld':src['nld'],
                'old_tur':ch[0]['old_tur'] if ch else src['tur'],'new_tur':src['tur'],'reason':reason})
save(cum_path,cum_fields,cum)

# A compact consistency report used later by the validator/package.
cons=[]
for r in changes:
    cons.append({'file':r['file'],'label':r['label'],'category':r['category'],'status':'DÜZELTİLDİ','details':r['reason']})
save(OUT/'V11_FINAL_TUTARLILIK_DUZELTMELERI.csv',['file','label','category','status','details'],cons)

print(json.dumps({'final_changes':len(changes),'rechecked':len(rechecked),'renewal_rows':len(renewal_rows)},ensure_ascii=False))
