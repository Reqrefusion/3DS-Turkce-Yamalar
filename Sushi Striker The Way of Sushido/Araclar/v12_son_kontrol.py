#!/usr/bin/env python3
import csv, os, glob, shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CSV_DIR=ROOT/'CSV'
REPORT_DIR=ROOT/'Raporlar'
REPORT_DIR.mkdir(exist_ok=True)

# Exact final-audit changes. Keep source control-code spellings exactly as CSV stores them.
EXACT={
 ('database_cmn.csv','SushiName_PineCut'): ('Ananas','TERİM','Resmî DE/FR/IT/NL karşılıkları yerelleştiriyor; İngilizce Pineapple kalıntısı final kontrolde yakalandı.'),
 ('database_cmn.csv','SushiName_MelonCut'): ('Kavun','TERİM','Tüm resmî diller kavun adını yerelleştiriyor; İngilizce Melon kalıntısı temizlendi.'),
 ('database_cmn.csv','SushiName_Buri'): ('Sarıkuyruk','TERİM','Yellowtail/Buri balığı için Sarıkanat yanlış tür çağrışımı yapıyordu; sushi bağlamında sarıkuyruk karşılığı seçildi.'),
 ('database_cmn.csv','SushiName_Anago'): ('Deniz Yılan Balığı','TERİM','DE Meeraal ve NL Zeepaling deniz yılan balığı anlamını doğruluyor; Tuzlu Su Yılan Balığı doğal Türkçe değildi.'),
 ('stageEndM009_After01.csv','stageEndM009_11_M'): ('Somonun çiğ gücü \\u000E\\u0000\\u0003\\u0004ﾑ＞Asta-Tak\\u000E\\u0000\\u0003\\u0004\\u0000＀!','TERİM/ESPRİ','Ana tabloda Salmon Favori Gücü Asta-Tak olarak yerelleştirilmişti; tek kalan A-Tax kullanımı ve raw/çiğ kelime oyunu eşitlendi.'),
 ('stageBeginM008.csv','stageBeginM009_09_M'): ("Biz Suşi Kurtuluş Cephesiyiz;\\nİmparatorluk'a başkaldıran bir avuç isyancı.",'TERİM','Sushi Liberation Front oyunun geri kalanında Suşi Kurtuluş Cephesi. Tek kalan Özgürlük Cephesi tutarsızlığı düzeltildi.'),
 ('homeKoziin.csv','homeKoziin_useful_09_02_M'): ("Örneğin, rakibin \\u000E\\u0000\\u0003\\u0004ﾑ＞Tatlı Şöleni\\u000E\\u0000\\u0003\\u0004\\u0000＀ kullanırsa,\\nbunu bozmak için \\u000E\\u0000\\u0003\\u0004ﾑ＞Çılgın Şeritler\\u000E\\u0000\\u0003\\u0004\\u0000＀'i kullan!",'TERİM','Sweets Paradise için kanonik ad Tatlı Şöleni; tek kalan Tatlı Cenneti düzeltildi.'),
 ('database_movieSerif_2B.csv','MovieSerifText_2b_0002_M'): ('Musashi sayesinde ormanı yine\\neskisi gibi sapasağlam hâle getirdik!','ANLAM','EN ve beş resmî çeviri başarının Musashi sayesinde olduğunu açıkça söylüyor; Türkçe özneyi tamamen düşürmüştü.'),
 ('scene_puzzlebattle.csv','Enemy_StgWin_102'): ("Halterlerime Musashi'yi patakladığımı\\nanlatmak için sabırsızlanıyorum!",'ANLAM/KARAKTER','EN ve ES/FR/IT/NL Musashi’yi yendiğini açıkça içeriyor; eski Türkçe yalnız halterlerin tepkisini bırakıp ana eylemi düşürmüştü.'),
 ('scene_puzzlebattle.csv','Enemy_StgLose_102'): ('Son karşılaşmadan beri durmadan çalıştım...\\nYine de yetmedi.','ANLAM','EN/IT/NL antrenmanın yetmediği sonucunu taşıyor; eski Türkçe ikinci düşünceyi tamamen düşürmüştü.'),
 ('scene_puzzlebattle.csv','Player_StgWin_275'): ('Bunca güçlü rakiple kapışınca\\ninsan ister istemez güçleniyor!','ANLAM','EN/DE/FR/IT/NL çok sayıda güçlü rakiple dövüşme deneyimini anlatıyor; eski Türkçe tersine yalnız “sonunda zorlu bir düşman” diyordu.'),
 ('scene_puzzlebattle.csv','Player_StgWin_275_f'): ('Bunca güçlü rakiple kapışınca\\ninsan ister istemez güçleniyor!','ANLAM/MF','Erkek varyantıyla aynı İngilizce kaynak; düzeltilmiş anlam kadın varyantına da eşitlendi.'),
 ('scene_puzzlebattle.csv','Enemy_StgLose_251'): ('Sana bilerek yenilmeyi düşünmüştüm ama\\nzaten fazlasıyla iyisin.','ANLAM','EN/NL rakibe bilerek yenilmeyi düşündüğünü söylüyor; eski Türkçe “hiç düşünmemiştim” diyerek anlamı tersine çevirmişti.'),
 ('scene_puzzlebattle.csv','Enemy_StgLose_107'): ('Benim ve mükemmektorallerimin\\nyolu burada bitiyor...','DOĞALLIK/ESPRİ','Perfectorals kelime oyunu korunurken Türkçedeki “yolun sonu” tamlaması gramer açısından doğal hâle getirildi.'),
 ('stageBeginArea04Ex001.csv','CharaSerif_10_M'): ('Centilmence. Şimdi başlayalım!','DOĞALLIK','Sportmence yapay bir türetimdi; IT/NL sporting anlamını Centilmence doğal biçimde karşılıyor.'),
 ('stageBeginArea05Ex001.csv','CharaSerif_01_M'): ('Musashi?! Sanki zaten yeterince\\nderdim yokmuş gibi!','YAZIM','“derin yokmuş” açık yazım/kelime hatasıydı; EN/DE/ES/FR/IT/NL problems/sorunlar anlamını doğruluyor.'),
 ('stageBeginArea06sub010.csv','CharaSerif_11_M'): ('Öyle bir şey yapmayacağız! Hatta... Jinrai\\nçalışmalarımızda çok işimize yarayabilir!','DİLBİLGİSİ','“Jinrai’ın çalışmalarımızda” bozuk tamlamaydı; EN cümlesindeki özne doğrudan Jinrai.'),
 ('stageBeginM003.csv','stageBeginM004_04B_M'): ("Franklin'i mi arıyorsun? Boşuna. Şimdiye\\nİmparatorluk yolunun yarısını çoktan geçmiştir!",'DOĞALLIK/ANLAM','“İmparatorluğun yarı yolunda” Türkçede yapaydı; EN halfway anlamı korunarak doğal söz dizimi kuruldu.'),
 ('stageEndM092.csv','CharaSerif_12_M'): ('Tamam. Ben hallederim!','DEYİM','I’m on it ES/FR/IT/NL’de işi üstlenme anlamında; “Tamam. Bende!” yanlış çağrışım yapıyordu.'),
 ('stageEndM092.csv','CharaSerif_12_F'): ('Tamam. Ben hallederim!','DEYİM/MF','Erkek varyantıyla aynı İngilizce kaynak; doğal karşılık kadın varyantına da eşitlendi.'),
 ('stageBeginM047.csv','CharaSerif_01_M'): ('Wasabisiz hiç aynı olmuyor.\\nGelişimlerini engelleyeceksin!','DOĞALLIK','“Wasabisiz asla aynı değil” İngilizce sözdizimini taşıyordu; anlam ve ton doğal Türkçeye çevrildi.'),
 ('stageBeginArea04subEx002.csv','CharaSerif_01_M'): ('(Ne olmuş yani? Suşi ruhlarının kokusunu\\nuzaktan alıyorsam ne yapayım.)','ESPRİ/DEYİM','EN/FR “have a nose/flair” burun-koku deyimiyle oynuyor; eski Türkçe “iyi bir burnum varsa” yapaydı, burun esprisi doğal biçimde korundu.'),
 ('stageBeginArea04subEx002.csv','CharaSerif_01_F'): ('(Ne olmuş yani? Suşi ruhlarının kokusunu\\nuzaktan alıyorsam ne yapayım.)','ESPRİ/DEYİM/MF','Erkek varyantıyla aynı İngilizce kaynak; deyimsel düzeltme kadın varyantına da taşındı.'),
 ('stageBeginM136.csv','CharaSerif_04_M'): ('Ta buralara bizimle oyun oynamaya mı geldin?\\nAman, hiç zahmet etmeseydin!','KARAKTER/DOĞALLIK','You shouldn’t have alaycı nezaket kalıbıydı; “Zahmet etmezdin” doğal değildi, Rio’nun şakacı tonu yeniden kuruldu.'),
 ('stageBeginM136.csv','CharaSerif_08_M'): ('Çünkü... oynamazsan peşimizi bırakmaz.\\nBöylesi daha kolay.','BAĞLAM','Önceki satır “oyununu oynayalım”; “yapmazsan gitmez” eylemi belirsiz bırakıyordu. Komşu replikle birlikte doğal hâle getirildi.'),
 ('stageBeginM136.csv','CharaSerif_08_F'): ('Çünkü... oynamazsan peşimizi bırakmaz.\\nBöylesi daha kolay.','BAĞLAM/MF','Erkek varyantıyla aynı kaynak; bağlamsal düzeltme kadın varyantına da eşitlendi.'),
}

GLOBAL_REPL=[
 ("Ausprey'in", "Ausprey'nin", 'ÖZEL AD EKİ', "Yabancı özel ada ek okunuşa göre getiriliyor; projedeki kanonik kullanım Ausprey'nin ile tekleştirildi."),
 ("Ausprey’in", "Ausprey'nin", 'ÖZEL AD EKİ', "Kıvrık kesmeli eski Ausprey’in biçimi kanonik Ausprey'nin ile tekleştirildi."),
 ("Ausprey'e", "Ausprey'ye", 'ÖZEL AD EKİ', "Ausprey adı ünlüyle biten telaffuza göre yönelme ekinde kaynaştırma y'siyle tekleştirildi."),
 ("Ausprey’e", "Ausprey'ye", 'ÖZEL AD EKİ', "Kıvrık kesmeli Ausprey’e biçimi kanonik Ausprey'ye ile tekleştirildi."),
 ("Jubay'in", "Jubay'ın", 'ÖZEL AD EKİ', "Jubay özel adının ilgi eki, oyundaki çoğunluk kullanımı ve telaffuz uyumuyla Jubay'ın biçiminde tekleştirildi."),
 ("Jubay’in", "Jubay'ın", 'ÖZEL AD EKİ', "Jubay ilgi eki kanonik Jubay'ın biçimine tekleştirildi."),
 ("Jubay'i", "Jubay'ı", 'ÖZEL AD EKİ', "Jubay belirtme eki oyundaki diğer kullanımla Jubay'ı biçiminde tekleştirildi."),
 ("Jubay’i", "Jubay'ı", 'ÖZEL AD EKİ', "Jubay belirtme eki kanonik Jubay'ı biçimine tekleştirildi."),
]

LANGS=['eng','deu','esp','fra','ita','nld']
changes=[]

def read_csv(path):
    with open(path,encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

def write_csv(path,rows,fieldnames):
    with open(path,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fieldnames,quoting=csv.QUOTE_MINIMAL)
        w.writeheader(); w.writerows(rows)

# Exact edits
for (fn,label),(new,cat,reason) in EXACT.items():
    p=CSV_DIR/fn
    rows=read_csv(p)
    fields=list(rows[0].keys())
    hit=0
    for r in rows:
        if r['label']==label:
            old=r['tur']
            if old!=new:
                r['tur']=new
                changes.append({'round':'v0.12-FINAL','category':cat,'file':fn,'label':label,
                                **{k:r.get(k,'') for k in LANGS},'old_tur':old,'new_tur':new,'reason':reason})
            hit+=1
    if hit!=1:
        raise SystemExit(f'Expected one row {fn}:{label}, got {hit}')
    write_csv(p,rows,fields)

# Global spelling/suffix consistency edits
for pstr in sorted(glob.glob(str(CSV_DIR/'*.csv'))):
    p=Path(pstr); rows=read_csv(p); fields=list(rows[0].keys()); dirty=False
    for r in rows:
        old0=r['tur']; cur=old0; reasons=[]; cats=[]
        for a,b,cat,why in GLOBAL_REPL:
            if a in cur:
                cur=cur.replace(a,b); reasons.append(why); cats.append(cat)
        if cur!=old0:
            r['tur']=cur; dirty=True
            changes.append({'round':'v0.12-FINAL','category':'+'.join(sorted(set(cats))),'file':p.name,'label':r['label'],
                            **{k:r.get(k,'') for k in LANGS},'old_tur':old0,'new_tur':cur,'reason':' '.join(dict.fromkeys(reasons))})
    if dirty: write_csv(p,rows,fields)

# Deduplicate report by file/label while preserving first old and last new, combining reasons.
merged={}
for c in changes:
    key=(c['file'],c['label'])
    if key not in merged:
        merged[key]=c.copy()
    else:
        m=merged[key]; m['new_tur']=c['new_tur'];
        if c['category'] not in m['category']: m['category'] += '+'+c['category']
        if c['reason'] not in m['reason']: m['reason'] += ' '+c['reason']
changes=list(merged.values())
changes.sort(key=lambda x:(x['file'],x['label']))

report=REPORT_DIR/'V12_SON_KONTROL_DEGISIKLIKLER.csv'
fields=['round','category','file','label','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
write_csv(report,changes,fields)

# Update master decision report if present.
master=REPORT_DIR/'TUM_10676_SATIR_DURUMU.csv'
if master.exists():
    rows=read_csv(master); fields=list(rows[0].keys()); cmap={(c['file'],c['label']):c for c in changes}
    for r in rows:
        c=cmap.get((r['file'],r['label']))
        if c:
            if not r.get('old_tur'): r['old_tur']=c['old_tur']
            r['current_tur']=c['new_tur']; r['decision']='DEĞİŞTİ'; r['review_status']='SON_KONTROL_v0.12'
            r['reason']='Son test adayı kontrolü: '+c['reason']
    write_csv(master,rows,fields)

# Copy key report to root later handled by build script.
print(f'Applied {len(changes)} unique final-audit changes')
for c in changes:
    print(f"{c['file']} :: {c['label']} :: {c['old_tur']} -> {c['new_tur']}")
