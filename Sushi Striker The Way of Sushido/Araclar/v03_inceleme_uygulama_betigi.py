from pathlib import Path
import csv, shutil, os, re

ROOT=Path('/mnt/data/sushi_work')
SRC=ROOT/'review_v02'/'csv'
OUT=ROOT/'review_v03'/'csv'
if (ROOT/'review_v03').exists(): shutil.rmtree(ROOT/'review_v03')
OUT.mkdir(parents=True)
for p in SRC.glob('*.csv'): shutil.copy2(p, OUT/p.name)

# Load all rows in memory
files={}
for p in OUT.glob('*.csv'):
    with p.open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f)); fields=list(rows[0].keys()) if rows else ['label','index','deu','eng','esp','fra','ita','nld','tur']
    files[p.name]=(fields,rows)

changes=[]
def getrow(fn,label):
    for r in files[fn][1]:
        if r['label']==label:return r
    raise KeyError((fn,label))

def add(fn,label,new,reason,category='manuel'):
    r=getrow(fn,label); old=r['tur']
    if old==new:return
    r['tur']=new
    changes.append({'round':'v0.3','category':category,'file':fn,'label':label,'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),'old_tur':old,'new_tur':new,'reason':reason})

# ---------- PLEDGE -> BAĞ system, only rows whose EN actually uses pledge ----------
pledge_reason='Pledge mekaniği diğer dillerde Pakt/Allianz, alianza, amitié/alliance, patto/legame, band olarak yerelleştirilmiş; dini/kişisel “yemin” değil, ruh ile kurulan bağ/ittifak.'
repls=[
('Yemin Tabağı','Bağ Tabağı'),('yemin tabağı','bağ tabağı'),('Yemin plakası','Bağ Tabağı'),('yemin plakası','bağ tabağı'),('yemin plakas','bağ tabağ'),
('Yemin Suşisi','Bağ Suşisi'),('yemin suşisi','bağ suşisi'),('Yemin suşisi','Bağ suşisi'),('Yemin suşi','Bağ suşi'),('yemin suşi','bağ suşi'),
('yeminleştik','bağ kurduk'),('yeminleşmek','bağ kurmak'),('yeminleş','bağ kur'),
('yemin edebilmemiz','bağ kurabilmemiz'),('yemin edebilirsin','bağ kurabilirsin'),('yemin edebilir','bağ kurabilir'),
('yemin etmeyi','bağ kurmayı'),('yemin etmeyecek','bağ kurmayacak'),('yemin etmeye','bağ kurmaya'),('yemin etmek','bağ kurmak'),
('yemin edersen','bağ kurarsan'),('yemin ettiğim','bağ kurduğum'),('yemin etmiş','bağ kurmuş'),('yemin etti','bağ kurdu'),('yemin edecek','bağ kuracak'),
('yemin bağı kurdun','bağ kurdun'),('bir yemin yapabilirsen','bir bağ kurabilirsen'),('bir yemin oluşur','bir bağ kurulur'),('bir yemine\ngirelim','bir bağ\nkuralım'),
('Yeminimizden sonra','Bağ kurduktan sonra'),('yeminimizden sonra','bağ kurduktan sonra'),
]
for fn,(fields,rows) in files.items():
    for r in rows:
        if 'pledge' not in r.get('eng','').lower() or not r.get('tur'): continue
        old=r['tur']; new=old
        for a,b in repls:new=new.replace(a,b)
        if new!=old: add(fn,r['label'],new,pledge_reason,'terim')

# Hand-tune pledge rows after basic terminology replacement.
custom_pledge={
('database_achieveInfo.csv','AchieveName_006'):'Bağ Ustası',
('database_achieveInfo.csv','AchieveFirstBorder_006'):'%d suşi ruhuyla\nbağ kur!',
('database_achieveInfo.csv','AchieveInfo_006'):'%d suşi ruhuyla\nbağ kurdun!',
('database_movieSerif_1B.csv','MovieSerifText_1b_0059_M'):'Bu bir Bağ Tabağı.\nBir suşi ruhunun seni\nkabul ettiğini gösterir.',
('database_movieSerif_1B.csv','MovieSerifText_1b_0060_M'):'O suşiyi yediğin anda\nikimiz arasında bir bağ kuruldu.',
('database_godInfo.csv','GodInfo_God042'):"Jinrai'nin tek gerçek dengi.\nYetenekleri, bağ kurduğu\nkişinin yüreğine göre değişir.",
('stageEndArea03Ex008.csv','CharaSerif_02_M'):'Gel! Derhal benimle bağ kur!!',
('stageEndArea02Ex004.csv','CharaSerif_00_M'):'Ne gün ama... Sanırım benimle de\nbağ kurmak isteyeceksin, değil mi?',
('homeShrine.csv','homeShrine_first_rank_02_M'):'Rütben yükseldikçe daha fazla suşi ruhuyla\nbağ kurabilirsin.',
('homeShrine.csv','homeShrine_first_out_06_M'):'Kendini kanıtlarsan bu tabaktaki suşi ruhu\nseninle bağ kurmayı teklif edebilir.',
('homeSushibar.csv','homeSushibar_01_a_02_M'):'Üstelik harika yetenekleri olan suşi ruhları\ngelip seninle bağ kurmak isteyecek!',
('homeSushibar.csv','homeSushibar_08_b_05_M'):'Heykelin altı aslında bir\nbağ tabağıymış; pat! Kyatten ortaya çıkmış!',
('stageEndArea04Ex004.csv','CharaSerif_01_M'):'Sırada ben varım! Hadi,\nbağ suşimi ye de bağımızı kuralım!',
('stageEndArea06Ex010.csv','CharaSerif_07_M'):'Bağ kurduktan sonra, suşiyle kasın\nzirvesine çıkacağını söyledi.',
('stageEndArea06Ex010.csv','CharaSerif_11_M'):'Bütün bunları bildiğin hâlde yine de\nbenimle bağ kurmak istiyor musun?',
('stageEndArea06Ex010.csv','CharaSerif_13_M'):'Çok teşekkür ederim. Sana inanıyorum.\nVe şimdi—bağ suşisi.',
('stageEndArea06subEx002.csv','CharaSerif_00_M'):'Hımm... Ben \\u000E\\u0000\\u0003\\u0004ﾑ＞Garu-o\\u000E\\u0000\\u0003\\u0004\\u0000＀. Benimle bağ kurmaya mı geldin?',
('stageBeginM041.csv','CharaSerif_10_M'):'Tanışın: yalnızca benimle bağ kurmuş\nnihai suşi ruhu Ghozo!',
('stageBeginM041.csv','CharaSerif_13_M'):'Tanışın: yalnızca benimle bağ kurmuş\nnihai suşi ruhu Konkan!',
('stageBeginM083.csv','CharaSerif_13_M'):'Tanış: Konkan, yalnızca benimle bağ kurmuş\nnihai suşi ruhu!',
('stageEndArea05Ex004.csv','CharaSerif_00_M'):'Selam. Ben suşi ruhu \\u000E\\u0000\\u0003\\u0004�ｱGolekan\\u000E\\u0000\\u0003\\u0004\\u0000＀.\nBenimle bağ kurmak mı istiyorsun?',
('stageEndM008.csv','stageEndM009_21_M'):'Üçüncü bağını kurduğun için tebrikler.\nArtık tam anlamıyla bir suşi vurucusun.',
('stageEndM073.csv','CharaSerif_09_M'):"İmparatorluk'a zorla bağlanan ruhlara da,\nsana bağlı olanlara da üzülüyorum.",
('stageEndM073.csv','CharaSerif_14_M'):'Artık hiçbir suşi ruhu onunla\nbir daha asla bağ kurmayacak.',
('stageBeginArea06Ex010.csv','CharaSerif_03_M'):'Şöyle ki, bu ormanda tapınağı buldum.\nOradaki suşi ruhuyla bağ kurdum.',
('ShrineGetMode.csv','Child_ChoiceYes_M'):'Yaşasın, bağ kurduk! Ben \\u000E\\u0000\\u0003\\u0004ﾑ＞\\u000E\\u0001\\n\\u0000\\u000E\\u0000\\u0003\\u0004\\u0000＀!\nTanıştığımıza sevindim!',
('ShrineGetMode.csv','AncMan_ChoiceYes_M'):'Böylece bağımız mühürlendi!\nBen \\u000E\\u0000\\u0003\\u0004ﾑ＞\\u000E\\u0001\\n\\u0000\\u000E\\u0000\\u0003\\u0004\\u0000＀. Şeref duydum.',
('ShrineGetMode.csv','AncChild_Contact2_M'):'Sakıncası yoksa suşimi yer misin?\nBöylece aramızda bir bağ kurabiliriz.',
('ShrineGetMode.csv','Noblewoman_Contact2_M'):'Suşimden ye; böylece ikimiz arasında\nbir bağ kuralım.',
('ShrineGetMode.csv','Simplicity_Contact2_M'):'Bağ suşimi yemeni öneririm.\nBöylece aramızda bir bağ kurulur.',
('stageEndM003.csv','stageEndM004_06_M'):'Bak sen... Bir suşi ruhunun Bağ Tabağı.\nİmparatorluk vermiş olmalı.',
('stageEndM003.csv','stageEndM004_07_M'):'O tabaktaki ruhla yeni bir bağ kurabilirsen,\nsana çok yardımı dokunur.',
('stageEndM003.csv','stageEndM004_08_M'):'Mweheh... Pekâlâ, şimdi\nbağ tabağım kimde bakalım?',
('database_itemInfo.csv','ItemInfo_ScenarioSukajan'):'Babandan kalma eski bir ceket.\nAstarında suşi ruhlarının özleri,\nkollarında Bağ Tabakları saklanır.',
('database_itemInfo.csv','ItemInfo_ScenarioDictionary'):'Yeni suşi ruhlarıyla bağ kurdukça onların\nbilgilerini kendiliğinden ekleyen\neski bir kitap.',
('database_tipsInfo.csv','TipsPage1_019'):"Bir savaşı kazanınca düşmanın suşi ruhu\nseninle \\u000E\\u0000\\u0003\\u0004Ü＀bağ kurmayı\\u000E\\u0000\\u0003\\u0004\\u0000＀ teklif edebilir.\nÇünkü Musashi'nin saldırıları düşmanın Bağ\nTabağı'nı kırıp mevcut bağı bozabilir.",
('database_tipsInfo.csv','TipsPage2_019'):'Teklifini kabul edip ruhla bağ kurarsan,\n\\u000E\\u0000\\u0003\\u0004Ü＀o senin suşi ruhun olur\\u000E\\u0000\\u0003\\u0004\\u0000＀. Aynı türden bir ruhun\nzaten varsa, \\u000E\\u0000\\u0003\\u0004Ü＀Deneyim\\u000E\\u0000\\u0003\\u0004\\u0000＀ kazandıran\n\\u000E\\u0000\\u0003\\u0004渀＀Suşi Özü\\u000E\\u0000\\u0003\\u0004\\u0000＀ bırakıp gider.',
('database_tipsInfo.csv','TipsPage1_023'):'Yolculuğunda bir noktada mutlaka\nPotansiyel Tabakla karşılaşırsın.\nBu, sahibi olmayan ama içinde bir suşi ruhu\nsaklanan \\u000E\\u0000\\u0003\\u0004渀＀Bağ Tabağıdır\\u000E\\u0000\\u0003\\u0004\\u0000＀!',
('database_tipsInfo.csv','TipsPage2_023'):'Savaşta bunu \\u000E\\u0000\\u0003\\u0004渀＀Hazır Eşya\\u000E\\u0000\\u0003\\u0004\\u0000＀ olarak kullanırsan,\n\\u000E\\u0000\\u0003\\u0004Ü＀sonuca\\u000E\\u0000\\u0003\\u0004\\u0000＀ göre içindeki suşi ruhu\nortaya çıkıp \\u000E\\u0000\\u0003\\u0004Ü＀seninle bağ kurmayı teklif edebilir\\u000E\\u0000\\u0003\\u0004\\u0000＀.',
}
for (fn,lbl),new in custom_pledge.items(): add(fn,lbl,new,pledge_reason,'terim')

# Contract dish info: manually naturalize and unify pledge rank + Prepared Item.
for i,name in enumerate(['','Kazurava','Golekan','Crowkan','Garu-o','','Kyatten','Owlten','Suiten','Boneten','Batten','Faeten','Hohten']):
    lbl=f'ItemInfo_ContractDish{i:02d}'
    try:r=getrow('database_itemInfo.csv',lbl)
    except KeyError:continue
    m=re.search(r'Requires striker rank (\d+) to pledge',r['eng'])
    rank=m.group(1) if m else '?'
    who=(name+' ortaya çıkabilir') if name else 'bir suşi ruhu ortaya çıkabilir'
    new=f'Bunu Hazır Eşya olarak kullan; savaşta iyi performans\ngösterirsen {who}.\nBağ kurmak için Vurucu rütbesi {rank} gerekir.'
    add('database_itemInfo.csv',lbl,new,'Diğer diller “equipped/auto item” + savaş performansı + alliance rank anlamını açık veriyor; Türkçe daha doğal ve terimler tutarlılaştırıldı.','terim')

# Prepared Item global terminology and natural phrasing.
prepared_reason='Prepared Item diğer dillerde Auto-Item/objeto equipado/objet équipé gibi tek bir ekipman mekaniği; yamadaki dört farklı Türkçe karşılık “Hazır Eşya” olarak standardize edildi.'
prep_manual={
('scene_menumydata.csv','TxtPreparationItem'):'Hazır Eşya',
('stageEndM015.csv','CharaSerif_04_M'):'Bunu Hazır Eşya olarak ayarlarsan,\nsavaşta \\u000E\\u0000\\u0003\\u0004쳿Ｏmaks. CAN yarıya iner\\u000E\\u0000\\u0003\\u0004\\u0000＀.',
('homeShrine.csv','homeShrine_first_out_05_M'):'Bunu \\u000E\\u0000\\u0003\\u0004ﾑ＞Hazır Eşya\\u000E\\u0000\\u0003\\u0004\\u0000＀ olarak ayarla, sonra\nbir suşi savaşına gir.',
('stageEndM011.csv','stageEndM011_07_M'):'Zorlu bir düşmanla karşılaşınca savaştan önce\nbunu \\u000E\\u0000\\u0003\\u0004ﾑ＞Hazır Eşya\\u000E\\u0000\\u0003\\u0004\\u0000＀ olarak ayarlamayı unutma.',
('database_itemInfo.csv','ItemInfo_ReadyRetryS'):"Hazır Eşya olarak kullanırsan CAN'ın 0'a\ndüştüğünde seni az miktarda CAN'la diriltir.",
('database_itemInfo.csv','ItemInfo_ReadyRetryM'):"Hazır Eşya olarak kullanırsan CAN'ın 0'a\ndüştüğünde seni yarım CAN'la diriltir.",
('database_itemInfo.csv','ItemInfo_ReadyRetryL'):"Hazır Eşya olarak kullanırsan CAN'ın 0'a\ndüştüğünde seni tam CAN'la diriltir.",
('database_itemInfo.csv','ItemInfo_ReadyRetryC'):"Hazır Eşya olarak kullanırsan CAN'ın 0'a düştüğünde\nseni tam CAN'la diriltir ve Gücünü ikiye katlar.",
('database_itemInfo.csv','ItemInfo_LimitOverScore'):"Hazır Eşya olarak kullanırsan savaşa azami CAN'ın\nyarısıyla başlarsın ama skorun 1,5 kat artar.",
('database_tipsInfo.csv','TipsPage4_025'):'-\\u000E\\u0000\\u0003\\u0004渀＀Hazır Eşya\\u000E\\u0000\\u0003\\u0004\\u0000＀ kullanamazsın.\n-Her ruhun suşisi 30. seviyedeki hâlini yansıtır;\n\\u000E\\u0000\\u0003\\u0004渀＀Mutfak Pürmüzü\\u000E\\u0000\\u0003\\u0004\\u0000＀ gibi etkiler hesaba katılmaz.',
}
for k,v in prep_manual.items():add(*k,v,prepared_reason,'terim')
# menu prompts (were untranslated, included solely for terminology consistency)
add('scene_menuitem.csv','WinTxt_SetReadyItem01','\\u000E\\u0000\\u0003\\u0004渀＀\\u000E\\u0001\\u000B\\u0000\\u000E\\u0000\\u0003\\u0004\\u0000＀\nHazır Eşya olarak ayarlansın mı?',prepared_reason,'terim')
add('scene_menuitem.csv','WinTxt_SetReadyItem02','Hazır Eşya olarak \\u000E\\u0000\\u0003\\u0004渀＀\\u000E\\u0001\\u000B\\u0000\\u000E\\u0000\\u0003\\u0004\\u0000＀ yerine \\u000E\\u0000\\u0003\\u0004Ü＀\\u000E\\u0001\\u000C\\u0000\\u000E\\u0000\\u0003\\u0004\\u0000＀\nkullanılsın mı?',prepared_reason,'terim')
add('scene_menuitem.csv','WinTxt_RemoveReadyItem','\\u000E\\u0000\\u0003\\u0004渀＀\\u000E\\u0001\\u000B\\u0000\n\\u000E\\u0000\\u0003\\u0004\\u0000＀ Hazır Eşya olmaktan çıkarılsın mı?',prepared_reason,'terim')

# Sushi Struggles -> Suşi Savaşları, supported by DE/ES/FR/IT localizations using "war".
strug_reason='“Sushi Struggles” diğer dillerin çoğunda doğrudan Sushi War/Guerre/Guerra/Krieg; “Suşi Mücadeleleri” yapay kaldığı için lore terimi “Suşi Savaşları” olarak yerelleştirildi.'
strug_custom={
('database_movieSerif_0A.csv','MovieSerifText_0a_0006_M'):'Bu karanlık dönem tarihe\nSuşi Savaşları olarak geçti.',
('database_movieSerif_2A.csv','MovieSerifText_2a_0005_M'):'Böylece Suşi Savaşları\nyeniden alevlendi.',
('database_movieSerif_5A.csv','MovieSerifText_5a_0048_M'):"Suşi Savaşları'nda\nİmparatorluk'a karşı savaştım.",
('stageEndM057.csv','CharaSerif_32_M'):"Onu da Suşi Savaşları aldı elimizden.\nİmparatorluk'a borçlu olduğumuz bir acı daha.",
('database_area.csv','areaText_area01'):"Sıcak, huzurlu bir bölge. Suşi\nSavaşları'nı İmparatorluk'a\nkaybettikten sonra suşi açısından\nçoraklaşmış.",
('stageEndM046.csv','CharaSerif_25_M'):"Jubay, Suşi Savaşları'nda Cumhuriyet'in\nen güçlü vurucusuydu. “Efsanevi” sözü tam ona göre.",
('homeSushibar.csv','homeSushibar_11_d_02_M'):"Yaşlı Ausprey'yi bilirsin;\nSuşi Savaşları'nda savaşmış bir gazi.",
('stageEndM116.csv','CharaSerif_04_M'):"Seni görünce aklıma o eski\nSuuuş Savaşları günleri geldi.",
('stageEndM116.csv','CharaSerif_07_M'):"Sen de orada mıydın? Suşi Savaşları'nda\ntam olarak ne yaptın?",
('database_movieInfo.csv','MovieInfo_EVC1S'):"\\u000E\\u0000\\u0003\\u0004Ü＀Musashi\\u000E\\u0000\\u0003\\u0004\\u0000＀, Suşi Savaşları'nda anne babasını\nkaybeden diğer yetimleri doyurmak için\normana yiyecek aramaya gider.",
('database_movieInfo.csv','MovieInfo_EVC2S'):"İmparatorluğun Jinrai'yi ele geçirme girişimi\nSuşi Savaşları'nı yeniden alevlendirdi.\nBu sırada Musashi, \\u000E\\u0000\\u0003\\u0004Ü＀Tapınak Korusu\\u000E\\u0000\\u0003\\u0004\\u0000＀'nu\ngeri alma harekâtına katılır.",
('chapterBeginM001.csv','Prologue01_02_M'):"Suşi Savaşları'nda ailesini kaybetti\nve çocukluğunu bir yetimhanede geçirdi.",
('chapterBeginM001.csv','Prologue01_02_F'):"Suşi Savaşları'nda ailesini kaybetti\nve çocukluğunu bir yetimhanede geçirdi.",
('chapterBeginM009.csv','CharaSerif_06_M'):"Kendimi Suşi Savaşları'nın içine attım.",
('stageEndM129.csv','CharaSerif_05_M'):"Majesteleri, önceki İmparator olan babasını\nSuşi Savaşları'nda kaybetti.",
}
for k,v in strug_custom.items():add(*k,v,strug_reason,'lore')

# ---------- Opening narration ----------
R='Diğer diller aynı anlatımı daha doğal/epik kuruyor; İngilizce söz dizimini taklit etmek yerine Türkçe anlatı ritmi ve anlamı korundu.'
manual={
('database_movieSerif_0A.csv','MovieSerifText_0a_0001_M'):'dünyanın sunduğu bütün nimetler arasında\nbirinin değeri hepsini aşıyordu...',
('database_movieSerif_0A.csv','MovieSerifText_0a_0002_M'):'...suşi denen o eşsiz yemek.',
('database_movieSerif_0A.csv','MovieSerifText_0a_0003_M'):'O eşsiz tadı arzulayanlar arasında\nbitmek bilmeyen çatışmalar çıktı.',
('database_movieSerif_0A.csv','MovieSerifText_0a_0004_M'):'Bu çekişme sonunda açık savaşa dönüştü.\nBir yanda dünyanın bütün suşisini\ntekeline almak isteyen İmparatorluk...',
('database_movieSerif_0A.csv','MovieSerifText_0a_0005_M'):'...öte yanda suşiyi bütün dünyayla\npaylaşmak isteyen Cumhuriyet vardı.',
('database_movieSerif_0A.csv','MovieSerifText_0a_0007_M'):"Cumhuriyet yenilince İmparatorluk,\nsuşinin adını anmayı bile kesinlikle yasakladı.",
('database_movieSerif_0A.csv','MovieSerifText_0a_0008_M'):'Suşi yemekse bundan da\nbüyük bir suç sayılıyordu.',
}
for k,v in manual.items():add(*k,v,R,'diyalog/anlatı')

# ---------- Opening song: freer localization, following ES/FR/DE/IT strategy ----------
song='Şarkı sözünde diğer yerelleştirmeler anlamı birebir izlemek yerine ritim, enerji ve kelime oyununu yeniden yazıyor; Türkçe de şarkı sözü gibi akacak şekilde serbestleştirildi.'
OP={
'0002_M':'Hey millet! Hoş geldiniz!',
'0003_M':'Siparişleri alayım!',
'0004_M':'Suşi ruhu stili!\nSamuray kıvılcım saçar!',
'0005_M':'Işıl ışıl şeritler\ndurmadan akıp gitsin!',
'0006_M':"Bantlar dönsün durmadan,\nDJ'nin plağı gibi!",
'0007_M':'Parıl parıl mücevherler\ntabaklarda göz kamaştırır!',
'0008_M':'Kaçmaz bu fırsat,\ntam bir gurme ziyafeti!',
'0009_M':'Dayanamam, karnım zil çalıyor,',
'0010_M':'iştahım kabarıyor,\nağzım sulanıyor,',
'0011_M':'sel gibi taşıyor!\nHadi, hazırdır artık!',
'0012_M':'Bak, Suşi Kapısı açıldı!',
'0013_M':'Bir adım at!',
'0014_M':'Önümde dönen şu dünyaya\ndalmaya hazırım!',
'0015_M':'Suşi vurucuysan\nsonuna kadar savaş, hey!',
'0016_M':'Çocuklar için\nyüreğim kocaman!',
'0018_M':'Dünya önümde bir tabak—\nhaydi, sofraya!',
'0021_M':'Gümbür gümbür, yıkılsın!',
'0023_M':'Adım adım yükselirim!',
'0024_M':'Korku yok bende!\nNe varsa yerim!',
'0025_M':'Sonra dans et,\ndans dans dans dans!',
'0028_M':'Bu şansı kaçırmam!',
'0031_M':'Korku yok bende!\nKim varsa kapışırım!',
'0032_M':'Sonra dans et,\ndans dans dans dans!',
}
for s,v in OP.items(): add('database_movieSerif_OP.csv','MovieSerifText_OP_'+s,v,song,'şarkı/espri')

# ---------- Epilogue ----------
ep='Diğer diller bağlamı daha doğal ve duygusal kuruyor; Türkçede kelimesi kelimesine yapı yerine anlatıcı/karakter sesi güçlendirildi.'
EP={
'0002_M':"Suşi bir zamanlar denizlerde yaşayan\n“balık” denen hayvanlardan yapılırdı.",
'0003_M':'Ne var ki insanlar denizleri kirletti\nve balıkların soyu tükendi.',
'0004_M':'Fakat balıklar, olağanüstü güçlere sahip\nsuşi ruhları olarak yeniden doğdu.',
'0005_M':'Suşi armağanını yalnızca\nonun kıymetini bilenlere sundular.',
'0006_M':'Biz suşi ruhlarını yaşatan, suşiyi yerken\nduyduğunuz minnettarlıktır. Bunu hiç unutma.',
'0009_M':'Ama bir gün annemle yeniden\nbuluşacağıma eminim.',
'0009_F':'Ama bir gün annemle yeniden\nbuluşacağıma eminim.',
'0010_M':'Çünkü yediğimiz nimetin kıymetini\nbildiğimiz sürece, suşi sonsuza dek var olacak!',
'0010_F':'Çünkü yediğimiz nimetin kıymetini\nbildiğimiz sürece, suşi sonsuza dek var olacak!',
'0011_M':'Musashi ailesine kavuşacağı günü düşlüyordu.\nO gün gelene dek dostlarıyla suşi dolu\nbir hayat ona yetiyordu.',
}
for s,v in EP.items():add('database_movieSerif_EP.csv','MovieSerifText_ep_'+s,v,ep,'diyalog/anlatı')

# ---------- 1A dialogue ----------
dlg='İngilizce anlamı korundu; ES/FR/DE tonları da karşılaştırılarak Türkçede daha doğal, karaktere uygun ve gerektiğinde daha esprili ifade seçildi.'
A={
'0002_M':'Yiyebildiğim kadar meyve!', '0002_F':'Yiyebildiğim kadar meyve!',
'0006_M':'Ne bereketli gün! Hepsini\ntaşımakta zorlanıyorum.', '0006_F':'Ne bereketli gün! Hepsini\ntaşımakta zorlanıyorum.',
'0007_M':'Bu kez bütün çocukların\nkarnı doyacak!', '0007_F':'Bu kez bütün çocukların\nkarnı doyacak!',
'0008_M':'Vay, köyün baş salağı da gelmiş.',
'0010_M':'Off, bir de Kojiro çıktı!', '0010_F':'Off, bir de Kojiro çıktı!',
'0011_M':'Meyveleri dalından\ntopluyorsun ha?',
'0013_M':'Acayip tip...',
'0023_M':'(Şaşırmadım...)',
'0026_M':'İğrenç, kabul... ama bundan başka\nne yiyeceğiz?!','0026_F':'İğrenç, kabul... ama bundan başka\nne yiyeceğiz?!',
'0100_M':'Siz ahmaklar çöpleri\nmideye indirip...',
'0101_M':'...üstüne bir de nefis bir şeymiş\ngibi bayılıyorsunuz!',
'0029_M':'Çöpoburlar! Çöpoburlar!',
'0035_M':'Nereye gittiniz siz?','0035_F':'Nereye gittiniz siz?',
'0036_M':'Of ya! Yine bana yiyecek kalmadı.','0036_F':'Of ya! Yine bana yiyecek kalmadı.',
'0039_M':'Sana ne? Sen kimsin?','0039_F':'Sana ne? Sen kimsin?',
'0040_M':'Bana Franklin de. Bu kıtlık içindeki\ntopraklarda gezip dururum.',
'0045_M':'Ben de açım, herkes de!','0045_F':'Ben de açım, herkes de!',
'0046_M':'Seni suçlayamam.',
'0052_M':'Bunun kesinlikle aramızda\nkalacağına söz verirsen...',
'0053_M':'Sana suşi ziyafeti çektiririm!',
'0056_M':'Adını duymuşsundur. Dünyada\ndaha lezzetli bir şey yok.',
'0058_M':'Sana suşinin tadına bakma şansı veriyorum.\nNe dersin? Nefistir.',
'0062_M':'Bütün o aptal savaş, sırf şu\naptal suşi yüzünden çıktı!','0062_F':'Bütün o aptal savaş, sırf şu\naptal suşi yüzünden çıktı!',
'0068_M':'Ama bunların suçlusu suşi değil.',
'0069_M':'Suşi sadece mide\ndoldurmak için yenmez.',
'0106_M':'İnsanın içini gerçek bir\nsevinçle doldurur.',
'0070_M':'Delikanlı...\nBir lokma al, anlarsın.','0070_F':'Genç hanım...\nBir lokma al, anlarsın.',
# mishearing gag completely recreated in Turkish
'0075_M':'Suşi turpu mu?','0075_F':'Suşi turpu mu?',
'0076_M':'Turp değil! Suşi ruhu!',
'0077_M':'Suşi gurusu?','0077_F':'Suşi gurusu?',
'0078_M':'SUŞİ RUHU dedim!',
'0079_M':'Franklin, bundan emin\nmisin?',
'0081_M':'Peki, tamam... yapıyorum.',
'0089_M':'Bu MUHTEŞEM!','0089_F':'Bu MUHTEŞEM!',
'0092_M':'Bu... bu...','0092_F':'Bu... bu...',
'0096_M':'E hadi! Durma, yemeye devam!',
}
for s,v in A.items():add('database_movieSerif_1A.csv','MovieSerifText_1a_'+s,v,dlg,'diyalog/espri')
# gag reason override isn't needed in file log but generic is okay.

# ---------- 1B ----------
B={
'0002_M':'Doğrusu hakkını vermek lazım.\nPeşimize düşecek yüreğin varmış.',
'0003_M':'Hey! Veledi de götürüyoruz.',
'0008_M':"İmparatorluk'a tek yön\nbilet kazandın.",
'0009_M':'Uzun süre dönemezsin,\nçelimsiz.',
'0019_M':'Off... Düşündükçe\nkarnım daha çok acıkıyor.','0019_F':'Off... Düşündükçe\nkarnım daha çok acıkıyor.',
'0021_M':'Bu gök gürültüsü gibi gurultu...\nAncak destansı bir açlıktan çıkabilir!',
'0024_M':'Güce aç mısın?',
'0026_M':'Hem de nasıl!','0026_F':'Hem de nasıl!',
'0027_M':'Yap hadi! Güüüüüç ver bana!','0027_F':'Yap hadi! Güüüüüç ver bana!',
'0029_M':'Seni, besleyici bir gücün saklı olduğu\ntapınağa götürecek.',
'0031_M':'Peki, hangi tarafta?','0031_F':'Peki, hangi tarafta?',
'0038_M':'Öyle sıradan bir suşi değil—\nsomonlu.',
'0039_M':'Ne bekliyorsun?\nO destansı açlığı doyur!',
'0048_M':'Umarım açlığın dinmiştir.',
'0049_M':'Gücümün geri dönmesini\nsana borçluyum.',
'0050_M':'Suşiye ne büyük bir\nsevgiyle yaklaştın!',
'0052_M':'Sen yoksa...','0052_F':'Sen yoksa...',
'0056_M':"Ben İmparatorluk'tan kaçmış bir suşi ruhuyum.\nBir süredir bu tapınakta saklanıyorum.",
'0064_M':'Bu ceket, biz suşi ruhlarının özünü\niçinde taşıyıp saklayabilir.',
'0066_M':'Seninle işim zor olacak...',
'0073_M':'Ne yüce bir hayal!',
'0074_M':'Öyleyse gücüm senin olsun!',
}
for s,v in B.items():add('database_movieSerif_1B.csv','MovieSerifText_1b_'+s,v,dlg,'diyalog')

# ---------- 2A / 2B ----------
D2={
('database_movieSerif_2A.csv','MovieSerifText_2a_0001_M'):'Jinrai’nin yeri tespit edilmişti.',
('database_movieSerif_2A.csv','MovieSerifText_2a_0018_M'):"Üstelik Cumhuriyet'in\nsafına katılmıştı.",
('database_movieSerif_2A.csv','MovieSerifText_2a_0009_M'):'Bana bir şans daha verin!',
('database_movieSerif_2A.csv','MovieSerifText_2a_0010_M'):'Söyle... Jinrai kimi\nefendisi seçti?',
('database_movieSerif_2B.csv','MovieSerifText_2b_0001_M'):'Siz HARİKASINIZ!',
('database_movieSerif_2B.csv','MovieSerifText_2b_0002_M'):'Musashi sayesinde ormanı\neski hâline, sapasağlam döndürdük!',
('database_movieSerif_2B.csv','MovieSerifText_2b_0005_M'):'Sizden bir iyilik daha\nisteyeceğim.',
('database_movieSerif_2B.csv','MovieSerifText_2b_0006_M'):'Hem de büyük bir iyilik! Gelmiş geçmiş\nen iyi suşi restoranını açmak istiyorum!',
('database_movieSerif_2B.csv','MovieSerifText_2b_0014_M'):'Benim kadar senin de\nkafan karıştı mı?',
('database_movieSerif_2B.csv','MovieSerifText_2b_0023_M'):'Gözümde canlandıramıyorum.',
('database_movieSerif_2B.csv','MovieSerifText_2b_0025_M'):'Daha önce kimse yapmadı!\nBen bitirince burası suşi cenneti olacak!',
('database_movieSerif_2B.csv','MovieSerifText_2b_0027_M'):'Hayal kuracaksan büyük kur!',
('database_movieSerif_2B.csv','MovieSerifText_2b_0031_M'):"Bilge Kyatten'a bırak işi...\nçözülür işin gerisi!",
}
for k,v in D2.items():add(*k,v,dlg,'diyalog/espri')

# ---------- 3A/B/C, 4A ----------
D3={
('database_movieSerif_3A.csv','MovieSerifText_3a_0008_M'):'Birini kolluyorum.',
('database_movieSerif_3A.csv','MovieSerifText_3a_0013_M'):'Ve işte buldum.',
('database_movieSerif_3A.csv','MovieSerifText_3a_0013_F'):'Ve işte buldum.',
('database_movieSerif_3A.csv','MovieSerifText_3a_0017_M'):"Aynen. Ben Suşi Vurucusu\nCelia'yım!",
('database_movieSerif_3A.csv','MovieSerifText_3a_0018_M'):"İmparatorluk seni ortadan kaldırmam\niçin beni gönderdi.",
('database_movieSerif_3A.csv','MovieSerifText_3a_0021_M'):"Sen... İmparatorluk için mi çalışıyorsun?\nAma daha çocuksun.",
('database_movieSerif_3A.csv','MovieSerifText_3a_0021_F'):"Sen... İmparatorluk için mi çalışıyorsun?\nAma daha çocuksun.",
('database_movieSerif_3A.csv','MovieSerifText_3a_0024_M'):'Şimdi... asıl meseleye gelelim!',
('database_movieSerif_3B.csv','MovieSerifText_3b_0003_M'):'Suşinin gücü, insanlara\nverdiği neşe...','database_movieSerif_3B.csv|MovieSerifText_3b_0003_F':'',
}
# add carefully due to dictionary hack avoidance
for k,v in list(D3.items()):
    if isinstance(k,tuple):add(*k,v,dlg,'diyalog')
more3={
('database_movieSerif_3B.csv','MovieSerifText_3b_0003_F'):'Suşinin gücü, insanlara\nverdiği neşe...',
('database_movieSerif_3B.csv','MovieSerifText_3b_0004_M'):'Beni buraya getiren o...\ngücüm değil.',
('database_movieSerif_3B.csv','MovieSerifText_3b_0004_F'):'Beni buraya getiren o...\ngücüm değil.',
('database_movieSerif_3B.csv','MovieSerifText_3b_0006_M'):'Çok karanlık günler\ngeçirdiğin belli.',
('database_movieSerif_3B.csv','MovieSerifText_3b_0007_M'):'Surat asarak suşi yemek,\nsuşiye saygısızlık.',
('database_movieSerif_3B.csv','MovieSerifText_3b_0010_M'):'Öyle mi?',
('database_movieSerif_3B.csv','MovieSerifText_3b_0011_M'):'Bunu... daha önce hiç böyle\nsöyleyen olmadı.',
('database_movieSerif_3B.csv','MovieSerifText_3b_0012_M'):"Üstlerim hep 'daha hızlı ye,\ndaha çok ye' derdi...",
('database_movieSerif_3B.csv','MovieSerifText_3b_0021_M'):'Onların gözünde bir suşi vurucusundan\nbaşka bir şey değildim.',
('database_movieSerif_3B.csv','MovieSerifText_3b_0016_M'):'Ama suşiyi hâlâ sevmiyorum.',
('database_movieSerif_3B.csv','MovieSerifText_3b_0018_M'):'belki de senin suşide ne bulduğunu\nanlamayı öğrenebilirim.',
('database_movieSerif_3B.csv','MovieSerifText_3b_0019_M'):'Anlayacaksın.',
('database_movieSerif_3B.csv','MovieSerifText_3b_0019_F'):'Anlayacaksın.',
('database_movieSerif_3C.csv','MovieSerifText_3c_0002_M'):'Artık şansın kalmadı,\nKodiak.',
('database_movieSerif_3C.csv','MovieSerifText_3c_0004_M'):'Yalvarmayı kes.',
('database_movieSerif_3C.csv','MovieSerifText_3c_0006_M'):'Hayır... oraya değil!',
('database_movieSerif_3C.csv','MovieSerifText_3c_0008_M'):'General yoldaşınız\ngörevden alındı.',
('database_movieSerif_3C.csv','MovieSerifText_3c_0012_M'):'Sıradaki hedef,\ntopraklarınızdan biri olabilir.',
('database_movieSerif_4A.csv','MovieSerifText_4a_0001_M'):'Karşınızda bizzat...',
('database_movieSerif_4A.csv','MovieSerifText_4a_0002_M'):'Altın çağın altın ismi,\nGeneral Ausprey!',
('database_movieSerif_4A.csv','MovieSerifText_4a_0009_M'):'Suşiyi wasabiye boğarak\nyemeye bayılırım!',
('database_movieSerif_4A.csv','MovieSerifText_4a_0010_M'):'Hatta benim bölgemde\nwasabi seçenek değil, kural!',
('database_movieSerif_4A.csv','MovieSerifText_4a_0014_M'):'Doğru suşi yemeyi\nküçük yaşta öğreniyorlar.',
('database_movieSerif_4A.csv','MovieSerifText_4a_0015_M'):'İyilik ediyorum onlara!',
('database_movieSerif_4A.csv','MovieSerifText_4a_0021_M'):'Şu hassas damaklı\nmıymıntılarla ilgilenin...',
('database_movieSerif_4A.csv','MovieSerifText_4a_0019_M'):'bir tutam wasabiye bile\ndayanamıyorlar!',
}
for k,v in more3.items():add(*k,v,dlg,'diyalog/espri')

# ---------- obvious Turkish grammar errors around the core term ----------
gram='Türkçe ek/iyelik yapısı bozuktu; anlam değiştirilmeden doğal gramerle düzeltildi.'
gram_fix={
('stageEndM074.csv','CharaSerif_03_M'):"İyi tahmin! Ben Suşi Vurucusu Musashi'yim!",
('stageEndM074.csv','CharaSerif_03_F'):"İyi tahmin! Ben Suşi Vurucusu Musashi'yim!",
('stageEndM057.csv','CharaSerif_42_M'):'Sevinçte de kederde de... Suşi hep yanındadır.\nSuşi vurucusunun yazgısı budur.',
('stageEndM046.csv','CharaSerif_21_M'):"Evet... ben de. Demek babam efsanevi bir\nsuşi vurucusuymuş, ha?",
('stageEndM046.csv','CharaSerif_21_F'):"Evet... ben de. Demek babam efsanevi bir\nsuşi vurucusuymuş, ha?",
('stageBeginArea04sub010.csv','CharaSerif_02_M'):"Benim! Ben Musashi, SLF'nin en iyi\nsuşi vurucusuyum!",
('stageBeginArea04sub010.csv','CharaSerif_02_F'):"Benim! Ben Musashi, SLF'nin en iyi\nsuşi vurucusuyum!",
('eventEndM001.csv','CharaSerif_27_M'):'Madem bilmek istiyorsun... Ben gezgin bir\nsuşi vurucusuyum.',
('stageBeginM003.csv','stageBeginM004_19_M'):'Ha, o mu? O bir \\u000E\\u0000\\u0003\\u0004ﾑ＞şerit-sürüş dişlisi\\u000E\\u0000\\u0003\\u0004\\u0000＀.\nSuşi vurucusunun gücünü artırır!',
('stageEndM003.csv','stageEndM004_10_M'):'Bak sen, büyük Jinrai! Bir suşi vurucusunu\nkanadının altına aldığını pek görmeyiz.',
('stageEndM003.csv','stageEndM004_20_M'):'Suşi vurucuları daha çok ruhla bağ kurdukça\ndaha fazla yararlı yetenek öğrenir.',
}
for k,v in gram_fix.items():add(*k,v,gram,'gramer')

# One related untranslated system line; necessary for new terminology consistency.
add('scene_menuencyclopedia.csv','TxtNoContract','*Bağ kurulamaz',pledge_reason,'terim')

# Write edited CSVs
for fn,(fields,rows) in files.items():
    with (OUT/fn).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

# Write change logs (new and cumulative)
logfields=['round','category','file','label','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
with (ROOT/'review_v03'/'V03_YENI_DEGISIKLIKLER.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=logfields);w.writeheader();w.writerows(changes)
# cumulative: v02 + v03
cum=[]
oldlog=ROOT/'review_v02'/'INCELEME_DEGISIKLIKLERI.csv'
with oldlog.open(encoding='utf-8-sig',newline='') as f:
    for r in csv.DictReader(f):
        cum.append({'round':'v0.2','category':'önceki tur',**r})
cum.extend(changes)
with (ROOT/'review_v03'/'INCELEME_DEGISIKLIKLERI.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=logfields);w.writeheader();w.writerows(cum)
print('new changes',len(changes),'files',len(set(c['file'] for c in changes)),'cumulative',len(cum))
