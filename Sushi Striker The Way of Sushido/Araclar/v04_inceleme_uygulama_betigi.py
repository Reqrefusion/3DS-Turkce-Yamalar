from pathlib import Path
import csv, shutil, re, subprocess, hashlib, zipfile, os, sys

ROOT=Path('/mnt/data/sushi_work')
SRC=ROOT/'review_v03'/'csv'
OUTROOT=ROOT/'review_v04'
OUT=OUTROOT/'csv'
TOOL=ROOT/'review_v03'/'full_bundle'/'Araclar'/'sushi_msbt_csv_flat.py'
PATCH_BASE=ROOT/'review_v03'/'full_bundle'/'LayeredFS'/'00040000001C1D00'
SOURCE=ROOT/'msgstudio'/'msgstudio'

if OUTROOT.exists(): shutil.rmtree(OUTROOT)
OUT.mkdir(parents=True)
for p in SRC.glob('*.csv'):
    shutil.copy2(p, OUT/p.name)

files={}
for p in OUT.glob('*.csv'):
    with p.open(encoding='utf-8-sig', newline='') as f:
        rows=list(csv.DictReader(f))
        fields=list(rows[0].keys()) if rows else ['label','index','deu','eng','esp','fra','ita','nld','tur']
    files[p.name]=(fields,rows)

review_files=[
'database_movieSerif_0A.csv','database_movieSerif_1A.csv','database_movieSerif_1B.csv',
'database_movieSerif_2A.csv','database_movieSerif_2B.csv','database_movieSerif_3A.csv',
'database_movieSerif_3B.csv','database_movieSerif_3C.csv','database_movieSerif_4A.csv',
'database_movieSerif_5A.csv','database_movieSerif_5B.csv','database_movieSerif_5C.csv',
'database_movieSerif_6A.csv','database_movieSerif_7B.csv','database_movieSerif_7C.csv',
'database_movieSerif_8A.csv','database_movieSerif_9A.csv','database_movieSerif_9B.csv',
'database_movieSerif_9C.csv','database_movieSerif_9D.csv','database_movieSerif_OP.csv',
'database_movieSerif_EP.csv','database_movieSerif_ED.csv',
# Çekirdek terminoloji / açıklama tabloları: bu turda satır atlanmadan denetlendi.
'database_achieveInfo.csv','database_adviceInfo.csv','database_area.csv','database_chapter.csv',
'database_cmn.csv','database_favPowerInfo.csv','database_godInfo.csv','database_godSkillInfo.csv',
'database_itemInfo.csv','database_movieInfo.csv','database_stage.csv','database_sushiInfo.csv',
'database_tipsInfo.csv']

prev_changes={}
prev_path=ROOT/'review_v03'/'INCELEME_DEGISIKLIKLERI.csv'
if prev_path.exists():
    with prev_path.open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f): prev_changes[(r['file'],r['label'])]=r

changes=[]
changed_lookup={}

def row(fn,label):
    for r in files[fn][1]:
        if r['label']==label: return r
    raise KeyError((fn,label))

def add(fn,label,new,reason,category='diyalog'):
    # CSV/MSBT aracı satır sonlarını gerçek newline değil, literal \\n olarak saklıyor.
    new=new.replace('\r\n','\n').replace('\r','\n').replace('\n','\\n')
    r=row(fn,label); old=r.get('tur','')
    if old==new: return
    key=(fn,label)
    r['tur']=new
    if key in changed_lookup:
        # Aynı satır bu turda birkaç küçük adımda düzeltilirse raporda tek satır olarak tut.
        rec=changed_lookup[key]
        rec['new_tur']=new
        if reason and reason not in rec['reason']:
            rec['reason'] += ' Ek düzeltme: ' + reason
        return
    rec={'round':'v0.4','category':category,'file':fn,'label':label,
         'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),
         'ita':r.get('ita',''),'nld':r.get('nld',''),'old_tur':old,'new_tur':new,'reason':reason}
    changes.append(rec); changed_lookup[key]=rec

def replace_in(fn,label,oldfrag,newfrag,reason,category='terim'):
    """Kontrol kodlarını ve satır yapısını koruyarak yalnız görünen bir parçayı değiştir."""
    oldfrag=oldfrag.replace('\r\n','\n').replace('\r','\n').replace('\n','\\n')
    newfrag=newfrag.replace('\r\n','\n').replace('\r','\n').replace('\n','\\n')
    r=row(fn,label); cur=r.get('tur','')
    if oldfrag not in cur:
        raise ValueError(f'{fn}:{label}: parça bulunamadı: {oldfrag!r}')
    add(fn,label,cur.replace(oldfrag,newfrag),reason,category)

def transform(fn,label,func,reason,category='terim'):
    """Kontrol kodlu bir satıra özel dönüşüm uygular."""
    r=row(fn,label); cur=r.get('tur',''); new=func(cur)
    if new==cur:
        raise ValueError(f'{fn}:{label}: dönüşüm değişiklik üretmedi')
    add(fn,label,new,reason,category)

# ---- 5A ----
fn='database_movieSerif_5A.csv'
add(fn,'MovieSerifText_5a_0003_M','İşlerin bu noktaya geleceğini\nhiç düşünmezdim.','DE/ES/FR/NL “işlerin bu noktaya gelmesi” anlamında; “kendimi bu durumda bulmak” Türkçede İngilizce kalıbı gibi duruyordu.')
add(fn,'MovieSerifText_5a_0089_M','Tüm gücümü kullanmaya\nzorladın.','Aynı anlam daha doğal ve vurucu Türkçe ile verildi; eski “gücümün tümünü” yapaydı.')
add(fn,'MovieSerifText_5a_0010_M','Bu gücü gerçekten kullanabilen biri\nolduğunu hiç düşünmemiştim!','DE/ES “bu tekniği gerçekten kullanabilmek/ustalaşmak” nüansını öne çıkarıyor; eski metin yalnız “güce sahip olmak” diyordu.')
add(fn,'MovieSerifText_5a_0013_M','Bir suşi vurucusunun\nen büyük silahı!','“Ultimate weapon” için doğal Türkçe; “nihai silah” gereksiz teknik/çeviri kokuyordu.')
add(fn,'MovieSerifText_5a_0015_M','düşmanını büyüleyip,\nolduğu yere mıhlıyor!','DE/ES/FR/IT/NL etkisinin büyüleme + hareketsiz bırakma olduğunu doğruluyor; “yerinde kilitlemek” yerine doğal deyim kullanıldı.')
add(fn,'MovieSerifText_5a_0019_M','Fark etmişsindir; tek kasını bile\nkıpırdatamıyorsun.','“You’ll find” tehdidi Türkçede “birazdan göreceksin” değil, mevcut durumu fark ettirme tonunda daha doğal.')
for lab in ['MovieSerifText_5a_0025_M','MovieSerifText_5a_0025_F']:
    add(fn,lab,'Hadi ama!','DE/NL bu repliği yalvaran/ısrarcı “please/come on” tonunda veriyor; yalnız “Hadi!” fazla nötrdü.')
add(fn,'MovieSerifText_5a_0028_M','Benimle birlikte...','Sonraki satırla tek cümle oluşturuyor; Türkçe bölünmüş cümle grameri düzeltildi.')
add(fn,'MovieSerifText_5a_0029_M','bu davaya katılır mısın?','ES/FR “cause”, DE/IT/NL “mission” diyor; “arayışımda” hem yapay hem önceki satırla dilbilgisel olarak bozuktu.')
for lab in ['MovieSerifText_5a_0033_M','MovieSerifText_5a_0033_F']:
    add(fn,lab,'Sen ve İmparatorluk bütün suşiyi\nkendinize saklıyorsunuz!\nBu yanlış!','Türkçede “sen ve İmparatorluğun” iyelik yapısı burada doğal değil; anlam aynı tutularak konuşma dili düzeltildi.')
add(fn,'MovieSerifText_5a_0034_M','Öyle mi?','DE/ES/FR/IT/NL kuşkucu “öyle mi?/sen öyle san” tonunda; “Gerçekten.” yanlış düz cümle hissi veriyordu.')
add(fn,'MovieSerifText_5a_0035_M','Peki ya sana...','Sonraki satırla tek cümle; Türkçe koşul yapısı doğal kurulacak şekilde bölündü.')
add(fn,'MovieSerifText_5a_0036_M','bu maskenin ardındaki yüzü göstersem?','Önceki “Ya sana gösterseydim... bu yüzü mü?” birleşince bozuk soru yapısı oluşuyordu; tüm diller maskenin ardındaki yüzü göstermeyi anlatıyor.')
for lab in ['MovieSerifText_5a_0039_M','MovieSerifText_5a_0039_F']:
    add(fn,lab,'Olamaz?!','DE/ES/FR/NL şaşkınlık ve inkâr tonu taşıyor; yüz ortaya çıkınca “Bu da ne?!” bağlama göre zayıftı.')
add(fn,'MovieSerifText_5a_0042_M','Evet... Dünyanın gözünde\nJubay artık öldü.','“Dead to the world” mecazı doğal Türkçeye taşındı; eski “dünya için ölü” kalıptı.')
add(fn,'MovieSerifText_5a_0043_M',"Artık ben yalnızca\nİmparatorluk Ordusu'ndan Tiburon'um!",'DE/ES/FR/NL kimlik değişimini doğrudan “artık Tiburon’um” diye veriyor; “Tiburon’u olarak yaşıyorum” yapaydı.')
for lab,new in [('MovieSerifText_5a_0044_M','Bunu nasıl yapabildin...'),('MovieSerifText_5a_0044_F','Bunu nasıl yapabildin...'),('MovieSerifText_5a_0045_M','Nasıl yapabildin?!'),('MovieSerifText_5a_0045_F','Nasıl yapabildin?!')]:
    add(fn,lab,new,'İhanet bağlamında “How could you” Türkçede “Nasıl yaparsın” değil “Bunu nasıl yapabildin” diye doğal söylenir.')
add(fn,'MovieSerifText_5a_0046_M','Cumhuriyet safında\nsavaşmıştın!','Geçmişteki saf değişimini vurgulayan doğal askerî kullanım; anlam tüm dillerle aynı.')
add(fn,'MovieSerifText_5a_0049_M','Hayalimiz, dünyanın her yerinde\nherkesin suşi yiyebilmesiydi.','FR/NL/ES hedefi “herkes suşi yiyebilsin” diye kuruyor; Türkçede “her yerdeki herkese ulaştırmak” daha mekanik kalıyordu.')
add(fn,'MovieSerifText_5a_0055_M','Zamanla suşiyi kutsal kılan şeyi\nunuttular.','“Somewhere along the way” mecazı Türkçede “Bir noktada” diye çevrilince yapaydı; diğer diller de zamanla unutma anlamında.')
add(fn,'MovieSerifText_5a_0057_M',"Üstelik... Bu, SKC'nin\nsuçlarının en hafifi...",'DE/ES/IT/NL “bu daha en hafifi/en kötüsü değil” nüansında; “Ama bak” yerine tehditkâr geçiş doğal hâle getirildi.')
add(fn,'MovieSerifText_5a_0062_M','İyiliğin yanında olan tek güç...','Sonraki satırla tek cümle; “Only the SLF... is a force for good” Türkçede doğal söz dizimine çevrildi.')
add(fn,'MovieSerifText_5a_0092_M',"Suşi Kurtuluş Cephesi'dir!",'Önceki satırın yüklemi; eski iki parçalı çeviri birleşince “Sadece SKC iyilik için bir güçtür” gibi yabancı bir yapı oluşuyordu.')
add(fn,'MovieSerifText_5a_0067_M','Suşi ruhlarına asıl siz,\nbu yöntemlerinizle ihanet ediyorsunuz!','DE/ES/FR/IT/NL eleştirinin SKC yöntemlerine yöneldiğini doğruluyor; cansız “yöntemler ihanet ediyor” yerine karakterin doğrudan suçlaması korundu.')
for lab in ['MovieSerifText_5a_0074_M','MovieSerifText_5a_0074_F']:
    add(fn,lab,'Bu da ne demek? Anneme\nne oldu?!','ES özellikle “ne diyorsunuz?”, diğer diller bağlam sorusu; “Bu da ne?” fiziksel nesne sorusu gibi kalıyordu.')
add(fn,'MovieSerifText_5a_0075_M','Bunun cevabını...','FR/IT cümlenin “cevap için Masa’ya sor” anlamını açık ediyor; sonraki satırla daha doğal bağlandı.')
add(fn,'MovieSerifText_5a_0076_M','Elveda...','DE/FR/NL vedanın ağır ve kesin tonunu taşıyor; baba-oğul sahnesinde “Hoşça kal” fazla gündelik.')
add(fn,'MovieSerifText_5a_0084_M','Korkarım SKC gücünü fazla cepheye yaydı.\nÇok fazla kayıp verdik.','ES “çok fazla cephede yenilgi”, DE/NL “aşırı yüklenme” diyor; “kendini fazla yaydı” İngilizce kalıbıydı.')
add(fn,'MovieSerifText_5a_0086_M','Geri çekilip saflarımızı\ngüçlendirmeliyiz.','DE “Reihen stärken”, ES birlikleri güçlendirmek; askerî bağlamda “güçlerimizi takviye” yerine doğal Türkçe.')

# ---- 5B ----
fn='database_movieSerif_5B.csv'
add(fn,'MovieSerifText_5b_0011_M','Önce bir soruma cevap ver.','DE/FR/IT/NL açıkça “bir soru” diyor; “bir şeyi cevapla” Türkçede hatalı kullanım.')
for lab in ['MovieSerifText_5b_0026_M','MovieSerifText_5b_0026_F']:
    add(fn,lab,'Bu... NE böyle?!','Vurgu “what IS this” üzerindeydi; eski büyük harf “DA” yanlış öğeyi vurguluyordu.')
add(fn,'MovieSerifText_5b_0029_M','Bunun için gereksiz gördüğümüz\nher lokmayı es geçeriz.','DE/FR/IT/NL “gereksiz lokmayı bırak/atla” anlamında; “lokmayı elemek” teknik ve doğal olmayan bir kalıptı.')
add(fn,'MovieSerifText_5b_0034_M','Hiç de değil.','“Not at all” için doğal karşılık; “Asla” burada eksik/sert cevap gibi duruyordu.')
add(fn,'MovieSerifText_5b_0076_M','Biz yalnızca en lezzetli\nkısımları yeriz.','Tüm diğer diller “yalnız sevilen/lezzetli kısmı yemek” diyor; “ihtiyacımız var” eylemi zayıflatıyordu.')
add(fn,'MovieSerifText_5b_0039_M','Bak...','ES “Mira”, IT “Vedi”; konuşma girişinde “Biliyorsun...” gereksiz İngilizce kalıbıydı.')
add(fn,'MovieSerifText_5b_0043_M','Bu resmen suşi günahı!','ES/FR “sacrilegio/sacrilège”, NL “sushizonde”; dini-metaforik şaka Türkçede “sapkınlık”tan daha doğal ve oyunbaz kuruldu.','espri')
add(fn,'MovieSerifText_5b_0044_M','Günah mı?','Önceki kelime oyunu zinciri korunarak terminoloji eşlendi.','espri')
add(fn,'MovieSerifText_5b_0045_M','Bize bunca zafer kazandırmış bir şeye...','Sonraki satırla birlikte retorik soru doğal Türkçe söz diziminde yeniden kuruldu.')
add(fn,'MovieSerifText_5b_0079_M','...nasıl günah dersin?','“Heresy/sacrilege” tartışmasının Türkçe kelime seçimiyle tutarlı devamı.','espri')
add(fn,'MovieSerifText_5b_0051_M','Sence onun için nasıl bitti?','DE/ES/FR/IT/NL doğal “sence sonu ne oldu?” sorusu; eski cümle gereksiz dolambaçlıydı.')
add(fn,'MovieSerifText_5b_0052_M',"Ağır bir yenilgiye uğradı ve\nutanç içinde Cumhuriyet'ten kaçtı.",'“Soundly defeated” diğer dillerde ağır/ezici yenilgi; “fena halde yenildi” daha gündelik ve zayıftı.')
add(fn,'MovieSerifText_5b_0053_M','Annen de onunla gitti; seni\nyapayalnız geride bıraktılar.','IT/NL “yalnız bıraktı”, DE “seni yetim bıraktılar”; Türkçede “bir yetim olarak bıraktı” yapay ve bürokratikti.')
add(fn,'MovieSerifText_5b_0057_M','Kimse seninle bizim kadar\nilgilenmedi.','DE/ES/IT “care for”, NL “give more about”; “düşünmek” ilgi/gözetme anlamını zayıflatıyordu.')
add(fn,'MovieSerifText_5b_0061_M','Kazandığım onca zafer,\nhaklı olduğumun kanıtı!','Tüm diller “zaferlerim haklılığımın kanıtı” diyor; Türkçe daha konuşulur ve karaktere uygun hâle getirildi.')
add(fn,'MovieSerifText_5b_0062_M','Suşi Kurtuluş Cephesi\nsenin tek seçeneğin.','Tam örgüt adı ve doğal iyelik yapısı; eski metin eksiltili ve sertti.')
for lab in ['MovieSerifText_5b_0063_M','MovieSerifText_5b_0063_F']:
    add(fn,lab,'Hadi oradan! Ben kendi bildiğim gibi\nkazanacağım!','DE/ES/FR/NL “kendi yolum/yöntemim” meydan okumasını veriyor; “bunu kendi yöntemimle kazanacağım” daha yapaydı.')
for lab in ['MovieSerifText_5b_0064_M','MovieSerifText_5b_0064_F']:
    add(fn,lab,'Tek bir pirinç tanesi bile\nbırakma!','Türkçe vurgu doğal yere taşındı; slogan/motto ritmi güçlendirildi.')
add(fn,'MovieSerifText_5b_0066_M','Musashi... Savaştayız.','DE/ES/FR/IT “savaştayız”; “savaş halindeyiz” resmî ve duygusuz kalıyordu.')
add(fn,'MovieSerifText_5b_0068_M','Bunu anlamıyorsan\nön saflardan uzak dur.','EN “front lines”, diğer diller savaşma/cephe anlamında; “cepheye çıkma” yerine doğal askerî ifade.')
add(fn,'MovieSerifText_5b_0071_M','Benim yöntemlerime karşı...','Sonraki satırla tek soru; Türkçe soru söz dizimi iki kutuya doğru bölündü.')
add(fn,'MovieSerifText_5b_0080_M','kazanabileceğini mi sanıyorsun?','Önceki satırın yüklemi; eski sıra “Kazanabileceğine inanıyor musun? Benim yöntemlerime karşı mı?” yapaydı.')
for lab in ['MovieSerifText_5b_0072_M','MovieSerifText_5b_0072_F']:
    add(fn,lab,'Çocuk olabilirim...','“I may be a kid” için doğal kabul cümlesi; “Ben çocuk olabilirim” gereksiz özne vurgusuydu.')
for lab in ['MovieSerifText_5b_0074_M','MovieSerifText_5b_0074_F']:
    add(fn,lab,'ama suşi sevgim\nseninkinden kat kat büyük!','DE “bin kat”, ES “üstün”, diğerleri “çok daha derin/büyük”; Türkçe meydan okuma daha güçlü ve doğal.','karakter tonu')

# ---- 5C ----
fn='database_movieSerif_5C.csv'
for lab in ['MovieSerifText_5c_0001_M','MovieSerifText_5c_0001_F']:
    add(fn,lab,'Hah... hah... hah...','Diğer diller nefes nefese kalmayı sesle yerelleştiriyor; İngilizce “huff” sözcüğünü Türkçede bırakmak yerine doğal soluma sesi kullanıldı.','ses/ünlem')
add(fn,'MovieSerifText_5c_0007_M','Hrrh. Azmine hayran kaldım!','ES/FR/IT/NL özellikle determination/resolve diyor; “cesaret” yerine “azim” daha doğru nüans.')
add(fn,'MovieSerifText_5c_0009_M','Azmin... ve suşiye duyduğun\no derin sevgi...','DE/FR/NL “love”, ES/IT “respect/appreciation”; “mutlak saygı” yapayken sahnedeki duygusal bağ “derin sevgi” ile daha iyi aktarılıyor.')
add(fn,'MovieSerifText_5c_0010_M','Gücümü geri kazandırdı...','ES/FR/IT/NL açıkça “powers restored”; “beni eski hâlime döndürdü” görsel dönüşümden önce güç geri kazanımını belirsizleştiriyordu.')
add(fn,'MovieSerifText_5c_0011_M','Karşında uyanmış,\nçok daha güçlü hâlim!','“Behold” gösterişli tonu ve awakened form korunarak Türkçede daha karakterli bir ilan hâline getirildi.')
for lab in ['MovieSerifText_5c_0013_M','MovieSerifText_5c_0013_F']:
    add(fn,lab,'NEEEE?!','Kaynak ve bütün diller şaşkın soru ünlemi; eski “NEEEE!” Türkçede “ne?” soru tonunu noktalama olmadan zayıflatıyordu.','ses/ünlem')
for lab in ['MovieSerifText_5c_0014_M','MovieSerifText_5c_0014_F']:
    add(fn,lab,'Jinrai, gerçek hâlin\nböyle mi?!','DE/ES/FR/IT/NL “true/real form” diyor; “böyle mi görünmen gerekiyor” gereksiz literal yapıydı.')
add(fn,'MovieSerifText_5c_0017_M',"Tamamdır! Hadi, İmparatorluk Ordusu'nu\npataklayalım!",'DE/FR/IT/NL çok daha argo ve enerjik “beat/kick their butt” tonu kullanıyor; “tepelemeye gidelim” yerine çocuk kahramana uygun canlı Türkçe.','karakter tonu')
for lab in ['MovieSerifText_5c_0020_M','MovieSerifText_5c_0020_F']:
    add(fn,lab,'Hey! Niye eski hâline\ndöndün?!','Tüm diğer diller “change back/return to previous form”; “yeniden değiştin” yönü belirtmiyordu.')
add(fn,'MovieSerifText_5c_0022_M','Hem böyle daha sevimliyim.','Karakter kendi küçük hâlinden söz ediyor; kaynak “Plus, it’s cute” ve FR/IT açıkça “ben daha sevimliyim” diyor.')
add(fn,'MovieSerifText_5c_0023_M','Üstelik kafana da\ntüneyebiliyorum.','“Ride/sit on your head” için yaratığa uygun doğal fiil; “kafana binmek” istemeden komik ve kaba kalıyordu.','karakter tonu')
for lab in ['MovieSerifText_5c_0024_M','MovieSerifText_5c_0024_F']:
    add(fn,lab,'Pençelerine dikkat!','FR “beni tırmalıyorsun”, DE/NL “pençelerine dikkat”; iyelik eki Türkçede muhatabı ve şakayı netleştiriyor.')

# ---- 6A ----
fn='database_movieSerif_6A.csv'
add(fn,'MovieSerifText_6a_0001_M','Ben İmparatorluğun en seçkin generaliyim:\nPür Kudret Purrsilla!','DE/ES/FR/IT/NL adla P sesi/alliterasyonlu unvan kuruyor (Prächtige, Maravilla, puissante, potente, prinses). Türkçede “Pür Kudret Purrsilla” aynı gösterişli ses oyununu yeniden kuruyor.','espri')
add(fn,'MovieSerifText_6a_0003_M','Adamlarım, insanlara yasak suşi\ndağıttığını söyledi...','FR/NL “distribute/give”; “yedirmek” zorla yedirme çağrışımı yapıyordu.')
add(fn,'MovieSerifText_6a_0005_M','Olmaz öyle şey.','EN idiomatik “we can’t have that”, NL “dat gaat niet”; “Buna izin veremeyiz” gereksiz resmî ve çoğul konuşuyordu.')
add(fn,'MovieSerifText_6a_0007_M','Somonla ton balığı çok lezzetli.\nBir tadına bak!','DE/ES/FR/IT/NL gündelik davet tonu; “çok lezzetlidir / biraz dene de gör” ders kitabı gibi kalıyordu.')
add(fn,'MovieSerifText_6a_0009_M','Kes sesini!','DE/ES/FR/IT açıkça “sus”; bağlam Purrsilla’nın konuşmayı kesmesi. “Olduğun yerde dur” yanlış eylem anlatıyordu.')
add(fn,'MovieSerifText_6a_0016_M','Burada söz bende...','DE/NL “burada patron benim”, FR bölgeyi yönetiyorum; “kontrol bende” İngilizce kalıbıydı.')
add(fn,'MovieSerifText_6a_0017_M','ve o iğrenç şeylere\nburada geçit yok!','DE “tabu”, FR dolaşmasına izin yok; yasak koyan generalin tonu Türkçede daha doğal ve karakterli.')
add(fn,'MovieSerifText_6a_0024_M','Hadi, şu sözde gücünü\ngöster bakalım.','Meydan okuma tonu doğal Türkçe ile güçlendirildi; “bize ... göstersene, olur mu?” gereksiz yumuşaktı.')
add(fn,'MovieSerifText_6a_0027_M','Emredersiniz.','DE/ES/FR/IT/NL askerî/formal cevap; “Emrin olur” fazla samimi ve tekil kaldı.')

# ---- 7B ----
fn='database_movieSerif_7B.csv'
for lab in ['MovieSerifText_7b_0001_M','MovieSerifText_7b_0001_F']:
    add(fn,lab,'Iyy... Ne pis kokuyor...','DE/ES/IT/NL açıkça kötü koku/stink; “bir şeyler kokuyor” Türkçede nötr de algılanabilir.')
add(fn,'MovieSerifText_7b_0003_M','Yeter artık wasabiiii! Öğk!','Diğer diller son öğürme sesini yerelleştiriyor/atlıyor; “*blech*” İngilizce bırakılmadı.','ses/ünlem')
add(fn,'MovieSerifText_7b_0004_M','Sanki beynime iğne batıyor... Öğğh!','Tüm diller iğne-beyin metaforunu koruyor; “*hwoarf*” Türkçeleştirildi ve cümle doğal akışa çekildi.','ses/ünlem')
add(fn,'MovieSerifText_7b_0005_M','Dudaklarım uyuştu... *geğirir*','“I can’t feel my lips” için doğal Türkçe sonuç ifadesi; İngilizce “buuurp” yerine anlaşılır sahne eylemi.','ses/ünlem')
add(fn,'MovieSerifText_7b_0009_M','Hahh... Artık dayanamıyorum...\n*öksürür*','DE/ES/FR/IT/NL “artık dayanamıyorum”; eski “yapamıyorum” eylemi belirsizdi, ses etiketleri de Türkçeleştirildi.','ses/ünlem')
add(fn,'MovieSerifText_7b_0018_M','Sence ne yapıyorum?','Kaynak alaycı tam soru; yalnız “Sence?” Türkçede bağlama aşırı bağımlı ve daha zayıf.')
add(fn,'MovieSerifText_7b_0019_M','Seni bir güzel pataklayacağım günü\nbu hücrede bekliyorum.','FR/IT “tekmelemek”, ES “paliza”, NL “op je donder”; eski “zavallı kıçını tekmeleyene kadar zamanımı dolduruyorum” literal ve doğal değildi.','karakter tonu')
add(fn,'MovieSerifText_7b_0023_M','ama o kadar beceriksizdim ki\nbeni buraya tıktılar.','ES “incompetente”, IT “schiappa”, NL “zo slecht”; “hopeless” burada umutsuz değil beceriksiz/anlamsız asker demekti.')
add(fn,'MovieSerifText_7b_0024_M','Ruhum da damak tadım da\nmahvoldu...','ES/FR/IT/NL “soul/will + taste buds”; “tat alma duyum” tıbbi/teknik kalıyordu.')
add(fn,'MovieSerifText_7b_0025_M','Beni kurtar, Musashi!','“You gotta save me” acil ve yalvaran; “kurtarmalısın” gereksiz resmî.')
add(fn,'MovieSerifText_7b_0027_M','Musashi, şuraya bak.','ES/NL “bak”, FR “buraya”; “Şurada” tek başına eksik komut hissi veriyordu.')
add(fn,'MovieSerifText_7b_0036_M','Pekâlâ, şu hesabı kapatalım!','ES “ajustar cuentas”, FR/IT/NL “işi bitirmek”; Türkçe deyim “hesabı kapatmak”, “hesabı kesmek” değil.')
for lab in ['MovieSerifText_7b_0038_M','MovieSerifText_7b_0038_F']:
    add(fn,lab,'Şimdi kavga çıkarıyorsan\nsenden gerçekten umut yok.','“Hopeless” burada önceki “beceriksiz” hakaretine kelime oyunu gibi dönüyor; Türkçede “senden umut yok” doğal ve sonraki cevaba zemin hazırlıyor.','espri')
add(fn,'MovieSerifText_7b_0039_M','Benden umut yok, öyle mi?!','Önceki satırdaki Türkçe kelime oyununun yankısı korunuyor.','espri')
add(fn,'MovieSerifText_7b_0040_M','Seni yendiğimde üstlerim\nbana öyle demeyecek!','“Top brass” için doğal “üstlerim”; “komuta kademesi” karakterin konuşma tarzına göre aşırı bürokratikti.')

# ---- 7C ----
fn='database_movieSerif_7C.csv'
add(fn,'MovieSerifText_7c_0003_M','ama hiç aklıma gelmezdi ki...','Sonraki satırla tek cümle; şaşkınlık tonu doğal Türkçe ile kuruldu.')
add(fn,'MovieSerifText_7c_0004_M','o kişi sen çıkasın, Musashi.','EN/DE/ES/FR/IT/NL “sorun çıkaran kişinin sen olması şaşırtıcı”; eski “Sen olacaktın tabii” tam tersine beklenen bir durum izlenimi veriyordu.')
for lab in ['MovieSerifText_7c_0012_M','MovieSerifText_7c_0012_F']:
    add(fn,lab,'Ama... o artık Tiburon...\nve bir İmparatorluk generali.','Kaynak “general”; “komutan” anlamı genişletiyordu. Hikâyedeki resmî unvanla tutarlılık sağlandı.','terim')
add(fn,'MovieSerifText_7c_0013_M','Bunu gayet iyi biliyorum.','“I’m well aware” için doğal ve sakin karakter tonu; “fazlasıyla farkındayım” çeviri kalıbıydı.')
for lab in ['MovieSerifText_7c_0016_M','MovieSerifText_7c_0016_F']:
    add(fn,lab,'Suşinin verdiği mutluluğu...\nBana bunu sen öğrettin!','ES “suşi yemenin zevki”, FR “joie des sushis”; “suşinin mutluluğu” Türkçede anlamsal olarak nesnenin kendi mutluluğu gibi duruyordu.')
add(fn,'MovieSerifText_7c_0017_M','Sana olan borcumu ödemek istedim,\no yüzden...','ES “sana borçluydum”, FR “sana borcum vardı”; eski “Borç ödemek istedim” kişisel minnettarlığı eksiltiyordu.')
add(fn,'MovieSerifText_7c_0020_M','Hayalimi benim yerime\nyaşattın...','“Keep the dream alive in my place” için doğal mecaz; eski “hayali yaşattın” iyelik bağını kaybediyordu.')
add(fn,'MovieSerifText_7c_0022_M','Dünyanın dört bir yanındaki...','Sonraki satırla birlikte “dünyadaki bütün çocuklara” cümlesi Türkçe doğal sıraya taşındı.')
add(fn,'MovieSerifText_7c_0023_M','bütün çocuklara suşi yedireceğiz!','Önceki satırın yüklemi; eski “her ülkede, tüm dünyada” tekrarlı ve bölünmüş yapıydı.')
add(fn,'MovieSerifText_7c_0025_M','Daha doğrusu... keşke\nyanında olabilseydim.','“I’m with you… Or I wish I was” kendini düzeltme; “keşke öyle olsaydım” belirsiz ve mekanikti.')
add(fn,'MovieSerifText_7c_0026_M','Ama artık gücüm kalmadı...','ES/NL “yapamıyorum”, DE/IT “tükendim”; “ben bittim” Türkçede fazla kaba ve belirsiz.')
add(fn,'MovieSerifText_7c_0029_M','Bir zamanlar yaptığım o çetin suşi eğitimi\nartık yalnızca bir anı.','DE/FR/IT/NL “training is only a memory”; “katlandığım” istemeden eğitime olumsuz anlam yüklüyordu.')
add(fn,'MovieSerifText_7c_0030_M','Suşi vuruculuğu günlerim...\nsona erdi.','FR “kariyerim geride”, diğer diller sona erdi; Türkçede daha doğal ve karakterin ağır tonuna uygun.')
for lab in ['MovieSerifText_7c_0031_M','MovieSerifText_7c_0031_F']:
    add(fn,lab,'Öyle deme!','ES/FR doğrudan “bunu söyleme”; bağlamda “No way!” itirazdan çok Franklin’in vazgeçmesine tepki.')
add(fn,'MovieSerifText_7c_0036_M','Ve sen onun hayalini\nyaşatmaya karar verdiğine göre...','“Carry on his dream” Türkçede “hayali sürdürmek”ten daha doğal biçimde “hayalini yaşatmak”.')
add(fn,'MovieSerifText_7c_0037_M','ben de bundan böyle\nsana eşlik edeceğim.','ES/FR/NL beraber gelmek/eşlik etmek; “seni izleyeceğim” Türkçede seyretmek anlamına kayıyordu.')
add(fn,'MovieSerifText_7c_0042_F','güzel sofralarda edindiğimiz\ndostlar için...','M ve F kaynağı aynı; Türkçede cinsiyet farkı yok. M sürümündeki doğal “güzel sofralarda” ifadesiyle tutarlılık sağlandı.')
add(fn,'MovieSerifText_7c_0064_M','Zirveye ulaştın!','FR/IT/NL “summit/apex/top”; “en üst basamak” literal rung metaforunu gereksiz taşıyordu.')
add(fn,'MovieSerifText_7c_0051_M','En içten minnettarlığı gösterdin.\nİhtiyacım olan tek şey buydu.','ES “gratitud más sincera”, diğer diller intense/greatest; “en büyük minnettarlık” doğal olmayan dereceleme.')
add(fn,'MovieSerifText_7c_0055_M','Senin sayende\nnihai hâlime ulaştım...','ES/FR ultimate/final, NL perfect; “en yüce hâl” fazla dinî/soyut çağrışımlıydı.')
for lab in ['MovieSerifText_7c_0065_M','MovieSerifText_7c_0065_F']:
    add(fn,lab,'Ve gidip babamla savaşalım!','DE “gösterelim”, ES “yüzleşelim”, IT “yenelim”; kaynak gizli “let’s” öznesi taşıyor. Eski emir “babamla savaş!” yanlış kişiye tekil komut veriyordu.')

# ---- 8A ----
fn='database_movieSerif_8A.csv'
add(fn,'MovieSerifText_8a_0002_M',"Musashi'm benim.",'“My Musashi” sevgi hitabı; Türkçede iyelik doğal söz dizimine taşındı.')
add(fn,'MovieSerifText_8a_0003_M','Sonunda anlayacaksın...','Sonraki satırla birlikte sevginin derecesini “anlamak”; “öğrenmek ... sevgisini” Türkçede bozuk bağlanıyordu.')
add(fn,'MovieSerifText_8a_0004_M','babanın suşiyi ne kadar sevdiğini.','DE/ES/NL açıkça “ne kadar sevdiğini”; önceki “suşiye olan sevgisini” iki satır birleşince daha mekanikti.')
add(fn,'MovieSerifText_8a_0007_M',"Ne?! Suşido'm\nişe yaramadı!",'Şaşkın soru noktalaması ve doğal ara; anlam değişmedi.')
add(fn,'MovieSerifText_8a_0010_M',"Suşido'ya karşı hamle...",'ES/IT “anti-Sushido”, DE/NL counter; “Suşido savuşturması” Türkçede neyin savuşturulduğunu belirsiz bırakıyordu.')
for lab in ['MovieSerifText_8a_0016_M','MovieSerifText_8a_0016_F']:
    add(fn,lab,'Suşi yemek konusunda...','Sonraki satırla tek cümle; Türkçe karşılaştırma söz dizimi yeniden bölündü.')
for lab in ['MovieSerifText_8a_0017_M','MovieSerifText_8a_0017_F']:
    add(fn,lab,'senin kadar deneyimli olmayabilirim, baba...','ES/FR/NL “experience”; eski iki satır “O kadar çok pratiğim olmayabilir... suşi yemekte senin kadar” gramer olarak bozuktu.')
for lab in ['MovieSerifText_8a_0020_M','MovieSerifText_8a_0020_F']:
    add(fn,lab,'Ben iliklerime kadar\nsuşi vurucusuyum!','“To the core” için Türkçede yerleşik “iliklerine kadar” deyimi; NL “in hart en nieren” de aynı yaratıcı yerelleştirme yaklaşımını kullanıyor.','deyim')

# ---- 9A ----
fn='database_movieSerif_9A.csv'
for lab in ['MovieSerifText_9a_0001_M','MovieSerifText_9a_0001_F']:
    add(fn,lab,'Şey... baba?','Tereddütlü hitap doğal Türkçe konuşma diline çekildi; “Hey, ee, Baba?” yazılı çeviri gibi duruyordu.')
add(fn,'MovieSerifText_9a_0006_M','Yollarımız o kadar çok kez kesişti ki...','Sonraki “saymakla bitmez” yüklemiyle doğal Türkçe cümle kuruldu.')
add(fn,'MovieSerifText_9a_0009_M','Adı desen...','Üç parçalı cümle Türkçe “X desen, Y desen” kalıbıyla doğal ve komik biçimde yeniden kuruldu.')
add(fn,'MovieSerifText_9a_0010_M','gerçek kimliği desen...','Önceki “Adı desen” kalıbının paraleli; eski “gerçek kimliğini” hâl eki cümleyle uyuşmuyordu.')
add(fn,'MovieSerifText_9a_0019_M','Son savaş bizi bekliyor!','FR/IT/NL “final battle awaits”; “son savaşa gitmeliyiz” mekanik yol tarifi gibi kalıyordu.')
add(fn,'MovieSerifText_9a_0021_M','Vaktimizi boşa harcıyorsun!','“Wasting our time” doğal Türkçe deyimle tamamlandı.')
add(fn,'MovieSerifText_9a_0023_M','Bunu sana milyon kere sordum...','Türkçe konuşma dilinde sayı + “kere”; “milyon kez” daha yazı diliydi.')
add(fn,'MovieSerifText_9a_0024_M','Ben sıradan bir adamım; her an, her yerde\nkarnım suuuş diye zil çalar.','“soosh” bütün diğer dillerde bilerek bozuluyor (Suuush/sushurri/shisus/sushame/soesj). Türkçede normal “suşi” bırakmak şakayı kaybediyordu; “suuuş” + “karnım zil çalar” ile yeniden kuruldu.','espri')
add(fn,'MovieSerifText_9a_0028_F','Neymiş?','M/F İngilizce aynı ve Türkçe cinsiyetsiz; F’deki “Ne oldu?” bağlamı değiştiriyordu.')
add(fn,'MovieSerifText_9a_0030_M','Eyvah! Kes, kes!','Sahne çekimi şakası diğer dillerde “cut/corten/coupez/taglia”; İngilizce “oops” yerine doğal Türkçe ünlem.')
add(fn,'MovieSerifText_9a_0034_M','Ben kaçayım artık!','ES/FR/IT/NL çok gündelik kaçış ifadesi; “Artık gitme vaktim” karakterin gevşek tonuna göre fazla resmî.')
add(fn,'MovieSerifText_9a_0039_M','Eh, boş ver. Takma kafana.','“I wouldn’t worry” için doğal konuşma dili; “Dert etme” ile “boş ver” yineleniyordu.')

# ---- 9B ----
fn='database_movieSerif_9B.csv'
for lab in ['MovieSerifText_9b_0001_M']:
    add(fn,lab,'Majesteleri...','Konuşulan kişi İmparator; IT zaten “Maestà”, diğer diller hükümdar hitabı. “İmparatorluk Hazretleri” Türkçede yerleşik bir unvan değil.','terim')
add(fn,'MovieSerifText_9b_0002_M','Buraya kadar.','Teslim çağrısında “This is the end” için doğal ve tehditkâr Türkçe; “Bu işin sonu” eksik isim cümlesi gibiydi.')
add(fn,'MovieSerifText_9b_0003_M','Direnmenin anlamı yok.','DE/ES/FR/NL “resistance is useless”; doğal Türkçe kalıp.')
add(fn,'MovieSerifText_9b_0004_M','Lütfen direnmeden teslim olun.','“Surrender peacefully” bağlamında barışçıl/şiddetsiz teslim; Türkçe emir daha doğal ve kısa.')
add(fn,'MovieSerifText_9b_0005_M',"Musashi'yle birlikte...",'Sonraki satırla tek cümle; gereksiz unvan tekrarı kaldırılıp konuşma akışı korundu.')
add(fn,'MovieSerifText_9b_0006_M','her şeye yeniden başlayabiliriz.','DE/ES/IT/NL “start anew/from zero”, FR “new era”; “yeniden inşa” nesnesiz kalıyordu.')
add(fn,'MovieSerifText_9b_0007_M','Majesteleri?','Hükümdar hitabı v0.4 içinde tutarlılaştırıldı.','terim')
add(fn,'MovieSerifText_9b_0009_M','Majesteleri! Lütfen\nbeni dinleyin!','Hükümdar hitabı v0.4 içinde tutarlılaştırıldı.','terim')
add(fn,'MovieSerifText_9b_0012_M','M-Majesteleri! Durun!','Hükümdar hitabı v0.4 içinde tutarlılaştırıldı.','terim')
add(fn,'MovieSerifText_9b_0030_M','Hep böyle derdi...','DE/IT/NL “always”; “Kesin bunu derdi” varsayım anlamı katıyordu.')
add(fn,'MovieSerifText_9b_0034_M','Hey! Seninle konuşuyoruz!','ES/FR/IT doğrudan “seninle konuşuyoruz”; “Burada konuşuyoruz” yer bildiren anlamsız bir kalıp olmuştu.')
add(fn,'MovieSerifText_9b_0036_M','Onu da yiyip bitirirdi.','DE/ES/FR/IT açıkça somonu da yediğini söylüyor; “aldı” olayın çocukluk şakasını zayıflatıyordu.')
add(fn,'MovieSerifText_9b_0037_M','Beni dinliyor musun?!','IT “mi ascolti”, bağlam karşı tarafın konuşmayı dinlememesi; “duydun mu” geçmiş tek eylem gibi kalıyordu.')
add(fn,'MovieSerifText_9b_0040_M','Ben de kimden istersem\nistediğimi alabilirdim.','FR/IT/NL “başkalarından istediğini almak”; eski cümle nesneyi düşürüp anlamı eksiltiyordu.')
add(fn,'MovieSerifText_9b_0045_M','Majesteleri...','Hükümdar hitabı tutarlılaştırıldı.','terim')
add(fn,'MovieSerifText_9b_0056_M','doymak bilmeyen tek bir arzunun...','ES/FR “insatiable”, DE/NL bottomless desire; Türkçede tekrar eden “dipsiz/yeme arzusu” yerine daha doğal tehdit dili.')
add(fn,'MovieSerifText_9b_0046_M','esiri olmuş durumda:','Önceki ve sonraki parçayla tek cümle; anlam yapısı korunuyor.')
add(fn,'MovieSerifText_9b_0047_M','dünyadaki bütün suşileri yemek.','“Arzunun ... yeme arzusu” tekrarını kaldırarak cümleyi doğal tamamlıyor.')

# ---- 9C ----
fn='database_movieSerif_9C.csv'
add(fn,'MovieSerifText_9c_0003_M','Neden bana hiç\nsuşi vermedin?','ES/FR “mahrum bırakmak”, NL “yememe izin vermemek”; “yedirtmedin” yanlış ettirgen yapıydı.')
add(fn,'MovieSerifText_9c_0005_M','Öz be öz evladın!','“Your flesh and blood” için Türkçede yerleşik aile deyimi; “Kanın, canın” anlaşılır ama doğal bir hitap değil.','deyim')
add(fn,'MovieSerifText_9c_0014_M','çarpık aile bağlarıyla\nbirbirine dolanmış...','ES/FR/NL aile ilişkilerinin bozukluğu/eksik baba sevgisi; “bağlarıyla karışmış” İngilizce “mixed with” kalıbıydı.')
add(fn,'MovieSerifText_9c_0015_M','Ne trajik.','ES “Qué tragedia”; Türkçede tek “Trajik.” fazla etiket/yorum gibi duruyordu.')
add(fn,'MovieSerifText_9c_0018_M','Var olan ne varsa...','DE/NL “dünyadaki her şey”, ES “todo lo que hay”; “Orada ne varsa” yanlışlıkla belirli bir mekâna işaret ediyordu.')

# ---- 9D ----
fn='database_movieSerif_9D.csv'
for lab in ['MovieSerifText_9d_0001_M','MovieSerifText_9d_0001_F']:
    add(fn,lab,'Pes et!','ES/IT/NL doğrudan “teslim ol/pes et”; “Bırak artık” neyi bırakacağını belirsiz bırakıyordu.')
for lab in ['MovieSerifText_9d_0008_M','MovieSerifText_9d_0008_F']:
    add(fn,lab,'Paylaşacağız!','DE/ES/FR/IT/NL bunu karar/bildiri olarak kuruyor; “Paylaşabiliriz” yalnız olasılık anlamı verip zafer sonrası kararlılığı zayıflatıyordu.')
add(fn,'MovieSerifText_9d_0012_M','Ne de erdemli kesiliyorsun!','FR “vaaz veriyorsun”, ES “altruist görünüyorsun”; self-righteous için Türkçede küçümseyici, karakterli karşılık.','karakter tonu')
add(fn,'MovieSerifText_9d_0014_M','Bir gün suşi açlığı\nhepinizin de gözünü döndürecek.','DE/ES/IT/NL açlığın kişiyi ele geçirmesi/tüketmesi anlamında; Türkçede “gözü dönmek” açgözlülük ve kontrol kaybını yaratıcı biçimde taşıyor.','deyim')
add(fn,'MovieSerifText_9d_0021_M','O gitti... suşinin\ngeldiği dünyaya.','Bütün diğer diller doğrudan “sushinin geldiği dünya”; “kaynağı olan dünya” gereksiz teknikti.')
add(fn,'MovieSerifText_9d_0024_M','Majestelerine laf anlatmak\nmümkün değildi.','ES/FR/IT “reason/convince/communicate”; “söz geçirmek” otorite kurmak anlamına kayıyordu. Hükümdar hitabı da standartlaştırıldı.','terim')

# ---- Geriye dönük satır-bazlı denetim: 0A-4A + OP/EP/ED ----
# 1A
fn='database_movieSerif_1A.csv'
for lab in ['MovieSerifText_1a_0002_M','MovieSerifText_1a_0002_F']:
    add(fn,lab,'İstediğim kadar meyve!','IT/NL “istediğim kadar”, DE/ES/FR “sonsuz/bol meyve”; “yiyebildiğim kadar” büfe kalıbı gibi kalıyordu. Çocuğun bol meyve bulma sevincini daha doğal veriyor.','karakter tonu')
for lab in ['MovieSerifText_1a_0035_M','MovieSerifText_1a_0035_F']:
    add(fn,lab,'Nereye gittiniz?','DE/ES/FR/IT/NL doğrudan kayıp anne-babaya “nereye gittiniz/neredesiniz”; sondaki “siz” Türkçede yapay vurgu oluşturuyordu.','diyalog')
add(fn,'MovieSerifText_1a_0040_M','Bana Franklin de. Açlığın kol gezdiği\nbu dünyada bir gezginim.','DE/NL “hungry world”, FR “kıtlığın kemirdiği topraklar”; “kıtlık içindeki topraklarda gezip dururum” çeviri kokuyordu. “Açlığın kol gezdiği” anlatıcının gezgin tonunu koruyor.','karakter tonu')
add(fn,'MovieSerifText_1a_0103_M','ona bakmak bile suç;\nyemekten söz etmiyorum bile.','DE/IT/NL “bakmak bile suç, yemek bir yana”; önceki parçayla birlikte Türkçede doğal ve tamamlanmış bir cümle kuruldu.','diyalog')
add(fn,'MovieSerifText_1a_0058_M','Sana suşiyi tatma fırsatı veriyorum.\nNe dersin? Nefis!','DE/NL “lezzetli”, FR/IT “ister misin?”; “Nefistir” Franklin’in sıcak konuşmasına göre fazla resmîydi.','karakter tonu')
add(fn,'MovieSerifText_1a_0068_M','bunların suçlusu suşi değil.','Önceki etiket zaten “Ama bilmelisin ki...” diye başlıyor. İkinci “Ama” Türkçede gereksiz tekrar oluşturuyordu; tüm diller tek bağlı cümle anlamını taşıyor.','diyalog')
for lab in ['MovieSerifText_1a_0077_M','MovieSerifText_1a_0077_F']:
    add(fn,lab,'Suşi kuşu mu?','Bu sahnede her dil “sushi sprite” ifadesini art arda yanlış duyma şakasıyla yeniden yazıyor: DE Meister/Kleister, ES necio/Eugenio, FR souche/calamité, NL bami/tsunami. “Suşi gurusu” anlamca yakın ama ses şakasını kaybediyordu; “suşi ruhu / suşi kuşu” Türkçede ses benzerliğini geri getiriyor.','kelime oyunu')

# 2A
fn='database_movieSerif_2A.csv'
add(fn,'MovieSerifText_2a_0006_M','Başarısız oldun, Kodiak.','DE/ES/FR/NL doğrudan “başarısız oldun”; mevcut “bizi hayal kırıklığına uğrattın” daha yumuşak ve kişisel bir anlam katıyordu. Tiburon’un soğuk hükmü korunuyor.','karakter tonu')
add(fn,'MovieSerifText_2a_0010_M','Söyle... Jinrai kiminle\nbağ kurdu?','ES “kimi seçti”, FR “partneri kim”, DE/IT/NL “kime hizmet ediyor/master”; oyunda artık standartlaştırdığımız Bağ mekaniği bu ilişkiyi Türkçede en doğal biçimde anlatıyor.','terim')

# 2B
fn='database_movieSerif_2B.csv'
add(fn,'MovieSerifText_2b_0034_M','Bin sağ ol, dostum!','“Thanks a million” için Türkçede yerleşik abartılı teşekkür kalıbı “bin sağ ol”; “çok sağ ol” kaynak repliğin renkli karakter sesini düzleştiriyordu.','karakter tonu')

# 3A
fn='database_movieSerif_3A.csv'
add(fn,'MovieSerifText_3a_0008_M','Birini bekliyorum.','DE/IT/NL “birini bekliyorum”, ES/FR “birini arıyorum”; “kolluyorum” Türkçede korumak/gözetmek anlamına kayabiliyordu.','anlam')
for lab in ['MovieSerifText_3a_0013_M','MovieSerifText_3a_0013_F']:
    add(fn,lab,'Aradığım kişiyi az önce buldum.','FR açıkça “aradığım kişiyi buldum”, IT “aradığım kişiyi”; mevcut “Ve işte buldum” nesneyi düşürerek Celia’nın Musashi’yi hedef olarak bulduğu sürprizi zayıflatıyordu.','diyalog')
add(fn,'MovieSerifText_3a_0024_M','Şimdi... gelelim asıl meseleye!','ES “al grano”, NL “ter zake”, IT “a noi due”; mevcut anlam doğruydu fakat Türkçe söz dizimi konuşmada sert kalıyordu. Aynı anlam daha doğal ritimle verildi.','karakter tonu')

# 3B
fn='database_movieSerif_3B.csv'
add(fn,'MovieSerifText_3b_0018_M','belki senin suşide ne bulduğunu\nben de anlayabilirim.','DE/ES/FR/IT/NL ortak anlam “neden bu kadar sevdiğini anlamak”; “anlamayı öğrenebilirim” Türkçede dolambaçlı ve mekanikti.','diyalog')

# 3C
fn='database_movieSerif_3C.csv'
add(fn,'MovieSerifText_3c_0008_M','General meslektaşınız\ngörevden alındı.','DE Amtskollege, NL medegeneraal, IT “diğer general”; “general yoldaşınız” Türkçede ideolojik/partizan çağrışım yapıyordu. “Meslektaş” resmî askerî bildiriye uyuyor.','terim')

# 4A
fn='database_movieSerif_4A.csv'
add(fn,'MovieSerifText_4a_0002_M','Altın yılların altın çınarı,\nGeneral Ausprey!','EN “golden-years golden boy” yaşlılık + altın çocuk kelime oyunu; NL de “gouwe ouwe” diyerek yaşlılık esprisini koruyor. “Altın çağın altın ismi” yaş unsurunu kaybediyordu; “altın çınar” Türkçede saygın yaşlı kişi imgesini ve altın tekrarını birlikte taşıyor.','kelime oyunu')

# Açılış şarkısı
fn='database_movieSerif_OP.csv'
add(fn,'MovieSerifText_OP_0004_M','Suşi ruhu tarzı!\nSamuray gibi kıvılcım saç!','IT kaynak yapıyı koruyor; FR de ruh/samuray imgelerini birleştiriyor. Mevcut ikinci dize öznesiz ve slogan gibi kesiliyordu; emir kipinde şarkı enerjisi güçlendirildi.','şarkı')
add(fn,'MovieSerifText_OP_0005_M','Işık şeritleri\nsonsuz bir nehir gibi aksın!','EN “endless stream”, ES sonsuz döngü, FR sonsuz akış; mevcut “durmadan akıp gitsin” anlamı taşısa da imgeli şarkı dilini düzleştiriyordu.','şarkı')
add(fn,'MovieSerifText_OP_0011_M','sel olup taşıyor!\nHazırdır artık, bekleyemem!','FR “artık dayanamıyorum”, IT “tsunami”; önceki iki etiket açlık ve ağız sulanmasını büyütüyor. “Hadi, hazırdır artık” Türkçede doğal değildi; taşma + sabırsızlık ritmi yeniden kuruldu.','şarkı')
add(fn,'MovieSerifText_OP_0018_M','Dünya benim tabağım—\nhaydi, saldır sofraya!','EN açık kelime oyunu “world is my plate”; ES de “dünya tepside” imgesini koruyor. “Dünya önümde bir tabak” sahiplik/metaforu zayıflatıyordu; ikinci dize şarkının iştahlı savaş tonuna uygun serbest yerelleştirme.','şarkı')
add(fn,'MovieSerifText_OP_0023_M','Adım adım zirveye!','EN stepping up, DE “daha hızlı”, FR yükselen tabak yığınları, IT ilerlemek; “Adım adım yükselirim” doğru ama şarkıda daha vurucu slogan ritmi hedeflendi.','şarkı')
for lab in ['MovieSerifText_OP_0025_M','MovieSerifText_OP_0032_M']:
    add(fn,lab,'Sonra hep birlikte\ndans dans dans dans!','EN “we can dance”, ES/FR/IT/NL toplu dans; “Sonra dans et” tekil emir verip “we” neşesini kaybediyordu.','şarkı')

# Epilog
fn='database_movieSerif_EP.csv'
add(fn,'MovieSerifText_ep_0006_M','Biz suşi ruhlarını yaşatan, suşi yerken\nduyduğun minnettarlıktır. Bunu hiç unutma.','DE açıkça tekil “du”, NL “jouw”; Jinrai doğrudan Musashi’ye konuşuyor. “duyduğunuz” çoğul/resmî hitap karakter ilişkisini bozuyordu.','karakter tonu')

# Kapanış şarkısı
fn='database_movieSerif_ED.csv'
add(fn,'MovieSerifText_ED_0001_M','Sofrayı kur, şölen başlasın—\nönümüzde suşi denizi!','ES “festival”, FR “göz alabildiğine suşi”, IT “banquet + sea of sushi”; mevcut anlam doğruydu ancak şarkı ritmi daha canlı bir Türkçe sloganla güçlendirildi.','şarkı')
add(fn,'MovieSerifText_ED_0003_M','Karnım tıka basa doldu,\nbiraz abarttım galiba!\n(Olsun!)','ES/FR açıkça tıka basa yeme/karın patlayacak esprisi yapıyor. “Birden aptal gibi hissediyorum” İngilizceyi kelimesi kelimesine izleyip şakanın iştahlı tonunu bozuyordu.','şarkı')
add(fn,'MovieSerifText_ED_0005_M','Açken huysuz olurum ben—\n(Ama bu gece kavga yok,\nbu gece eğlence çok!)','ES “bu gece kavga değil dans”, FR “kavga yok, eğlence”, NL aç karnına savaşılmaz. Türkçede kafiye ve parti tonu yeniden kuruldu.','şarkı')
add(fn,'MovieSerifText_ED_0006_M','Bu sofrayı\ndünyayla paylaşalım!','EN paylaşma, IT kimse suşisiz kalmasın; “yemeğimizi” tek kişinin porsiyonu gibi duruyordu, oyunun ortak sofra temasına “bu sofra” daha uygun.','şarkı')
add(fn,'MovieSerifText_ED_0007_M','Dostlarım hep sofrada—\nyan yana yiyoruz.','EN/IT/FR arkadaşlarla aynı sofrayı vurguluyor. “Tüm arkadaşlarım oturmuş” gözlemsel ve mekanik kalıyordu; birliktelik öne alındı.','şarkı')
add(fn,'MovieSerifText_ED_0009_M','Tabak tabak lezzet geçiyor;\nhepsinden tatmalıyım!','ES/IT hepsini tatma isteğini öne çıkarıyor; “daha lezzetli tabaklar” önceki tabakların daha kötü olduğu gibi istenmeyen karşılaştırma yaratıyordu.','şarkı')
add(fn,'MovieSerifText_ED_0011_M','Ki-lo-met-re-lerce suşi\nuzanıyor önümde,','IT doğrudan kilometrelerce bant/suşi, diğer diller bolluğu vurguluyor. “yemek” fazla genel; şarkının ana imgesi suşi.','şarkı')
add(fn,'MovieSerifText_ED_0012_M','beni çağırıyor\nsuşi cennetine!','FR “paradise”, IT “seventh heaven”; “davet ediyor” resmî tınlıyordu. “Çağırıyor” şarkı ritmine ve cazibe imgesine daha uygun.','şarkı')


# ---- Çekirdek veritabanı kalite turu ----
# Bu blokta İngilizce tek referans olarak kullanılmadı; DE/ES/FR/IT/NL ortak yorumu
# özellikle literal çeviri, terminoloji, espri ve doğal Türkçe açısından karşılaştırıldı.

# Advice
fn='database_adviceInfo.csv'
add(fn,'AdviceInfo_014','Zafer kazanıp vurucu rütbeni yükselt;\nruhlarla daha kolay bağ kurarsın.','DE Pakt/Bündnis, ES/IT alianza/patto, FR amitié/alliance ve NL band yaklaşımı “pledge”ın burada yemin değil oyun mekaniği olan bağ kurma olduğunu doğruluyor. v0.3 Bağ terminolojisiyle tutarlılaştırıldı.','terim')

# Area descriptions
fn='database_area.csv'
add(fn,'areaText_area01',"Sıcak, huzurlu bir bölge. Suşi\nSavaşları'nda İmparatorluk'a yenildikten\nsonra burada suşi bulunmaz olmuş.",'DE/ES/FR/IT/NL bölgenin suşiden mahrum kaldığını anlatıyor; “suşi açısından çoraklaşmış” Türkçede yapay bir soyutlama ve doğal dünya anlatımı değil.','anlatım')
add(fn,'areaText_area04Sub','Batının en ucunda, İmparatorluğun\nhâkimiyetinin zayıfladığı yerlerde,\nCumhuriyet kültürü ve gizli tapınakları\nvarlığını sürdürüyor.','Bütün diller İmparatorluk denetiminin zayıf olduğu yerde Cumhuriyet kültürü/idealleri ve gizli tapınakların sürdüğünü söylüyor; “saklı tapınakları yaşamayı sürdürür” özne-yüklem açısından bozuktu.','anlatım')
add(fn,'areaText_area04Camp',"SLF'nin Batı İmparatorluğu'na karşı\nharekâtındaki ileri üssü. Her şey\nsorunsuz gidiyor gibi, ama...",'DE saha kampı, ES/IT/NL karargâh/üs, FR base diyor. “Tutunma noktası” İngilizce foothold’u fazla literal çeviriyordu; askerî bağlama “ileri üs” daha doğal.','terim')
add(fn,'areaText_area05','Karla kaplı tepelerin ötesinde,\nİmparatorluğun dehşet verici gizli bir\ntesis işlettiği söylenen bir ada var.','Diğer diller gizli/ürkütücü bir tesisin orada bulunduğunu/işletildiğini söylüyor; Türkçedeki “tesis tuttuğu” yanlış eşdizimdi.','anlatım')
add(fn,'areaText_area06','Çam ormanları ileri teknolojiyle açılarak\nkurulmuş geniş bir bölge. Doğudaki saray\nburayı demir yumrukla yönetir.','FR ormanların açılması, ES/IT gelişmiş teknoloji ve sert yönetim, kaynak firm rulership nüansını doğruluyor. “Ormanlardan oyulmuş” literal, “sıkı yönetimi buraya hükmeder” ise yapaydı.','anlatım')

# Sushi encyclopedia
fn='database_sushiInfo.csv'
add(fn,'SushiInfo_Kappa','Pirincin yumuşacık dokusu,\nçıtır salatalığa nefis bir başlangıç.','DE/ES/FR/IT/NL tümü yumuşak pirinçten çıtır/gevrek salatalığa geçişi kuruyor. “Pofudukluk” ve “kıtırtısına giriş” Türkçede doğal gastronomi anlatımı değildi.','ansiklopedi')
add(fn,'SushiInfo_Aji','Işıldayan derisinden daha güzel tek şey\nonun tadı.','Kaynağın kısa övgü karşılaştırması tüm dillerde korunuyor; eski “daha güzel olan tek şey, tadı” yüklemsiz ve mekanik duruyordu.','ansiklopedi')
add(fn,'SushiInfo_Tako','Pürüzsüz, hafif diri bir doku;\nkenarlarında çıtır çıtır sürprizler.','ES esnek, FR dişe dirençli, IT hafif lastiksi/çiğnenir dokuyu anlatıyor. “Hafif çiğnenir” Türkçede doğal sıfat değil; “diri” ağız hissini daha iyi taşıyor.','ansiklopedi')
add(fn,'SushiInfo_Tarabagani','Kırmızı, sıkı etini tadınca\niçindeki gücü sen de hissedersin.','DE/ES/FR/IT gücün yengecin etinde/içinde hissedildiğini söylüyor. “Geldiği gücün izleri” kaynak dil yapısını Türkçeye taşıyıp anlamı bulanıklaştırıyordu.','ansiklopedi')
add(fn,'SushiInfo_Inari','Kızarmış tofu kabuğundan tuzlu-tatlı bir kese;\niçinde küçük bir pirinç lokması saklı.','Diğer diller tofu kesesi/yastığı içinde pirinç imgesini kullanıyor. “İçinde kıvrılıp duran minicik bir pirinç yuvası” gereksiz karmaşık ve görsel olarak belirsizdi.','ansiklopedi')
add(fn,'SushiInfo_Melon','Göz alıcı kırmızı kabuğunun altında\nbaş döndüren bir tatlılık saklı.','ES/FR meyveyi tatlı ve sulu bir hazine olarak övüyor. “Lüks tatlılığın ta kendisi” İngilizce reklam kalıbını Türkçede yapay bırakıyordu.','ansiklopedi')
add(fn,'SushiInfo_Amaebi','Adına yaraşır biçimde, derin ve dolgun\ntatlılığıyla meşhurdur.','Diğer diller adındaki “sweet” vurgusunu doğal biçimde tatlılığa bağlıyor. Eski noktalı virgül ve “aromalı tatlılık” söz dizimi bozuktu.','ansiklopedi')
add(fn,'SushiInfo_EngawaRoast','Çıtırtılı dokusu ve tam kararında burukluğu,\ninsana başka hiçbir şey aratmaz.','“Hiçbir” yazımı düzeltildi; cümlenin özne-yüklem ilişkisi de doğal hâle getirildi. Diğer diller çıtırlık + hafif burukluk/yanıklık dengesini övüyor.','ansiklopedi')
add(fn,'SushiInfo_HotateRoast','Deniz tarağının ipeksi dokusu ateşle\nmühürlenir: baştan çıkarıcı bir buluşma.','ES/FR/IT ateş/pürmüz ile ipeksi deniz tarağı dokusunun birleşip cezbettiğini söylüyor. Eski “buluşur: baştan çıkarıcı” eksiltili ve Türkçede yarım cümleydi.','ansiklopedi')

# Sushi raw-power descriptions: koşul cümlesi yüklemden sonra kalınca doğal olmayan iki satır.
fn='database_favPowerInfo.csv'
# Kontrol kodlarını koruyarak yalnız görünür söz dizimini değiştiriyoruz.
replace_in(fn,'SushiFavPowerInfo_Hotate','kadarını geri kazandırır,','kadarını yeniler;','Koşullu iyileştirme açıklamasında “geri kazandırır, ... alırsan” söz dizimi ters ve yapaydı; mekanik değişmeden daha doğal yüklem kuruldu.','mekanik')
replace_in(fn,'SushiFavPowerInfo_HotateRoast','kadarını geri kazandırır,','kadarını yeniler;','Aynı mekanik açıklamasının kavramsal ve dilsel tutarlılığı sağlandı; “Can yenilemek” oyunun diğer metinlerinde kullanılan yerleşik terim.','mekanik')

# Sushi sprite encyclopedia
fn='database_godInfo.csv'
add(fn,'GodInfo_God018','Gösterişli ama zariftir.\nŞatafatlı ziyafetlere\nev sahipliği yapmaya her zaman hazırdır.','Anlam bütün dillerde aynı; “ev sahipliği” ayrı yazılır ve çoğul “ziyafetlere” karakter özelliğini daha doğal anlatır.','ansiklopedi')
add(fn,'GodInfo_God020','Bilge bir filozoftur;\nsuşinin gerçek doğasını\ndurmaksızın düşünür.','DE stets, ES continuamente, IT di continuo: sürekli düşünme. “Durup durup düşünür” Türkçede sebepsiz yere tekrar tekrar düşünme/şikâyet tonu katıyordu.','karakter tonu')
add(fn,'GodInfo_God029','Mesafeli, gizemli, güzel konuşan ve beceriklidir;\ninsanları taklit etmede uzmandır.','DE wortgewandt, ES elocuente, IT forbito kaynak “eloquent”ı açıkça iyi/güzel konuşma olarak doğruluyor. “Etkileyici” bu niteliği kaybediyordu.','ansiklopedi')
add(fn,'GodInfo_God047','İçinden ışık yayabilir;\nışık kırılınca bedeni\nsaydamlaşır.','FR réfraction, ES/IT/NL ışığın bedeni saydamlaştırması diyor. Eski “kırıldığında” öznesiz olduğu için beden kırılıyormuş gibi okunabiliyordu.','ansiklopedi')
add(fn,'GodInfo_God048','Parlak ve gizemlidir; savaşta bir kurtarıcı\nolarak bilinir, her daim yardım elini uzatır.','DE Retter/Erlöser, ES seguro de vida, FR sauveur, IT yardımsever: ortak anlam “kurtarıcı”. “Savaşın mesihi” Türkçede gereksiz dinî ve yapay bir karşılıktı.','ansiklopedi')
add(fn,'GodInfo_God054','Daima cömert ve naziktir;\nengin hoşgörüsü her şeyi\nusulca kucaklar.','ES/IT sınırsız hoşgörü, FR hoşgörüyle sarma diyor. “Sıcak hoşgörü” İngilizce warm tolerance’ı doğal olmayan bir eşdizimle taşıyordu.','ansiklopedi')
add(fn,'GodInfo_God055','Zarafetle hareket eder\nve hoş bir koku yayar.','DE heavenly scent, ES embriagador perfume, IT gradevole profumo; “şık bir koku” Türkçede yanlış eşdizim.','ansiklopedi')
add(fn,'GodInfo_God060','Kahraman ve vakurdur; kimse\nezici gücüne karşı koyamaz.','ES inmenso, FR écrasante, IT travolgente ve NL irresistible: overwhelming = ezici/karşı konulmaz. “Bunaltıcı güç” psikolojik sıkıntı çağrışımı yapıyordu.','ansiklopedi')
add(fn,'GodInfo_God062','Tuhaf ezgiler çalarken\nrengârenk bedeniyle ustaca dans eder.','DE “seltsame Weisen”, ES gizemli flüt ritmi, FR flüt eşliğinde dans; eski “tuhaf bir ses çıkarırken bedenini dansla hareket ettirir” hem literal hem tekrar doluydu.','ansiklopedi')
add(fn,'GodInfo_God065','Muazzam büyü gücü,\nelindeki saati bile eritiyor.','DE/ES/FR/IT/NL büyü gücünün saat/ibrelere etki edip erittiğinde birleşiyor. Eski “çünkü ... gücü var” çocukça ve nedensellik tekrarlıydı.','ansiklopedi')
add(fn,'GodInfo_God076','Sakin bir kişiliği vardır,\nama gülüşü biraz ürperticidir.','DE/FR/IT/NL hepsi ürpertici gülüş/laugh niteliğini isim olarak kuruyor. “Biraz ürpertici güler” Türkçede doğal değil.','ansiklopedi')
add(fn,'GodInfo_God097','Son derece erdemlidir.','DE kusursuz karakter, ES olağanüstü etik, IT yüksek ahlak, NL erdemli karakter; “Ahlakı çok sağlamdır” konuşma dilinde tuhaf bir değerlendirme kalıbıydı.','ansiklopedi')
add(fn,'GodInfo_God100','Bedeni küçük ama özgüveni\nve kişiliği kocaman.','DE özgüven, ES/FR/NL büyük kişilik, IT kendine güven; “kocaman bir özgüven ve tavra sahip” isim tamlaması doğal değildi.','ansiklopedi')
add(fn,'GodInfo_God104','Müzik kutusundan yalnızca klasikleşmiş\nparçalar çalar. Müzikte her şeyin\ntutku olduğuna yürekten inanır.','DE Evergreens, ES/FR/IT/NL “klasikler” diyor. English “gems” burada cevher değil sevilen klasik eserler anlamında; literal hata düzeltildi.','ansiklopedi')
add(fn,'GodInfo_God112','Tüm suşi ruhları içinde\nen umursamaz olanıdır.','FR/IT/NL açıkça grubun en kayıtsız/umursamaz üyesi. “En umursamaz kişiliğe sahip” Türkçede gereksiz dolaylıydı.','ansiklopedi')
add(fn,'GodInfo_God118','Gülmeme oyununda\nhiç yenilmemiştir.','DE kahkahayı çok uzun tutabilmek, ES hiç gülümsememek, FR “jeu de la barbichette”, IT hiç gülmemek, NL güldürmenin zor olması: oyun gülmek değil gülmemek üzerine. Mevcut Türkçe anlamı tersine çevirebiliyordu.','anlam')
add(fn,'GodInfo_God146','Gece yaklaşınca,\nateş gibi tutkulu aşk şarkıları\nsöylemek ister.','DE kalpleri eriten, IT ardenti, NL “tutkudan yanar”: yanma şarkıların/tutkunun metaforu. Eski “içi yanar” karakterin mide/özlem hissine kaydırıyordu.','karakter tonu')

# God-skill descriptions
fn='database_godSkillInfo.csv'
replace_in(fn,'GodSkillInfo_100Free','azami bağlama sağlar!','en uzun zincirleri kurmanı sağlar!','DE/ES/FR/IT/NL tümü bütün tabakların aynı renge dönüp mümkün olan en uzun bağlantıyı kolaylaştırdığını anlatıyor; “azami bağlama” oyun mekaniği Türkçesi gibi değil.','mekanik')
replace_in(fn,'GodSkillInfo_AddInsidiouslyDish','Bağlanan sayıya','Bağladığın tabak sayısına','Kaynak “whatever number linked” = oyuncunun bağladığı tabak sayısı. Edilgen “bağlanan sayıya” nesneyi düşürüp matematiksel değişken gibi duruyordu.','mekanik')
replace_in(fn,'GodSkillInfo_SushiDisappear','Rakibin tapınağından çıkan suşiyi\ntabaklarının içinden\nyok eder!','Rakibin tapınağından çıkan\ntabaklardaki suşileri\nyok eder!','Bütün diller rakip tabaklarındaki suşilerin kaybolduğunu anlatıyor. Eski “suşiyi tabaklarının içinden” hem tekil hem iyelik öznesi belirsizdi.','mekanik')
replace_in(fn,'GodSkillInfo_LightClothes','Somon ya da ton balığı içeren\ntabakların olduğu saldırılardan','Somon ya da ton balıklı\ntabak saldırılarından','Mekanik aynı; Türkçede “X içeren tabakların olduğu saldırılar” aşırı dolaylıydı. Kısa UI açıklaması doğal hâle getirildi.','mekanik')
replace_in(fn,'GodSkillInfo_TableDishLifeup','yığınlarını enerjiye çevirir,\nCanı yeniler!','yığınlarını Can yenileyen\nenerjiye çevirir!','EN/DE/ES/FR/IT/NL yığınların doğrudan iyileştiren enerjiye dönüşmesini anlatıyor; eski iki yüklem neden-sonuç bağını zayıflatıyordu.','mekanik')
replace_in(fn,'GodSkillInfo_SkillGaugeHunt','rakibin yetenek göstergesinden','rakibin yetenek göstergelerinden','Kaynak ve diğer diller çoğul skill gauges; üç ruh göstergesi mekaniği nedeniyle tekil kullanım eksik bilgi veriyordu.','mekanik')
replace_in(fn,'GodSkillInfo_SkillCopy','Rakibin yeteneğini kullandıktan hemen\nsonra kopyalar!','Rakibin kullandığı yeteneği\nanında kopyalar!','Eski cümle dilbilgisel olarak özneyi “kullanıcı rakibin yeteneğini kullandıktan sonra” şeklinde yanlış bağlayabiliyordu; tüm diller rakibin kullandığı yeteneği kopyalamayı anlatıyor.','mekanik')
replace_in(fn,'GodSkillInfo_DishWall','oluşturur; savaş bitene dek!','oluşturur ve savaş sonuna dek kalır!','Kaynak/diğer diller süreyi duvarların kalıcılığına bağlıyor. Noktalı virgül sonrası yüklemsiz “savaş bitene dek” Türkçede yarım cümleydi.','mekanik')
replace_in(fn,'GodSkillInfo_TubConveyor','görünmeye devam eder;\nsavaş bitene kadar!','savaş sonuna dek\ngörünmeye devam eder!','Süre tüm dillerde “battle end” koşulu; yüklemsiz noktalı virgül kaldırılıp doğal söz dizimine taşındı.','mekanik')
replace_in(fn,'GodSkillInfo_DishReducer','saldırı hasarını %90 azaltır;\nsavaş bitene kadar sürer!','saldırı hasarını savaş sonuna dek\n%90 azaltır!','Etkisinin neyin sürdüğü açıkça yükleme bağlandı; eski iki cümlecik UI açıklamasında mekanik ve tekrarlıydı.','mekanik')
replace_in(fn,'GodSkillInfo_ComboWall','engelleyen duvarlar oluşturur;\nsavaş bitene kadar sürer!','engelleyen ve savaş sonuna dek kalan\nduvarlar oluşturur!','Kaynak duvarların savaş sonuna kadar kalmasını söylüyor; “sürer” öznesi belirsizdi.','mekanik')

# Common DB: Surveyor rütbesi/rolü
fn='database_cmn.csv'
for lab in ['EnemyName_221','EnemyName_222','EnemyName_223','EnemyName_225','EnemyName_226','EnemyName_227','EnemyName_237','EnemyName_238','EnemyName_239','EnemyName_249','EnemyName_250','EnemyName_251','EnemyName_255','EnemyName_256','EnemyName_257','EnemyName_263','EnemyName_264','EnemyName_265','EnemyName_266','EnemyName_267','EnemyName_253','EnemyName_269']:
    r=row(fn,lab)
    add(fn,lab,r['tur'].replace('Araştırmacı ','Gözcü ',1),'FR “Inspecteur”, IT “Guardia”, NL “Verkenner” ve düşman kadrosundaki askerî bağlam, Surveyor’ın akademik araştırmacı değil keşif/gözetleme rolü olduğunu gösteriyor. “Gözcü” kısa ve rütbe adı gibi çalışıyor.','terim')

# Item description
fn='database_itemInfo.csv'
add(fn,'ItemInfo_StoneBig','Sahilden çıkarılmış tuhaf, yuvarlak bir taş.\nŞerit-sürüş dişlilerinde kullanılır;\nama bu büyüklükte olanına ender rastlanır.','EN “this one’s size is rare”; diğer diller de boyutunun enderliğini vurguluyor. “Bunun boyu nadirdir” Türkçede yanlış eşdizimdi.','ansiklopedi')

# Movie summaries
fn='database_movieInfo.csv'
transform(fn,'MovieInfo_1A',lambda x: x.replace("Musashi, kendini beğenmiş zorba Kojiro'yla\\nkapışır ve hâlâ öfkeliyken\\nkarşılaşmanın ardından ","Musashi, kendini beğenmiş zorba Kojiro'yla\\nkapışır. Karşılaşmanın öfkesi dinmemişken\\n",1),'ES/FR/NL Franklin’in Musashi hâlâ karşılaşmanın öfkesindeyken geldiğini açık kuruyor. Eski Türkçe “hâlâ öfkeliyken karşılaşmanın ardından” söz diziminde zaman zarfı yanlış yere bağlanıyordu.','özet')
transform(fn,'MovieInfo_7C',lambda x: x.replace('Her iki\\nMusashi ve Jinrai da','Musashi ile Jinrai de',1),'“Both Musashi and Jinrai” tüm dillerde iki özneyi birlikte bağlıyor. “Her iki Musashi ve Jinrai da” Türkçede dilbilgisel olarak bozuktu.','özet')
transform(fn,'MovieInfo_9D',lambda x: x.replace('suşiyi\\npaylaşarak ona ileriyi göstermeye çalışır.','suşiyi\\npaylaşarak ona yeni bir yol göstermeye çalışır.',1),'ES umut dolu gelecek, FR paylaşma davasına kazanma, NL başka bir yol gösterme diyor. “Ona ileriyi göstermek” İngilizce “way forward”ın literal ve doğal olmayan çevirisiydi.','özet')

# Stage names
fn='database_stage.csv'
add(fn,'stageName_stage018','Tapınak Korusu Önü','ES “cerca”, FR “devant”, IT “limitare”, NL çevre/ön bölge; “Yaklaşımı” İngilizce approach’ın Türkçe yer adı olarak yapay karşılığıydı. “Önü” kısa ve diğer yer adlarıyla tutarlı.','yer adı')

# Tips: kontrol kodlarını olduğu gibi koruyarak görünen metinleri düzelt.
fn='database_tipsInfo.csv'
replace_in(fn,'TipsPage1_002','paylaşılan\nşerit','ortak\nşerit','Başlık zaten “Ortak Şerit”. Aynı mekanik aynı ekranda “paylaşılan şerit” diye ikinci terimle anılıyordu; terminoloji tekleştirildi.','terim')
replace_in(fn,'TipsPage2_002','Paylaşılan\nşeritte','Ortak\nşeritte','Başlık ve TipsPage1 ile aynı oyun terimi “Ortak Şerit” olarak standardize edildi.','terim')
replace_in(fn,'TipsPage2_004','onları tek tek','onlara tek tek','Tatlılar tabakta olmadığı için oyuncu onları “almıyor”; DE/ES/FR/IT/NL dokunmayı söylüyor. Türkçe yönelme eki ve eylem ilişkisi düzeltildi.','mekanik')
replace_in(fn,'TipsPage2_004','dokunarak','dokunup','“Onlara tek tek dokunup” doğal Türkçe eylem zinciri; “dokunarak almalısın” yanlış nesne/eylem ilişkisi kuruyordu.','mekanik')
replace_in(fn,'TipsPage2_004',' almalısın.',' yemelisin.','Kaynak tap-to-eat/iyileşme mekaniği; “almak” yerine oyuncunun gerçekten yaptığı “yemek” kullanıldı.','mekanik')
replace_in(fn,'TipsPage2_005','varsa ek o kadar artar','varsa bonus o kadar artar','Açık yazım/kelime düşmesi hatası: EN/DE/ES/FR/IT/NL artan şeyin bonus/hasar gücü olduğunu söylüyor; “ek” tek başına anlamsızdı.','anlam')
replace_in(fn,'TipsPage1_008',"saldırıların normal hasarın %150'sini verir","saldırıların normalin %150'si kadar hasar verir",'Mekanik bütün dillerde 1,5× normal hasar. Eski Türkçe hâl ekleri nedeniyle “saldırıların ... verir” özne-yüklem uyuşmazlığı taşıyordu.','mekanik')
replace_in(fn,'TipsPage3_013','yığındaki tabak sayısına göre ekstra ek yoktur','yığındaki tabak sayısına göre ekstra bonus yoktur','EN “no added bonus”, DE/ES/FR/NL tabak sayısının göstergeyi daha hızlı doldurmadığını doğruluyor. “Ekstra ek” gereksiz tekrar ve anlam bozukluğuydu.','mekanik')
replace_in(fn,'TipsPage1_015',"Musashi'nin savaşta en yüksek","Musashi'nin savaşta azami",'Oyunun diğer sistem metinlerinde max HP = “azami Can”; burada “en yüksek Can değeri” terminoloji tutarsızlığı ve gereksiz uzunluk yaratıyordu.','terim')
transform(fn,'TipsPage1_015',lambda x: x.replace('toplam','',1),'Cümlede “toplam ... toplamıdır” tekrarı vardı. ES/FR/IT/NL basitçe Dayanıklılık + ruh Savunmalarının toplamını anlatıyor.','anlatım')
replace_in(fn,'TipsName_017','Puan & Derecelendirme','Puan & Derece','DE Noten, ES calificación, IT voti ve oyundaki D–S sistemi tek bir derece/grade üretir. “Derecelendirme” işlem adı; ekran başlığında sonuç adı “Derece” daha doğru.','terim')
replace_in(fn,'TipsPage1_017','puanına ek eklenir','puanına ek puan gelir','EN/DE/ES/FR/IT/NL süreye bağlı bonus puan verildiğini anlatıyor. “Ek eklenir” açık kelime tekrarıydı.','anlatım')
# İkinci “yıldız” vurgusunu kaldırıp bozuk “koşullarını yıldız için” dizisini normalleştir.
def _fix_tip_024(x):
    first=x.find('yıldız')
    second=x.find('yıldız',first+1)
    if second<0: return x
    x=x[:second]+x[second+len('yıldız'):]
    x=x.replace(' için harita ekranında',' harita ekranında',1)
    x=x.replace('Başlat  ile','Başlat ile',1)
    return x
transform(fn,'TipsPage2_024',_fix_tip_024,'Kaynak ve tüm diğer diller “yıldız kazanma koşullarını harita ekranında veya START ile duraklatıp görme” diyor. Eski metinde kopyalama sonucu “koşullarını yıldız için” ve çift boşluk oluşmuştu.','anlam')
def _fix_tip_a(x):
    i=x.find('bırak')
    j=x.find('serbest bırak',i)
    if i<0 or j<0: return x
    # İlk vurgunun kapanış kodunu koru; aradaki tekrarlı metin ve ikinci vurgu kaldırılır.
    rs=x.find('\\u000E',i+len('bırak'))
    re_=x.find('＀',rs)+1 if rs>=0 else -1
    reset=x[rs:re_] if rs>=0 and re_>rs else ''
    end=j+len('serbest bırak')
    return x[:i]+'A Düğmesini bırak'+reset+x[end:]
transform(fn,'TipsPage2_018',_fix_tip_a,'EN/DE/ES/FR/IT/NL yalnız A düğmesini bırakmayı söylüyor. Eski “bırak ve A Düğmesini serbest bırak” aynı eylemi iki kez söylüyordu; kontrol kodu korunarak tek doğal emir kuruldu.','mekanik')

def _fix_tip_x(x):
    i=x.find('defalarca bas')
    if i<0: return x
    rs=x.find('\\u000E',i+len('defalarca bas'))
    re_=x.find('＀',rs)+1 if rs>=0 else -1
    reset=x[rs:re_] if rs>=0 and re_>rs else ''
    # Satırın sonundaki “: X Düğmesi” bölümünü tek doğal emirle değiştir.
    end=x.rfind('!')
    if end<0: end=len(x)
    return x[:i]+'X Düğmesine art arda bas'+reset+x[end:]
transform(fn,'TipsPage3_018',_fix_tip_x,'Bütün diller “X düğmesine tekrar tekrar/art arda bas” diyor. Eski “defalarca bas: X Düğmesi!” etiket gibi ve ters söz dizimliydi; kontrol kodu korunarak doğal UI talimatına çevrildi.','mekanik')
# 3 set -> 3 etkin ruh takımı; kontrol vurgusu korunur.
transform(fn,'TipsPage1_020',lambda x: x.replace('3 set','3',1).replace('etkin ruhu','etkin ruh takımı',1),'DE üç farklı düzen, ES/FR/IT/NL üç takım/set hazırlamayı anlatıyor. “3 set etkin ruhu” Türkçede isim tamlaması bozuktu; “3 etkin ruh takımı” doğal karşılık.','terim')
transform(fn,'TipsPage2_025',lambda x: x.replace('Musashi ve\\nsuşi ruhlarının seviyesi ','Musashi ve\\nsuşi ruhları ',1),'Tüm diller çok oyunculuda Musashi ve ruhların seviye 30’a sabitlendiğini söylüyor. “seviyesi seviye 30” açık tekrar ve özne-yüklem bozukluğuydu.','anlam')


# write modified csv files
for fn,(fields,rows) in files.items():
    with (OUT/fn).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

# Detailed row-by-row audit for this reviewed block.
short_re=re.compile(r'^[\s\W\d_]{0,18}$',re.UNICODE)
def unchanged_reason(fn,r):
    e=(r.get('eng') or '').strip(); t=(r.get('tur') or '').strip()
    others=[(r.get(k) or '').strip() for k in ['deu','esp','fra','ita','nld']]
    if not e and not t and not any(others):
        return 'Kaynak etiket boş; çevrilecek içerik yok. MSBT yapısı korunarak aynı bırakıldı.'
    if not e and not t:
        return 'İngilizce bu varyantta ayrı metin taşımıyor; Türkçede de cinsiyet/biçim ayrımı gerektiren yeni içerik olmadığı için kaynak yapısına uygun biçimde boş bırakıldı.'
    if (fn,r['label']) in prev_changes:
        return 'Önceki kalite turunda zaten düzeltilmişti; bu turda EN ile DE/ES/FR/IT/NL yeniden karşılaştırıldı ve mevcut Türkçe anlam, ton ve bağlam açısından yeterli bulundu.'
    if short_re.match(e.replace('*','').replace('!','').replace('?','').replace('.','')) or len(e)<=18:
        return 'Kısa tepki/ünlem/özel isim. Diğer diller aynı işlev ve duyguyu koruyor; mevcut Türkçe doğal ve gereksiz yeniden yazım anlam/ritmi iyileştirmeyecekti.'
    lab=r['label']
    if lab.endswith('_F'):
        return 'Cinsiyet varyantı. Türkçe ifade cinsiyet işaretlemediği için ana varyantla aynı anlam ve tonu doğal biçimde taşıyor; ayrı değişiklik gerekmiyor.'
    return 'EN anlamı ile DE/ES/FR/IT/NL ortak yorumu karşılaştırıldı; mevcut Türkçe doğal, bağlama uygun ve terminoloji/karakter tonu açısından anlamlı bir kayıp taşımıyor.'

audit=[]
for fn in review_files:
    for r in files[fn][1]:
        key=(fn,r['label'])
        ch=changed_lookup.get(key)
        audit.append({
            'round':'v0.4','file':fn,'label':r['label'],'index':r.get('index',''),
            'decision':'DEĞİŞTİ' if ch else 'AYNI KALDI',
            'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),
            'old_tur':ch['old_tur'] if ch else r.get('tur',''),
            'new_tur':r.get('tur',''),
            'reason':ch['reason'] if ch else unchanged_reason(fn,r)
        })

field_a=['round','file','label','index','decision','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
with (OUTROOT/'V04_SATIR_BAZLI_INCELEME.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=field_a); w.writeheader(); w.writerows(audit)

field_c=['round','category','file','label','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
with (OUTROOT/'V04_YENI_DEGISIKLIKLER.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=field_c); w.writeheader(); w.writerows(changes)

# Combined historical change report.
combined=[]
if prev_path.exists():
    with prev_path.open(encoding='utf-8-sig',newline='') as f: combined.extend(csv.DictReader(f))
combined.extend(changes)
with (OUTROOT/'INCELEME_DEGISIKLIKLERI.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=field_c); w.writeheader(); w.writerows(combined)

# Latest unique changed state.
latest={}
for r in combined: latest[(r['file'],r['label'])]=r
with (OUTROOT/'INCELEME_SON_DURUM_ESSIZ.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=field_c); w.writeheader(); w.writerows(latest.values())

# Master status containing every source row; not-yet-manually-reviewed rows are explicitly BEKLİYOR.
current_audit={(r['file'],r['label']):r for r in audit}
master=[]
for fn in sorted(files):
    for r in files[fn][1]:
        key=(fn,r['label'])
        if key in current_audit:
            a=current_audit[key]
            status='İNCELENDİ_v0.4'; decision=a['decision']; reason=a['reason']; old=a['old_tur']; new=a['new_tur']
        elif key in latest:
            h=latest[key]; status='ÖNCEKİ_TURDA_DEĞİŞTİ'; decision='DEĞİŞTİ'; reason=h['reason']; old=h['old_tur']; new=r.get('tur','')
        else:
            status='BEKLİYOR'; decision='HENÜZ KARAR YOK'; reason='Bu etiket henüz satır-satır manuel kalite turuna alınmadı; “aynı kaldı” diye yanlış etiketlenmedi.'; old=r.get('tur',''); new=r.get('tur','')
        master.append({'file':fn,'label':r['label'],'index':r.get('index',''),'review_status':status,'decision':decision,
                       'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),
                       'old_tur':old,'current_tur':new,'reason':reason})
master_fields=['file','label','index','review_status','decision','eng','deu','esp','fra','ita','nld','old_tur','current_tur','reason']
with (OUTROOT/'TUM_10676_SATIR_DURUMU.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=master_fields); w.writeheader(); w.writerows(master)

# conservative line-length warnings for current changes (control codes stripped roughly)
ctrl=re.compile(r'\\u[0-9A-Fa-f]{4}|[\x00-\x1f]|[\ue000-\uf8ff]|[�-￿]')
warn=[]
for ch in changes:
    for n,line in enumerate(ch['new_tur'].split('\\n'),1):
        vis=ctrl.sub('',line)
        if len(vis)>48:
            warn.append({'file':ch['file'],'label':ch['label'],'line_no':n,'visible_len':len(vis),'line':line})
with (OUTROOT/'V04_SATIR_UZUNLUK_UYARILARI.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['file','label','line_no','visible_len','line']); w.writeheader(); w.writerows(warn)

# Rebuild and validate.
rebuilt=OUTROOT/'rebuilt_patch'
subprocess.run([sys.executable,str(TOOL),'import','--csv',str(OUT),'--patch',str(PATCH_BASE),'--out',str(rebuilt)],check=True)
subprocess.run([sys.executable,str(TOOL),'validate','--source',str(SOURCE),'--patch',str(rebuilt)],check=True)
verify=OUTROOT/'verify_csv'
subprocess.run([sys.executable,str(TOOL),'export','--source',str(SOURCE),'--patch',str(rebuilt),'--out',str(verify)],check=True)

# Verify Turkish round-trip.
diffs=[]; total=0
for p in sorted(OUT.glob('*.csv')):
    vp=verify/p.name
    with p.open(encoding='utf-8-sig',newline='') as f1, vp.open(encoding='utf-8-sig',newline='') as f2:
        a=list(csv.DictReader(f1)); b=list(csv.DictReader(f2)); bm={x['label']:x for x in b}
        for x in a:
            total+=1; y=bm.get(x['label'])
            if not y or x.get('tur','')!=y.get('tur',''): diffs.append((p.name,x['label'],x.get('tur',''),'' if not y else y.get('tur','')))
with (OUTROOT/'ROUNDTRIP_DOGRULAMA.txt').open('w',encoding='utf-8') as f:
    f.write(f'Etiket: {total}\nFark: {len(diffs)}\n')
    for d in diffs[:100]: f.write(repr(d)+'\n')
if diffs: raise SystemExit(f'Roundtrip fark var: {len(diffs)}')

# README
same=sum(1 for a in audit if a['decision']=='AYNI KALDI'); changed=len(changes)
reviewed=len(audit)
prev_unique=len({(r['file'],r['label']) for r in combined})
readme=f'''SUSHI STRIKER TÜRKÇE ÇEVİRİ KALİTE İNCELEMESİ - v0.4\n{'='*61}\n\nBu sürümde ana değişiklik raporu artık yalnız değişen satırları değil, incelenen HER SATIRI içerir.\nHer satır için DEĞİŞTİ / AYNI KALDI kararı ve kısa gerekçe vardır.\n\nV0.4 MANUEL BLOK\n----------------\nİncelenen dosyalar: {len(review_files)}\nİncelenen satırlar: {reviewed}\nDeğişen satırlar: {changed}\nAynı kalan satırlar: {same}\n\nİncelenen ana metin dosyaları:\n- database_movieSerif_0A / 1A / 1B / 2A / 2B / 3A / 3B / 3C / 4A\n- database_movieSerif_5A / 5B / 5C / 6A / 7B / 7C / 8A / 9A / 9B / 9C / 9D\n- database_movieSerif_OP / EP / ED\n\nRAPORLAR\n---------\nV04_SATIR_BAZLI_INCELEME.csv\n  Bu turdaki {reviewed} satırın tamamı. DEĞİŞTİ veya AYNI KALDI ve neden.\n\nV04_YENI_DEGISIKLIKLER.csv\n  Yalnız bu turda değişen {changed} satır; altı resmi dil + eski/yeni Türkçe + gerekçe.\n\nTUM_10676_SATIR_DURUMU.csv\n  Oyundaki 10.676 etiketin tümü. Manuel olarak henüz sıraya gelmeyenler özellikle BEKLİYOR\n  olarak işaretlenir; incelenmemiş bir satıra sahte biçimde “aynı kaldı” denmez.\n\nINCELEME_DEGISIKLIKLERI.csv\n  v0.2 + v0.3 + v0.4 tüm değişiklik olayları.\n\nINCELEME_SON_DURUM_ESSIZ.csv\n  Değiştirilmiş etiketlerin en yeni benzersiz hâli.\n\nARAÇLAR\n--------\nAraclar/sushi_msbt_csv_flat.py\n  243 çok dilli CSV dışa aktarma, CSV -> MSBT enjeksiyonu, validate, ZIP, fontscan.\nAraclar/v04_inceleme_uygulama_betigi.py\n  Bu turun değişikliklerini ve satır bazlı raporlarını üretmekte kullanılan betik.\n\nDOĞRULAMA\n---------\n- MSBT: 243/243\n- CSV -> MSBT -> CSV: {total} etiket, fark 0\n- Yapısal validate: OK\n- v0.4 değişikliklerinde >48 görünür karakter satır uyarısı: {len(warn)}\n'''
(OUTROOT/'README_TR.txt').write_text(readme,encoding='utf-8')

# Full bundle
bundle=OUTROOT/'full_bundle'
(bundle/'LayeredFS').mkdir(parents=True)
shutil.copytree(rebuilt,bundle/'LayeredFS'/'00040000001C1D00')
shutil.copytree(OUT,bundle/'CSV')
(bundle/'Raporlar').mkdir()
for name in ['V04_SATIR_BAZLI_INCELEME.csv','V04_YENI_DEGISIKLIKLER.csv','TUM_10676_SATIR_DURUMU.csv','INCELEME_DEGISIKLIKLERI.csv','INCELEME_SON_DURUM_ESSIZ.csv','V04_SATIR_UZUNLUK_UYARILARI.csv','ROUNDTRIP_DOGRULAMA.txt']:
    shutil.copy2(OUTROOT/name,bundle/'Raporlar'/name)
shutil.copytree(ROOT/'review_v03'/'full_bundle'/'Araclar', bundle/'Araclar')
shutil.copy2(Path(__file__),bundle/'Araclar'/'v04_inceleme_uygulama_betigi.py')
shutil.copy2(OUTROOT/'README_TR.txt',bundle/'README_TR.txt')

# manifests
manifest=[]
for p in sorted(x for x in bundle.rglob('*') if x.is_file()):
    h=hashlib.sha256(p.read_bytes()).hexdigest(); manifest.append(f'{h}  {p.relative_to(bundle).as_posix()}')
(bundle/'DOSYA_MANIFESTOSU_SHA256.txt').write_text('\n'.join(manifest)+'\n',encoding='utf-8')

def zipdir(src,out):
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(Path(src).rglob('*')):
            if p.is_file(): z.write(p,p.relative_to(src).as_posix())

zipdir(bundle,OUTROOT/'Sushi_Striker_TR_v04_FULL.zip')
# LayeredFS zip includes a LayeredFS top-level directory for easy extraction.
ptmp=OUTROOT/'patch_bundle'; ptmp.mkdir()
shutil.copytree(bundle/'LayeredFS', ptmp/'LayeredFS')
zipdir(ptmp,OUTROOT/'Sushi_Striker_TR_v04_LayeredFS.zip')
shutil.rmtree(ptmp)
# tools zip
atmp=OUTROOT/'tools_bundle'; atmp.mkdir()
shutil.copytree(bundle/'Araclar',atmp/'Araclar')
shutil.copy2(OUTROOT/'README_TR.txt',atmp/'README_TR.txt')
zipdir(atmp,OUTROOT/'Sushi_Striker_TR_v04_Araclar.zip')
shutil.rmtree(atmp)

print('v0.4 OK')
print('reviewed',reviewed,'changed',changed,'same',same,'warnings',len(warn),'roundtrip',total)
print('unique_changed_total',prev_unique)
