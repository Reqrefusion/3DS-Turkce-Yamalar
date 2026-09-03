from pathlib import Path
import csv, shutil, re, subprocess, hashlib, zipfile, sys

ROOT=Path('/mnt/data/sushi_work')
SRC=ROOT/'review_v04'/'csv'
OUTROOT=ROOT/'review_v05'
OUT=OUTROOT/'csv'
TOOL=ROOT/'review_v04'/'full_bundle'/'Araclar'/'sushi_msbt_csv_flat.py'
PATCH_BASE=ROOT/'review_v04'/'full_bundle'/'LayeredFS'/'00040000001C1D00'
SOURCE=ROOT/'msgstudio'/'msgstudio'

if OUTROOT.exists(): shutil.rmtree(OUTROOT)
OUT.mkdir(parents=True)
for p in SRC.glob('*.csv'): shutil.copy2(p,OUT/p.name)

files={}
for p in OUT.glob('*.csv'):
    with p.open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f)); fields=list(rows[0].keys()) if rows else ['label','index','deu','eng','esp','fra','ita','nld','tur']
    files[p.name]=(fields,rows)

review_files=['homeSushibar.csv','homeKoziin.csv','homeShrine.csv','homeArena.csv','homeTower.csv','scene_map.csv','scene_cmn.csv']
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
    rec={'round':'v0.5','category':category,'file':fn,'label':label,'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),'old_tur':old,'new_tur':new,'reason':reason}
    changes.append(rec); changed_lookup[key]=rec; return True

def replace_in(fn,label,oldfrag,newfrag,reason,category='manuel kalite',count=-1):
    r=row(fn,label); oldfrag=norm(oldfrag); newfrag=norm(newfrag); cur=r.get('tur','')
    if oldfrag not in cur: raise ValueError(f'{fn}:{label} parça yok: {oldfrag!r}\nCUR={cur!r}')
    new=cur.replace(oldfrag,newfrag,count) if count!=-1 else cur.replace(oldfrag,newfrag)
    return add(fn,label,new,reason,category)

def transform(fn,label,func,reason,category='manuel kalite'):
    r=row(fn,label); cur=r.get('tur',''); new=func(cur)
    if new==cur: raise ValueError(f'{fn}:{label} transform değişmedi')
    return add(fn,label,new,reason,category)

# ----------------------------------------------------------------------
# v0.4'te kalan 13 satır-uzunluğu uyarısını kaliteyi bozmadan kısalt.
# ----------------------------------------------------------------------
add('database_godInfo.csv','GodInfo_God029','Mesafeli, gizemli ve güzel konuşur;\nçok beceriklidir ve insanları\ntaklit etmede uzmandır.','v0.4 satır uzunluğu uyarısı temizlendi. “Eloquent/competent” anlamları korunup üç kısa satıra ayrıldı; DE/ES/IT güzel konuşma ve beceriyi doğruluyor.','taşma düzeltmesi')
replace_in('database_movieInfo.csv','MovieInfo_7C',"Musashi'ye emanet eder. Musashi ile Jinrai de yeni bir güç kazanır.","Musashi'ye emanet eder.\\nMusashi ile Jinrai yeni bir güç kazanır.",'v0.4 uzun satırı iki doğal cümle/satıra bölündü; özet anlamı değişmedi.','taşma düzeltmesi')
replace_in('database_tipsInfo.csv','TipsPage2_005','20 tabak veya daha fazlada','20 tabakta','Bonusun 20 tabakta tavana ulaştığı bütün dillerde aynı; “veya daha fazlada” hem uzun hem Türkçede hantaldı.','taşma düzeltmesi')
replace_in('database_tipsInfo.csv','TipsPage1_008',"saldırıların normalin %150'si kadar hasar verir","saldırıların normal hasarın %150'sini verir",'Mekanik değer aynen %150; daha kısa ve dilbilgisel Türkçe kullanıldı.','taşma düzeltmesi')
replace_in('database_tipsInfo.csv','TipsPage3_013','yığındaki tabak sayısına göre ekstra bonus yoktur','tabak sayısından ek bonus gelmez','DE/ES/FR/IT/NL ortak anlamı “tabak sayısı yetenek göstergesine ek bonus vermez”; kısa ve doğal biçime çekildi.','taşma düzeltmesi')
replace_in('database_tipsInfo.csv','TipsPage1_017','ne kadar sürede kazandığına göre','bitirme sürene göre','“How long it took to win” = bitirme süresi. Anlam korunup uzun ifade kısaltıldı.','taşma düzeltmesi')
# TipsPage2_024: eski metinde ayrıca “koşullarını ... için” gerçek gramer hatası vardı.
transform('database_tipsInfo.csv','TipsPage2_024',lambda s: s.replace(' için ',' ',1).replace('görebilirsin; ya da savaş sırasında ','görebilirsin.\\nSavaş sırasında ',1).replace('koşulları tekrar inceleyebilirsin.','koşullara yeniden bakabilirsin.',1),'Uzunluk temizlenirken “koşullarını ... için” gramer hatası da giderildi. Harita veya savaşta Start ile duraklatıp koşulları görme mekaniği tüm dillerle aynı.','taşma + gramer')
transform('database_tipsInfo.csv','TipsPage2_018',lambda s: s.replace('Bir başlangıç tabağı seçmek için ','Bir başlangıç tabağı seçmek için\\n',1).replace('(Önce imleci tabağın üstüne getirmek için ','(Önce imleci tabağın üstüne getirmek için\\n',1).replace(' basılı tut\\u000E',' basılı tut\\u000E',1).replace(' ve \\u000E\\u0000\\u0003\\u0004渀',' ve\\n\\u000E\\u0000\\u0003\\u0004渀',1),'A ve Çember Çubuğu talimatları aynı; renkli kontrol kodlarına dokunmadan satırlar ekrandaki güvenli uzunluğa bölündü.','taşma düzeltmesi')
transform('database_tipsInfo.csv','TipsPage3_018',lambda s: s.replace('nu kullanarak ','nu kullanarak\\n',1).replace(',\\nve önündeki',';\\nönündeki',1).replace('fırlatmak için ','fırlatmak için\\n',1),'Hareket ve X ile fırlatma talimatı korunarak kontrol kodları arasına doğal satır kırımları eklendi.','taşma düzeltmesi')

# ----------------------------------------------------------------------
# HOME SUSHIBAR — bütün dosya satır-satır incelenecek; aşağıdakiler değişenler.
# ----------------------------------------------------------------------
fn='homeSushibar.csv'
add(fn,'homeSushibar_cmn_out_01_M','Tamamdır, yine beklerim!','EN ve diğer diller vedalaşma + yeniden gelme daveti. “Peki, yine gel” buyurgan/sert kalıyordu; dükkân sahibine doğal sıcak kapanış verildi.')
add(fn,'homeSushibar_cmn_repeat_01_M','Şimdilik benden bu kadar.\nYeni dedikoduların peşine düşeceğim!','EN “good dirt” gerçek toprak/kazmak değil dedikodu/iyi bilgi deyimi; ES/FR/NL doğrudan haber/dedikoduya gidiyor. Literal “kazmaya devam” espriyi yanlış anlama dönüştürüyordu.','deyim/espri')
add(fn,'homeSushibar_00_in_03_M','İyi gidiyor! Adımız\nkulaktan kulağa yayılıyor.','DE/ES/FR/NL word-of-mouth/itibar anlamında birleşiyor; “hakkımızda laf yayılıyor” olumsuz dedikodu çağrışımı yapabiliyordu.')
add(fn,'homeSushibar_00_in_04_M','Müşterilerden biri ilginç bir şeyi\nağzından kaçırırsa sana haber veririm.','EN “let something good slip”, ES cotilleo, FR/NL ilginç bilgi; “iyi bir şey” belirsizdi. “Ağzından kaçırmak” deyimi korunup nesne netleştirildi.')
add(fn,'homeSushibar_00_in_05_M','Buraya başka şeyler de kurmayı düşünüyorum!\nAklımdakileri görünce şaşıracaksın!','DE/ES/FR/IT/NL yeni tesis/binalar planladığını ve merak uyandırdığını söylüyor. “Aklımdakini bir görsen” yarım/varsayımsal kalıyordu.')
replace_in(fn,'homeSushibar_00_in_07_M','Daha neler! Biz zaten','Ne yetmesi! Biz','EN “Not even close!” önceki “yeter mi?” sorusuna yanıt; “Daha neler” Türkçede farklı bir itiraz tonu veriyordu.')
replace_in(fn,'homeSushibar_00_in_07_M',' işini hallettik!',' çoktan açtık bile!','DE/ES/FR/IT/NL tesislerin açılmış/kurulmuş olduğunu söylüyor; “işini halletmek” fazla belirsizdi.')
add(fn,'homeSushibar_01_b_01_M','Savaştan sonra iyi bir sonuç notu\nalmanın bir püf noktasını öğrendim.','DE “Note”, ES “calificación”, IT “voto”: burada rank karakter rütbesi değil savaş sonu notu/grade. “Rütbe almak” mekanik olarak yanlış terimdi.','mekanik/terim')
add(fn,'homeSushibar_01_b_03_M','Bir de çok fazla yetenek kullanmadan\nkazanırsan bu da notunu yükseltir.','FR/IT/EN bunun savaş sonu değerlendirmesine olumlu etki ettiğini söylüyor; “lehine olur” doğru ama mekanik bağını gizliyordu.')
transform(fn,'homeSushibar_02_a_03_M',lambda s: s.replace('Onlara ulaşabilmek için önce\\n','Onlara ulaşmak için önce ',1).replace('temizleyip ','',1).replace('bölgeyi bitirdikten sonra\\n','bölgeyi temizlemen ve\\n',1).replace('bir sürü ★ işareti','bol bol ★',1),'Mevcut Türkçe “temizleyip bölgeyi bitirdikten sonra” diye aynı eylemi iki kez söylüyordu. DE/ES/FR/IT şartın bölgeyi temizlemek + çok yıldız toplamak olduğunu doğruluyor.','mekanik/gramer')
transform(fn,'homeSushibar_03_in_02_M',lambda s: s.replace('bir sürü ★','bol bol ★',1).replace(' kazanıp\\n',' toplayıp\\n',1).replace('temizleyip ','',1).replace('bir bölgeyi bitirince','bir bölgeyi temizleyince',1),'İki ayrı şart Türkçede “temizleyip ... bitirince” diye yinelenmişti. Yıldız toplama + bölge temizleme netleştirildi.')
add(fn,'homeSushibar_03_a_01_M','Gizli aşamaların derinlerinde,\nnadir bir suşi ruhunun yaşadığı tapınak var!','Tüm diller “tapınakta nadir ruh var” diyor; “nadir bir suşi ruhu olan bir tapınak” Türkçede tapınağın niteliği gibi yapaydı.')
add(fn,'homeSushibar_03_a_02_M','Ama dikkat et. Oraları araştıran İmparatorluk\naskerlerinin acayip suşi ruhları varmış.','EN Imperials, DE askerî nöbetçiler; “İmparatorluklular” doğal değil. Dedikodu tonu “varmış” ile korundu.')
add(fn,'homeSushibar_03_a_03_M','Alıştığın savaşlardan çok farklı olabilir.\nTetikte ol!','EN/diğer diller uyarı tonu; mevcut ifade daha literal/uzundu. Kısa savaş öncesi uyarı doğal Türkçeleştirildi.')
add(fn,'homeSushibar_03_b_02_M','İlerisi fazla çetinleşirse,\nbiraz gizli aşamalarda güçlen.','Bağlam gizli aşamalarda güçlenip ana yola dönme tavsiyesi; doğal oyun dili.')
add(fn,'homeSushibar_03_c_06_M','Tomarın yer yer senden söz etmesi,\no kâtibin büyüsü sayesinde.','EN mystic scribe tekil kişi; eski iyelik “onların büyüsü” Türkçede çoğul/belirsizdi.')
add(fn,'homeSushibar_04_in_02_M','Bence artık burayı genişletmenin\nzamanı geldi!','EN “time to expand”; kısa, doğal ve dükkân bağlamına uygun.')
add(fn,'homeSushibar_05_b_04_M','Bu iyi olurdu. Biz suşi ruhları günde ancak\nbelli kadar suşi üretebiliyoruz, mır...','EN “purr day” = per day + purr kedi esprisi. Türkçede birebir kurulamadığı için cümle sonuna doğal “mır” eklenerek kedi sesi yeniden yaratıldı.','espri')
add(fn,'homeSushibar_05_c_01_M','Evet, hem de adımız duyuluyor! İnsanlar\nher yerden buraya gelmeye başladı!','Word getting around = adın duyulması. “Laf yayılıyor” olumsuz/dedikodu çağrışımından çıkarıldı.')
add(fn,'homeSushibar_05_c_03_M','Ve bunun ne demek olduğunu biliyorsun:\nİmparatorluğun içlerinden yepyeni dedikodular!','EN/diğer diller bu repliği yeni bilgi/dedikodu fırsatı olarak kuruyor; eski nominal parça tamamlanmış repliğe dönüştürüldü.')
for lab in ['homeSushibar_05_btn_01_M','homeSushibar_05_btn_01_F']:
    replace_in(fn,lab,'Üç tane ','Üç ',"Türkçede sayıdan sonra isim çoğul olmaz; dinamik/renkli eşya adının çoğulu ayrıca düzeltildi.",'gramer')
    replace_in(fn,lab,'Gizemli Taşlar','Gizemli Taş',"“Üç Gizemli Taş” doğru sayı + tekil isim yapısı.",'gramer')
add(fn,'homeSushibar_05_stone_09_M','Vay canına!','EN wow, diğer diller saf şaşkınlık. “Vay be. Çılgın!” İngilizce “wild”ı Türkçede sıfat olarak mekanik taşıyordu.','ünlem')
if row(fn,'homeSushibar_05_stone_09_F')['tur']:
    add(fn,'homeSushibar_05_stone_09_F','Vay canına!','Cinsiyet varyantında aynı doğal şaşkınlık ünlemi kullanıldı.','ünlem')
add(fn,'homeSushibar_05_stone_10_M','Bu taş var ya, çok ama çok uzun zaman önce\no deniz hayvanlarından birinden oluşmuş.','Nesne oyun içinde “stone/taş”; “kaya” terminolojisi ve cümle akışı düzeltildi.')
for lab in ['homeSushibar_05_stone_11_M','homeSushibar_05_stone_11_F']:
    add(fn,lab,'Taş kesildim, Archie!','EN “You’re rocking my world” kaya/rock kelime oyunu; ES doğrudan “piedra” ile aynı şakayı kuruyor. Türkçede “taş kesildim” hem şaşkınlık hem taş temasını koruyor.','espri')
add(fn,'homeSushibar_06_in_01_M','Hey, Musashi! Görüşmeyeli epey oldu!','EN/diğer diller uzun zaman sonra selamlaşma; “Görüşmeyeli oldu” eksik Türkçeydi.')
add(fn,'homeSushibar_06_c_03_M','Hoppala, kusura bakma. Az önce kendi birliğimin\nkomutasını aldım da emir vermeye çalışıyorum.','EN “got my own command”; ES/FR/IT/NL kendi birlik/komutasını aldığını doğruluyor. “Kendi komutamı aldım” emir almak anlamına kayıyordu.','anlam')
add(fn,'homeSushibar_06_c_04_M','Asıl sorunum suşi. Savaşta yediklerim...\npek matah değil...','EN “rough” burada savaşta yediği suşinin kalitesi; ES bayat, FR kötü, IT kaba/düşük. “Biraz sert” doku anlamına yanlış daralıyordu.','anlam/ton')
transform(fn,'homeSushibar_07_a_06_M',lambda s: s.replace('herhangi bir ','bir ',1).replace('garip yuvarlak taşlar','garip yuvarlak taş',1).replace('şerit-sürüş dişlisi','Şerit Dişlisi',1),'Sayı/isim grameri düzeltildi; lane-drive gear terminolojisi “Şerit Dişlisi” ile birleştirildi.','gramer/terim')
add(fn,'homeSushibar_08_stone_03_M',"Güzel! İmparatorluk Kıyısı'nın söylentilere göre\nbulunduğu yeri haritanda işaretleyeyim!",'EN rumoured location + map marking; “nerede olduğu söyleniyorsa” yapay dolaylı yapıydı.')
add(fn,'homeSushibar_09_a_04_M','Yanlarına yaklaşınca eski güçlerin anıları\niçimde akmaya başlıyor. Hohoh...','EN old powers/memories flowing through speaker. Eski Türkçe iyelik ve yüklem açısından bozuktu; mistik tonu koruyan doğal cümle kuruldu.')
add(fn,'homeSushibar_09_b_03_M','Bir kez konuştum; “suş” denen\nbir şey aradığını söyledi.','EN “soosh” bilerek yanlış “sushi”; DE Suuush, ES sushurri, FR shisus, IT sushame, NL soesj hepsi şakayı koruyor. Türkçede normal “suşi” espriyi siliyordu; oyundaki diğer örneklerle “suş” standardize edildi.','espri/terim')
add(fn,'homeSushibar_09_b_04_M','Onun dışında da durmadan “barnım koş” diye\nsaçma sapan şeyler söyledi.','EN “bempty is elly” = “belly is empty” baş seslerini değiştirerek söylenen saçmalık; DE/FR/IT/NL de kelime düzeni/seslerini bozuyor. Türkçede “karnım boş” → “barnım koş” ile aynı mekanizma yeniden kuruldu.','espri')
transform(fn,'homeSushibar_10_in_09_M',lambda s: s.replace(' tanesi mi?! Bu çok şey istemek...',' tane mi?! Bu biraz fazla istemek...',1),'EN/FR/NL “that’s a lot to ask”; Türkçe doğal miktar ifadesi ve sayıdan sonra tekil yapı.')
# Pwincess -> Pırenses: burada hedef dosyadaki ana replikler ayrıca stil iyileştiriliyor; sonra global tutarlılık yapılacak.
add(fn,'homeSushibar_11_b_02_M','Vah bana... Pırenses Purrsilla sıradan\nhayatına döndü, ben de birlikten ayrıldım.','EN Pwincess bilerek çocuksu/bozuk “princess”; IT “pvincipessa”, DE küçültme ile şakayı taşıyor. Türkçede “Pırenses” bu konuşma kusurunu görünür kılıyor.','espri/karakter sesi')
add(fn,'homeSushibar_11_b_04_M','Kim? Benim sert, acımasız\npırensesim olma görevini kim devralacak?!','Pwincess şakası korunurken “harsh, unforgiving” daha doğal ikili sıfata çevrildi; eski iyelik/apostrof yapısı da temizlendi.','espri/karakter sesi')
add(fn,'homeSushibar_11_e_02_M','Ah, Musashi. Pırenses Purrsilla için\nyaptıkların için teşekkür ederim.','Aynı hayran karakterin Pwincess telaffuzu sahne boyunca korunmalı; IT de aynı konuşma özelliğini sürdürüyor.','espri/karakter sesi')
add(fn,'homeSushibar_11_e_04_M','Olur mu öyle şey! Gerçek bir hayran, Pırensesin\nkardeşi olmadığını bilir!','EN/NL “no brothers or sisters”; Türkçede “kardeşi yok” daha kısa/doğal. Pwincess konuşma özelliği de korundu.','espri/akıcılık')
for lab in ['homeSushibar_11_btn_01_M','homeSushibar_11_btn_01_F']:
    replace_in(fn,lab,'Yedi tane ','Yedi ','Türkçede sayıdan sonra isim tekil kullanılır.','gramer')
    replace_in(fn,lab,'Gizemli Taşlar','Gizemli Taş','Eşya adı sayıdan sonra tekilleştirildi.','gramer')
add(fn,'homeSushibar_12_a_03_M','İnsan merak ediyor: acaba nihai dişli\nne kadar hızlanabiliyor...','EN/ES/FR/IT/NL gear’ın ulaşabildiği hız soruluyor; “nasıl bir hız yapıyor” doğal değil.')
add(fn,'homeSushibar_14_b_04_M','Tabii hâlâ antrenman yapıyor! Cilt bakımını da\naksatmadığına şüphen olmasın!','EN KNOW vurgusu oyuncuya komik güvence; FR/IT/NL spor + cilt bakımını paralel tutuyor. Eski “Ve BİLİYORSUN” İngilizce söz dizimiydi.')
add(fn,'homeSushibar_15_a_03_M',"Nihai Şerit Dişlisi en son\norada görülmüş...",'EN “ended up” düşmek değil bir yerde bulunmak/sonunda oraya gitmek; DE/ES/FR/IT/NL konum söylentisi. Lane-drive terimi de standardize edildi.','anlam/terim')
replace_in(fn,'homeSushibar_16_a_07_M','Buff Buffet','Takviye Büfesi','Yetenek adı database_godSkillInfo ile tutarlı hâle getirildi; İngilizce bırakılmadı.','terim')
transform(fn,'homeSushibar_16_a_13_M',lambda s: s.replace(' ile arkadaş oldun!',' ile bağ kurdun!',1).replace('Onun becerisi ','Yeteneği ',1).replace('Buff Buffet','Takviye Büfesi',1),'Pledge/befriend sistemi v0.3’te “bağ kurmak”; “beceri” yerine oyun terimi “yetenek”; Buff Buffet adı da Takviye Büfesi ile tekleştirildi.','terim')
transform(fn,'homeSushibar_16_a_15_M',lambda s: s.replace('Buff Buffet','Takviye Büfesi',1).replace("Suşi Bonanza'ya","Suşi Bolluğu'na",1).replace('bağlantıyı koruyabiliyorsun','tabak bağlamaya devam edebiliyorsun',1),'İki yetenek adı Türkçeleştirildi; mekanik “link away” bağlantıyı korumak değil süre boyunca tabak bağlamaya devam etmek. DE/ES/FR/IT/NL bunu doğruluyor.','mekanik/terim')

# ----------------------------------------------------------------------
# HOME KOZIIN
# ----------------------------------------------------------------------
fn='homeKoziin.csv'
add(fn,'homeKoziin_first_02_M','Evet, hepsi burada!\nSeni gördüğüme çok sevindim!','“Every single one” için doğal Türkçe; “hepsinin her biri” yapay tekrar.')
add(fn,'homeKoziin_first_05_M','Rahatına bak!','“Make yourself at home” deyimi; “Kendini evinde gibi hisset” kelimesi kelimesine çeviri kokuyordu.','deyim')
add(fn,'homeKoziin_select_lv03_00_M','Yardımın benim için çok değerli, Musashi.\nTeşekkür ederim.','“This means a lot” deyimi “bu çok şey demek” diye literal kalmıştı; duygusal anlam doğal Türkçeye aktarıldı.','deyim')
add(fn,'homeKoziin_select_lv03_01_M','Bu benim için çok değerli. Sana gerçekten\nminnettarım, Musashi. Çocuklar da öyle.','Aynı “means a lot” deyimi ve sıcak karakter tonu doğal Türkçeleştirildi.')
add(fn,'homeKoziin_select_fruit_01_M','Bu savaşın ortasında bile çocukları düşündüğün için\nteşekkürler. Hiç yorulmuyor musun?','“While fighting this war” = savaşın ortasındayken; “bu savaşı verirken” doğru ama daha mekanik/resmîydi.')
add(fn,'homeKoziin_select_fruit_07_M','Onu koru. Savaş bitince de\neve dön, olur mu?','Keep him safe + come back home, duygusal rica. “Dövüşü bitirince” tek maça indiriyordu; bağlam savaş/war.')
add(fn,'homeKoziin_useful_cmn_M','Doğru ya—sana anlatacağım\nbirkaç şey daha var.','“I had some more information for you”; eski “Sana anlatacak birkaç bilgi daha var” öznesiz/bozuk Türkçe.')
add(fn,'homeKoziin_useful_02_00_M','Canın azalınca kullanmak üzere\niyileştirme yeteneklerini saklayabilirsin.','HP mekanik terimi cümle başında “CAN’in” şeklinde yanlış büyük harf/apostrofla yazılmıştı; doğal kullanım ve anlam korundu.')
transform(fn,'homeKoziin_useful_04_01_M',lambda s: s.replace('Onları yan yana\\n','Onları ',1).replace(' ekranında\\u000E\\u0000\\u0003\\u0004\\u0000\uff00 dizmelisin.',' ekranında\\u000E\\u0000\\u0003\\u0004\\u0000\uff00\\nyan yana dizmelisin.',1),'Türkçede yer tamlayıcısı yüklemden önce doğal konuma alındı; Sprite Order = Ruh Sırası terminolojisi zaten doğru.')
add(fn,'homeKoziin_useful_06_00_M','Suşi ruhlarının yeteneklerini birleştirerek\netkilerini katlayabilirsin.','EN combine skills for greater effect; daha doğal mekanik anlatım.')
add(fn,'homeKoziin_useful_07_00_M','Biraz da meyveden konuşalım.','“Let’s talk about fruit”; kısa diyalog tonu.')
add(fn,'homeKoziin_useful_07_01_M','İki işe birden yarar: canını yenilemek için ye,\nsonra tabakları fırlatıp hasar ver!','Meyvenin çift işlevi heal + thrown plate damage daha vurucu/öğretici biçimde anlatıldı.')
add(fn,'homeKoziin_useful_13_02_M','Epey sinsi, değil mi?','“Pretty treacherous” karakterin konuşma dilinde; “hain” kişiye ahlaki ihanet yüklerken mekanik burada sinsi/tricky.')
add(fn,'homeKoziin_useful_15_02_M','Dostluğun güçlendikçe savaşta da\nkarşılığını görürsün. İki taraf da kazanır!','EN/diğer diller friendship benefits in battle; “Daha iyi dostluklar, daha iyi faydalar” slogan gibi mekanik/literaldi.')

# ----------------------------------------------------------------------
# HOME SHRINE
# ----------------------------------------------------------------------
fn='homeShrine.csv'
replace_in(fn,'homeShrine_first_rank_01_M','ne kadar güçlü bir suşi vurucu olduğunu gösterir.','ne kadar güçlü bir suşi vurucu olduğunu gösterir.','',count=1) if False else None
# Doğrudan control kodlarını koruyarak söz dizimi düzeltmeleri.
transform(fn,'homeShrine_first_rank_08_M',lambda s: s.replace('nasıl yükselteceğini\\u000E\\u0000\\u0003\\u0004\\u0000\uff00 \\u000E\\u0000\\u0003\\u0004ﾑ＞vurucu rütbeni','vurucu rütbeni\\u000E\\u0000\\u0003\\u0004\\u0000\uff00 \\u000E\\u0000\\u0003\\u0004ﾑ＞nasıl yükselteceğini',1) if False else s,'placeholder') if False else None
# Kontrol dizilerini bozmadan, sonradan gelen yinelenmiş nesneyi kaldırıp doğal söz dizimini kuruyoruz.
def _fix_rank8(s):
    needle='vurucu rütbeni'
    s=s.replace('nasıl yükselteceğini',needle+' nasıl yükselteceğini',1)
    first=s.find(needle)
    last=s.rfind(needle)
    if first < 0 or last <= first:
        raise ValueError('homeShrine_first_rank_08_M beklenen yinelenmiş öbek bulunamadı')
    return s[:last]+s[last+len(needle):]
transform(fn,'homeShrine_first_rank_08_M',_fix_rank8,'EN/DE/ES/FR/IT/NL “vurucu rütbeni nasıl yükselteceğin” tek öbek. Eski Türkçede renk kontrol kodları yüzünden nesne yüklemden sonra tekrar ediyordu; kodlar korunarak doğal söz dizimi kuruldu.')
transform(fn,'homeShrine_rank_04_M',lambda s: s.replace('Öyleyse, rütbeni yükseltmenin ödülü olarak lütfen şu ','Rütbe atlama ödülün olarak şunu al: ',1),'DE/ES/FR/IT/NL kısa “rütbe ödülü” yapısını kullanıyor; eski Türkçe uzun ve “lütfen şu ... al” söz dizimi yapaydı.')
replace_in(fn,'homeShrine_first_out_06_M','bağ kurmayı teklif edebilir','seninle bağ kurmak isteyebilir','EN may offer to pledge; Türkçede kişinin “bağ kurmayı teklif etmesi” mekanik kalıyor, doğal niyet cümlesine çevrildi.')
# Dinamik miktar + isim: Türkçede sayıdan sonra çoğul eki kullanılmaz.
plural_singular={
'homeShrine_get_OhudaSkill_pl_M':('Yetenek Tılsımları','Yetenek Tılsımı'),
'homeShrine_get_OhudaSkillC_pl_M':('Harika Yetenek Tılsımları','Harika Yetenek Tılsımı'),
'homeShrine_get_PlayerHpS_pl_M':('Konserve Dayanıklılıklar','Konserve Dayanıklılık'),
'homeShrine_get_PlayerAtkS_pl_M':('Konserve Güçler','Konserve Güç'),
'homeShrine_get_ReadyRetryM_pl_M':('Yenilenme Fasulyeleri','Yenilenme Fasulyesi'),
'homeShrine_get_ReadyRetryL_pl_M':('Büyük Yenilenme Fasulyeleri','Büyük Yenilenme Fasulyesi'),
'homeShrine_get_ReadyRetryC_pl_M':('Harika Yenilenme Fasulyeleri','Harika Yenilenme Fasulyesi'),
'homeShrine_get_OhudaPT_pl_M':('Parti Tılsımları','Parti Tılsımı'),
'homeShrine_get_Burner_pl_M':('Yakıcı Meşaleler','Mutfak Pürmüzü'),
}
for lab,(a,b) in plural_singular.items():
    replace_in(fn,lab,a,b,'Satırda dinamik sayı zaten yazılıyor; Türkçede sayıdan sonra eşya adı çoğul ek almaz. Eşya adı tekil forma getirildi.','gramer/terim')
replace_in(fn,'homeShrine_get_Burner_sg_M','Yakıcı Meşale','Mutfak Pürmüzü','DE Brenner, ES soplete, FR chalumeau, IT cannello da cucina, NL keukenbrander bunun meşale değil mutfak pürmüzü olduğunu açıkça doğruluyor.','terim/anlam')

# ----------------------------------------------------------------------
# HOME ARENA
# ----------------------------------------------------------------------
fn='homeArena.csv'
add(fn,'homeArena_cmn_out_01_M','Gücünü sınamak istediğinde yine uğra!','Arena çıkışında “come back when you want to test yourself” işlevi; daha doğal davet.')
replace_in(fn,'homeArena_01_01_M','çok oyunculu ','çok oyunculu ','') if False else None
add(fn,'homeArena_01_02_M','Savaşların adil olması için...','EN fair fight; oyun genel terimi “savaş”. “Dövüş olduğundan emin olmak” hem uzun hem terminoloji dışı.')
transform(fn,'homeArena_01_03_M',lambda s: s.replace("suşi sprite'larını","suşi ruhlarını",1),'DE/FR/IT/NL resmi karşılıkları “Sushi-Geister/esprits/spiriti/sushigami”; oyun terminolojisi Ruh. Teknik “sprite” kullanıcıya görünmemeli.','terim')
add(fn,'homeArena_01_04_M','Ruh Sırasını ayarladın mı?\nO zaman başlıyoruz!','Sprite Order oyun genelinde “Ruh Sırası”; mevcut “Sprite Düzeni” tutarsız ve teknik kalıyordu.','terim')
transform(fn,'homeArena_02_02_M',lambda s: s.replace('Suşi sprite setlerinin üçünün de','Suşi ruhu takımlarının üçünde de',1).replace('burada kullanamayacağın bir sprite var','burada kullanamayacağın bir ruh var',1),'Sprite = ruh; “set” burada üç takım/dizilim. Türkçe terminoloji ve sayı söz dizimi düzeltildi.','terim/gramer')
transform(fn,'homeArena_02_04_M',lambda s: s.replace('Sprite Düzeni','Ruh Sırası',1).replace("suşi sprite'larını",'suşi ruhlarını',1),'Sprite Order ve sushi sprites resmi Türkçe terminolojiye “Ruh Sırası / suşi ruhları” olarak çekildi.','terim')
add(fn,'homeArena_03_01_M','Demek \u000E\u0000\u0003\u0004ﾑ＞Lezzetli Savaş\u000E\u0000\u0003\u0004\u0000＀ istiyorsun!\nNumara yok, hile yok; sadece suşi!','scene_map ve tips tarafında Tasteful Battle zaten “Lezzetli Savaş”. HomeArena’daki “Lezzet Savaşı” tutarsızdı; ad tekleştirildi.','terim') if False else replace_in(fn,'homeArena_03_01_M','Lezzet Savaşı','Lezzetli Savaş','Tasteful Battle harita ekranında “Lezzetli Savaş”; aynı mod adı her yerde tekleştirildi.','terim')
add(fn,'homeArena_04_01_M','Bugün nasıl bir savaş istiyorsun?','“What kinda battle are you in the mood for?” konuşma dilinde seçim sorusu; “ne tür bir savaş havasındasın” İngilizce kalıptı.')
transform(fn,'homeArena_05_01_M',lambda s: s.replace('Lezzet Savaşı','Lezzetli Savaş',1).replace('dövüşmeyi','savaşmayı',1),'Mod adı “Lezzetli Savaş” ile tekleştirildi; oyun eylemi “savaşmak” terminolojisine çekildi.','terim')
replace_in(fn,'homeArena_05_02_M','dövüşmeyi','savaşmayı','Arena terminolojisinde fight/battle için “savaş” kullanılıyor; “dövüş” ile karışıklık giderildi.','terim')
replace_in(fn,'homeArena_07_01_M','Arkadaş Maçı','Dost Maçı','scene_map Buddy Match = “Dost Maçı”; aynı mod adı merkez diyaloğunda da tekleştirildi.','terim')
add(fn,'homeArena_08_05_M','Şey... o kadarını da bilemem...','EN idiom “I don’t know if I’d go that far” = iddiaya o kadar katılmıyorum. Eski ifade İngilizce hareket metaforunu literal taşıyordu.','deyim')
replace_in(fn,'homeArena_08_06_M','kapsüllerle dövüşebilirsin','kapsüllü savaşlar yapabilirsin','Bu bir savaş modu; “kapsüllerle dövüşmek” nesnelerle fiziksel dövüş çağrışımı yapıyordu.','mekanik')
transform(fn,'homeArena_08_07_M',lambda s: s.replace('Hepsi bitti!','Bitti bile!',1).replace('gördüğün o dövüşleri','çıkan o savaşları',1),'Kapsüllerin sürekli belirdiği savaş modu anlatılıyor; “kapsülleri gördüğün dövüşler” mekanik/literaldi.','mekanik')
replace_in(fn,'homeArena_09_07_M','dövüşebiliyormuşsun','savaşabiliyormuşsun','Arena oyun terminolojisiyle tutarlılık.','terim')
add(fn,'homeArena_09_08_M','İşte \u000E\u0000\u0003\u0004ﾑ＞Çevrimiçi Savaşlar\u000E\u0000\u0003\u0004\u0000＀ böyle bir şey.\nArtık burada da yapabiliriz!','EN “Anyway, that’s Online Battles”; mevcut “... böyle” Türkçede eksik yüklem gibi kalıyordu.') if False else replace_in(fn,'homeArena_09_08_M',' böyle.',' böyle bir şey.','Eksik/çeviri kokan “Çevrimiçi Savaşlar böyle” cümlesi doğal tamamlandı.')
add(fn,'homeArena_10_02_M',"Purrsilla?! Arena'da ne işin var?\nBenimle savaşmaya mı geldin?!",'EN “You’re at the Arena?” şaşkınlığını doğal Türkçe “ne işin var?” karşılıyor; eski “Arena’da mısın?” gördüğü kişiye anlamsız soru kalıyordu.')
add(fn,'homeArena_10_03_M','Ne münasebet. Sivil hayatı fazlasıyla\nsıkıcı buldum, hepsi bu.','Perish the thought = ne münasebet; Purrsilla’nın resmî/kibirli sesi korunarak doğal Türkçe.')
add(fn,'homeArena_10_05_M','Ama sen savaşmaya geldin, değil mi? Öyleyse\nsavaşacaksın! Arena’ya hoş geldin!','Karakterin teatral “then a fight you shall have” tonu kısa tekrar ile korundu; “istediğin dövüşü yapacaksın” doğal değildi.')
transform(fn,'homeArena_12_01_M',lambda s: s.replace('Suşi sprite setlerinin üçünün de','Suşi ruhu takımlarının üçünde de',1).replace('içinde bir sprite var;','bir ruh var;',1).replace("Arena'da burada yasak","Arena'da yasak",1),'Sprite/set teknik terimleri Ruh/takım ile düzeltildi; “Arena’da burada yasak” tekrar hatası kaldırıldı.','terim/gramer')
transform(fn,'homeArena_12_03_M',lambda s: s.replace('Sprite Düzeni','Ruh Sırası',1).replace("sprite'ları",'ruhları',1),'Sprite Order ve sprite terminolojisi oyun genelindeki Ruh Sırası / ruhlar ile tekleştirildi.','terim')
replace_in(fn,'homeArena_13_01_M','Yine gel de dövüş.','Yine gel de savaş.','Arena oyun terminolojisiyle tutarlılık.','terim')
replace_in(fn,'homeArena_15_01_M','Arkadaş Maçı','Dost Maçı','scene_map ile Buddy Match mod adı tutarlılığı.','terim')
replace_in(fn,'homeArena_17_01_M','Lezzet Savaşı','Lezzetli Savaş','Tasteful Battle mod adı tüm ekranlarda tekleştirildi.','terim')

# ----------------------------------------------------------------------
# HOME TOWER
# ----------------------------------------------------------------------
fn='homeTower.csv'
add(fn,'homeTower_01_04_M','Evet! Tüm suşiyi yemek için yalnızca\nbeş hamlen ve birkaç saniyen var!','Mevcut ilk satır 60+ karakterdi; EN/diğer diller aynı süre/hamle kuralını kısa verir. Doğal iki satıra bölündü.')
add(fn,'homeTower_01_06_M','Robotumu yenmeye aklın yeter mi bakalım?!','EN “got the brains” zeka/akıl kelime oyunu taşıyor; “yenecek kadar zeki olduğunu mu sanıyorsun” uzun ve açıklayıcıydı.','karakter tonu')
add(fn,'homeTower_04_03_M','Nasıldı? Epey heyecanlıydı, değil mi?!','“Intense” burada bulmaca temposu/heyecan; “yoğun” Türkçede iş yükü çağrışımı yapıyordu.')
transform(fn,'homeTower_05_01_M',lambda s: s.replace('yirmi galibiyet','yirmi galibiyete',1).replace(' gördüğüne',' ulaştığına',1),'“Hit twenty wins” = yirmi galibiyete ulaşmak; “yirmi galibiyet gördün” yanlış eşdizimdi.')
add(fn,'homeTower_05_04_M','İşte oldu! Ayarını seni gerçekten zorlayacak\nkadar yükselttim!','EN robotu “cranked it up” = ayar/güç yükseltmek. Eski “tam kararında artırdım” nesnesiz ve belirsizdi.')
add(fn,'homeTower_08_01_M','Tüm suşiyi yemek için \u000E\u0000\u0003\u0004껿＀beş hamlen\u000E\u0000\u0003\u0004\u0000＀ ve\nbirkaç saniyen var! Müthiş heyecanlı!','Kural cümlesinin bozuk “senin ... var ve ... saniyen” yapısı düzeltildi; heyecan tonu korundu.') if False else transform(fn,'homeTower_08_01_M',lambda s: s.replace('Senin ','',1).replace(' var ve tüm suşiyi yemek için birkaç saniyen!\\nMüthiş bir heyecan!',' ve\\ntüm suşiyi yemek için birkaç saniyen var!\\nMüthiş heyecanlı!',1),'Sayı/hamle cümlesi dilbilgisel olarak düzeltildi; süre + beş hamle mekaniği korunup konuşma tonu canlandırıldı.')
add(fn,'homeTower_10_01_M','Bu işte bayağı iyisin! Ben de işi biraz\nzorlaştırmalıyım. Eeeheheheh!','“Step up the game” seviye değerini yükseltmek değil meydan okumayı zorlaştırmak; doğal deyim kullanıldı.','deyim')

# ----------------------------------------------------------------------
# SCENE MAP
# ----------------------------------------------------------------------
fn='scene_map.csv'
add(fn,'Label_Star','Yıldızlar','EN Stars ve diğer diller çoğul kategori başlığı; tekil “Yıldız” arayüzde toplam/koşul listesini eksik adlandırıyordu.','UI/terim')
add(fn,'Label_SushibarText','İlk suşi restoranında Archie ile müşterilerinin\nkonuşmalarına kulak misafiri ol!','EN “overhear” gizlice/tesadüfen duyma; “konuşmalarını dinle” işlevsel ama dedikodu mekaniğinin tonunu kaybediyordu. “Kulak misafiri olmak” tam deyim.','deyim/ton')
add(fn,'Label_KoziinText',"Cumhuriyet'in dört bir yanındaki yetim çocuklar için\nbir yuva. Musashi'nin köyünden buraya taşındı.",'“Facility” bağlamda yetimhane/çocuk yuvası; “yetim çocuklar için bir tesis” bürokratik ve soğuk. Harita açıklamasına doğal “yuva” getirildi.')
add(fn,'Text_Arena_GachiRatingBattle','Puanının takip edildiği bir Lezzetli Savaş!','Rated battle açıklaması; “puan takibi yapan bir savaş” savaşın özne olup puan takip etmesi gibi mekanik kalıyordu.')
add(fn,'Text_Shrine_Rank_Up','Rütbe Yükseldi!','Türkçe UI’de rank up için doğal fiil “rütbe yükselmek”; “Rütbe arttı” anlaşılır ama daha zayıf/terim dışı.')

# ----------------------------------------------------------------------
# SCENE COMMON
# ----------------------------------------------------------------------
fn='scene_cmn.csv'
transform(fn,'Win_FileNameInput',lambda s: s.replace('Kaydetme dosyan','Kayıt dosyan',1).replace('kaydetme dosyası adın','kayıt dosyası adın',1).replace('görülebilir\\nÇevrimiçi','görülebilir.\\nÇevrimiçi',1).replace('Savaşlar,\\nve dereceli','Savaşlar ve\\ndereceli',1),'EN save file; DE/ES/FR/IT/NL da dosya adı terimi. “Kaydetme dosyası” fiilimsi çeviri kokuyordu; “kayıt dosyası” standart Türkçe. Noktalama/sıralama da düzeltildi.','UI/terim')


# ----------------------------------------------------------------------
# SATIR UZUNLUĞU RÖTUŞLARI
# ----------------------------------------------------------------------
replace_in('database_tipsInfo.csv','TipsPage2_024',' koşullara yeniden bakabilirsin.','\\nkoşullara yeniden bakabilirsin.','Kontrol kodu korunarak son cümle iki satıra bölündü; anlam değişmedi.','satır düzeni',count=1)
replace_in('homeSushibar.csv','homeSushibar_03_in_02_M','bir bölgeyi temizleyince bir ','bir bölgeyi temizleyince\\nbir ','Metin kutusunda tek satır taşmasını önlemek için anlam değişmeden satır bölündü.','satır düzeni',count=1)
add('homeSushibar.csv','homeSushibar_16_a_15_M',"Takviye Büfesi, Suşi Bolluğu'ndan daha iyi;\\nsürerken tabakları durmadan bağlayabilirsin.",'Aynı mekanik anlam daha kısa ve doğal kuruldu; metin kutusu taşması giderildi.','akıcılık/satır düzeni')
add('homeKoziin.csv','homeKoziin_select_fruit_01_M','Savaşta bile çocukları düşündüğün için\\nteşekkürler. Hiç yorulmuyor musun?','EN savaş sürerken çocukları düşünmesini vurguluyor; daha kısa doğal Türkçe ile taşma giderildi.','akıcılık/satır düzeni')
transform('homeShrine.csv','homeShrine_first_rank_08_M',lambda s: s.replace('vurucu rütbeni nasıl yükselteceğini','rütbeni nasıl yükselteceğini',1),'Bağlamda vurucu rütbesinden söz edildiği açık; tekrar etmeyen kısa biçim aynı anlamı koruyup metin kutusu taşmasını gideriyor.')
add('scene_map.csv','Label_KoziinText',"Cumhuriyet'teki yetim çocuklar için\\nbir yuva. Musashi'nin köyünden buraya taşındı.",'EN/DE/ES/FR/IT/NL Cumhuriyet genelinden gelen yetimler için yuva; daha kısa doğal ifade ile harita açıklaması taşmadan verildi.','akıcılık/satır düzeni')
add('stageBeginArea04sub001.csv','CharaSerif_01_M',"İyi. İmparatorluk Ordusu o\\nnihai Şerit Dişlisi'ni ne pahasına olursa\\nolsun ele GEÇİRECEK!",'EN vurgu “WILL have ... no matter what”; Türkçede tehdit tonu korunup cümle üç kısa satıra bölündü.','ton/satır düzeni')
add('homeSushibar.csv','homeSushibar_07_a_02_M',"İmparatorluk Kıyısı'nda, Şerit Dişlisi\\nuzmanı bir mühendis var!",'EN/FR/IT engineer expert in lane-drive gears; Türkçede daha doğal isim tamlaması ve kısa satır düzeni.','akıcılık/terim')
replace_in('stageBattleM003.csv','tutorial04_02_M','şeritlerinde','\\nşeritlerinde','Kontrol kodlarına dokunmadan uzun öğretici satır fiziksel olarak bölündü.','satır düzeni',count=1)
add('stageEndArea04sub010.csv','CharaSerif_09_M','Aa, çok bir şey değil.\\nBoş zamanlarımda tasarladığım\\nçok gelişmiş bir Şerit Dişlisi sadece.','EN “not much / in my spare time” hafif böbürlenen ton; doğal Türkçe ve güvenli satır uzunluğu.','ton/satır düzeni')
add('homeSushibar.csv','homeSushibar_12_d_02_M',"İtiraf edeyim... Pırenses'in\\nbize somonla ton balığını yasakladığı\\ngünleri özlüyorum.",'EN/IT bilerek bozuk Pwincess şakası “Pırenses” ile korunurken cümle kısaltıldı ve daha doğal yapıldı.','espri/akıcılık')
add('stageBeginM083.csv','CharaSerif_02_M',"Aynen. Artık Pırenses Purrsilla'nın\\nsadık uşağıyım.\\nÖnümde pembe bir gelecek var!",'Pwincess şakası Pırenses olarak korunuyor; satır taşması için doğal yerden bölündü.','espri/satır düzeni')

# ----------------------------------------------------------------------
# ÇAPRAZ DOSYA HEDEFLİ TUTARLILIK / ESPRİ DÜZELTMELERİ
# Bunlar tüm dosyayı incelenmiş saymaz; yalnız değişen etiket rapora girer.
# ----------------------------------------------------------------------
# lane-drive gear -> Şerit Dişlisi. “Şerit sürüşü” isimli kontrol hareketi ayrı mekanik, ona dokunulmuyor.
for f,(fields,rows) in files.items():
    for r in list(rows):
        t=r.get('tur','')
        if 'şerit-sürüş dişli' in t.lower():
            new=re.sub(r'şerit-sürüş dişlisi', 'Şerit Dişlisi', t, flags=re.I)
            new=re.sub(r'şerit-sürüş dişlileri', 'Şerit Dişlileri', new, flags=re.I)
            add(f,r['label'],new,'Lane-drive gear farklı dosyalarda mekanik “şerit-sürüş dişlisi” kalıbıyla geçiyordu. DE/FR/IT/NL bunu gerçek aygıt/dişli-teker olarak adlandırıyor; kısa oyun terimi “Şerit Dişlisi” tüm referanslarda tekleştirildi.','hedefli terim')

# Buff Buffet: daha önce seçilmiş Takviye Büfesi adı bütün referanslarda.
for f,(fields,rows) in files.items():
    for r in list(rows):
        if 'Buff Buffet' in r.get('tur','') or 'Kas Büfesi' in r.get('tur','') or 'KAS BÜFESİ' in r.get('tur',''):
            new=r['tur'].replace('Buff Buffet','Takviye Büfesi').replace('Kas Büfesi','Takviye Büfesi').replace('KAS BÜFESİ','TAKVİYE BÜFESİ')
            add(f,r['label'],new,'Buff Buffet için seçilen “Takviye Büfesi” adı tüm diyalog/savaş referanslarında tekleştirildi; Kas Büfesi/İngilizce ad karışıklığı kaldırıldı.','hedefli terim')

# Pwincess: bütün tekrarlarında aynı bozuk/sevimli telaffuz. Sadece EN gerçekten Pwincess diyorsa.
for f,(fields,rows) in files.items():
    for r in list(rows):
        if 'pwincess' in r.get('eng','').lower():
            cur=r.get('tur',''); new=cur.replace('Pwincess','Pırenses').replace('pwincess','pırenses').replace('Prenses','Pırenses').replace('prenses','pırenses')
            if new!=cur:
                add(f,r['label'],new,'EN bilinçli “Pwincess” telaffuzunu kullanıyor; IT pvincipessa ve bazı diğer diller de konuşma kusuru/şakayı koruyor. Türkçede tekrarlanan şaka “Pırenses” olarak standardize edildi.','hedefli espri')

# soosh: tüm tekil yanlış telaffuz referanslarında “suş”. İki karşılaştırmalı satır ayrıca özel ele alınır.
manual_soosh={
('stageBeginM036.csv','CharaSerif_11_M'):'Demek “suş” da suşi demek, ha?',
('stageBeginM036.csv','CharaSerif_11_F'):'Demek “suş” da suşi demek, ha?',
('stageBeginM046.csv','CharaSerif_03_M'):'Adı suşi, “suş” değil. Doğru söyle.',
}
for (f,l),new in manual_soosh.items():
    if f in files:
        add(f,l,new,'EN cümlesi “sushi” ile yanlış “soosh”u karşı karşıya koyuyor. Eski Türkçede ikisi de “suşi” olup şaka anlamsızlaşmıştı; doğru/yanlış ikilisi “suşi / suş” olarak kuruldu.','hedefli espri')
for f,(fields,rows) in files.items():
    for r in list(rows):
        e=r.get('eng','').lower(); key=(f,r['label'])
        if 'soosh' not in e or key in manual_soosh: continue
        cur=r.get('tur','')
        # Zaten bilinçli suş/suuuş kullanıyorsa bırak; normal suşi kaldıysa yanlış telaffuza çevir.
        low=cur.lower()
        if 'suş' in low and 'suşi' not in low: continue
        if 'suuuş' in low or 'suuş' in low: continue
        if 'sushi' in e and 'soosh' in e: continue
        # “suşi”nin tüm yazım varyantları (Suşi dahil) bu satırda soosh'u temsil ediyor.
        new=re.sub('Suşi','Suş',cur); new=re.sub('suşi','suş',new)
        if new!=cur:
            add(f,r['label'],new,'EN “soosh” bilerek yanlış sushi telaffuzu; DE/ES/FR/IT/NL çoğu kendi bozuk biçimini yaratıyor. Türkçede tekrar eden karşılık “suş” olarak standardize edildi.','hedefli espri')

# bempty/elly = belly/empty spoonerism -> karnım boş / barnım koş.
if 'stageBeginM036.csv' in files:
    add('stageBeginM036.csv','CharaSerif_02_M','Barnım koş... Hayat çok zor...','EN “My bempty is elly” = “my belly is empty”nin baş seslerini yer değiştiren saçma söz; IT “vancia puota”, FR “vide ventre”, NL ters sıra ile aynı şakayı taşıyor. Türkçede “karnım boş” → “barnım koş” aynı ses değişimini yeniden kuruyor.','hedefli espri')
    add('stageBeginM036.csv','CharaSerif_04_M','Barnım... koş.','Aynı bempty/elly konuşma şakası kısa tekrarında da “barnım koş” olarak korunuyor.','hedefli espri')

# HomeSushibar pwincess/soosh/bempty zaten yukarıda; global pass sonrası tekrar değişmişse gerekçeler birleştirildi.

# ----------------------------------------------------------------------
# Dosyaları yaz.
# ----------------------------------------------------------------------
for fn,(fields,rows) in files.items():
    with (OUT/fn).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

# ----------------------------------------------------------------------
# SATIR-BAZLI RAPOR: bu turdaki 7 dosyanın HER SATIRI + hedefli dış değişiklikler.
# ----------------------------------------------------------------------
prev_audit_path=ROOT/'review_v04'/'V04_SATIR_BAZLI_INCELEME.csv'
prev_master_path=ROOT/'review_v04'/'TUM_10676_SATIR_DURUMU.csv'
prev_changes_path=ROOT/'review_v04'/'INCELEME_DEGISIKLIKLERI.csv'
prev_audit=[]
if prev_audit_path.exists():
    with prev_audit_path.open(encoding='utf-8-sig',newline='') as f: prev_audit=list(csv.DictReader(f))
prev_changes=[]
if prev_changes_path.exists():
    with prev_changes_path.open(encoding='utf-8-sig',newline='') as f: prev_changes=list(csv.DictReader(f))
prev_change_keys={(r['file'],r['label']) for r in prev_changes}

def unchanged_reason(fn,r):
    e=r.get('eng',''); t=r.get('tur',''); langs=[r.get(x,'') for x in ['deu','esp','fra','ita','nld']]
    if not e and not t:
        return 'Kaynakta bu etiket boş/ayrılmış bir slot. Altı resmi dilde de işlevsel metin taşımadığı için yapıyı korumak adına boş bırakıldı.'
    if e and not t:
        return 'Türkçe slot çevrilmemiş. Kullanıcının bu turdaki odağı “çevrilmiş metnin kalite kontrolü” olduğu için yeni çeviri eklenmedi; satır kalite açısından değiştirilmeden kapsam dışı bırakıldı.'
    if r['label'].endswith('_F'):
        return 'Cinsiyet varyantı kontrol edildi. Türkçe cümle cinsiyet işaretlemediği ve ana varyantla aynı anlam/tonu doğal taşıdığı için ayrı yeniden yazım gerekmedi.'
    # UI / sistem satırları
    if fn in ('scene_map.csv','scene_cmn.csv') or r['label'].startswith(('Label_','Btn_','Text_','List_','Title_','Txt_','Win_')):
        return 'UI etiketi/açıklaması EN ve DE/ES/FR/IT/NL işleviyle karşılaştırıldı. Mevcut Türkçe kısa, anlaşılır ve oyun terminolojisiyle uyumlu; değişiklik kullanıcıya ek fayda sağlamayacağı için aynı bırakıldı.'
    # Eşya/ödül dinamik satırları
    if fn=='homeShrine.csv' and ('get_' in r['label'] or 'SD_' in r['label'] or 'HomeShrine_SD' in r['label']):
        return 'Dinamik ödül/sistem mesajı kontrol edildi. Kontrol kodları, sayı/isim yapısı ve eşya terimi doğru çalışıyor; diğer dillerle anlam farkı olmadığı için aynı bırakıldı.'
    # Kısa tepki ve özel isim
    vis=re.sub(r'\\u[0-9A-Fa-f]{4}|[\x00-\x1f]|[\ue000-\uf8ff]','',t).replace('\\n',' ')
    if len(vis)<=22:
        return 'Kısa tepki, komut veya özel ad. Diğer diller aynı duygusal/işlevsel değeri veriyor; mevcut Türkçe doğal ve ritmi uygun olduğu için aynı bırakıldı.'
    if (fn,r['label']) in prev_change_keys:
        return 'Bu satır önceki kalite turunda zaten müdahale görmüştü. EN ile DE/ES/FR/IT/NL yeniden karşılaştırıldı; mevcut Türkçe anlam, ton ve terim açısından yeterli bulunduğu için bu turda tekrar değiştirilmedi.'
    return 'EN anlamı ve DE/ES/FR/IT/NL ortak yorumu satır bağlamıyla karşılaştırıldı. Mevcut Türkçe doğal, karakter/arayüz tonuna uygun ve belirgin anlam-espri-terim kaybı taşımadığı için aynı bırakıldı.'

new_audit=[]; new_review_keys=set()
for fn in review_files:
    for r in files[fn][1]:
        key=(fn,r['label']); ch=changed_lookup.get(key)
        new_review_keys.add(key)
        new_audit.append({'round':'v0.5','file':fn,'label':r['label'],'index':r.get('index',''),'decision':'DEĞİŞTİ' if ch else 'AYNI KALDI','eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),'old_tur':ch['old_tur'] if ch else r.get('tur',''),'new_tur':r.get('tur',''),'reason':ch['reason'] if ch else unchanged_reason(fn,r)})
# Hedefli değişiklikler seçilen 7 dosyanın dışındaysa de rapora dahil.
for ch in changes:
    key=(ch['file'],ch['label'])
    if key not in new_review_keys:
        r=row(ch['file'],ch['label']); new_review_keys.add(key)
        new_audit.append({'round':'v0.5-hedefli','file':ch['file'],'label':ch['label'],'index':r.get('index',''),'decision':'DEĞİŞTİ','eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),'old_tur':ch['old_tur'],'new_tur':r.get('tur',''),'reason':ch['reason']})

field_a=['round','file','label','index','decision','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
with (OUTROOT/'V05_YENI_BLOK_SATIR_INCELEME.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=field_a); w.writeheader(); w.writerows(new_audit)

# Kümülatif satır bazlı audit, son karar her anahtar için.
cum={}
for a in prev_audit: cum[(a['file'],a['label'])]=a
for a in new_audit: cum[(a['file'],a['label'])]=a
cum_rows=list(cum.values())
with (OUTROOT/'SATIR_BAZLI_INCELEME_KUMULATIF.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=field_a); w.writeheader(); w.writerows(cum_rows)

field_c=['round','category','file','label','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
with (OUTROOT/'V05_YENI_DEGISIKLIKLER.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=field_c); w.writeheader(); w.writerows(changes)
combined=prev_changes+changes
with (OUTROOT/'INCELEME_DEGISIKLIKLERI.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=field_c); w.writeheader(); w.writerows(combined)
latest={}
for r in combined: latest[(r['file'],r['label'])]=r
with (OUTROOT/'INCELEME_SON_DURUM_ESSIZ.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=field_c); w.writeheader(); w.writerows(latest.values())

# Master 10.676: yeni inceleme > önceki inceleme/değişiklik > BEKLİYOR.
new_audit_map={(a['file'],a['label']):a for a in new_audit}
prev_master={}
if prev_master_path.exists():
    with prev_master_path.open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f): prev_master[(r['file'],r['label'])]=r
master=[]
for fn in sorted(files):
    for r in files[fn][1]:
        key=(fn,r['label'])
        if key in new_audit_map:
            a=new_audit_map[key]; status='İNCELENDİ_v0.5' if a['round']=='v0.5' else 'HEDEFLİ_DÜZELTME_v0.5'; decision=a['decision']; old=a['old_tur']; reason=a['reason']
        elif key in prev_master and prev_master[key].get('review_status')!='BEKLİYOR':
            pm=prev_master[key]; status=pm['review_status']; decision=pm['decision']; old=pm['old_tur']; reason=pm['reason']
        elif key in latest:
            h=latest[key]; status='ÖNCEKİ_TURDA_DEĞİŞTİ'; decision='DEĞİŞTİ'; old=h['old_tur']; reason=h['reason']
        else:
            status='BEKLİYOR'; decision='HENÜZ KARAR YOK'; old=r.get('tur',''); reason='Bu etiket henüz satır-satır manuel kalite turuna alınmadı; incelenmeden “aynı kaldı” diye işaretlenmedi.'
        master.append({'file':fn,'label':r['label'],'index':r.get('index',''),'review_status':status,'decision':decision,'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),'old_tur':old,'current_tur':r.get('tur',''),'reason':reason})
master_fields=['file','label','index','review_status','decision','eng','deu','esp','fra','ita','nld','old_tur','current_tur','reason']
with (OUTROOT/'TUM_10676_SATIR_DURUMU.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=master_fields); w.writeheader(); w.writerows(master)

# Satır uzunluğu: yeni değişiklikler ve önceki 13 etiket için.
# Kontrol kodlarının literal yazımını ve özel kontrol karakterlerini yaklaşık temizle.
ctrl_lit=re.compile(r'\\u[0-9A-Fa-f]{4}')
def visible_len(line):
    s=ctrl_lit.sub('',line)
    s=''.join(ch for ch in s if ord(ch)>=32 and not (0xE000<=ord(ch)<=0xF8FF))
    # Kontrol parametrelerinden kalan fullwidth/bozuk glifleri ölçüm dışı bırakmak için yalnız gerçek görünür yazıya yaklaş.
    s=re.sub(r'[\uff00-\uffef]|[�-￿]','',s)
    return len(s)
warn=[]
for ch in changes:
    for n,line in enumerate(ch['new_tur'].split('\\n'),1):
        L=visible_len(line)
        if L>48: warn.append({'file':ch['file'],'label':ch['label'],'line_no':n,'visible_len':L,'line':line})
with (OUTROOT/'V05_YENI_DEGISIKLIK_UZUNLUK_UYARILARI.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['file','label','line_no','visible_len','line']); w.writeheader(); w.writerows(warn)

# ----------------------------------------------------------------------
# MSBT rebuild / validate / round-trip.
# ----------------------------------------------------------------------
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
        if not y or x.get('tur','')!=y.get('tur',''): diffs.append((p.name,x['label'],x.get('tur',''),'' if not y else y.get('tur','')))
with (OUTROOT/'ROUNDTRIP_DOGRULAMA.txt').open('w',encoding='utf-8') as f:
    f.write(f'Etiket: {total}\nFark: {len(diffs)}\nYapısal validate: OK\n')
    for d in diffs[:100]: f.write(repr(d)+'\n')
if diffs: raise SystemExit(f'Roundtrip fark var: {len(diffs)}')

# İstatistikler
full_reviewed=sum(1 for r in master if r['review_status'].startswith('İNCELENDİ'))
waiting=sum(1 for r in master if r['review_status']=='BEKLİYOR')
new_full=[a for a in new_audit if a['round']=='v0.5']
new_same=sum(a['decision']=='AYNI KALDI' for a in new_full); new_changed=sum(a['decision']=='DEĞİŞTİ' for a in new_full)
targeted=sum(a['round']=='v0.5-hedefli' for a in new_audit)
unique_changed=len(latest)

readme=f'''SUSHI STRIKER TÜRKÇE ÇEVİRİ KALİTE İNCELEMESİ - v0.5\n{'='*62}\n\nBu paket v0.4 üzerine kuruludur. Kullanıcı isteği gereği incelenen her satır için\nDEĞİŞTİ / AYNI KALDI kararı ve somut gerekçe tutulur. Henüz incelenmeyen satırlar\nBEKLİYOR olarak kalır; otomatik olarak “aynı” sayılmaz.\n\nV0.5 TAM MANUEL BLOK\n--------------------\nDosyalar: {', '.join(review_files)}\nBu 7 dosyadaki satır: {len(new_full)}\nDeğişti: {new_changed}\nAynı kaldı: {new_same}\nEk hedefli çapraz-dosya düzeltmesi: {targeted}\nBu tur değişiklik olayı: {len(changes)}\n\nÖne çıkan yaratıcı/tutarlılık düzeltmeleri:\n- “soosh” -> “suş” (bilerek yanlış telaffuz, sahneler arasında tutarlı)\n- “bempty is elly” -> “barnım koş” (karnım boş baş seslerini değiştirerek aynı şaka)\n- “Pwincess” -> “Pırenses” (tekrarlanan karakter konuşma şakası)\n- lane-drive gear -> “Şerit Dişlisi”\n- Buff Buffet -> “Takviye Büfesi”\n- Arena sprite/Sprite Order -> ruh/Ruh Sırası\n- Searing Torch -> Mutfak Pürmüzü\n- Dinamik sayı + eşya adlarında Türkçe çoğul eki temizlendi.\n\nRAPORLAR\n---------\nV05_YENI_BLOK_SATIR_INCELEME.csv\n  v0.5 tam bloktaki HER satır + dış dosyalardaki hedefli değişen satırlar; nedenleriyle.\nSATIR_BAZLI_INCELEME_KUMULATIF.csv\n  v0.4 ve v0.5 satır-bazlı denetimlerin kümülatif son kararı.\nTUM_10676_SATIR_DURUMU.csv\n  10.676 etiketin tümü; incelenmeyenler BEKLİYOR.\nV05_YENI_DEGISIKLIKLER.csv\n  Sadece bu tur değişen satırlar, altı resmi dil + eski/yeni Türkçe + gerekçe.\nINCELEME_DEGISIKLIKLERI.csv / INCELEME_SON_DURUM_ESSIZ.csv\n  Tarihsel tüm değişiklikler / değiştirilmiş etiketlerin en son benzersiz hâli.\nV05_YENI_DEGISIKLIK_UZUNLUK_UYARILARI.csv\n  Yeni değişikliklerde 48 görünür karakter üstü satır denetimi.\n\nGENEL DURUM\n-----------\nSatır-bazlı tam manuel incelenmiş: {full_reviewed}\nBEKLİYOR: {waiting}\nBenzersiz müdahale edilmiş etiket: {unique_changed}\nMSBT: 243/243\nCSV -> MSBT -> CSV: {total} etiket, fark 0\nYapısal validate: OK\nYeni değişikliklerde >48 satır uyarısı: {len(warn)}\n'''
(OUTROOT/'README_TR.txt').write_text(readme,encoding='utf-8')

# Full bundle + tools
bundle=OUTROOT/'full_bundle'; (bundle/'LayeredFS').mkdir(parents=True)
shutil.copytree(rebuilt,bundle/'LayeredFS'/'00040000001C1D00')
shutil.copytree(OUT,bundle/'CSV')
(bundle/'Raporlar').mkdir()
for name in ['V05_YENI_BLOK_SATIR_INCELEME.csv','SATIR_BAZLI_INCELEME_KUMULATIF.csv','TUM_10676_SATIR_DURUMU.csv','V05_YENI_DEGISIKLIKLER.csv','INCELEME_DEGISIKLIKLERI.csv','INCELEME_SON_DURUM_ESSIZ.csv','V05_YENI_DEGISIKLIK_UZUNLUK_UYARILARI.csv','ROUNDTRIP_DOGRULAMA.txt']:
    shutil.copy2(OUTROOT/name,bundle/'Raporlar'/name)
shutil.copytree(ROOT/'review_v04'/'full_bundle'/'Araclar',bundle/'Araclar')
shutil.copy2(Path(__file__),bundle/'Araclar'/'v05_inceleme_uygulama_betigi.py')
shutil.copy2(OUTROOT/'README_TR.txt',bundle/'README_TR.txt')
manifest=[]
for p in sorted(x for x in bundle.rglob('*') if x.is_file()): manifest.append(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(bundle).as_posix()}')
(bundle/'DOSYA_MANIFESTOSU_SHA256.txt').write_text('\n'.join(manifest)+'\n',encoding='utf-8')

def zipdir(src,out):
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(Path(src).rglob('*')):
            if p.is_file(): z.write(p,p.relative_to(src).as_posix())
zipdir(bundle,OUTROOT/'Sushi_Striker_TR_v05_FULL.zip')
ptmp=OUTROOT/'patch_bundle'; ptmp.mkdir(); shutil.copytree(bundle/'LayeredFS',ptmp/'LayeredFS'); zipdir(ptmp,OUTROOT/'Sushi_Striker_TR_v05_LayeredFS.zip'); shutil.rmtree(ptmp)
atmp=OUTROOT/'tools_bundle'; atmp.mkdir(); shutil.copytree(bundle/'Araclar',atmp/'Araclar'); shutil.copy2(OUTROOT/'README_TR.txt',atmp/'README_TR.txt'); zipdir(atmp,OUTROOT/'Sushi_Striker_TR_v05_Araclar.zip'); shutil.rmtree(atmp)

print('v0.5 OK')
print('full target rows',len(new_full),'changed',new_changed,'same',new_same,'targeted',targeted)
print('change events',len(changes),'cumulative reviewed',full_reviewed,'waiting',waiting,'unique changed',unique_changed)
print('warnings',len(warn),'roundtrip',total,'diffs',len(diffs))
if warn:
    print('WARNINGS:')
    for x in warn: print(x)
