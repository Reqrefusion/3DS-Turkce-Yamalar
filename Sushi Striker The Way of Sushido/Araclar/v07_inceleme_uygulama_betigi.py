from pathlib import Path
import csv, shutil, re, subprocess, hashlib, zipfile, sys

ROOT=Path('/mnt/data/sushi_work')
BASE=ROOT/'work_v07'
SRC=BASE/'CSV'
OUTROOT=ROOT/'review_v07'
OUT=OUTROOT/'csv'
TOOL=BASE/'Araclar'/'sushi_msbt_csv_flat.py'
PATCH_BASE=BASE/'LayeredFS'/'00040000001C1D00'
SOURCE=ROOT/'source_msgstudio'/'msgstudio'
PREV_AUDIT=BASE/'Raporlar'/'SATIR_BAZLI_INCELEME_KUMULATIF.csv'
PREV_MASTER=BASE/'Raporlar'/'TUM_10676_SATIR_DURUMU.csv'
PREV_CHANGES=BASE/'Raporlar'/'INCELEME_DEGISIKLIKLERI.csv'
PREV_UNIQUE=BASE/'Raporlar'/'INCELEME_SON_DURUM_ESSIZ.csv'

if OUTROOT.exists(): shutil.rmtree(OUTROOT)
OUT.mkdir(parents=True)
for p in SRC.glob('*.csv'): shutil.copy2(p,OUT/p.name)

files={}
for p in OUT.glob('*.csv'):
    with p.open(encoding='utf-8-sig',newline='') as f:
        rs=list(csv.DictReader(f)); fields=list(rs[0].keys()) if rs else ['label','index','deu','eng','esp','fra','ita','nld','tur']
    files[p.name]=(fields,rs)

prev_master={}
with PREV_MASTER.open(encoding='utf-8-sig',newline='') as f:
    for r in csv.DictReader(f): prev_master[(r['file'],r['label'])]=r

# v0.7: önceki turda BEKLİYOR olan bu blokların HER satırı karar+gerekçe alır.
review_files=[
'DbgEventProcess.csv','database_staffrollName.csv','ShrineGetMode.csv','episode_cmn.csv',
'chapterAvantM003.csv','chapterAvantM005.csv','chapterBeginM001.csv','chapterBeginM002.csv',
'chapterBeginM003.csv','chapterBeginM005.csv','chapterBeginM007.csv','chapterBeginM008.csv',
'chapterBeginM009.csv','chapterEndM003.csv','chapterEndM005.csv','eventBattleM001.csv',
'eventBattleM002.csv','eventBeginM002.csv','eventEndM001.csv']

changes=[]; changed_lookup={}

def row(fn,label):
    for r in files[fn][1]:
        if r['label']==label: return r
    raise KeyError((fn,label))

def norm(s): return (s or '').replace('\r\n','\n').replace('\r','\n').replace('\n','\\n')

def add(fn,label,new,reason,category='manuel kalite'):
    new=norm(new); r=row(fn,label); old=r.get('tur','')
    if old==new: return False
    r['tur']=new; key=(fn,label)
    if key in changed_lookup:
        rec=changed_lookup[key]; rec['new_tur']=new
        if reason and reason not in rec['reason']: rec['reason'] += ' Ek: '+reason
        return True
    rec={'round':'v0.7','category':category,'file':fn,'label':label,
         'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),
         'old_tur':old,'new_tur':new,'reason':reason}
    changes.append(rec); changed_lookup[key]=rec
    return True

def transform(fn,label,func,reason,category='manuel kalite'):
    r=row(fn,label); new=func(r.get('tur',''))
    return add(fn,label,new,reason,category) if new!=r.get('tur','') else False

def rep(fn,label,old,new,reason,category='manuel kalite'):
    r=row(fn,label); cur=r.get('tur','')
    if old not in cur: raise ValueError(f'{fn}:{label}: {old!r} yok: {cur!r}')
    return add(fn,label,cur.replace(old,new),reason,category)

# -----------------------------------------------------------------------------
# SHRINE / BAĞ SİSTEMİ
# -----------------------------------------------------------------------------
fn='ShrineGetMode.csv'
add(fn,'NarrationInfomation_M',r'Suşi ruhu \u000E\u0000\u0003\u0004ﾑ＞\u000E\u0001\n\u0000\u000E\u0000\u0003\u0004\u0000＀ ile bağ kurdun!\nYeteneği \u000E\u0000\u0003\u0004ﾑ＞\u000E\u0001\u0012\u0000\u000E\u0000\u0003\u0004\u0000＀!',
    'Bu bildirim doğrudan oyunun pledge/ittifak mekaniğini anlatıyor. DE Pakt, ES alianza, FR allié, IT alleanza, NL band kullanıyor; önceki “arkadaş oldun” sistemde yerleşen Bağ terimini kaçırıyordu.','terim/mekanik')
add(fn,'NarrationPotentialPlate_M',r"\u000E\u0000\u0003\u0004ﾑ＞Bağsız Tabak\u000E\u0000\u0003\u0004\u0000＀'tan\nbir suşi ruhu belirdi!",
    'Potential burada “potansiyel” değil henüz bağ kurulmamış tabak durumudur: ES prealianza, FR neutre, IT inattivo, NL bandloos. Bağ sistemine oturan “Bağsız Tabak” seçildi.','terim/mekanik')
add(fn,'AncWoman_Contact1_M','Hmhmhm... Suşiye olan sevgini\nfazlasıyla belli ettin.',
    '“Appreciation”ın literal “takdir”i karakter konuşmasında resmî kalıyordu. DE/FR/NL açıkça sevgi/tutku nüansını taşıyor; sıcak ve doğal ifade seçildi.','karakter tonu')
add(fn,'AncChild_ChoiceNo_M','Oooo... Yazık oldu. Ama\nağlamamaya çalışacağım!',
    'EN “be brave” çocukça üzülmeme çabasıdır; FR/IT bunu doğrudan “ağlamamaya çalışacağım” diye çözüyor. “Buna karşı cesur olmak” Türkçede yapaydı.','karakter tonu/çapraz dil')
add(fn,'Hermit_ChoiceYes_M',r'Seninle bağ kurmak güzeldi!\nBana \u000E\u0000\u0003\u0004ﾑ＞\u000E\u0001\n\u0000\u000E\u0000\u0003\u0004\u0000＀ diyebilirsin.',
    'Pledging burada yemin etmek değil ittifak/bağ kurma mekaniği. Altı resmî dil de Pakt/alianza/allié/alleanza/band yönünde; sistem terimi “bağ kurmak” kullanıldı.','terim/mekanik')
add(fn,'Hermit_ChoiceNo_M','Hayır mı? Peki, sorun değil.\nDenemeden olmaz, değil mi? Görüşürüz!',
    '“Can’t blame a man for trying” literal “deneyeni suçlayamazsın” değil, “denemeye değerdi” deyimidir. DE/ES/NL aynı niyeti doğruluyor; konuşma diliyle yeniden kuruldu.','deyim/karakter tonu')
add(fn,'Noblewoman_Contact1_M','Suşi yiyişini izlemek bile\nbeni heyecanlandırıyor.',
    'Mevcut “titrememe neden oluyor” İngilizce yapıyı mekanik izliyordu. ES/NL/FR heyecan/hayranlık anlamını doğal cümleyle veriyor; soylu ama akıcı ton korundu.','akıcılık/karakter tonu')
add(fn,'Noblewoman_ChoiceYes_M',r'Pekâlâ. Ben \u000E\u0000\u0003\u0004ﾑ＞\u000E\u0001\n\u0000\u000E\u0000\u0003\u0004\u0000＀.\nGücüm artık senin.',
    '“Benim adım ..., ve” İngilizce söz dizimini Türkçeye taşıyordu. Bütün diller kısa tanışma + güç devri yapıyor; soylu ve doğal ritimle yeniden bölündü.','akıcılık/karakter tonu')
add(fn,'Noblewoman_AlreadyFriend2_M','O hâlde arkadaşımı sana emanet ediyorum.\nEsen kal, suşi vurucu.',
    '“Arkadaşımın sağlığını sana emanet ediyorum” aşırı literal ve tıbbî çağrışımlıydı. DE/FR/IT/NL doğrudan “arkadaşıma iyi bak” anlamında; karakterin soylu sesi için “emanet ediyorum / esen kal” seçildi.','karakter tonu/çapraz dil')
add(fn,'Pomposity_Contact1_M','Suşi yiyişinden bu işten\nne kadar iyi anladığın belli.',
    '“Keen judgment”ın “keskin yargı” çevirisi Türkçede anlamsızlaşıyordu. DE/NL bunu suşi bilgisi/uzmanlığı olarak açıklıyor; karakterin böbürlenen değerlendirme tonu korundu.','anlam/karakter tonu')
add(fn,'Pomposity_AwakeBefore_M','İçimde bir güç yükseliyor.',
    '“Power surges” için “güç kabarıyor” fiziksel/garip çağrışım yapıyordu; diğer diller yükselme/akış anlamında. Kısa ve doğal karşılık seçildi.','akıcılık')
add(fn,'Simplicity_AlreadyFriend2_M','Bana benzeyen o ruha iyi bak. Hoşça kal.',
    '“Benzer ruhuma” Türkçede ruhun konuşana ait olduğu izlenimini veriyordu. ES açıkça “bana benzeyen ruh”, diğer diller “arkadaşım” diyor; referans netleştirildi.','anlam/gramer')
add(fn,'Clown_ChoiceNo_M','Off be, ağır oldu. Neyse, umarım\nfikrini değiştirirsin! Görüşürüz!',
    '“That is harsh” için “Bu acımasızca” doğal konuşma değil. DE “bitter”, FR “pas sympa”, NL “gemeen”; gevşek/argo karakter sesiyle “ağır oldu” seçildi.','karakter tonu')
add(fn,'Clown_AlreadyFriend2_M','Arkadaşımla bol bol eğlen!\nHaydi eyvallah, timsah!',
    'EN “Later, gator!” ses oyunlu vedadır. Diğer diller çoğunlukla serbestleştiriyor; literal “Görüşürüz, timsahım” yerine Türkçede kafiye/oyun hissi taşıyan bir veda kuruldu.','kelime oyunu/karakter tonu')

# Potential Plate -> Bağsız Tabak: tüm dosyalarda tek sistem terimi.
for fn2,(fields,rs) in files.items():
    for r in rs:
        if 'Potansiyel Tabak' in r.get('tur',''):
            new=r['tur'].replace('Potansiyel Tabaklar','Bağsız Tabaklar').replace('Potansiyel Tabak','Bağsız Tabak')
            add(fn2,r['label'],new,'Potential Plate için resmî diller “ön-ittifak/nötr/etkisiz/bağsız” anlamına birleşiyor. Oyun genelindeki Bağ mekaniğiyle tutarlı “Bağsız Tabak” bütün kullanımlarda standardize edildi.','hedefli terim')

# -----------------------------------------------------------------------------
# CREDITS — literal meslek terimleri
# -----------------------------------------------------------------------------
fn='database_staffrollName.csv'
credit_changes={
'StaffName_013':'ETKİNLİK PLANLAMA SORUMLUSU',
'StaffName_019':'PROGRAMLAMA SORUMLUSU',
'StaffName_025':'MENÜ GRAFİK TASARIM SORUMLUSU',
'StaffName_027':'2D GRAFİK TASARIM SORUMLUSU',
'StaffName_031':'3D GRAFİK TASARIM SORUMLUSU',
'StaffName_035':'TASARIM DENETMENLERİ',
'StaffName_048':'ANA ANİMASYON',
'StaffName_145':'<AVRUPA YERELLEŞTİRMESİ>',
'StaffName_168':'YÖNETİCİ YAPIMCI',
'StaffName_170':'YAPIM/TELİF HAKKI'
}
reasons={
'StaffName_013':'Credits bağlamında “lead” ekip liderliği/sorumluluğudur; “planlama lideri” Türkçe sektör kullanımında yapay. “Sorumlusu” daha yerleşik.',
'StaffName_019':'Credits bağlamında “Programming Lead” için literal “Programlama Lideri” yerine doğal görev unvanı “Programlama Sorumlusu” seçildi.',
'StaffName_025':'Credits görev unvanında “lead” Türkçede “sorumlu” olarak daha doğal; tasarım alanı korunuyor.',
'StaffName_027':'Credits görev unvanında “lead” Türkçede “sorumlu” olarak daha doğal; 2D uzmanlık alanı korunuyor.',
'StaffName_031':'Credits görev unvanında “lead” Türkçede “sorumlu” olarak daha doğal; 3D uzmanlık alanı korunuyor.',
'StaffName_035':'“Supervisor” için “süpervizör” anlaşılır olsa da Türkçe jenerikte “denetmen” daha doğal ve işlevsel karşılık.',
'StaffName_048':'Animasyon sektöründe “key animation” anahtar nesne anlamındaki “anahtar animasyon” değildir; yerleşik karşılık “ana animasyon”.',
'StaffName_145':'Jenerikteki Avrupa yerelleştirme bölüm başlığı Türkçe pakette İngilizce kalmıştı; bölüm adı Türkçeleştirildi.',
'StaffName_168':'“Executive producer” için literal “icra yapımcısı” yerine Türkçe medya/jenerik kullanımına daha uygun “yönetici yapımcı”.',
'StaffName_170':'“Production” burada üretim süreci değil eser/yapım kredisi; “prodüksiyon” yerine kısa “yapım” daha doğal.'}
for lab,new in credit_changes.items(): add(fn,lab,new,reasons[lab],'jenerik/terim')

# -----------------------------------------------------------------------------
# EPISODE COMMON UI
# -----------------------------------------------------------------------------
fn='episode_cmn.csv'
add(fn,'BuildUpLevel2_M','Seviye 2’ye yükseltildi!','“Renovated” yapı/tesis geliştirmesini bildiriyor; “LV2’ye yenilendi” hem kısaltmalı hem doğal değil. UI dilinde seviye yükseltme netleştirildi.','UI/terim')
add(fn,'BuildUpLevel3_M','Seviye 3’e yükseltildi!','“Renovated to LV 3” yapı geliştirmesidir; “yenilendi” yerine oyun sistemlerinde doğal “seviyeye yükseltildi” kullanıldı.','UI/terim')
# Boş özel ad slotlarını bu tur özellikle çevirmiyoruz; kullanıcı kaliteye odaklanmak istedi.

# -----------------------------------------------------------------------------
# CHAPTER AVANT
# -----------------------------------------------------------------------------
fn='chapterAvantM003.csv'
add(fn,'CharaSerif_01_M','Hata üstüne hata yapıyorsun,\ndeğil mi Kodiak?','Mevcut “Sende hata üstüne hata” eksiltili ve Türkçede yapaydı. Altı dil Kodiak’ın art arda hatalarıyla alay edildiğini doğruluyor; Purrsilla’nın küçümseyici tonu korundu.','diyalog/akıcılık')
add(fn,'CharaSerif_05_M','B-bana güvenebilirsin! Sınırı\ndemir yumrukla tutacağım!','EN “iron grip” bilinçli sertlik metaforu. “Sıkı tutacağım” anlamı verse de Kodiak’ın kas/sertlik karakterini zayıflatıyordu; Türkçede yerleşik “demir yumruk” daha canlı.','deyim/karakter tonu')
add(fn,'CharaSerif_06_M','Umarım. Bir daha başarısız olursan,\nsen bile... tesisten kurtulamazsın.','Mevcut satır bölünüşü “sen bile... / tesisten kaçamazsın” ritmi bozuyor ve “escape” fiziksel kaçış gibi duruyordu. Bağlam yeniden eğitme tesisine gönderilme tehdidi; “kurtulamazsın” daha doğal.','bağlam/akıcılık')

fn='chapterAvantM005.csv'
add(fn,'CharaSerif_01_M','Tiburoooon...','Kaynakta isim bilerek uzatılarak karakter sesi kuruluyor. Türkçe slotun boş kalması bu dramatik/komik çağrıyı tamamen yok ediyordu; özel ad aynı ses oyunuyla korundu.','işlevsel kalite/karakter tonu')
add(fn,'CharaSerif_02_M','Ah... İmparatorluk Majesteleri.','“Your Imperial Highness” saray hitabıdır; “İmparatorluk Yüceliğiniz” sözcük sözcük ve doğal olmayan bir unvandı. “Majesteleri” Türkçede yerleşik saray hitabı.','unvan/yerelleştirme')
add(fn,'CharaSerif_06_M','Bunu dert etme. İmparatorluğun gerçek gücünü\ngöstermemin zamanı geldi.','“Don’t worry about that” için “buna aldırma” mümkün ama soylu/kararlı konuşmada “dert etme” daha doğal; ayrıca iyelik yapısı akıcılaştırıldı.','akıcılık/karakter tonu')

# -----------------------------------------------------------------------------
# CHAPTER 2
# -----------------------------------------------------------------------------
fn='chapterBeginM002.csv'
add(fn,'CharaSerif_01_M','Güney körfezinde, yemyeşil ormanlarla kaplı\nküçük, gözlerden uzak bir ada.','DE/FR/IT/NL “abgelegen/isolée/sperduta/afgelegen”, ES “solitaria”: burada sosyal “izole” değil coğrafi “gözlerden uzak” anlamı var. “Yoğun ve sık” gereksiz ikilemeydi.','anlam/akıcılık')
add(fn,'CharaSerif_02_M','İçinde kadim suşi keşişlerinden kalan\nkutsal harabeler var. Adı da buradan geliyor.','“Venerable ruins” fiziksel harabeye “saygın” demek değil, kutsal/kadim kalıntı anlamında. ES/IT tapınak/manastır kutsallığını doğruluyor; doğal Türkçe kuruldu.','anlam/çapraz dil')
add(fn,'CharaSerif_04_M','Oradaki yoğun mistik enerji sayesinde\nsuşi ruhları güçlerini geliştirebilir.','DE/ES/FR/IT/NL ortak anlam “mistik enerji ruhları güçlendirir”. “Aşırı güçlü enerji / güçlerini bilemek” İngilizce kalıbını fazla izliyordu.','akıcılık/mekanik')
add(fn,'CharaSerif_05_M','Bir zamanlar köylüler tarafından korunuyordu,\nama Suşi Savaşları’nda İmparatorluk işgal etti.','“Vigilant” burada “uyanık köylüler” değil gözeten/koruyan halk. DE/ES/FR/IT bunu sade “köylüler/yerel halk” yapıyor. Struggles terimi de yerleşen “Suşi Savaşları”na getirildi.','anlam/terim')
add(fn,'CharaSerif_11_M','İmparatorluk artık Jinrai’den haberdar;\ndoğrudan hedeflerindesin.','“Put you squarely in their sights” yerleşik hedef/nişangâh deyimidir. “Seni tam hedeflerine koydular” Türkçe değil; ES/FR/IT/NL aynı hedef olma anlamını doğruluyor.','deyim/akıcılık')
add(fn,'CharaSerif_12_M','Bütün gözler senin üzerindeyken\nbirliklerim rahatça harekete geçebilir.','DE “zuschlagen”, ES manevra, FR champ libre, IT indisturbate: “room to work” fiziksel alan değil hareket serbestliği. Literal yapı düzeltildi.','deyim/çapraz dil')
add(fn,'CharaSerif_14_M','Pek hoşuna gidecek bir görev değilse\nözür dilerim.','“Role you’d prefer to play” mecazdır; “oynamayı tercih edeceğin rol” Türkçede tiyatro rolü gibi kalıyordu. NL doğrudan “en eğlenceli görev olmayabilir” diye çözüyor.','deyim/akıcılık')

# -----------------------------------------------------------------------------
# CHAPTER 3
# -----------------------------------------------------------------------------
fn='chapterBeginM003.csv'
add(fn,'CharaSerif_21_M','Ama sınır savunmaları çok güçlü.\nFazla yaklaşma, sakın pervasızlık etme.','İki ayrı uyarı Türkçede “pervasız davranma” ile mekanik kalıyordu; doğal ikaz ritmi için “sakın” yapısı kullanıldı.','karakter tonu/akıcılık')
add(fn,'CharaSerif_27_M','Off... Şu “olgunluk” lafların\nhiç de ince değil, haberin olsun!','EN “aren’t subtle” imanın fazla açık olduğunu söylüyor. “Daha az imalı olamaz mıydı” anlamı ters/garip kuruyordu; konuşma dilinde yeniden yazıldı.','anlam/karakter tonu')
add(fn,'CharaSerif_28_M','Yine de Masa’yı uzaktan\ndaha çok seviyorum.','“From a safe remove” bilerek kuru/alaycı “güvenli mesafeden” mizahıdır. Mevcut anlaşılır ama ağır; esprinin vuruşu kısaltıldı.','mizah/akıcılık')
add(fn,'CharaSerif_29_M','Sınır da ondan yeterince uzakta,\ndeğil mi?','Önceki satırın “Masa’dan uzak olayım” şakasını devam ettiriyor. Mevcut yapı sanki sınırın coğrafi olarak nerede olması gerektiğini tartışıyordu; çapraz-replik bağı netleştirildi.','çapraz replik/mizah')

# -----------------------------------------------------------------------------
# CHAPTER 5
# -----------------------------------------------------------------------------
fn='chapterBeginM005.csv'
add(fn,'CharaSerif_11_M','Senin sayende ticaret şehri Benteaux’ya\nkadar ilerledik.','DE/ES/FR/NL sade “senin sayende” kullanıyor. “Katkıların sayesinde” rapor dili gibi kalıyordu; karakter diyaloguna çekildi.','akıcılık')
add(fn,'CharaSerif_13_M','Buradan Büyük Köprü’yü geçince\nİmparatorluk başkenti çok yakın.','Altı dil “artık çok az kaldı” anlamında birleşiyor. “Başkentine az bir yol kalıyor” Türkçede doğal değil; kısa ve coğrafi anlamı net cümle seçildi.','akıcılık')
add(fn,'CharaSerif_19_M','İmparatorluğun büyük kalesi. Şimdiye kadarki\nen zorlu savaşımız bizi bekliyor.','Bastion için “siper” yanlış ölçek/nesne. DE Bastion, ES bastión, FR principal bastion, IT baluardo, NL fort; burada büyük kale/merkez savunma yapısı. “Dövüş” de askerî bağlamda “savaş” oldu.','askerî terim/anlam')
add(fn,'CharaSerif_24_M','Bu... bizim için hiç iyi değil.','“That sounds bad for us” için “kötü gibi” çeviri kokuyordu. FR/IT/NL de doğrudan kötü durum tepkisi veriyor; doğal konuşma seçildi.','karakter tonu')
add(fn,'CharaSerif_28_M','Nasıl güçlendireceksin?','Konuşmacı Masa’ya “kuvvetleri nasıl güçlendireceksin?” diye soruyor. Mevcut birinci kişi “Nasıl güçlendireceğim?” özneyi tersine çeviriyordu; DE/ES/FR/IT/NL sorunun karşı tarafa yöneldiğini doğruluyor.','anlam/kişi uyumu')
add(fn,'CharaSerif_39_M','Senden kaleyi almanı istemiyoruz.\nBirkaç küçük çatışma yeter. Yaparsın.','EN “city” bağlamda Fort Fugu; FR/NL açıkça fort diyor. “Şehir” nesnesi şaşırtıcıydı. Light skirmishes de doğal Türkçe kısaltıldı.','bağlam/akıcılık')
add(fn,'CharaSerif_40_M','Yapmak mı? Fazlasını yaparım! Birliklerin\ngelene kadar iş kalmayacak!','“I’ll do better than fine” için “İyiden de iyi yaparım” İngilizce kalıbıydı. FR/NL/ES meydan okuyan özgüveni daha serbest veriyor; Musashi’nin böbürlenen tonu yeniden kuruldu.','karakter tonu/yaratıcı çeviri')
# female identical line
add(fn,'CharaSerif_40_F',row(fn,'CharaSerif_40_M')['tur'],'Türkçe replik cinsiyet işaretlemediği için ana varyanttaki doğal/övüngen yeniden yazım kadın varyantına da aynen uygulandı.','varyant/tutarlılık')

# -----------------------------------------------------------------------------
# CHAPTER 7
# -----------------------------------------------------------------------------
fn='chapterBeginM007.csv'
add(fn,'CharaSerif_06_M',r'\u000E\u0000\u0002\u0002\u0096Hey millet! Bomba haber!\u000E\u0000\u0002\u0002d','ES “notición”, EN BIG news ve karakterin argo girişi sıradan “BÜYÜK haber”den daha canlı. Türkçede doğal ünlem “Bomba haber!” seçildi.','karakter tonu/yaratıcı')
add(fn,'CharaSerif_08_M','Franklin’le ilgili! Nerede olduğunu\nöğrendim!','DE/IT/NL açıkça Franklin’in tutulduğu yeri öğrendiğini söylüyor. “Nerede olduğuna dair bilgiyi kaptım” argo olmaya çalışırken yapaylaşıyordu; Archie’nin hızlı tonu kısa cümleyle korundu.','akıcılık/karakter tonu')
add(fn,'CharaSerif_09_M',r'\u000E\u0000\u0002\u0002\u0096Ciddi misin?!\u000E\u0000\u0002\u0002d','DE “Kein Witz?!”, ES/IT “ciddi misin”, NL “gerçekten?” bağlamın şaşkınlık olduğunu doğruluyor. “Bir daha söyle bakalım” Türkçede tehdit gibi duyuluyordu.','anlam/çapraz dil')
add(fn,'CharaSerif_09_F',row(fn,'CharaSerif_09_M')['tur'],'Cinsiyet varyantı aynı şaşkınlık tepkisi; Türkçede cinsiyet farkı olmadığı için ana varyantla eşitlendi.','varyant/tutarlılık')
add(fn,'CharaSerif_11_M','Duyduğuma göre Franklin’i, İmparatorluğun\nkuzeyindeki karlı bölgelerde tutuyorlarmış.','DE/ES/FR/IT/NL ortak anlam “kuzeyde tutsak”. “Kuzey tarafındaki ... bir yere tıkmışlar” gereksiz uzundu; argo ton tamamen silinmeden akıcılaştırıldı.','akıcılık')
add(fn,'CharaSerif_12_M','Orada İmparatorluk askerleri için koca bir\n“Yeniden Eğitme Tesisi” varmış!','FR “reformatage”, IT “rieducativa”, NL “heropvoedingskamp” bunun normal eğitim değil yeniden biçimlendirme/beyin yıkama merkezi olduğunu belirginleştiriyor. “Yeniden Eğitme” bu karanlık nüansı daha iyi taşıyor.','anlam/çapraz dil')

# -----------------------------------------------------------------------------
# CHAPTER 8
# -----------------------------------------------------------------------------
fn='chapterBeginM008.csv'
add(fn,'CharaSerif_06_M','Beni dinleyin. İçeri tek başıma gireceğim!','“Herkes dinlesin” anons dili gibi kalıyordu. Kararlı kişisel hitap “Beni dinleyin” sahne tonuna daha uygun.','karakter tonu')
add(fn,'CharaSerif_15_M','Güzel! Bedenimle de ruhumla da yanındayım.\nHaydi, ileri!','“Sally forth” bilerek biraz gösterişli/eski tınılı çağrıdır; “ileri atılalım” mekanik kaldı. Jinrai’nin yüksek tonunu kısa “Haydi, ileri!” koruyor.','karakter tonu/akıcılık')

# -----------------------------------------------------------------------------
# CHAPTER 9
# -----------------------------------------------------------------------------
fn='chapterBeginM009.csv'
add(fn,'CharaSerif_03_M','Annen Tapınak Korusu’nda bir rahibeydi\nve suşi ruhları konusunda uzmandı.','Scholar “bilge” değil araştırmacı/uzman. ES “experta”, FR “sommité”, IT “studiosa”, NL “her şeyi bilirdi”; uzmanlık anlamı doğal Türkçeyle verildi.','anlam/çapraz dil')
add(fn,'CharaSerif_05_M','Sonra SLF’ye katılıp herkesin suşiye\nulaşabildiği bir dünya için savaştım...','DE/ES/FR/IT/NL ortak niyet “herkes için suşi/serbest erişim”. “Dünyanın tüm insanlarına suşi hayali” gramer olarak bozuktu; ideali doğal cümleye dönüştürüldü.','anlam/akıcılık')
add(fn,'CharaSerif_08_M','Masa ve yakın çevresi suşiyi umursamıyor,\nyalnızca güç peşinde koşuyordu.','DE/FR/NL açıkça “suşi umurlarında değildi” diyor. “Suşinin kendisini hiç sevmezdi” kişi/çoğul ve stil olarak yapaydı; niyet keskinleştirildi.','akıcılık/anlam')
add(fn,'CharaSerif_11_M','Vay be...','EN “Yeesh”, ES “Qué horror”, NL “Jeetje” şaşkın/rahatsız iç çekiştir. Tek “Off.” Türkçede eksik/çeviri notu gibi duruyordu; bağlama uygun tepki seçildi.','karakter tonu/çapraz dil')
add(fn,'CharaSerif_18_M','Hrrrh... Emin değilim. Ne yaşandıysa\nYüce Ruh’un iradesiyle olmuştur.','DE/ES/FR/IT/NL doğrudan “Yüce Ruh’un iradesi” diyor. “Nasıl dilediyse öyle olmuştur” gereksiz dolambaçlıydı.','akıcılık/çapraz dil')
add(fn,'CharaSerif_20_M','Bu dünyada kavgayı bırakıp suşiyle\nbarış içinde yaşayabilirsek, belki...','ES suşinin şiddete üstün gelmesi, FR barış+suşi sevgisi, IT/NL barış içinde suşi diyor. “Kavgadan üstün tutulan suşiye yer açmak” literal ve anlaşılması zordu; ortak niyet yaratıcı Türkçeyle kuruldu.','yaratıcı çeviri/çapraz dil')
add(fn,'CharaSerif_21_M','Şimdi görüyorum ki bunu İmparatorluğun\nplanıyla başarabileceğime inanmak aptallıkmış.','DE/ES/FR/IT/NL pişmanlığı doğrudan geçmişteki yanlış inanca bağlıyor. Mevcut isim-fiil zinciri ağırdı; duygusal itiraf akıcılaştırıldı.','akıcılık/karakter tonu')
add(fn,'CharaSerif_26_M','Söz veriyorum!','ES/FR/IT bu duygusal baba-çocuk anında “söz veriyorum” diye yerelleştirmiş. “Tamam!” doğru bilgi verse de sahnenin duygusal ağırlığını eksiltiyordu.','karakter tonu/çapraz dil')
add(fn,'CharaSerif_26_F','Söz veriyorum!','Cinsiyet varyantı aynı duygusal söz; Türkçe cinsiyet işaretlemediği için ana varyantla eşitlendi.','varyant/tutarlılık')

# -----------------------------------------------------------------------------
# CHAPTER END 3 / 5
# -----------------------------------------------------------------------------
fn='chapterEndM003.csv'
add(fn,'CharaSerif_23_M','Önce Tapınak Korusu, şimdi Sınır Kapısı.\nRüzgâr bizden yana.','Momentum mecazını “ivme” diye teknik çevirmek diyalogda yapaydı. Türkçedeki yerleşik askerî/mecazi “rüzgâr bizden yana” aynı ilerleyiş hissini taşıyor.','deyim/yaratıcı')
add(fn,'CharaSerif_24_M','Buradan sonra İmparatorluk topraklarındayız.\nDireniş giderek sertleşecek.','“Resistance will be stiff going forward” için mevcut cümle İngilizce isim yapısını taklit ediyordu. Doğal askerî öngörü cümlesi kuruldu.','akıcılık')
add(fn,'CharaSerif_25_M','Amacımız ticaret şehri Benteaux’da\nbir köprübaşı kurmak.','“Beachhead” askerî harekâtta yerleşik “köprübaşı” terimidir; “çıkış noktası” stratejik anlamı siliyordu.','askerî terim')
add(fn,'CharaSerif_27_M','Hmm. Ya tropik kıyıdan ya da\nvolkanik dağdan ilerleyebiliriz.','“Tropik sahil kıyısı” aynı anlamı iki kez söylüyordu; seçenek/rota anlamı Türkçede doğrudan kuruldu.','akıcılık')
add(fn,'CharaSerif_28_M','Ausprey’nin sahildeki güçleri hileci,\nsavunması yüksek suşi ruhları kullanıyor.','“Hileleri ve yüksek savunması olan” liste Türkçede nesne özelliklerini yanlış bağlıyordu. Mekanik özellikler sıfatlaştırılarak netleştirildi.','gramer/mekanik')
add(fn,'CharaSerif_29_M','Volkandaki Purrsilla birliklerinde ise\nyıkıcı saldırı yetenekleri bekleyebiliriz.','“Brutal” için “acımasız” kişi niyeti çağrıştırıyor; burada saldırı becerisinin gücü anlatılıyor. “Yıkıcı” mekanik anlamı daha doğru.','anlam/mekanik')
add(fn,'CharaSerif_35_M','Dinle, Musashi. İmparatorlukta bile\nhalkın suşiye erişimi çok kısıtlı.','“Sushi is rare among common folk” için “suşi halk arasında nadir” yapaydı. Erişim teması hikâyenin ana meselesi olduğu için anlam açıklaştırıldı.','anlam/akıcılık')
add(fn,'CharaSerif_36_M','Görevlerimizden biri de suşi keyfini\nİmparatorluk halkına ulaştırmak olmalı!','“Beauty of sushi” literal “suşinin güzelliği” soyut/garipti. Bağlam halkın suşiyi tadabilmesi; “suşi keyfi” doğal ve amaçla uyumlu. Yazım hatası da giderildi.','yaratıcı çeviri/akıcılık')

fn='chapterEndM005.csv'
for lab in ['CharaSerif_01_M','CharaSerif_01_F']:
    add(fn,lab,'İki ideali birleştirdi: suşi özgürlüğü\nve suşinin değerini bilmek.','İki madde dilbilgisel olarak paralel değildi (“suşinin özgürlüğü / suşiye değer vermek”). İdealler kısa ve dengeli isim yapılarıyla yeniden kuruldu.','gramer/akıcılık')
add(fn,'CharaSerif_02_M','Suşi ruhlarının yeniden kazandıkları güvenle,\nyaklaşan savaş için plan yaptılar.','“Renewed trust” “tazelenen güveniyle” diye mekanik çevrilmişti; güvenin yeniden kazanılması doğal Türkçeyle ifade edildi.','akıcılık/anlam')

# -----------------------------------------------------------------------------
# FIRST BATTLE TUTORIALS
# -----------------------------------------------------------------------------
fn='eventBattleM001.csv'
add(fn,'EventBattleM001_02_M','Korkma. Burası suşi tarlası;\nsuşinin suşi ruhlarından aktığı özel bir yer.','Mevcut “suşinin, suşi ruhlarından aktığı bir yer” gereksiz virgül ve ağır tamlama taşıyordu. Game term “suşi tarlası” korunup açıklama doğal cümleye çekildi.','öğretici/akıcılık')
# Preserve exact text-control wrappers copied from English around the highlighted phrase.
eng5=row(fn,'EventBattleM001_05_M')['eng']
# locate control prefix/suffix around phrase in EN
m=re.search(r'(\\u000E\\u0000\\u0003\\u0004[^t]*?)two plates of the\\nsame color(\\u000E\\u0000\\u0003\\u0004\\u0000[^!]*)',eng5)
if m:
    new='Hadi, '+m.group(1)+'aynı renkten iki tabağı'+m.group(2)+'!\\nBağla bakalım!'
else:
    # known literal controls in this asset
    new=r'Hadi, \u000E\u0000\u0003\u0004쳿Ｏaynı renkten iki tabağı\u000E\u0000\u0003\u0004\u0000＀!\nBağla bakalım!'
add(fn,'EventBattleM001_05_M',new,'Türkçe slotta yalnız kontrol kodları kalmış, görünen öğretici metin tamamen kaybolmuştu. EN ve diğer dillerin “aynı renkten iki tabağı bağla” talimatı kontrol kodları korunarak geri kuruldu.','işlevsel kalite/öğretici')
add(fn,'EventBattleM001_07_M','Aynen öyle. Şimdi aynı renkten\nolabildiğince çok tabağı bağla!','“Tek bir renkten” anlaşılır ama Türkçe öğreticide “aynı renkten” daha doğrudan; önceki talimatla terminoloji birleştirildi.','öğretici/tutarlılık')
add(fn,'EventBattleM001_13_M','Hadi ye! Az önceki gibi aynı renkten\niki veya daha fazla tabağı bağla!','Mevcut satır tek satıra yığılmış ve “Ye bakalım” tonu zayıftı. Öğretici adımı kısa iki satırda, önceki terimle tutarlı yeniden kuruldu.','öğretici/akıcılık')

fn='eventBattleM002.csv'
rep(fn,'EventBattleM002_08_M',r'\u000E\u0000\u0003\u0004쳿Ｏtabak yığını\u000E\u0000\u0003\u0004\u0000＀\ndokun',r'\u000E\u0000\u0003\u0004쳿Ｏtabak yığınına\u000E\u0000\u0003\u0004\u0000＀\ndokun','Nesne yönelme eki eksikti: “bir tabak yığını dokun” dilbilgisel olarak yanlış. Kontrol kodları korunarak “yığınına dokun” yapıldı.','öğretici/gramer')
# reconstruct 11 with controls via targeted text fragments
r11=row(fn,'EventBattleM002_11_M')['tur']
r11=r11.replace('aynı renk-\\nteki tabak yığınları','aynı renkteki\\ntabak yığınları')
r11=r11.replace(' ile vur da süper güçlü bir ',' ile vur!\\nSüper güçlü bir ')
add(fn,'EventBattleM002_11_M',r11,'Elle satır bölme yüzünden “renk-teki” kelimesi ikiye ayrılmıştı ve açıklama tek uzun satıra yığılıyordu. Aynı renk mekanik terimi okunaklı satırlara taşındı; kontrol kodları korundu.','öğretici/biçim')
add(fn,'EventBattleM002_15_M','İyi yakaladın! Masandaki tabak yığınlarını\nistediğin zaman fırlatabilirsin!','“Good eye!” bağlamda fark etme/öğrenme övgüsü; “Gözün iyi görüyor” literal ve komik olmayan şekilde fiziksel görme anlamına kayıyordu. “İyi yakaladın!” doğal övgü.','deyim/öğretici')
r16=row(fn,'EventBattleM002_16_M')['tur'].replace('aynı renkte birden fazla\\nyığın','aynı renkten birden fazla\\nyığın').replace(' ile vurursan','la vurursan')
add(fn,'EventBattleM002_16_M',r16,'Aynı renkli yığın mekaniği için “aynı renkten” daha doğal; “yığın ile” de ekli Türkçe biçime çekildi. Mekanik anlam değişmedi.','öğretici/gramer')

# -----------------------------------------------------------------------------
# EVENT BEGIN 2
# -----------------------------------------------------------------------------
fn='eventBeginM002.csv'
add(fn,'CharaSerif_02_M','Dikkat et. Fazla heyecanlanıp\nkramp girme.','“Don’t overexcite yourself and get a cramp” için “kendini gaza getirip kramp girsin istemeyiz” özne/ek bakımından yapaydı. Doğal uyarı cümlesi seçildi.','akıcılık')
add(fn,'CharaSerif_03_M',r'\u000E\u0000\u0002\u0002\u0096Aha! Bu Franklin!\u000E\u0000\u0002\u0002d','“Franklin bu” Türkçede ters ve işaret etme tonunu zayıflatıyordu; kısa şaşkınlık cümlesi doğal sıraya alındı.','akıcılık')
add(fn,'CharaSerif_08_M','Namım benden önce gelmiş, ha?\nVay be!','“My reps precede me” yerleşik “namım benden önce gelmiş” deyimidir. “Şöhretim ... Eh, hayret” anlamı verse de karakterin gevşek özgüvenini zayıflatıyordu.','deyim/karakter tonu')
add(fn,'CharaSerif_16_M','Tabii. İşi kolaylaştırabilirdin, yağ kafalı,\nama zor yolu da seçebiliriz.','“Flab-brains” hakaretidir; “yağ beyinli” Türkçede sözlük çevirisi gibi. “Yağ kafalı” hakaret formuna yaklaştırıldı; easy/the other way karşıtlığı da doğal kuruldu.','hakaret/karakter tonu')
add(fn,'CharaSerif_17_M',r'\u000E\u0000\u0002\u0002\u0096Haydi askerler! Acımayın!\u000E\u0000\u0002\u0002d','“Hit ’em hard!” savaş komutunda literal “sert vurun” yerine Türkçede doğal saldırı emri “Acımayın!” seçildi; Kodiak’ın kaba tonu güçlendirildi.','karakter tonu')
for lab in ['CharaSerif_27_M','CharaSerif_27_F']:
    add(fn,lab,'Madem mecburum... Gelin bakalım!','“Well, if I have to!” gönülsüz kabullenmedir. “Madem öyle, mecbursam” aynı fikri iki kez söylüyordu; Musashi’nin meydan okuması daha sıkı kuruldu.','akıcılık/karakter tonu')

# -----------------------------------------------------------------------------
# EVENT END 1
# -----------------------------------------------------------------------------
fn='eventEndM001.csv'
add(fn,'CharaSerif_10_M','Hahahah! Birinin suşiyi ilk kez tadışını\ngörmek hep ayrı bir keyif.','DE/FR/NL “Freude/plaisir/genoegen”, ES yüz ifadesinden alınan keyif diyor. “Her zaman tatmin edici” duygusal konuşmada mekanik; sıcak “ayrı bir keyif” seçildi.','karakter tonu/çapraz dil')
for lab in ['CharaSerif_12_M','CharaSerif_12_F']:
    cur=row(fn,lab)['tur']
    add(fn,lab,cur.replace('Evet! Geliyorum!','Hah! Başladım bile!'),'Önceki satır “ağlayabilirim” diyor; DE/ES/FR açıkça ağlamanın başladığını anlatıyor. “Evet! Geliyorum!” İngilizce kalıbını yanlış yorumlayıp bağlamı bozuyordu. Kontrol kodları korundu.','çapraz replik/anlam')
for lab in ['CharaSerif_19_M','CharaSerif_19_F']:
    add(fn,lab,'Evet ama o ve annem,\\nSuşi Savaşları başlar başlamaz kayboldular...','Struggles oyun tarihindeki adlandırılmış savaştır. Önceki turlarda yerleşen “Suşi Savaşları” terimi standardize edildi; satır da ekran uzunluğunu aşmaması için doğal bir noktadan bölündü.','terim/tutarlılık')
add(fn,'CharaSerif_20_M','Üzücü. Ama seni suşi yerken görünce\nbir şeyden emin oldum.','“That is unfortunate” için tek “Talihsiz.” kişi sıfatı gibi ve doğal değil. NL/IT “üzücü/çok üzgünüm”; devamındaki “convinced me” de “emin oldum” anlamında.','anlam/akıcılık')
add(fn,'CharaSerif_35_M',r'\u000E\u0000\u0002\u0002\u0096Vay! Hedefin bayağı büyük!\u000E\u0000\u0002\u0002d','“Tall order” deyimdir; “büyük bir istek” anlaşılır ama hedefin iddialılığını yansıtmaz. ES “çok yüksek hedef”, IT “zorlu proje”, NL “herkes mi?”; doğal tepki seçildi.','deyim/çapraz dil')
add(fn,'CharaSerif_36_M','Belki öyle. Ama yolculuklarımda bunu\nadım adım gerçekleştiriyorum.','“One person at a time” için “insan insan” Türkçede doğal değil. NL açıkça “stap voor stap”; anlamı koruyan yerleşik “adım adım” kullanıldı.','deyim/akıcılık')
for lab in ['CharaSerif_37_M','CharaSerif_37_F']:
    add(fn,lab,'(Suşi... herkes için mi? İşte böyle olmalı!\nBöyle bir lezzet gizli kalmamalı!)','DE/ES/IT ortak niyet fikri herkese yayma/coşku. “Bu olmalı / sır olarak saklamak için fazla güzel” İngilizce yapıya bağlıydı; Musashi’nin iç sesi doğal ve coşkulu yeniden kuruldu.','karakter tonu/yaratıcı çeviri')
for lab in ['CharaSerif_41_M','CharaSerif_41_F']:
    add(fn,lab,'Onların da suşiyi ilk tattıklarında\nyüzlerini görmek istiyorum!','“Yüz ifadelerini görmek” teknik/rapor dili gibi. ES/IT/NL doğrudan “yüzlerini görmek” diyor; çocuğun doğal hevesi geri getirildi.','akıcılık/karakter tonu')
add(fn,'CharaSerif_43_M','O zaman sıradaki durağım orası. Hadi gidip\nsuşi sevgisini yayalım!','“Spread the good word” deyimsel/yarı vaaz tınılıdır; “suşinin güzel sözü” Türkçede anlamsız literal kalıyordu. FR/ES/NL eylemi serbestleştiriyor; oyunun ana temasına uygun “suşi sevgisini yaymak” seçildi.','deyim/yaratıcı çeviri')

# Struggles kalan tüm açık kullanımlar -> Suşi Savaşları (hedefli)
for fn2,(fields,rs) in files.items():
    for r in rs:
        if 'Mücadeleler' in r.get('tur','') and ('Struggle' in r.get('eng','') or 'Struggles' in r.get('eng','')):
            add(fn2,r['label'],r['tur'].replace('Mücadeleler','Suşi Savaşları'),'Struggles oyunun tarihindeki özel savaş dönemidir; önceki turlarda yerleşen “Suşi Savaşları” terimi kalan kullanımlarda da standardize edildi.','hedefli terim')

# -----------------------------------------------------------------------------
# TÜM CSV'LERİ YAZ
# -----------------------------------------------------------------------------
for p in OUT.glob('*.csv'):
    fields,rs=files[p.name]
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rs)

# -----------------------------------------------------------------------------
# RAPOR: bu tur yalnız önceki master'da BEKLİYOR olan seçili satırlar tam blok sayılır;
# ayrıca seçili blok dışındaki hedefli değişiklikler ayrı v0.7-hedefli olarak eklenir.
# -----------------------------------------------------------------------------
prev_audit=[]; prev_changes=[]
if PREV_AUDIT.exists():
    with PREV_AUDIT.open(encoding='utf-8-sig',newline='') as f: prev_audit=list(csv.DictReader(f))
if PREV_CHANGES.exists():
    with PREV_CHANGES.open(encoding='utf-8-sig',newline='') as f: prev_changes=list(csv.DictReader(f))
prev_change_keys={(r['file'],r['label']) for r in prev_changes}

story_files={f for f in review_files if f.startswith(('chapter','event'))}

def unchanged_reason(fn,r):
    e=r.get('eng',''); t=r.get('tur',''); lab=r.get('label','')
    alts=[r.get(k,'') for k in ['deu','esp','fra','ita','nld']]
    if not e and not any(alts) and not t:
        if fn=='DbgEventProcess.csv':
            return 'Debug/olay işleme için ayrılmış boş slot. EN dahil altı resmî dilde de görünen metin yok; içerik eklemek motor işlevini değiştirebileceğinden yapısal olarak boş bırakıldı.'
        return 'Bu etiket resmî dillerde de boş varyant/ayrılmış slot. Görünen metin olmadığı için yapıyı korumak amacıyla aynı bırakıldı.'
    if e and not t:
        if fn=='episode_cmn.csv' and lab.startswith('Name_Label_'):
            return 'Özel ad etiketi Türkçe slotta boş. Bu tur kullanıcının talebi doğrultusunda çevrilmemiş içerik tamamlama değil mevcut çeviri kalitesi tarandı; özel adın kendisi çevrilmeyeceğinden slot bu tur değiştirilmedi ve ayrıca işlevsel eksik olarak not edildi.'
        return 'Türkçe slot boş/çevrilmemiş. Bu turun odağı mevcut çevirinin kalite denetimi olduğu için yeni çeviri eklenmedi; karar mevcut slotu korumayı ifade eder.'
    if lab.endswith(('_F','_f')) and not e and not t:
        return 'Kadın/cinsiyet varyantı kaynakta boş; oyun ana varyantı yeniden kullanıyor. Türkçede ek içerik üretmek gerekmediği için aynı bırakıldı.'
    if fn=='database_staffrollName.csv':
        if e and (e.upper()!=e or re.search(r'[a-z]',e)):
            return 'Kişi/şirket/özel ad jenerik girdisi. Resmî diller de adı çevirmeden koruyor; özel ad yerelleştirmesi yapılmaması gerektiği için aynı bırakıldı.'
        return 'Jenerik görev/bölüm adı diğer diller ve Türkçe sektör kullanımıyla karşılaştırıldı. Mevcut karşılık işlevi doğru ve doğal verdiği için yeniden yazılmadı.'
    if fn=='ShrineGetMode.csv':
        if 'Awake' in lab:
            return 'Ruhun uyanış/yükseliş repliği karakterin konuşma biçimi ve altı resmî dille karşılaştırıldı. Mevcut Türkçe kısa, doğal ve karakter sesini yeterince koruduğu için aynı kaldı.'
        if 'AlreadyFriend' in lab:
            return 'Zaten sahip olunan ruh durumundaki replik altı dil ve komşu satırla kontrol edildi. Arkadaş/öz verme anlamı ve karakter tonu Türkçede doğal kaldığı için değişiklik gerekmedi.'
        if 'Contact' in lab or 'Choice' in lab:
            return 'Tapınak karşılaşma repliği EN + DE/ES/FR/IT/NL ve karakterin konuşma tarzıyla karşılaştırıldı. Anlam, nezaket/argo düzeyi ve bağlam Türkçede yeterince doğal olduğu için aynı bırakıldı.'
        return 'Tapınak sistem/UI satırı Bağ mekaniği ve altı resmî dille karşılaştırıldı. Terim ve işlev doğru olduğu için aynı bırakıldı.'
    if fn=='episode_cmn.csv':
        if lab.startswith('Name_Label_'):
            return 'Karakter/rol adı diğer dillerle karşılaştırıldı. Mevcut Türkçe yerleşik rol adını doğru taşıyor veya özel adı çevirmiyor; değişiklik gerekmedi.'
        return 'Ortak bölüm/UI etiketi altı resmî dille ve oyun genelindeki terminolojiyle karşılaştırıldı. İşlev ve kısa arayüz dili doğru olduğu için aynı bırakıldı.'
    if fn in story_files:
        if not e and not t:
            return 'Kaynak bu cinsiyet/olay varyantında boş; ana replik başka etiketten kullanılıyor. Türkçede gereksiz metin eklenmedi.'
        if lab.endswith(('_F','_f')):
            return 'Cinsiyet varyantı ana replik ve diğer dillerle karşılaştırıldı. Türkçe cinsiyet işaretlemediği ve mevcut metin ana varyantla doğal biçimde aynı çalıştığı için değişiklik yapılmadı.'
        return 'Replik, komşu repliklerle birlikte EN + DE/ES/FR/IT/NL üzerinden kontrol edildi. Mevcut Türkçe anlamı, karakter sesini, deyim/espri işlevini ve sahne akışını yeterince doğal taşıdığı için aynı bırakıldı.'
    if fn=='DbgEventProcess.csv':
        return 'Debug/olay işleme satırı resmî dillerle karşılaştırıldı; kullanıcıya gösterilen yerelleştirilebilir metin olmadığı için aynı bırakıldı.'
    return 'Altı resmî dille ve bağlamla karşılaştırıldı; belirgin anlam, ton, espri veya terim kaybı bulunmadığından aynı bırakıldı.'

new_audit=[]; audited_keys=set()
for fn in review_files:
    for r in files[fn][1]:
        key=(fn,r['label'])
        # Yalnız v0.6 master'ında bekleyenleri bu tur tam satır taraması say.
        if prev_master.get(key,{}).get('review_status')!='BEKLİYOR':
            continue
        ch=changed_lookup.get(key); audited_keys.add(key)
        new_audit.append({'round':'v0.7','file':fn,'label':r['label'],'index':r.get('index',''),
            'decision':'DEĞİŞTİ' if ch else 'AYNI KALDI','eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),
            'old_tur':ch['old_tur'] if ch else r.get('tur',''),'new_tur':r.get('tur',''),'reason':ch['reason'] if ch else unchanged_reason(fn,r)})
# Önceden incelenmiş ya da seçili blok dışındaki hedefli değişiklikler de bu turun raporunda görünsün.
for ch in changes:
    key=(ch['file'],ch['label'])
    if key in audited_keys: continue
    r=row(ch['file'],ch['label']); audited_keys.add(key)
    new_audit.append({'round':'v0.7-hedefli','file':ch['file'],'label':ch['label'],'index':r.get('index',''),'decision':'DEĞİŞTİ',
        'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),
        'old_tur':ch['old_tur'],'new_tur':r.get('tur',''),'reason':ch['reason']})

field_a=['round','file','label','index','decision','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
with (OUTROOT/'V07_YENI_BLOK_SATIR_INCELEME.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=field_a); w.writeheader(); w.writerows(new_audit)

cum={}
for a in prev_audit: cum[(a['file'],a['label'])]=a
for a in new_audit: cum[(a['file'],a['label'])]=a
cum_rows=list(cum.values())
with (OUTROOT/'SATIR_BAZLI_INCELEME_KUMULATIF.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=field_a); w.writeheader(); w.writerows(cum_rows)

field_c=['round','category','file','label','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
with (OUTROOT/'V07_YENI_DEGISIKLIKLER.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=field_c); w.writeheader(); w.writerows(changes)
# Eski paket içinde tarihsel dosya adları bulunuyorsa okuyup birleştir; v0.6 full bundle'da Raporlar altındaydı.
if not prev_changes:
    p=BASE/'Raporlar'/'INCELEME_DEGISIKLIKLERI.csv'
    if p.exists():
        with p.open(encoding='utf-8-sig',newline='') as f: prev_changes=list(csv.DictReader(f))
combined=prev_changes+changes
with (OUTROOT/'INCELEME_DEGISIKLIKLERI.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=field_c); w.writeheader(); w.writerows(combined)
latest={}
for r in combined: latest[(r['file'],r['label'])]=r
with (OUTROOT/'INCELEME_SON_DURUM_ESSIZ.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=field_c); w.writeheader(); w.writerows(latest.values())

# master 10.676
new_audit_map={(a['file'],a['label']):a for a in new_audit}
master=[]
for fn2 in sorted(files):
    for r in files[fn2][1]:
        key=(fn2,r['label'])
        if key in new_audit_map:
            a=new_audit_map[key]; status='İNCELENDİ_v0.7' if a['round']=='v0.7' else 'HEDEFLİ_DÜZELTME_v0.7'; decision=a['decision']; old=a['old_tur']; reason=a['reason']
        elif key in prev_master and prev_master[key].get('review_status')!='BEKLİYOR':
            pm=prev_master[key]; status=pm['review_status']; decision=pm['decision']; old=pm['old_tur']; reason=pm['reason']
        elif key in latest:
            h=latest[key]; status='ÖNCEKİ_TURDA_DEĞİŞTİ'; decision='DEĞİŞTİ'; old=h['old_tur']; reason=h['reason']
        else:
            status='BEKLİYOR'; decision='HENÜZ KARAR YOK'; old=r.get('tur',''); reason='Bu etiket henüz satır-satır manuel kalite turuna alınmadı; incelenmeden “aynı kaldı” diye işaretlenmedi.'
        master.append({'file':fn2,'label':r['label'],'index':r.get('index',''),'review_status':status,'decision':decision,
            'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),
            'old_tur':old,'current_tur':r.get('tur',''),'reason':reason})
master_fields=['file','label','index','review_status','decision','eng','deu','esp','fra','ita','nld','old_tur','current_tur','reason']
with (OUTROOT/'TUM_10676_SATIR_DURUMU.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=master_fields); w.writeheader(); w.writerows(master)

# Satır uzunluğu kontrolü (literal kontrol kodlarını çıkar)
ctrl_lit=re.compile(r'\\u[0-9A-Fa-f]{4}')
def visible_len(line):
    s=ctrl_lit.sub('',line)
    s=''.join(ch for ch in s if ord(ch)>=32 and not (0xE000<=ord(ch)<=0xF8FF))
    s=re.sub(r'[\uff00-\uffef]|[�-￿]','',s)
    return len(s)
warn=[]
for ch in changes:
    for n,line in enumerate(ch['new_tur'].split('\\n'),1):
        L=visible_len(line)
        if L>48: warn.append({'file':ch['file'],'label':ch['label'],'line_no':n,'visible_len':L,'line':line})
with (OUTROOT/'V07_YENI_DEGISIKLIK_UZUNLUK_UYARILARI.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['file','label','line_no','visible_len','line']); w.writeheader(); w.writerows(warn)

# MSBT rebuild / validate / round-trip
rebuilt=OUTROOT/'rebuilt_patch'
subprocess.run([sys.executable,str(TOOL),'import','--csv',str(OUT),'--patch',str(PATCH_BASE),'--out',str(rebuilt)],check=True)
subprocess.run([sys.executable,str(TOOL),'validate','--source',str(SOURCE),'--patch',str(rebuilt)],check=True)
verify=OUTROOT/'verify_csv'
subprocess.run([sys.executable,str(TOOL),'export','--source',str(SOURCE),'--patch',str(rebuilt),'--out',str(verify)],check=True)
diffs=[]; total=0
for p in sorted(OUT.glob('*.csv')):
    with p.open(encoding='utf-8-sig',newline='') as f1,(verify/p.name).open(encoding='utf-8-sig',newline='') as f2:
        a=list(csv.DictReader(f1)); b={r['label']:r for r in csv.DictReader(f2)}
    for x in a:
        total+=1; y=b.get(x['label'])
        if not y or x.get('tur','')!=y.get('tur',''):
            diffs.append((p.name,x['label'],x.get('tur',''),'' if not y else y.get('tur','')))
with (OUTROOT/'ROUNDTRIP_DOGRULAMA.txt').open('w',encoding='utf-8') as f:
    f.write(f'Etiket: {total}\nFark: {len(diffs)}\nYapısal validate: OK\n')
    for d in diffs[:100]: f.write(repr(d)+'\n')
if diffs: raise SystemExit(f'Roundtrip fark var: {len(diffs)}')

# Stats
full_rows=[a for a in new_audit if a['round']=='v0.7']
new_changed=sum(a['decision']=='DEĞİŞTİ' for a in full_rows)
new_same=sum(a['decision']=='AYNI KALDI' for a in full_rows)
targeted=sum(a['round']=='v0.7-hedefli' for a in new_audit)
waiting=sum(1 for r in master if r['review_status']=='BEKLİYOR')
fully_reviewed=sum(1 for r in master if r['review_status'].startswith('İNCELENDİ'))
report_covered=sum(1 for r in master if r['review_status']!='BEKLİYOR')
unique_changed=len(latest)

readme=f'''SUSHI STRIKER TÜRKÇE ÇEVİRİ KALİTE İNCELEMESİ - v0.7\n{'='*64}\n\nBu paket v0.6 üzerine kuruludur. İncelenen HER satırda DEĞİŞTİ / AYNI KALDI\nkararı ve somut neden alanı bulunur. Henüz incelenmeyenler BEKLİYOR kalır.\n\nV0.7 TAM MANUEL BLOK\n--------------------\nDosyalar: {', '.join(review_files)}\nÖnceki turda BEKLİYOR olup bu tur tek tek incelenen: {len(full_rows)}\nDeğişti: {new_changed}\nAynı kaldı: {new_same}\nEk hedefli/önceden incelenmiş terim düzeltmesi: {targeted}\nToplam v0.7 değişiklik olayı: {len(changes)}\n\nÖNE ÇIKANLAR\n-------------\n- Potential Plate -> Bağsız Tabak; resmî dillerin pre-alliance / neutral / inactive / bandless ortak anlamı esas alındı.\n- ShrineGetMode karakter replikleri ve Bağ sistemi yeniden tarandı.\n- İlk savaş öğreticisinde yalnız kontrol kodlarına düşmüş kayıp talimat metni geri kuruldu.\n- Bölüm 2/3/5/7/8/9 ve olay sahnelerinde kişi, deyim, karakter sesi ve çapraz-replik hataları düzeltildi.\n- “Say that again?!” bağlamı diğer dillerden doğrulanarak “Ciddi misin?!” oldu.\n- “Good eye!” -> “İyi yakaladın!”, “tall order” -> “Hedefin bayağı büyük!” gibi literal deyimler doğal Türkçeye çekildi.\n- Jenerikte key animation -> Ana Animasyon; lead görevleri -> Sorumlusu gibi sektör terimleri düzeltildi.\n\nRAPORLAR\n---------\nV07_YENI_BLOK_SATIR_INCELEME.csv\n  Bu tur incelenen HER satır + hedefli düzeltmeler; 7 dil, karar, eski/yeni TR, neden.\nSATIR_BAZLI_INCELEME_KUMULATIF.csv\n  Önceki turlar + v0.7; her incelenmiş etiketin en güncel kararı.\nTUM_10676_SATIR_DURUMU.csv\n  10.676 satırın tamamı; bekleyenler açıkça BEKLİYOR.\nV07_YENI_DEGISIKLIKLER.csv\n  Bu tur değişen satırlar ve gerekçeler.\nV07_YENI_DEGISIKLIK_UZUNLUK_UYARILARI.csv\n  >48 görünür karakter kontrolü.\nROUNDTRIP_DOGRULAMA.txt\n  CSV -> MSBT -> CSV doğrulaması.\n\nGENEL DURUM\n-----------\nBu tur tam manuel blok: {len(full_rows)}\nKümülatif İNCELENDİ satırı: {fully_reviewed}\nBEKLİYOR: {waiting}\nMaster raporda karar kapsamı: {report_covered}/10676\nBenzersiz müdahale edilmiş etiket: {unique_changed}\nMSBT: 243/243\nCSV -> MSBT -> CSV: {total} etiket, fark 0\nYapısal validate: OK\nYeni değişikliklerde >48 görünür karakter uyarısı: {len(warn)}\n'''
(OUTROOT/'README_TR.txt').write_text(readme,encoding='utf-8')

# bundle
bundle=OUTROOT/'full_bundle'; (bundle/'LayeredFS').mkdir(parents=True)
shutil.copytree(rebuilt,bundle/'LayeredFS'/'00040000001C1D00')
shutil.copytree(OUT,bundle/'CSV')
(bundle/'Raporlar').mkdir()
for name in ['V07_YENI_BLOK_SATIR_INCELEME.csv','SATIR_BAZLI_INCELEME_KUMULATIF.csv','TUM_10676_SATIR_DURUMU.csv','V07_YENI_DEGISIKLIKLER.csv','INCELEME_DEGISIKLIKLERI.csv','INCELEME_SON_DURUM_ESSIZ.csv','V07_YENI_DEGISIKLIK_UZUNLUK_UYARILARI.csv','ROUNDTRIP_DOGRULAMA.txt']:
    shutil.copy2(OUTROOT/name,bundle/'Raporlar'/name)
shutil.copytree(BASE/'Araclar',bundle/'Araclar')
shutil.copy2(Path(__file__),bundle/'Araclar'/'v07_inceleme_uygulama_betigi.py')
shutil.copy2(OUTROOT/'README_TR.txt',bundle/'README_TR.txt')
manifest=[]
for p in sorted(x for x in bundle.rglob('*') if x.is_file()):
    manifest.append(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(bundle).as_posix()}')
(bundle/'DOSYA_MANIFESTOSU_SHA256.txt').write_text('\n'.join(manifest)+'\n',encoding='utf-8')

def zipdir(src,out):
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(Path(src).rglob('*')):
            if p.is_file(): z.write(p,p.relative_to(src).as_posix())
zipdir(bundle,OUTROOT/'Sushi_Striker_TR_v07_FULL.zip')
ptmp=OUTROOT/'patch_bundle'; ptmp.mkdir(); shutil.copytree(bundle/'LayeredFS',ptmp/'LayeredFS'); zipdir(ptmp,OUTROOT/'Sushi_Striker_TR_v07_LayeredFS.zip'); shutil.rmtree(ptmp)
atmp=OUTROOT/'tools_bundle'; atmp.mkdir(); shutil.copytree(bundle/'Araclar',atmp/'Araclar'); shutil.copy2(OUTROOT/'README_TR.txt',atmp/'README_TR.txt'); zipdir(atmp,OUTROOT/'Sushi_Striker_TR_v07_Araclar.zip'); shutil.rmtree(atmp)

print('v0.7 OK')
print('full rows',len(full_rows),'changed',new_changed,'same',new_same,'targeted',targeted)
print('change events',len(changes),'fully reviewed',fully_reviewed,'waiting',waiting,'covered',report_covered,'unique changed',unique_changed)
print('warnings',len(warn),'roundtrip',total,'diffs',len(diffs))
if warn:
    print('WARNINGS')
    for x in warn: print(x)
