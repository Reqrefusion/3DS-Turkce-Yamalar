#!/usr/bin/env python3
from pathlib import Path
import csv, shutil, re, json

BASE=Path('/mnt/data/sushi_work/review_v11_work')
CSV_DIR=BASE/'CSV'
RAP=BASE/'Raporlar'
OUT=Path('/mnt/data/sushi_work/review_v11')
OUT.mkdir(parents=True,exist_ok=True)

# control-style sequences in the escaped CSV representation
RESET='\\u000E\\u0000\\u0003\\u0004\\u0000＀'
YELLOW='\\u000E\\u0000\\u0003\\u0004Ü＀'
BLUE='\\u000E\\u0000\\u0003\\u0004渀＀'
RED='\\u000E\\u0000\\u0003\\u0004껿＀'
PINK='\\u000E\\u0000\\u0003\\u0004쳿Ｏ'
ITEM='\\u000E\\u0000\\u0003\\u0004ﾑ＞'

def read_csv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

def write_csv(path, fields, rows):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with Path(path).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

files={}; rows={}
for p in sorted(CSV_DIR.glob('*.csv')):
    with p.open(encoding='utf-8-sig',newline='') as f:
        rr=list(csv.DictReader(f)); fields=list(rr[0].keys()) if rr else ['label','index','deu','eng','esp','fra','ita','nld','tur']
    files[p.name]=(fields,rr)
    for r in rr: rows[(p.name,r['label'])]=r

master_prev=read_csv(RAP/'TUM_10676_SATIR_DURUMU.csv')
master_map={(r['file'],r['label']):r for r in master_prev}
prev_changes=read_csv(RAP/'INCELEME_DEGISIKLIKLERI.csv') if (RAP/'INCELEME_DEGISIKLIKLERI.csv').exists() else []
prev_cum=read_csv(RAP/'SATIR_BAZLI_INCELEME_KUMULATIF.csv') if (RAP/'SATIR_BAZLI_INCELEME_KUMULATIF.csv').exists() else []

changes=[]; rechecked={}

def add_recheck(fn,lab,decision,reason):
    if (fn,lab) not in rows: raise KeyError((fn,lab))
    rechecked[(fn,lab)]=(decision,reason)

def setv(fn,lab,new,reason,category='KALİTE'):
    r=rows[(fn,lab)]; old=r['tur']
    add_recheck(fn,lab,'DEĞİŞTİ',reason)
    if old==new: return
    r['tur']=new
    changes.append({'round':'v0.11','category':category,'file':fn,'label':lab,'eng':r['eng'],'deu':r['deu'],'esp':r['esp'],'fra':r['fra'],'ita':r['ita'],'nld':r['nld'],'old_tur':old,'new_tur':new,'reason':reason})

def same(fn,lab,reason): add_recheck(fn,lab,'AYNI KALDI',reason)

# ------------------------------------------------------------------
# A) Third-pass semantic/copy-paste/typo fixes
# ------------------------------------------------------------------
setv('scene_puzzlebattle.csv','Enemy_StgWin_143','İmparatorluğun tasarladığı\\nkusursuz gelecekten kork!',
     'İlk geçişte Enemy_StgWin_286 ile aynı Türkçeye kopyalanmıştı. EN/DE/ES/FR/IT/NL bu satırın İmparatorluğun gelecek vizyonundan söz ettiğini açıkça doğruluyor; Manyetik Atış satırından ayrıldı.','KALİTE/kopyala-yapıştır')
setv('scene_puzzlebattle.csv','Enemy_StgWin_286','Manyetik Atışın ezici\\ngücü karşısında titre!',
     'Bu satırın kaynağı Magnetic Shot gücü. Önceki Türkçe Enemy_StgWin_143 ile yanlışlıkla aynıydı; altı resmî dil de Manyetik Atış/kanon gücünü koruyor.','KALİTE/kopyala-yapıştır')
setv('stageEndArea04Ex004.csv','CharaSerif_03_M',
     f'Suşi ruhu {ITEM}Popokan{RESET} ile bağ kurdun!\\nYeteneği {ITEM}Bütçe Vurucu{RESET}!',
     'Kaynak “You befriended...” fiilini içeriyor; Türkçede yalnız ruh adı kalmış ve eylem düşmüştü. Dinamik/vurgu komutları korunarak “ile bağ kurdun” geri getirildi.','KALİTE/eksik-anlam')
setv('scene_puzzlebattle.csv','Enemy_StgLose_200','O tapınağı nereden duydun?!\\nGizliydi!',
     '“tapınakyi” yazım/çekim hatasıydı. Shrine burada mezar/türbe değil, oyun genelindeki tapınak terminolojisi; doğru belirtme hâli “tapınağı”.','DİL/yazım')
setv('scene_puzzlebattle.csv','Enemy_StgLose_258','Peki, tapınağı buldun.\\nNe istiyorsan yap.',
     '“tapınakyi” çekim hatası düzeltildi; diğer diller de temple/sanctuary anlamını doğruluyor.','DİL/yazım')
setv('scene_puzzlebattle.csv','Player_StgAdvice057',
     rows[('scene_puzzlebattle.csv','Player_StgAdvice057')]['tur'].replace('eşyayi','eşyayı'),
     'Belirtme hâli yazım hatası “eşyayi” → “eşyayı”; vurgu kontrol dizisi aynen korundu.','DİL/yazım')
setv('stageEndM031.csv','CharaSerif_20_M','Anlaşıldı! Vurucu sözü!',
     'Striker’s honor burada bir söz verme/şeref yemini. “vurucu şerefi” hem küçük harfle başlıyor hem de doğal Türkçe değil; ES/FR/IT/NL “söz/şeref sözü” anlamını doğruluyor.','KALİTE/deyim')
setv('stageEndM031.csv','CharaSerif_20_F','Anlaşıldı! Vurucu sözü!',
     'M/F aynı kaynak ve Türkçede cinsiyet ayrımı yok; “Striker’s honor” doğal “Vurucu sözü!” olarak tekleştirildi.','KALİTE/deyim')
setv('scene_puzzlebattle.csv','Enemy_StgLose_056','İleride benden daha güçlüleri var.\\nTetikte olsan iyi olur.',
     'İkinci cümle yanlışlıkla küçük harfle başlıyordu; anlam zaten doğruydu, yalnız yazım düzeltildi.','DİL/yazım')
setv('scene_puzzlebattle.csv','Enemy_StgWin_204','Ben bu timin en dişlisiyim;\\nkaybetmen kaçınılmazdı.',
     'Önceki Türkçe yalnız “timin en dişlisiyim” kısmını taşıyor, “so you were bound to lose” sonucunu düşürüyordu. DE/ES/FR/IT/NL de iki parçalı böbürlenmeyi koruyor.','KALİTE/eksik-anlam')
setv('scene_puzzlebattle.csv','TxtPuzzleSettlementSerifEnemy09','BULMACA YETENEĞİN...\\nNEREDEYSE. KUSURSUZ.',
     'Robotun kasıtlı mekanik noktalaması korunurken “puzzle-solving skill” bilgisi Türkçede tamamen düşmüştü. Tüm resmî diller bulmaca yeteneğini açıkça söylüyor.','KALİTE/eksik-anlam')
for lab in ['Player_StgWin_288','Player_StgWin_288_f']:
    setv('scene_puzzlebattle.csv',lab,'Şey... bilmiyorum, kapıştık mı?\\nBen de hatırlamıyorum.',
         'Kaynakta tereddütlü “Umm... I don’t know” girişi var; eski Türkçe doğrudan soruya atlıyordu. DE/ES/FR/IT/NL tereddüt tonunu koruyor.','KALİTE/karakter-sesi')
setv('scene_puzzlebattle.csv','Enemy_StgLose_143','Sonsuz yeme ülkümüz...\\nNeredeyse gerçekleşmişti...',
     '“Almost...there...” eski Türkçede yalnız “Neredeyse...” kalıyordu. Dramatik yarım kalmış ton korunarak Türkçede anlam tamamlandı.','KALİTE/eksik-anlam')
setv('scene_puzzlebattle.csv','Enemy_StgLose_077','B-bu demek...\\nyenilginin tadı böyleymiş...',
     'Kaynakta kekeleme ve dramatik keşif var; eski Türkçe anlamı veriyor ama karakter sesini düzleştiriyordu.','KALİTE/karakter-sesi')
setv('database_movieSerif_3C.csv','MovieSerifText_3c_0008_M','Diğer İmparatorluk generali\\ngörevden alındı.',
     '“General meslektaşınız” Türkçede bürokratik ve yapay. IT/NL doğrudan “diğer/öteki general”, ES/FR “yoldaş” diyor; bağlama en doğal karşılık seçildi.','KALİTE/doğallık')
setv('stageBeginM057.csv','CharaSerif_03_M','Suşiye... öff... “suş” deyip\\naşağılayanlara suşi yok.',
     '“ugh” İngilizce bırakılmış ve noktalama sıkışıktı. “soosh” yanlış telaffuz şakası oyun genelindeki “suş” standardıyla korunup cümle doğal Türkçeye çekildi.','KALİTE/espri+doğallık')

# ------------------------------------------------------------------
# B) Terminology consistency
# ------------------------------------------------------------------
for fn,lab in [
 ('stageBeginM072.csv','CharaSerif_00_M'),('stageEndM062.csv','CharaSerif_06_M'),
 ('chapterBeginM005.csv','CharaSerif_17_M'),('chapterBeginM005.csv','CharaSerif_36_M')]:
    r=rows[(fn,lab)]
    setv(fn,lab,r['tur'].replace("Fort Fugu'ya","Fugu Kalesi'ne").replace('Fort Fugu','Fugu Kalesi'),
         'Aynı mekân database_stage ve film özetlerinde “Fugu Kalesi” olarak kullanılıyor. Tek kalan İngilizce “Fort Fugu” kullanımı oyun genelindeki Türkçe yer adına çekildi.','TERİM/tutarlılık')
setv('database_cmn.csv','SushiName_Bintoro','Yağlı Albakor Ton Balığı',
     'Albacore tür adı İngilizce bırakılmıştı. Türkçede yerleşik yazım “albakor”; sushi adı daha doğal ve tamamı Türkçeleştirilmiş oldu.','TERİM/gıda')
setv('stageBeginM093.csv','CharaSerif_00_M',rows[('stageBeginM093.csv','CharaSerif_00_M')]['tur'].replace('sushiyle','suşiyle'),
     'Tek bir sahnede “sushi” İngilizce yazımı kalmıştı; oyun genelindeki “suşi” standardına çekildi.','TERİM/tutarlılık')
for lab in ['CharaSerif_26_M','CharaSerif_26_F']:
    setv('stageBeginM072.csv',lab,'Rüyanda görürsün! Suşi Kurtuluş Cephesi\\ndünyanın dört yanında savaşıyor! Planın işlemez!',
         'Sushi Liberation Front oyunun büyük bölümünde “Suşi Kurtuluş Cephesi”. Burada hem “Özgürlük” sapması hem küçük harf vardı; ayrıca “Dream on!” Türkçede doğal “Rüyanda görürsün!” yapıldı.','TERİM+KALİTE')
setv('chapterBeginM002.csv','CharaSerif_06_M',
     rows[('chapterBeginM002.csv','CharaSerif_06_M')]['tur'].replace('suşi Kurtuluş Cephesi','Suşi Kurtuluş Cephesi'),
     'Özel örgüt adı cümle içinde yanlışlıkla küçük harfle başlamıştı. Terminoloji değişmedi; yazım standardize edildi.','DİL/yazım')
setv('scene_puzzlebattle.csv','Enemy_StgWin_075',rows[('scene_puzzlebattle.csv','Enemy_StgWin_075')]['tur'].replace("SLF'in","SLF'nin"),
     'SLF kısaltmasının iyelik eki diğer dosyalarda “SLF’nin” olarak kullanılıyor; tek sapma standardize edildi.','TERİM/yazım')
for lab in ['CharaSerif_04_M','CharaSerif_04_F']:
    setv('stageBeginM062.csv',lab,'Suşi Kurtuluş Cephesi bu! Musashi’yi\\nbizzat buraya göndermişler!',
         '“Bu Suşi Kurtuluş Cephesi!” İngilizce söz dizimini taşıyordu. Örgüt adı korunarak Türkçe ünlem yapısı doğal hâle getirildi; M/F cinsiyetsiz Türkçede tekleştirildi.','KALİTE/doğallık')
setv('stageBeginM053.csv','CharaSerif_00_M','Suşi Kurtuluş Cephesi bu!\\nBurada HİÇ olmamaları gerekiyordu!',
     '“Bu Suşi Kurtuluş Cephesi!” yapay söz dizimi düzeltildi; kaynak vurgusundaki ALL etkisi Türkçede HİÇ ile korunuyor.','KALİTE/doğallık')
for lab in ['MovieInfo_3C','MovieInfo_EVC5S','MovieInfo_5A']:
    setv('database_movieInfo.csv',lab,rows[('database_movieInfo.csv',lab)]['tur'].replace('Dehşet Generali','Korkunç General'),
         'Dread General oyunun 11 başka kullanımında “Korkunç General” olarak standardize edilmişti; film özetlerinde kalan “Dehşet Generali” sapmaları giderildi.','TERİM/tutarlılık')
setv('database_movieInfo.csv','MovieInfo_EVC3S',
     rows[('database_movieInfo.csv','MovieInfo_EVC3S')]['tur'].replace(f'{RESET}\\n.',f'{RESET}.'),
     'Vurgu kapandıktan sonra nokta tek başına yeni satıra düşmüştü. Metin/kontrol kodu aynı tutulup noktalama doğru yere alındı.','TEKNİK/UI-noktalama')

# ------------------------------------------------------------------
# C) Tutorial semantic highlights: fix lost/empty spans, preserve concepts
# ------------------------------------------------------------------
setv('database_tipsInfo.csv','TipsPage1_015',
     f"Musashi'nin savaştaki azami {BLUE}Can{RESET} değeri,\\n{BLUE}Dayanıklılığı{RESET} ile etkin ruhların {BLUE}Savunma{RESET}\\ndeğerlerinin {YELLOW}toplamına{RESET} eşittir.",
     'Kaynakta HP/Stamina/Defense ile “sum total” ayrı anlamlı vurgular. Türkçede sarı toplam vurgusu boş span hâline gelmişti; dört kavram yeniden görünür metne bağlandı.','TEKNİK/vurgu')
setv('database_tipsInfo.csv','TipsPage2_016',
     f'{BLUE}Yetenek Seviyelerini{RESET}, ruha\\n{BLUE}Yetenek Tılsımı{RESET} kullanarak veya savaştan sonra\\nseninle bağ kurmak isteyen bir ruhtan\\n{BLUE}Suşi Özü{RESET} alarak yükseltebilirsin.\\n{BLUE}Yetenek Tılsımlarını{RESET} akıllıca kullan!',
     'Kaynak son cümlede Skill Charms terimini tekrar mavi vurguluyor; Türkçede son vurgu tamamen düşmüştü. Bağ terminolojisi korunarak eksik vurgu geri getirildi.','TEKNİK/vurgu')
setv('database_tipsInfo.csv','TipsPage2_018',
     f'Bir başlangıç tabağı seçmek için\\n{BLUE}A Düğmesine{RESET} bas. (İmleci tabağa getirmek için\\n{BLUE}Çember Çubuğu{RESET}nu kullanabilirsin.)\\n{YELLOW}A Düğmesini basılı tut{RESET} ve {BLUE}Çember Çubuğu{RESET} ile\\ndaha fazla tabak bağla; suşiyi yemek için\\n{BLUE}A Düğmesini{RESET} {YELLOW}bırak{RESET}!',
     'Kaynağın son adımında “release” sarı, “A Button” mavi ayrı vurgular. Türkçede ikisi tek sarı span olmuştu; kullanım adımı ve renk anlamı yeniden ayrıldı.','TEKNİK/vurgu')
setv('database_tipsInfo.csv','TipsPage3_018',
     f'{BLUE}Çember Çubuğu{RESET}nu kullanarak {YELLOW}Musashi’yi hareket ettir{RESET};\\nönündeki yığını fırlatmak için {BLUE}X Düğmesine{RESET} bas.\\nYığınları hızlıca art arda fırlatmak için\\n{BLUE}X Düğmesine{RESET} {YELLOW}art arda bas{RESET}!',
     'Kaynak ikinci X Button’ı mavi, repeatedly pressing eylemini sarı vurguluyor. Türkçede ikisi tek sarı span olmuştu; beş anlamlı kavramın tamamı tekrar ayrı vurgulandı.','TEKNİK/vurgu')
setv('database_tipsInfo.csv','TipsPage1_023',
     f'Yolculuğunda bir noktada mutlaka\\nBağsız Tabakla karşılaşırsın.\\nBu, {YELLOW}sahibi olmayan ama içinde bir suşi ruhu\\nsaklı olan{RESET} {BLUE}Bağ Tabağıdır{RESET}!',
     'Kaynak “pledge plate” ile “sahibi yok ama ruh içeriyor” koşulunu iki ayrı renkle vurguluyor. Türkçede koşul vurgusu tamamen kayıptı.','TEKNİK/vurgu')
setv('database_tipsInfo.csv','TipsPage1_024',
     f'{YELLOW}Her aşamada{RESET} {YELLOW}3{RESET} {BLUE}yıldız{RESET} kazanabilirsin.\\nHer {BLUE}yıldız{RESET} için o aşamadaki\\n{YELLOW}özel koşulu{RESET} yerine getirmen gerekir.',
     'Türkçede yıldız çevresinde iki boş renk spanı kalmıştı. ES/DE/IT gibi resmî diller de iç içe İngilizce vurguyu sadeleştiriyor; anlamsız boş komutlar kaldırılıp kavram vurguları korunuyor.','TEKNİK/vurgu')
setv('database_tipsInfo.csv','TipsPage2_024',
     f'Her aşamanın {YELLOW}yıldız kazanma koşullarını{RESET}\\n{BLUE}harita ekranında{RESET} görebilirsin.\\nSavaş sırasında {BLUE}Başlat{RESET} ile oyunu {YELLOW}duraklatıp{RESET}\\nkoşullara yeniden bakabilirsin.',
     'Koşullar ile harita ekranı arasında görünür metni olmayan mavi span vardı. Diğer resmî yerelleştirmeler yıldız vurgusunu farklı biçimde birleştiriyor; boş span kaldırılıp anlamlı dört vurgu bırakıldı.','TEKNİK/vurgu')
setv('homeShrine.csv','homeShrine_first_rank_08_M',
     f'{ITEM}Vurucu rütbeni{RESET} {PINK}nasıl yükselteceğini{RESET}\\nartık {ITEM}Gizli Tomar{RESET}dan görebilirsin.',
     'Kaynakta Secret Scroll / how to raise / striker rank üç ayrı vurgu. Türkçede son “vurucu rütbesi” vurgu spanı boş kalmıştı; üç kavram doğal Türkçe söz dizimiyle tekrar bağlandı.','TEKNİK/vurgu')
setv('homeSushibar.csv','homeSushibar_02_a_03_M',
     f'Onlara ulaşmak için önce {RED}bölgeyi temizlemen{RESET} ve\\n{RED}bol bol ★{RESET} toplaman gerekiyor.',
     'Kaynak “clearing” ve “lots of ★” ifadelerini ayrı vurguluyor. Türkçede ilk kırmızı span boştu; vurgu doğru eyleme taşındı.','TEKNİK/vurgu')
setv('homeSushibar.csv','homeSushibar_03_in_02_M',
     f'Sence {PINK}bol bol ★{RESET} toplayıp\\n{PINK}bir bölgeyi temizleyince{RESET} bir\\n{PINK}gizli aşama{RESET} ortaya çıkar mı?',
     'Kaynak üç kavramı vurguluyor; Türkçede “clearing” spanı boştu. Üç anlamlı vurgu yeniden görünür ifadelere bağlandı.','TEKNİK/vurgu')
setv('database_tipsInfo.csv','TipsPage4_025',
     f'-{BLUE}Hazır Eşya{RESET} kullanamazsın.\\n-Her ruhun suşisi 30. seviyedeki hâlini yansıtır;\\nbu yüzden {BLUE}Mutfak Pürmüzü{RESET} gibi etkiler\\nhesaba katılmaz.',
     'İki madde korunurken ikinci madde “.-Her” gibi bitişik görünme riski taşıyordu. Satır kırımı ve noktalama temizlendi; iki vurgulu oyun terimi aynen korundu.','TEKNİK/UI')
for lab,n in [('Label_ExStage_Advent',40),('Label_ExStage30_Advent',30)]:
    r=rows[('scene_battleresult.csv',lab)]
    # preserve exact runtime zone-name command from current text
    m=re.search(r'(\\u000E\\u0000\\u0003\\u0004渀＀\\u000E\\u0001\\u0013\\u0000 ?\\u000E\\u0000\\u0003\\u0004\\u0000＀)',r['tur'])
    dyn=m.group(1) if m else f'{BLUE}\\u000E\\u0001\\u0013\\u0000 {RESET}'
    new=f'Bölgeyi temizleyip {n} yıldız topladın!\\n{dyn} bölgesinde\\n{YELLOW}gizli aşamalar{RESET} açıldı!'
    setv('scene_battleresult.csv',lab,new,
         'Eski Türkçede vurgu kapandıktan sonra “gizli aşamalar! açıldı!” biçiminde ünlem fiilin önüne düşüyordu. Dinamik bölge adı komutu korunarak cümle doğal ve güvenli sıraya alındı.','TEKNİK/UI')

# ------------------------------------------------------------------
# D) Favorite Power wordplay — recreate nutrient pun in Turkish
# ------------------------------------------------------------------
pun_changes={
 'SushiFavPowerName_Inari':'Molib-Den',
 'SushiFavPowerName_Ebi':'Arji-Nin',
 'SushiFavPowerName_Tako':'Kobala-Min',
 'SushiFavPowerName_CaliforniaRoll':'İyo-T',
 'SushiFavPowerName_Bintoro':'Niya-Sin',
 'SushiFavPowerName_Maguro':'His-Tidin',
 'SushiFavPowerName_Anago':'Reti-Nol',
 'SushiFavPowerName_Kinmedai':'Fos-For',
 'SushiFavPowerName_Chuutoro':'Piri-Doks',
}
pun_reason={
 'SushiFavPowerName_Inari':'Molyb-D, molibden/molybdenum kelime oyunu. “Molib-D” bağlantıyı yarıda bırakıyordu; “Molib-Den” Türkçe molibden sözcüğünü duyuruyor.',
 'SushiFavPowerName_Ebi':'Arg-9, arginine/arjinin üstüne kurulmuş. FR/DE de besin adını bozarak şaka yapıyor; “Arji-Nin” Türkçe “arjinin” sesini koruyor.',
 'SushiFavPowerName_Tako':'Cobal, cobalamin/B12 göndermesi. “Kobalt” başka elemente kayıyordu; “Kobala-Min” gerçek hedef olan kobalamini duyuruyor.',
 'SushiFavPowerName_CaliforniaRoll':'Io-9, iodine/iyot göndermesi. “İyo-T” Türkçe “iyot” sözcüğünü doğrudan seslendiriyor.',
 'SushiFavPowerName_Bintoro':'Nia-Zin, niacin/niasin göndermesi. “Niya-Sin” Türkçe niasin sesini koruyup uydurma güç adı havasını sürdürüyor.',
 'SushiFavPowerName_Maguro':'Hist-9, histidine/histidin göndermesi. “His-Tidin” Türkçe histidini tanınır hâle getiriyor.',
 'SushiFavPowerName_Anago':'Retin-O, retinol göndermesi. “Reti-Nol” besin adını Türkçede doğrudan yakalıyor.',
 'SushiFavPowerName_Kinmedai':'Phospho, phosphorus/fosfor göndermesi. “Fos-For” hem gerçek Türkçe sözcüğü hem oyunlu bölünmeyi koruyor.',
 'SushiFavPowerName_Chuutoro':'P-Dox, pyridoxine/piridoksin göndermesi. “Piri-Doks” Türkçe besin adını daha görünür kılıyor.'
}
for base,new in pun_changes.items():
    for lab in [base,base+'_lc']:
        if ('database_cmn.csv',lab) in rows:
            setv('database_cmn.csv',lab,new,pun_reason[base]+' Diğer dillerin çoğu da birebir İngilizceyi korumak yerine kendi kelime oyununu yaratıyor.','KALİTE/kelime-oyunu')
# roasted Ebi Z variant
for lab in ['SushiFavPowerName_EbiRoast','SushiFavPowerName_EbiRoast_lc']:
    setv('database_cmn.csv',lab,'Arji-Nin Z',pun_reason['SushiFavPowerName_Ebi']+' Z sürümü aynı şaka ailesiyle eşlendi.','KALİTE/kelime-oyunu')

# ------------------------------------------------------------------
# E) Manually rechecked but intentionally unchanged rows
# ------------------------------------------------------------------
same('database_movieSerif_5B.csv','MovieSerifText_5b_0071_M',
     'Tek başına bakınca yanlış görünüyor; ancak bir sonraki MovieSerifText_5b_0080_M ile birlikte okununca Türkçe “Benim yöntemlerime karşı... / kazanabileceğini mi sanıyorsun?” diye doğru ve doğal bir devrik yapı kuruyor. Bu nedenle değiştirilmedi.')
same('database_movieSerif_5B.csv','MovieSerifText_5b_0080_M',
     'Önceki etiketle çapraz satır söz dizimi oluşturuyor; EN satır sırasını Türkçede ters çevirmek anlam kaybı değil, doğal yerelleştirme. Değiştirilmedi.')
same('scene_puzzlebattle.csv','Enemy_StgLose_060',
     '“Don’t get a swelled head” deyimi Türkçede “Zafer başına vurmasın!” ile birebir sözcük değil ama aynı mecazı doğal biçimde veriyor; DE/IT/NL de “başına çıkmak” deyimini kullanıyor. İyi yerelleştirme olduğu için korundu.')
for lab in ['Player_StgWin_292','Player_StgWin_292_f']:
    same('scene_puzzlebattle.csv',lab,'“That’s what sushi striking is about! Get with the program!” için “İşin raconu bu! Öğren artık!” Türkçede kısa, karakterli ve işlevsel; literal çeviriden daha iyi olduğu için korundu.')
for lab in ['homeSushibar_05_stone_11_M','homeSushibar_05_stone_11_F']:
    same('homeSushibar.csv',lab,'“You’re rocking my world” satırındaki rock kelime oyunu “Taş kesildim, Archie!” ile taş üzerinden yeniden kurulmuş. Anlam serbest ama espri işlevi güçlü; korunması tercih edildi.')
same('stageBeginArea06Ex006.csv','CharaSerif_08_M','“Who’s gonna spot me now?!” spor salonu jargonudur. “Şimdi bana kim spot atacak?!” Türk oyuncuların ağırlık antrenmanı jargonunda anlaşılır ve karakterin kas takıntılı sesine uyuyor; bilinçli olarak değiştirilmedi.')
same('database_godInfo.csv','GodInfo_God118','“laughing game” bağlamı diğer dillerle kontrol edildi; amaç gülmeden dayanma oyunu. Mevcut “Gülmeme oyununda hiç yenilmemiştir.” önceki düzeltmeyle doğru ve doğal, korundu.')
same('database_godInfo.csv','GodInfo_God107','Popülerlik cümlesi daha önce doğal Türkçeye çekilmiş; “tek ölçütün popülerlik olduğuna yürekten inanır” anlam ve karakter tonu bakımından yeterli, yeniden oynanmadı.')
same('database_cmn.csv','GodSkillName_DamageReflection','“Dish Served Cold” intikam deyimine gönderme. “İntikam Soğuk Yenir” Türkçede aynı deyimsel espriyi yeniden kuruyor; üçüncü geçişte de doğru bulundu.')
same('scene_puzzlebattle.csv','Enemy_StgLose_088','“Thanks a mil!” ile sonraki “A mill?” yanlış-anlama şakasını sürdürebilmek için “Bin teşekkür!” seçimi bilinçli. Sonraki Türkçe “Bin mi? Neye bineyim?” ile yeni bir homonim şaka kurduğu için korundu.')
same('scene_puzzlebattle.csv','Player_StgWin_088','“A mill?” İngilizce flour/mill şakasını Türkçeye taşımak mümkün olmadığından “Bin mi? Neye bineyim?” ile önceki “Bin teşekkür”e bağlanan yeni ses şakası kurulmuş. İşlevsel yerelleştirme olduğu için korundu.')
same('homeSushibar.csv','homeSushibar_16_a_07_M','“Buff Buffet” oyun genelinde “Takviye Büfesi” olarak tutarlı; buff=takviye ve buffet=büfe iki anlamı da taşıdığı için iyi kelime oyunu, korundu.')
same('database_cmn.csv','SushiFavPowerName_Engawa','“Riboflavor” için “Ribo-Lezzet” riboflavin kökünü ve flavor/lezzet şakasını birlikte taşıyor; üçüncü geçişte de başarılı bulundu.')

# ------------------------------------------------------------------
# Write updated CSV set
# ------------------------------------------------------------------
for fn,(fields,rr) in files.items(): write_csv(CSV_DIR/fn,fields,rr)

# v11 detailed report for all rechecked rows
review_rows=[]
for (fn,lab),(decision,reason) in sorted(rechecked.items()):
    r=rows[(fn,lab)]; prev=master_map.get((fn,lab),{})
    ch=next((x for x in reversed(changes) if x['file']==fn and x['label']==lab),None)
    review_rows.append({'round':'v0.11','file':fn,'label':lab,'index':r.get('index',''),
                        'previous_review_status':prev.get('review_status',''),'previous_decision':prev.get('decision',''),
                        'decision':decision,'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),
                        'old_tur':ch['old_tur'] if ch else prev.get('current_tur',r.get('tur','')),'new_tur':r.get('tur',''),'reason':reason})
review_fields=['round','file','label','index','previous_review_status','previous_decision','decision','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
write_csv(OUT/'V11_UCUNCU_GECIS_INCELEME.csv',review_fields,review_rows)
change_fields=['round','category','file','label','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
write_csv(OUT/'V11_YENI_DEGISIKLIKLER.csv',change_fields,changes)

# cumulative historical change report
combined=prev_changes+changes
write_csv(OUT/'INCELEME_DEGISIKLIKLERI.csv',change_fields,combined)
latest={}
for x in combined: latest[(x['file'],x['label'])]=x
write_csv(OUT/'INCELEME_SON_DURUM_ESSIZ.csv',change_fields,list(latest.values()))

# master 10,676 rows, preserving earlier reasons unless rechecked
master=[]
for fn in sorted(files):
    for r in files[fn][1]:
        key=(fn,r['label']); prev=master_map.get(key,{})
        if key in rechecked:
            dec,reason=rechecked[key]
            ch=next((x for x in reversed(changes) if x['file']==fn and x['label']==r['label']),None)
            master.append({'file':fn,'label':r['label'],'index':r.get('index',''),'review_status':'ÜÇÜNCÜ_GECİS_v0.11','decision':dec,
                           'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),
                           'old_tur':ch['old_tur'] if ch else prev.get('current_tur',r.get('tur','')),'current_tur':r.get('tur',''),'reason':reason})
        else:
            master.append({'file':fn,'label':r['label'],'index':r.get('index',''),'review_status':prev.get('review_status','İNCELENDİ_ÖNCEKİ'),'decision':prev.get('decision','AYNI KALDI'),
                           'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),
                           'old_tur':prev.get('old_tur',r.get('tur','')),'current_tur':r.get('tur',''),'reason':prev.get('reason','Önceki geçişte incelendi; v0.11 yüksek-risk taramasında yeni sinyal çıkmadı.')})
master_fields=['file','label','index','review_status','decision','eng','deu','esp','fra','ita','nld','old_tur','current_tur','reason']
write_csv(OUT/'TUM_10676_SATIR_DURUMU.csv',master_fields,master)

# cumulative latest audit per key
cum={(r['file'],r['label']):r for r in prev_cum}
for rr in review_rows:
    cum[(rr['file'],rr['label'])]={'round':'v0.11','file':rr['file'],'label':rr['label'],'index':rr['index'],'decision':rr['decision'],
                                  'eng':rr['eng'],'deu':rr['deu'],'esp':rr['esp'],'fra':rr['fra'],'ita':rr['ita'],'nld':rr['nld'],
                                  'old_tur':rr['old_tur'],'new_tur':rr['new_tur'],'reason':rr['reason']}
cum_fields=['round','file','label','index','decision','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
write_csv(OUT/'SATIR_BAZLI_INCELEME_KUMULATIF.csv',cum_fields,list(cum.values()))

print(json.dumps({'changed':len(changes),'rechecked':len(rechecked),'total_rows':sum(len(x[1]) for x in files.values())},ensure_ascii=False))
