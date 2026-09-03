from pathlib import Path
import csv, shutil, re, subprocess, hashlib, zipfile, sys, os, struct, importlib.util, py_compile
from collections import OrderedDict, Counter

ROOT=Path('/mnt/data/sushi_work')
PREV=ROOT/'review_v09'
OUTROOT=ROOT/'review_v10'
OUT=OUTROOT/'csv'
SOURCE=ROOT/'review_v09_source'/'msgstudio'
PATCH_BASE=PREV/'rebuilt_title'
TOOL=PREV/'Araclar'/'sushi_msbt_csv_flat.py'
PREV_MASTER=PREV/'TUM_10676_SATIR_DURUMU.csv'
PREV_AUDIT=PREV/'SATIR_BAZLI_INCELEME_KUMULATIF.csv'
PREV_CHANGES=PREV/'INCELEME_DEGISIKLIKLERI.csv'

if OUTROOT.exists(): shutil.rmtree(OUTROOT)
OUT.mkdir(parents=True)
for p in (PREV/'csv').glob('*.csv'): shutil.copy2(p,OUT/p.name)

files={}; rows_by_key={}
for p in OUT.glob('*.csv'):
    with p.open(encoding='utf-8-sig',newline='') as f:
        rs=list(csv.DictReader(f)); fields=list(rs[0].keys()) if rs else ['label','index','deu','eng','esp','fra','ita','nld','tur']
    files[p.name]=(fields,rs)
    for r in rs: rows_by_key[(p.name,r['label'])]=r

prev_master={}
with PREV_MASTER.open(encoding='utf-8-sig',newline='') as f:
    for r in csv.DictReader(f): prev_master[(r['file'],r['label'])]=r
with PREV_AUDIT.open(encoding='utf-8-sig',newline='') as f: prev_audit=list(csv.DictReader(f))
with PREV_CHANGES.open(encoding='utf-8-sig',newline='') as f: prev_changes=list(csv.DictReader(f))

changes=[]; changed_lookup={}; reviewed={}

def row(fn,label):
    if (fn,label) not in rows_by_key: raise KeyError((fn,label))
    return rows_by_key[(fn,label)]

def add(fn,label,new,reason,category='derin kalite'):
    r=row(fn,label); old=r.get('tur',''); new=(new or '').replace('\r\n','\n').replace('\r','\n').replace('\n','\\n') if '\n' in (new or '') else (new or '')
    # Above only converts ACTUAL newlines. Existing escaped \n remains untouched.
    if old==new:
        reviewed[(fn,label)]=('AYNI KALDI',reason)
        return False
    r['tur']=new; key=(fn,label)
    if key in changed_lookup:
        rec=changed_lookup[key]; rec['new_tur']=new
        if reason and reason not in rec['reason']: rec['reason'] += ' Ek: '+reason
        reviewed[key]=('DEĞİŞTİ',rec['reason'])
        return True
    rec={'round':'v0.10','category':category,'file':fn,'label':label,
         'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),
         'old_tur':old,'new_tur':new,'reason':reason}
    changes.append(rec); changed_lookup[key]=rec; reviewed[key]=('DEĞİŞTİ',reason)
    return True

def set_escaped(fn,label,new,reason,category='derin kalite'):
    # new is already CSV-escaped representation; never normalize literal backslash sequences.
    r=row(fn,label); old=r.get('tur','')
    if old==new:
        reviewed[(fn,label)]=('AYNI KALDI',reason); return False
    r['tur']=new; key=(fn,label)
    if key in changed_lookup:
        rec=changed_lookup[key]; rec['new_tur']=new
        if reason not in rec['reason']: rec['reason']+=' Ek: '+reason
        reviewed[key]=('DEĞİŞTİ',rec['reason']); return True
    rec={'round':'v0.10','category':category,'file':fn,'label':label,
         'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),
         'old_tur':old,'new_tur':new,'reason':reason}
    changes.append(rec); changed_lookup[key]=rec; reviewed[key]=('DEĞİŞTİ',reason); return True

def both(fn,label,new,reason,category='derin kalite'):
    n=0
    for lab in (label,label+'_f'):
        if (fn,lab) in rows_by_key and row(fn,lab).get('eng',''):
            n+=bool(set_escaped(fn,lab,new,reason,category))
    return n

# ---------------------------------------------------------------------------
# A) TEKNİK ONARIMLAR — kaynak ENG kontrol dizisi referans alınır
# ---------------------------------------------------------------------------
technical_reason_trunc=("MSBT içindeki 0x000E kontrol komutu, group/type alanlarından sonra argüman uzunluğu baytı olmadan yarım kalmıştı. "
                       "Bu yalnız metin sorunu değil; oyun komutu yanlış okuyabilir. İngilizce kaynakta aynı dinamik alanın komutu sıfır argüman uzunluğuyla bitiyor; eksik \\u0000 geri eklendi.")
trunc_labels=['GodSkillEffective_Double','GodSkillEffective_SoulShoot','GodSkillEffective_TableBreak','GodSkillEffective_DirectAttack',
              'GodSkillEffective_100Free','GodSkillEffective_LaneFill','GodSkillEffective_SweetsHeaven','GodSkillEffective_SkillCopy',
              'GodSkillEffective_SkillTerminate','GodSkillEffective_HpChange','GodSkillEffective_SushiShuffleer']
for lab in trunc_labels:
    r=row('database_godSkillInfo.csv',lab); cur=r['tur']
    if not cur.endswith('\\u0000'):
        set_escaped('database_godSkillInfo.csv',lab,cur+'\\u0000',technical_reason_trunc,'TEKNİK/kontrol-komutu')

runtime_labels=[
('ShrineGetMode.csv','NarrationInfomation_M'),('ShrineGetMode.csv','NarrationEquipMain_M'),('ShrineGetMode.csv','NarrationEquipSub_M'),
('ShrineGetMode.csv','NarrationEquipNone_M'),('ShrineGetMode.csv','NarrationAwakeLv2_M'),('ShrineGetMode.csv','NarrationAwakeLv3_M'),
('ShrineGetMode.csv','Child_ChoiceYes_M'),('ShrineGetMode.csv','AncMan_ChoiceYes_M'),('ShrineGetMode.csv','AncWoman_ChoiceYes_M'),
('ShrineGetMode.csv','AncChild_ChoiceYes_M'),('ShrineGetMode.csv','Hermit_ChoiceYes_M'),('ShrineGetMode.csv','Catten_ChoiceYes_M'),
('ShrineGetMode.csv','Noblewoman_ChoiceYes_M'),('ShrineGetMode.csv','Pomposity_ChoiceYes_M'),('ShrineGetMode.csv','Simplicity_ChoiceYes_M'),
('ShrineGetMode.csv','Clown_ChoiceYes_M'),('homeKoziin.csv','homeKoziin_select_01_M'),('homeKoziin.csv','homeKoziin_select_03_M')]
runtime_reason=("Dinamik MSBT değişken komutu çeviri sırasında type 13'ten type 10'a dönüşmüş. CSV gösteriminde bunlar sırasıyla \\r ve \\n gibi görünse de burada satır sonu değil komut türü söz konusu. "
                "ENG kaynak komut dizisi birebir referans alınarak type 13 geri yüklendi; böylece yanlış çalışma-zamanı değişkeni çağrılması önlendi.")
for fn,lab in runtime_labels:
    r=row(fn,lab); cur=r['tur']; old='\\u000E\\u0001\\n\\u0000'; new='\\u000E\\u0001\\r\\u0000'
    if old in cur: set_escaped(fn,lab,cur.replace(old,new),runtime_reason,'TEKNİK/runtime-değişkeni')

# Replacement-character corruption where English carries escaped high surrogate command parameter.
fffd_reason=("Türkçe kontrol parametresindeki yüksek surrogate kod birimi U+D85F, önceki dönüştürmede Unicode değiştirme karakterine (�) bozulmuştu. "
             "Bu değer görünür metin değil, biçim/renk komutunun parametresi. ENG kaynaktaki \\uD85F kod birimi aynen geri kondu.")
for fn,(_,rs) in files.items():
    for r in rs:
        if '�' in r.get('tur','') and '\\uD85F' in r.get('eng','') and '�' not in r.get('eng',''):
            set_escaped(fn,r['label'],r['tur'].replace('�','\\uD85F'),fffd_reason,'TEKNİK/kontrol-parametresi')

SP_START='\\u000E\\u0000\\u0002\\u0002\\u0096'; SP_END='\\u000E\\u0000\\u0002\\u0002d'
speech_fixes={
('stageBeginM037.csv','CharaSerif_06_M'):'Grrrk!',('stageBeginM037.csv','CharaSerif_06_F'):'Grrrk!',
('stageBeginM110.csv','CharaSerif_02_M'):'Franklin!',('stageEndM111.csv','CharaSerif_09_M'):'Franklin?!',('stageEndM111.csv','CharaSerif_09_F'):'Franklin?!',
('stageEndM029.csv','CharaSerif_01_M'):'G... General Kodiaaaak!',('stageBeginM014.csv','CharaSerif_00_M'):'HEY!',('stageBeginM014.csv','CharaSerif_00_F'):'HEY!',
('stageBeginM014.csv','CharaSerif_13_M'):'EMREDERSİN!',
('stageBeginArea03Ex008.csv','CharaSerif_01_M'):'Durun!',
('stageBeginM072.csv','CharaSerif_11_M'):'Gourai, yanıma!'}
speech_reason=("Kaynakta 0x000E group 0/type 2 konuşma-vurgu komutuyla sarılı görünen replik Türkçede ya yalnız komutlara düşmüş ya da vurgu komutları silinmişti. "
               "Metin bağlama göre geri çevrildi ve başlangıç/bitiş komutları ENG ile aynı yapıda korundu.")
for (fn,lab),txt in speech_fixes.items(): set_escaped(fn,lab,SP_START+txt+SP_END,speech_reason,'TEKNİK/eksik-replik')

# Visible source text that was fully blank in Turkish.
blank_reason_name=("ENG ve diğer yerelleştirmelerde görünen karakter/başlık adı varken Türkçe slot tamamen boştu. Bu alan bir çeviri tercihi değil UI etiketi; özel ad kaynak yazımıyla geri kondu.")
for r in files['episode_cmn.csv'][1]:
    if r['eng'].strip() and not r['tur'].strip() and (r['label'].startswith('Name_Label_') or r['label'].startswith('BossEntryLabelGeneral_')):
        set_escaped('episode_cmn.csv',r['label'],r['eng'],blank_reason_name,'TEKNİK/boş-görünen-metin')
for lab in ['homeShrine_first_rank_07_M','homeShrine_rank_02_M','homeShrine_word_02B_M','homeShrine_word_07B_M']:
    set_escaped('homeShrine.csv',lab,'Ah!',"Kaynakta ve diğer dillerde karakterin kısa tepki ünlemi var; Türkçe slot boş kalmıştı. Görünen replik 'Ah!' olarak geri kondu.",'TEKNİK/boş-görünen-metin')
for lab in ['homeSushibar_00_in_01_M','homeSushibar_cap4_00_M','homeSushibar_cap5_00_M']:
    set_escaped('homeSushibar.csv',lab,'Musashi! Musashi!',"Karakterin Musashi'ye seslendiği görünen replik Türkçede boştu; özel ad ve ünlem kaynaktaki ritimle geri kondu.",'TEKNİK/boş-görünen-metin')
set_escaped('homeSushibar.csv','homeSushibar_04_in_01_M','Musashi!',"Karakterin Musashi'ye seslendiği görünen replik Türkçede boştu; özel ad geri kondu.",'TEKNİK/boş-görünen-metin')
for lab in ['Child_laugh_M','AncMan_laugh_M','AncWoman_laugh_M','Noblewoman_laugh_M','Pomposity_laugh_M','Simplicity_laugh_M','Araoh_laugh_M','Clown_laugh_M']:
    r=row('homeKoziin.csv',lab); set_escaped('homeKoziin.csv',lab,r['eng'],"Kahkaha/tepki sesi ENG ve diğer dillerde görünürken Türkçe slot boştu. Ses efekti metni kaynak ritmiyle geri kondu.",'TEKNİK/boş-görünen-metin')
# highlighted key rewards: preserve ENG control sequence exactly, localize visible words
for fn,lab,name in [('stageEndM094.csv','CharaSerif_17_M',"Purrsilla'nın Anahtarını"),('stageEndM052.csv','CharaSerif_15_M',"Ausprey'in Anahtarını")]:
    e=row(fn,lab)['eng']; n=e.replace('You got ','').replace("Purrsilla's Key",name).replace("Ausprey's Key",name)
    if n.endswith('!'): n=n[:-1]+' aldın!'
    set_escaped(fn,lab,n,"Ödül satırında biçim kontrol kodları kalmış fakat eşya adı ve görünen cümle tamamen silinmişti. ENG biçim komutları aynen korunup anahtar adı Türkçeleştirilerek görünen ödül mesajı geri oluşturuldu.",'TEKNİK/boş-görünen-metin')

# ---------------------------------------------------------------------------
# B) v0.9'daki M/F uygulama boşluklarını düzelt
# ---------------------------------------------------------------------------
syncs=[
('database_movieSerif_1A.csv','MovieSerifText_1a_0001_F','Eveeeeeeet!'),
('database_movieSerif_1A.csv','MovieSerifText_1a_0036_F','Of ya! Yine aç kaldım.'),
('database_movieSerif_1A.csv','MovieSerifText_1a_0064_F','Bir lokma alacağıma\\naç kalırım!'),
('database_movieSerif_1A.csv','MovieSerifText_1a_0075_F','Suşi gurusu mu?'),
('homeSushibar.csv','homeSushibar_cap4_03_F','Vay... Ne güzel düşünmüşsün!'),
('database_movieSerif_1B.csv','MovieSerifText_1b_0019_F','Off... Düşündükçe\\ndaha da acıkıyorum.'),
('database_movieSerif_1B.csv','MovieSerifText_1b_0076_F','Eveeeet!'),
('stageBeginM072.csv','CharaSerif_29_F','Jinrai... Üzgünüm ama mecburum.\\nOnu elimizden kaçırmamalıyız!')]
sync_reason=("Aynı ENG kaynağa sahip erkek/kadın varyantından yalnız erkek etiketi v0.9'da güncellenmiş, kadın varyantı eski metinde kalmıştı. "
             "Cinsiyete bağlı sözcük bulunmadığı için iki varyant aynı nihai Türkçede senkronlandı.")
for fn,lab,n in syncs: set_escaped(fn,lab,n,sync_reason,'TEKNİK/M-F-senkron')

# ---------------------------------------------------------------------------
# C) Derin kalite geçişi — önceki 'doğru' kararlarında kaçan eksik anlam/şaka/ton
# ---------------------------------------------------------------------------
def q(fn,lab,new,reason): return set_escaped(fn,lab,new,reason,'DERİN KALİTE')
def qb(lab,new,reason): return both('scene_puzzlebattle.csv',lab,new,reason,'DERİN KALİTE')

# Enemy win/lose — lost clauses or wrong semantic subject
quality=[
('Enemy_StgWin_065','Açlığı hiçbir strateji yenemez!\\nYemeye devam eden kazanır!',"İlk Türkçe yalnız ilk cümleyi taşıyordu; kaynak ve diğer diller kazanma ilkesini de açıkça söylüyor. İkinci düşünce geri eklendi."),
('Enemy_StgWin_113','İyi direndin ama müfrezenin\\nen dişli savaşçısı benim!',"Kaynakta rakibin iyi direndiğini kabul eden ilk yarı düşmüştü. Övgü + böbürlenme karşıtlığı geri kuruldu."),
('Enemy_StgWin_132','İmparator çok yaşa!\\nDavetsizin payına utanç düşer...',"Kaynağın 'Glory to the Emperor!' ünlemi tamamen kayıptı. İki parçalı zafer söylemi geri getirildi."),
('Enemy_StgWin_198','O garip taş artık İmparatorluğun!\\nHeheheh!',"Kaynağın alaycı kahkahası karakter tonunun parçasıydı; mevcut anlam korunup kahkaha geri eklendi."),
('Enemy_StgWin_233',"Pırenses'in emri mutlak!\\nNe derse harfiyen yaparız!","Mevcut Türkçe 'yolun burada bitiyor' diye kaynakta olmayan bir tehdit ekliyordu. EN ve diğer diller mutlak itaati vurguluyor; anlam geri kuruldu."),
('Enemy_StgWin_260','Kapışma bitti! Gizlilik\\neğitimine dönüyorum! Vuhuu!',"Kaynağın 'Fight's over!' ilk düşüncesi düşmüştü. Çocuksu/coşkulu son ünlem korunarak iki fikir birleştirildi."),
('Enemy_StgWin_271',"Muahaha... Chamelva'nın\\ngücü karşısında titre!","Chamelva özel adı yanlışlıkla 'İmparatorluk' olmuştu; kaynakta kişisel güç gösterisi var. Varlık adı düzeltildi."),
('Enemy_StgWin_296','Moralin çökmüş galiba? Hamlelerin\\nher zamanki kadar akıcı değildi.',"Down in the dumps ilk cümlesi düşmüştü. Rakibin moralini iğneleyen ton ve ikinci gözlem birlikte korundu."),
('Enemy_StgWin_301','Şimdiden bitti mi? O zaman\\nsuşiye daha çok vaktim kalır...',"'Şimdiden bitti mi?' şaşkınlığı kayıptı; sonraki yemek şakası bunun sonucu olduğu için ilişki geri kuruldu."),
('Enemy_StgLose_001','Bir çocuk beni nasıl dağıttı?!\\nNe utanç verici!',"Mevcut Türkçe özneyi yanlışlıkla suşi ruhuna çevirmişti ve aşağılanma cümlesini atmıştı. EN/diğer diller çocuğa yenilmeyi vurguluyor."),
('Enemy_StgLose_006','Anlamıyorum! Suşi Kalkanım beni\\nhiç yarı yolda bırakmamıştı!',"İlk şaşkınlık cümlesi kayıptı; savunmanın ilk kez başarısız olmasıyla birlikte geri eklendi."),
('Enemy_StgLose_021','Celia işi batırmasaydı\\nseninle hiç kapışmazdım!',"Celia'nın hatası mevcut Türkçede tamamen kaybolmuştu. Olay nedeni geri eklendi; bu hikâye bağlantısı önemli."),
('Enemy_StgLose_041','Hadi ama! İki Ucu Küvetli\\nseni nasıl durduramadı?!',"Kaynak şaşkın bir soru. Mevcut Türkçe yorgun bir tespit gibiydi; tepki ve soru tonu geri kuruldu."),
('Enemy_StgLose_065','Söylemesi zor ama... Seni yerken\\nizlemek bile beni acıktırıyor...',"'I hate to say it' isteksiz itiraf tonu düşmüştü. Karakterin gururuna karşı işleyen giriş geri eklendi."),
('Enemy_StgLose_073','Olamaz! Yöntemlerimi savaşlarda\\nince ince geliştirmiştim!',"İlk şok ünlemi kayıptı; kaynakta yöntemlerine duyduğu güvenin kırılması var."),
('Enemy_StgLose_091',"P-Pırenses'e söyleme ama...\\ncanım ton balığı çekti.","Kritik ters anlam: kaynak 'Pırenses'e söyleme' derken Türkçe 'haber vermem gerek' diyordu. Diğer diller gizleme + ton balığı isteğini doğruluyor."),
('Enemy_StgLose_111','Takviye Büfesi yeterince\\ntakviye etmedi... Çenem güçlenmeli...',"Buff/buffet şakası korunurken kaynakta bulunan 'daha fazla çene gücü' ikinci cümlesi geri eklendi."),
('Enemy_StgLose_126',"Ne güzel suşi tarzı! Tiburon'un\\nadamından da bu beklenir...","Rakibin stiline iltifat eden ilk cümle kayıptı; yalnız Tiburon referansı kalmıştı. Övgü geri kondu."),
('Enemy_StgLose_133','Dur, Musashi... İleride seni\\nyalnız sonun bekliyor...',"Kaynağın doğrudan 'Dur, Musashi' hitabı düşmüştü; uyarının kime yöneldiği ve dramatik ton geri kuruldu."),
('Enemy_StgLose_209','Buradan sonrası daha da zor...\\nSeni bundan kurtarmaya çalıştım!',"Kaynağın 'I tried to spare you!' ikinci düşüncesi tamamen kayıptı. Düşmanın kendini merhametli gösterme tonu geri kuruldu."),
('Enemy_StgLose_250','Suşi ruhu nerede? Kapışmamız\\nyeterince gösterişli değil miydi?!',"İlk soru düşmüştü; ikinci soru tek başına neden sorulduğunu kaybediyordu. İki parçalı şaka geri kuruldu."),
('Enemy_StgLose_259','Uzun zamandır suşi savaşı\\nyapmamıştım. Paslanmışım.',"Kaynağın asıl sonucu 'rusty/paslanmış' mevcut Türkçede yoktu. Sebep-sonuç tamamlandı."),
('Enemy_StgLose_276','Nerede hata yaptım? Taktiklerimdeki\\nkusurları analiz etmeliyim...',"İlk öz-eleştiri sorusu düşmüştü; analitik karakter sesi için geri eklendi."),
('Enemy_StgLose_280','Kimin kazandığı kimin umurunda?\\nSavaş zaten hiçbir şeyi çözmez.',"Kaynağın alaycı ilk cümlesi düşmüştü. İkinci pasifist cümlenin tonunu taşıdığı için geri eklendi."),
('Enemy_StgLose_281','Kaybettim mi? Şimdi de\\ncanım suşi çekti...',"Kaybettiğini fark etme sorusu kayıptı; açlık tepkisi onun sonucu olarak geri bağlandı."),
('Enemy_StgLose_294','Tısss... Bitmek bilmeyen tabaklar\\nneredeyse maskemi kıracaktı...',"Hissss karakter/ses efekti mevcut Türkçede yoktu; yılanımsı ton için yerelleştirildi."),
]
for lab,new,reason in quality: qb(lab,new,reason)

player=[
('Player_StgWin_028','Vay... Seni o kadar mı fena yendim ki\\nşiire döktün?',"Kaynakta 'seni o kadar kötü yendim ki' alayının derecesi var; mevcut kısa Türkçe bu sataşmayı azaltıyordu."),
('Player_StgWin_034','Ama böyle tadı çıkmaz! Suşinin\\ntadını çıkarmadan savaşılır mı?',"Mevcut 'soğuk algınlığı' kaynakta yok ve anlamı bozuyor. EN/diğer diller savaşırken suşiden keyif alma fikrini vurguluyor; 'tat/tadı çıkmak' çift anlamıyla yeniden kuruldu."),
('Player_StgWin_073','O “yöntemler”in önemi yok!\\nSuşi bir yöntemden çok daha fazlası!',"İlk karşı çıkış cümlesi düşmüştü; tırnaklı 'methods' küçümsemesi geri eklendi."),
('Player_StgWin_105','Hadi oradan! Kendine acı çektirerek\\ngüçlenemezsin!',"Get real! ünlemi karakter tonunu taşıyor; mevcut Türkçe yalnız öğüdü bırakmıştı."),
('Player_StgWin_108','Şiirlerini özlemişim! Onu tam\\nzamanlı yapmayı hiç düşündün mü?',"İlk 'şiirini özledim' iğnelemesi kayıptı; meslek önerisi şakasının zemini geri kuruldu."),
('Player_StgWin_127','Suşiyi gerçekten seviyorsun...\\nBabam iyi insanlarla çalışıyor demek.',"Rakibin suşi sevgisini kabul eden ilk cümle düşmüştü; sonraki babaya ilişkin övgünün nedeni geri eklendi."),
('Player_StgWin_223','Biraz kötü hissettim doğrusu. Ona\\n“Musashi fazla iyiydi” dersin belki?',"Kaynağın önceki empati cümlesi düşmüştü; övünme şakasının kontrastı geri kuruldu."),
('Player_StgWin_225','Ö-özür dilerim. Darılmaca yok,\\ntamam mı?',"Kaynağın kekelemeli özrü düşmüştü; karakterin mahcup tonu geri eklendi."),
('Player_StgWin_257','Kolay! Suşi ruhlarını\\nkokumu izleyerek bulurum!',"'It'll be easy!' girişindeki özgüven düşmüştü. Follow my nose deyimi Türkçede serbestçe korunarak tamamlandı."),
('Player_StgWin_263','Ö-özür dilerim. Bazen gücümü\\nbiraz FAZLA kaçırıyorum...',"Kaynağın özür girişi düşmüştü; mevcut vurgu ve öz-eleştiri korunarak tamamlandı."),
('Player_StgWin_277','Suşi vuruculuğunda çok ilerledim!\\nAma sen zaten biliyordun, değil mi?',"Kaynağın karşı tarafa dönük son tag-question cümlesi düşmüştü; ilişki/özgüven tonu geri eklendi."),
('Player_StgWin_293','Tereddüt edemem! Hele\\nkonu sen olunca!',"M/F varyantları gereksiz farklıydı; daha doğal ve kısa kadın varyantındaki ifade iki cinsiyette tekleştirildi."),
('Player_StgWin_296','Sağ ol! Senin gibi biriyle\\nkapışınca formda olmak şart!',"Thanks! cevabı düşmüştü; repliğin önceki iltifata yanıt olduğu açık hale getirildi."),
]
for lab,new,reason in player: qb(lab,new,reason)

# Other quality / term consistency
other=[
('stageBeginM126.csv','CharaSerif_03_M',None,"Autoshoot Shutdown daha önce oyun genelinde 'Otoatış Kilidi' olarak standardize edilmişti; bu sahnede eski ad kalmış. Aynı özel komut parametresi onarılırken görünür terim de standarda çekildi."),
('homeSushibar.csv','homeSushibar_16_a_07_M',"Takviye Büfesi'ni en son ne zaman\\nkullandığımı bile hatırlamıyorum.","Özel ada gelen belirtme eki yanlış yazılmıştı ('Büfesi'i'). Türkçe ekleme kuralına göre 'Büfesi'ni' yapıldı; cümle doğal akıtıldı."),
('stageBeginM021.csv','CharaSerif_02_M','Fark etmez! Seni durduracak kadar\\nkaslıyım da artarım!',"More than beefy enough abartılı böbürlenme. Mevcut çeviri düz kalıyordu; Türkçedeki '... da artarım' kalıbıyla karakter sesi güçlendirildi."),
('stageBeginM013.csv','CharaSerif_13_M','Şuna bak: bana verdikleri süper özel\\nsuşi ruhu Hakkan!',"Kaynak yeni ruhu çocuksu bir gururla gösteriyor. Cümle Türkçede daha konuşma diline uygun ve coşkulu biçimde yeniden kuruldu."),
('homeSushibar.csv','homeSushibar_17_n_03_M','O katı hareketleri, o pırıl pırıl gözleri...\\nFazla çekiciler! Dayanamıyorum!',"'It’s all too much! I can’t take it!' mevcut 'Hepsi çok fazla' ile İngilizce kalıp olarak kalmıştı. Önceki betimlemeye bağlanan doğal hayranlık tepkisine çevrildi."),
('stageEndM001.csv','stageEndM001_02_M','Hrhrr... İlk savaşına göre\\nhiç fena değildin.',"'For a first-time striker, you handled yourself well' mevcut Türkçede uzun ve mekanikti. Karakterin homurtusu ve kısa övgüsü doğal Türkçeyle verildi."),
('stageEndM092.csv','CharaSerif_13_M','(Bütün bunlar nedense çok tanıdık...)',"Feels familiar ifadesi 'tuhaf bir şekilde' diye dolaylı kalmıştı; Türkçedeki doğal iç ses 'nedense çok tanıdık' seçildi."),
]
for fn,lab,new,reason in other:
    if new is None:
        r=row(fn,lab); q(fn,lab,r['tur'].replace('Otoatış Kapatma','Otoatış Kilidi'),reason)
    else:q(fn,lab,new,reason)

# Zing-a-rama recurring catchphrase; recreate wordplay consistently.
zing_reason=("Zing-a-rama / prezzo, Rio'nun bilinçli uydurma kafiyeli konuşması. Bazı Türkçe satırlarda 'prezzo' İngilizce bırakılmış, bazılarında şaka farklılaşmıştı. "
             "Diğer diller de birebir çevirmek yerine yeni bir ünlem/ödül sözcüğü üretiyor; yedi tekrar 'Şahane-rama! Buna bir ödülcük yakışır!' olarak tekleştirildi.")
for fn in ['stageEndM136.csv','stageEndM046.csv','stageEndM057.csv','stageEndM078.csv','stageEndM088.csv','stageEndM036.csv','stageEndM116.csv']:
    q(fn,'CharaSerif_00_M','Şahane-rama! Buna bir\\nödülcük yakışır!',zing_reason)

q('stageBeginM036.csv','CharaSerif_16_M','Oyunkvimin nasıl? Bir el atacak\\nvaktin var mı?',"Skedge, schedule'ın bilerek bozulmuş argo biçimi ve sonraki replik bunu sorguluyor. DE 'Zockenda', ES 'partidurri' gibi kendi uydurma sözcüğünü yaratıyor. Türkçede oyun+takvim birleşimi 'oyunkvim' ile şaka yeniden kuruldu.")
for lab in ['CharaSerif_17_M','CharaSerif_17_F']:
    q('stageBeginM036.csv',lab,'“Oyunkvim” mi? O da kelime mi?',"Bir önceki skedge şakasının cevabı; Türkçe uydurma 'oyunkvim' sorgulanarak iki repliklik espri korunuyor.")

# Runaway Lane highlighted term — preserve all existing controls.
r=row('stageBeginM007.csv','stageBeginM008_04_M'); q('stageBeginM007.csv','stageBeginM008_04_M',r['tur'].replace('Runaway Lane','Çılgın Şerit'),"Runaway Lanes yeteneği oyun genelinde 'Çılgın Şeritler' olarak standardize edilmişti; bu tekil şerit repliğinde İngilizce ad kalmıştı. Tekil bağlama uygun 'Çılgın Şerit' kullanıldı.")

# M/F natural consistency in stageBeginM030
for lab in ['CharaSerif_04_M','CharaSerif_04_F']:
    if ('stageBeginM030.csv',lab) in rows_by_key and row('stageBeginM030.csv',lab)['eng']:
        q('stageBeginM030.csv',lab,'Olmaz! Bu dövüşte sana suşinin\\nkıymetini nasıl bileceğini göstereceğim!',"'The right way to appreciate sushi' mevcut Türkçede çeviri kokan 'takdir etmenin doğru yolu' kalıbındaydı. Türkçedeki doğal 'kıymetini bilmek' deyimiyle karakterin meydan okuması yeniden kuruldu.")

# Menu abbreviation consistency
if ('scene_menumydata.csv','TxtExpMax') in rows_by_key: q('scene_menumydata.csv','TxtExpMax','MAKS',"Aynı maksimum seviye kısaltması başka menüde 'MAKS' iken burada İngilizce 'MAX' kalmıştı; Türkçe UI tutarlılığı için 'MAKS' yapıldı.")

# ---------------------------------------------------------------------------
# D) Yaz ve raporla
# ---------------------------------------------------------------------------
for fn,(fields,rs) in files.items():
    with (OUT/fn).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rs)

def writecsv(p,fields,rows):
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

change_fields=['round','category','file','label','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
writecsv(OUTROOT/'V10_YENI_DEGISIKLIKLER.csv',change_fields,changes)

# v10 reviewed report includes every changed/rechecked key, with previous decision.
review_rows=[]
for (fn,lab),(dec,reason) in sorted(reviewed.items()):
    r=row(fn,lab); pm=prev_master.get((fn,lab),{})
    ch=changed_lookup.get((fn,lab))
    review_rows.append({'round':'v0.10','file':fn,'label':lab,'index':r.get('index',''),
                        'previous_review_status':pm.get('review_status',''),'previous_decision':pm.get('decision',''),
                        'decision':dec,'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),
                        'old_tur':ch['old_tur'] if ch else r.get('tur',''),'new_tur':r.get('tur',''),'reason':reason})
review_fields=['round','file','label','index','previous_review_status','previous_decision','decision','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
writecsv(OUTROOT/'V10_DERIN_KALITE_VE_TEKNIK_INCELEME.csv',review_fields,review_rows)

# cumulative changes
combined=prev_changes+changes
writecsv(OUTROOT/'INCELEME_DEGISIKLIKLERI.csv',change_fields,combined)
latest={}
for x in combined: latest[(x['file'],x['label'])]=x
writecsv(OUTROOT/'INCELEME_SON_DURUM_ESSIZ.csv',change_fields,list(latest.values()))

# master all rows — v10 changed keys override prior reason/status. Every row remains reasoned.
master=[]
for fn in sorted(files):
    for r in files[fn][1]:
        key=(fn,r['label']); pm=prev_master.get(key,{})
        if key in reviewed:
            dec,reason=reviewed[key]; ch=changed_lookup.get(key)
            old=ch['old_tur'] if ch else pm.get('old_tur',r.get('tur',''))
            master.append({'file':fn,'label':r['label'],'index':r.get('index',''),'review_status':'DERİN+TEKNİK_v0.10','decision':dec,
                           'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),
                           'old_tur':old,'current_tur':r.get('tur',''),'reason':reason})
        else:
            master.append({'file':fn,'label':r['label'],'index':r.get('index',''),'review_status':pm.get('review_status','İNCELENDİ_ÖNCEKİ'),'decision':pm.get('decision','AYNI KALDI'),
                           'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),
                           'old_tur':pm.get('old_tur',r.get('tur','')),'current_tur':r.get('tur',''),'reason':pm.get('reason','Önceki kalite geçişinde incelendi; v0.10 teknik taramasında yeni risk sinyali bulunmadı.')})
master_fields=['file','label','index','review_status','decision','eng','deu','esp','fra','ita','nld','old_tur','current_tur','reason']
writecsv(OUTROOT/'TUM_10676_SATIR_DURUMU.csv',master_fields,master)

# cumulative latest audit: use master-representative rows for changed keys, retain older audit otherwise
cum={}
for a in prev_audit: cum[(a['file'],a['label'])]=a
for rr in review_rows:
    cum[(rr['file'],rr['label'])]={'round':'v0.10','file':rr['file'],'label':rr['label'],'index':rr['index'],'decision':rr['decision'],
                                  'eng':rr['eng'],'deu':rr['deu'],'esp':rr['esp'],'fra':rr['fra'],'ita':rr['ita'],'nld':rr['nld'],
                                  'old_tur':rr['old_tur'],'new_tur':rr['new_tur'],'reason':rr['reason']}
cum_fields=['round','file','label','index','decision','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
writecsv(OUTROOT/'SATIR_BAZLI_INCELEME_KUMULATIF.csv',cum_fields,list(cum.values()))

# Length warnings for v10 only and whole-patch informational report.
ctrl_esc=re.compile(r'\\u[0-9A-Fa-f]{4}')
def visible_len(line):
    s=ctrl_esc.sub('',line); s=''.join(c for c in s if ord(c)>=32 and not 0xE000<=ord(c)<=0xF8FF and not 0xFF00<=ord(c)<=0xFFEF); return len(s)
warn=[]
for ch in changes:
    for i,line in enumerate(ch['new_tur'].split('\\n'),1):
        L=visible_len(line)
        if L>48: warn.append({'file':ch['file'],'label':ch['label'],'line_no':i,'visible_len':L,'line':line})
writecsv(OUTROOT/'V10_YENI_DEGISIKLIK_UZUNLUK_UYARILARI.csv',['file','label','line_no','visible_len','line'],warn)

# Build patch
rebuilt=OUTROOT/'rebuilt_title'
subprocess.run([sys.executable,str(TOOL),'import','--csv',str(OUT),'--patch',str(PATCH_BASE),'--out',str(rebuilt)],check=True)
subprocess.run([sys.executable,str(TOOL),'validate','--source',str(SOURCE),'--patch',str(rebuilt)],check=True)
verify=OUTROOT/'verify_csv'
subprocess.run([sys.executable,str(TOOL),'export','--source',str(SOURCE),'--patch',str(rebuilt),'--out',str(verify)],check=True)
# Exact CSV roundtrip
diffs=[]; total=0
for pp in OUT.glob('*.csv'):
    qq=verify/pp.name
    with pp.open(encoding='utf-8-sig',newline='') as f1, qq.open(encoding='utf-8-sig',newline='') as f2:
        aa=list(csv.DictReader(f1)); bb={x['label']:x for x in csv.DictReader(f2)}
        for rr in aa:
            total+=1; vv=bb.get(rr['label'])
            if vv is None or rr.get('tur','')!=vv.get('tur',''):
                diffs.append({'file':pp.name,'label':rr['label'],'expected':rr.get('tur',''),'actual':'' if vv is None else vv.get('tur','')})
writecsv(OUTROOT/'ROUNDTRIP_FARKLARI.csv',['file','label','expected','actual'],diffs)

# Copy tools now; validator written externally / copied by build caller if present.
arac=OUTROOT/'Araclar'; arac.mkdir()
for pp in (PREV/'Araclar').glob('*.py'): shutil.copy2(pp,arac/pp.name)
shutil.copy2(Path(__file__),arac/'v10_derin_kalite_teknik_gecis.py')
validator_src=ROOT/'msbt_technical_validator.py'
if validator_src.exists(): shutil.copy2(validator_src,arac/'msbt_technical_validator.py')
for pp in arac.glob('*.py'): py_compile.compile(str(pp),doraise=True)

# Bundle first, technical validator will be run after zips are made.
bundle=OUTROOT/'bundle'; bundle.mkdir()
shutil.copytree(OUT,bundle/'CSV')
shutil.copytree(arac,bundle/'Araclar')
shutil.copytree(rebuilt,bundle/'LayeredFS'/'00040000001C1D00')
rap=bundle/'Raporlar'; rap.mkdir()
for name in ['V10_DERIN_KALITE_VE_TEKNIK_INCELEME.csv','V10_YENI_DEGISIKLIKLER.csv','V10_YENI_DEGISIKLIK_UZUNLUK_UYARILARI.csv',
             'SATIR_BAZLI_INCELEME_KUMULATIF.csv','TUM_10676_SATIR_DURUMU.csv','INCELEME_DEGISIKLIKLERI.csv','INCELEME_SON_DURUM_ESSIZ.csv','ROUNDTRIP_FARKLARI.csv']:
    shutil.copy2(OUTROOT/name,rap/name)

readme=f'''Sushi Striker Türkçe yama v0.10 — derin kalite + teknik bütünlük geçişi

İçerik:
- LayeredFS/00040000001C1D00/: yeniden enjekte edilmiş tam yama
- CSV/: 243 MSBT için DEU/ENG/ESP/FRA/ITA/NLD/TUR sütunlu CSV'ler
- Araclar/: CSV↔MSBT aracı, önceki uygulama betikleri, v0.10 uygulama betiği ve bağımsız teknik doğrulayıcı
- Raporlar/: 10.676 satır master raporu, v0.10 değişiklikleri, teknik doğrulama ve kümülatif raporlar

v0.10 özellikle round-trip testinin yakalayamadığı kontrol-kodu bozulmalarını düzeltir:
- yarım kalmış inline komutlar
- yanlış runtime değişken türleri
- bozulmuş surrogate kontrol parametreleri
- görünür kaynağı varken boş kalmış Türkçe UI/replik alanları
- konuşma/vurgu kontrol çiftleri
- M/F varyant senkron hataları

Ayrıca ikinci kalite geçişinde daha önce gözden kaçan eksik cümleler, yanlış özneler ve karakter/kelime oyunu kayıpları yeniden işlendi.
'''
(bundle/'README_TR.txt').write_text(readme,encoding='utf-8')

# Package LayeredFS and tools
layerzip=OUTROOT/'Sushi_Striker_TR_v10_LayeredFS.zip'
with zipfile.ZipFile(layerzip,'w',zipfile.ZIP_DEFLATED) as z:
    for pp in rebuilt.rglob('*'):
        if pp.is_file(): z.write(pp,Path('LayeredFS')/'00040000001C1D00'/pp.relative_to(rebuilt))
toolszip=OUTROOT/'Sushi_Striker_TR_v10_Araclar.zip'
with zipfile.ZipFile(toolszip,'w',zipfile.ZIP_DEFLATED) as z:
    for pp in arac.rglob('*'):
        if pp.is_file() and '__pycache__' not in pp.parts: z.write(pp,pp.relative_to(arac))

# technical validator invoked before full package; it may generate reports then copy into bundle.
if (arac/'msbt_technical_validator.py').exists():
    tech_report=OUTROOT/'V10_TEKNIK_DOGRULAMA.csv'; tech_txt=OUTROOT/'V10_TEKNIK_DOGRULAMA_OZETI.txt'
    subprocess.run([sys.executable,str(arac/'msbt_technical_validator.py'),
                    '--source',str(SOURCE),'--patch',str(rebuilt),'--csv',str(OUT),
                    '--roundtrip',str(verify),'--layer-zip',str(layerzip),'--report',str(tech_report),'--summary',str(tech_txt)],check=True)
    shutil.copy2(tech_report,rap/tech_report.name); shutil.copy2(tech_txt,rap/tech_txt.name)

# Add roundtrip summary.
summary=(f'CSV/MSBT dosyaları: {len(list(OUT.glob("*.csv")))}\nToplam etiket: {total}\n'
         f'v0.10 değişen satır: {len(changes)}\nv0.10 yeniden gerekçelendirilen satır: {len(review_rows)}\n'
         f'CSV→MSBT→CSV farkı: {len(diffs)}\nYeni değişiklik uzun satır uyarısı (>48): {len(warn)}\n')
(OUTROOT/'ROUNDTRIP_DOGRULAMA.txt').write_text(summary,encoding='utf-8'); shutil.copy2(OUTROOT/'ROUNDTRIP_DOGRULAMA.txt',rap/'ROUNDTRIP_DOGRULAMA.txt')

# Manifest (not self-hashed)
manifest=[]
for pp in sorted(bundle.rglob('*')):
    if pp.is_file() and pp.name!='DOSYA_MANIFESTOSU_SHA256.txt':
        manifest.append(hashlib.sha256(pp.read_bytes()).hexdigest()+'  '+str(pp.relative_to(bundle)).replace('\\','/'))
(bundle/'DOSYA_MANIFESTOSU_SHA256.txt').write_text('\n'.join(manifest)+'\n',encoding='utf-8')
fullzip=OUTROOT/'Sushi_Striker_TR_v10_FULL.zip'
with zipfile.ZipFile(fullzip,'w',zipfile.ZIP_DEFLATED) as z:
    for pp in bundle.rglob('*'):
        if pp.is_file(): z.write(pp,pp.relative_to(bundle))

# Re-run validator including FULL zip structure.
if (arac/'msbt_technical_validator.py').exists():
    subprocess.run([sys.executable,str(arac/'msbt_technical_validator.py'),
                    '--source',str(SOURCE),'--patch',str(rebuilt),'--csv',str(OUT),
                    '--roundtrip',str(verify),'--layer-zip',str(layerzip),'--full-zip',str(fullzip),
                    '--report',str(OUTROOT/'V10_TEKNIK_DOGRULAMA.csv'),'--summary',str(OUTROOT/'V10_TEKNIK_DOGRULAMA_OZETI.txt')],check=True)
    # update report inside bundle and rebuild full ZIP with final validator result + manifest
    shutil.copy2(OUTROOT/'V10_TEKNIK_DOGRULAMA.csv',rap/'V10_TEKNIK_DOGRULAMA.csv')
    shutil.copy2(OUTROOT/'V10_TEKNIK_DOGRULAMA_OZETI.txt',rap/'V10_TEKNIK_DOGRULAMA_OZETI.txt')
    manifest=[]
    for pp in sorted(bundle.rglob('*')):
        if pp.is_file() and pp.name!='DOSYA_MANIFESTOSU_SHA256.txt':manifest.append(hashlib.sha256(pp.read_bytes()).hexdigest()+'  '+str(pp.relative_to(bundle)).replace('\\','/'))
    (bundle/'DOSYA_MANIFESTOSU_SHA256.txt').write_text('\n'.join(manifest)+'\n',encoding='utf-8')
    with zipfile.ZipFile(fullzip,'w',zipfile.ZIP_DEFLATED) as z:
        for pp in bundle.rglob('*'):
            if pp.is_file(): z.write(pp,pp.relative_to(bundle))

print('DONE')
print(summary)
print('changes',len(changes),'reviewed',len(review_rows),'warn',len(warn),'diffs',len(diffs))
print(fullzip);print(layerzip);print(toolszip)
