#!/usr/bin/env python3
from pathlib import Path
import csv,json,re,sys,unicodedata
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'araclar'))
import tr_iyilestir as base
import v4_quality_pass as v4
CSV=ROOT/'ceviri/layton_tr.csv'; JSONL=ROOT/'ceviri/layton_tr.jsonl'; EASY=ROOT/'ceviri/CEVIRI_KOLAY.csv'; REP=ROOT/'raporlar'

# Kaynaktan tekrar okunarak düzeltilen; kısaltma/yanlış kayıt yüzünden anlam kaybı olan satırlar.
OV={
('03/03_030415.xs','text000012'):'<T>Ve ata dönüştürülen o insanlar neden hâlâ\nbir yerlerde ot yiyip duruyor?',
('40/40_001000.xs','text000119'):"Henry'nin izni olsa bile, özel işlerine burnumu sokmak\nvicdanımı rahatsız ediyor. Yine de bulduğum bilgiler,\nHenry'nin şimdiye dek açıklanamayan davranışlarına yeni\nbir ışık tutuyor.\n\nMeğer o, baştan beri Monte d'Or'u korumaya ve Randall'ın\ndönüşüne hazır tutmaya çalışmış. Şehrin muhafızı olarak\nHenry, Maskeli Beyefendi'nin yarattığı yıkımın her izini\nsilip süpürmeye kararlıymış.",
('50/50_000060.xs','text000003'):"Doğru!\n\nHer fotoğrafta uzakta görünen manzaraya dikkatle bakarsan,\nnerede çekildiklerini anlayabilirsin.\n\nSağa kıvrılan bir mağarada ışık sol tarafta, sola\nkıvrılanda ise sağ tarafta görünür. Bunu aklında tutarak\ndoğru rotayı çıkarabilirsin.",
('05/05_050550.xs','text000008'):'<T><M2/2/1/80>Oh!<W> Anlıyorum. Ne kadar asil. Gerçekten\nçok asil. Anne baban seninle gurur duymalı.',
('07/07_070340.xs','text000008'):'<T>At yarışını seçkin ve asil bir spor olarak\ngörüyorum.',
('40/40_001200.xs','text000117'):"Layton dizginleri eline aldığında rüzgâr gibi koşan\nheybetli siyah bir kısrak. Engelleri zahmetsizce aşar;\nöyle asil görünür ki sanki kraliyet soyundan geliyor.\nProfesörün duruşuna çok yakışır.",
('05/05_050630.xs','text000033'):'<T>Şu işe bak!',
('07/07_070080.xs','text000018'):"<T>Bay Dalston'ın sözde mucizelerinin aslında en basit\ngözbağcılığı numaralarından ibaret olduğunu söylediğini\nduydum.",
}

# Kayıt bazlı, kaynak anlamı doğrulanmış düzeltmeler.
RR={
('05/05_050590.xs','text000027'):[('net kari','net kârı'),('Besi elde taşı','Beşi elde taşı')],
('07/07_071120.xs','text000014'):[('hani us olarak','hanı üs olarak')],
('06/06_065030.xs','text000002'):[('Uc beş sus','Üç beş süs')],
('05/05_050550.xs','text000007'):[('Ucumuz','Üçümüz')],
('05/05_050660.xs','text000011'):[('siz ucunuz','siz üçünüz')],
('03/03_030080.xs','text000015'):[('işim takan','isim takan')],
('03/03_030480.xs','text000045'):[('turistlerin gerçekten data dönüştüğünü','turistlerin gerçekten ata dönüştüğünü')],
('82/82_001000.xs','text000378'):[('Bir ise daha yarar','Bir işe daha yarar')],
('40/40_001010.xs','text000049'):[('geri donemeyiz','geri dönemeyiz')],
('02/02_020030.xs','text000008'):[('öne surdu','öne sürdü')],
('03/03_030482.xs','text000064'):[('sununla','şununla')],
('03/03_030450.xs','text000015'):[("Yard'in","Yard'ın"),('cagirttiklarina','çağırttıklarına')],
('40/40_001200.xs','text000017'):[('dinc','dinç'),('tüm koyun','tüm köyün')],
('40/40_001000.xs','text000012'):[("Angela'nın Sabri Tasti","Angela'nın Sabrı Taştı")],
('40/40_001500.xs','text000035'):[('Koyun en zengin evi','Köyün en zengin evi'),('kati kurallara','katı kurallara')],
('08/08_080020.xs','text000017'):[('uzak bir koyun kıyılarına','uzak bir köyün kıyısına')],
('03/03_030310.xs','text000013'):[('suren','süren')],
('20/20_209080.xs','text000008'):[('Demo surumunu','Demo sürümünü')],
('82/82_000009.xs','text000021'):[('pencereye surundu','pencereye süründü')],
('06/06_067611.xs','text000004'):[('örümcek surusuyle','örümcek sürüsüyle')],
('30/30_003110.xs','text000001'):[('Kısa ve oz.','Kısa ve öz.')],
('03/03_030480.xs','text000017'):[('kor etti','kör etti')],
('03/03_030480.xs','text000042'):[('kor edici','kör edici')],
('03/03_030480.xs','text000056'):[('kor etti','kör etti')],
('03/03_030480.xs','text000071'):[('kor etti','kör etti')],
('07/07_071250.xs','text000005'):[('gözünü öyle kor ettiği','gözünü öyle kör ettiği')],
('05/05_050420.xs','text000006'):[('tasa dönüşme','taşa dönüşme')],
('40/40_001100.xs','text000011'):[('Tasa Dönüşme','Taşa Dönüşme')],
('50/50_000040.xs','text000008'):[('yarisini','yarışını')],
('05/05_050070.xs','text000007'):[('ACIL TOPLANTI','ACİL TOPLANTI')],
('40/40_002300.xs','text000000'):[('Isim Kayıt Menusu','İsim Kayıt Menüsü')],
('40/40_002300.xs','text000004'):[('Isim Girişi','İsim Girişi')],
('04/04_040055.xs','text000004'):[('seker mısırımızdan','şeker mısırımızdan')],
('08/08_080090.xs','text000037'):[('seklini','şeklini')],
('03/03_030657.xs','text000001'):[('Bloom isini','Bloom işini')],
('40/40_001200.xs','text000037'):[('babasının isini','babasının işini'),('aklından geceni','aklından geçeni')],
('82/82_000009.xs','text000029'):[('Isini bitirirken','İşini bitirirken')],
('07/07_070260.xs','text000007'):[('cevabin','cevabın')],
('02/02_020150.xs','text000006'):[('isleri','işleri')],
('07/07_070080.xs','text000017'):[('isleri','işleri'),('odunc','ödünç')],
('50/50_000134.xs','text000005'):[('isleri','işleri')],
('50/50_000136.xs','text000006'):[('isleri','işleri')],
('01/01_010053.xs','text000011'):[('isimize','işimize')],
('06/06_060102.xs','text000003'):[('isimize','işimize')],
('01/01_010300.xs','text000025'):[('durtusune','dürtüsüne'),('urunu','ürünü')],
('81/81_000300.xs','text000010'):[('urunu','ürünü')],
('05/05_050810.xs','text000008'):[('besimiz','beşimiz')],
('50/50_000115.xs','text000005'):[('besini','beşini')],
('03/03_030650.xs','text000036'):[('hesabini','hesabını')],
('03/03_030415.xs','text000002'):[('isimde','işimde')],
('02/02_020110.xs','text000008'):[('isinden','işinden')],
('50/50_000149.xs','text000007'):[('islerini','işlerini')],
('40/40_001200.xs','text000049'):[('isletir','işletir'),('Iri yari','İri yarı'),('kaslarini','kaslarını')],
('03/03_030421.xs','text000019'):[('katilin','katılın')],
('30/30_008070.xs','text000006'):[('bel kiran','bel kıran')],
('40/40_002100.xs','text000071'):[('deve ayağı susu','deve ayağı süsü')],
('81/81_000020.xs','text000092'):[('dolup tasar','dolup taşar')],
('02/02_020070.xs','text000012'):[('aklin','aklın')],
('18/18_180160.xs','text000006'):[('Aklin','Aklın')],
('05/05_050230.xs','text000012'):[('hakim','hâkim')],
('05/05_050775.xs','text000008'):[('hakim','hâkim')],
('01/01_010180.xs','text000016'):[('islerinden','işlerinden')],
('07/07_070480.xs','text000026'):[('islerinden','işlerinden')],
('03/03_030582.xs','text000008'):[('isten','işten')],
('09/09_092035.xs','text000010'):[('isten','işten')],
('05/05_050446.xs','text000004'):[('uzun zamandır','uzun zamandır')],
('05/05_050446.xs','text000005'):[('omur boyu','ömür boyu')],
('06/06_068140.xs','text000004'):[('omur boyu','ömür boyu')],
('81/81_000007.xs','text000003'):[('urun','ürün'),('<CR>green</CR>','<CR>yeşil</CR>')],
('81/81_000100.xs','text000203'):[('urun','ürün')],
('07/07_070480.xs','text000006'):[(' us ',' üs ')],
('03/03_030540.xs','text000027'):[('zekan','zekân'),('gimnastikci','jimnastikçi'),('durusun','duruşun')],
('20/20_200220.xs','text000004'):[('zekan','zekân')],
('18/18_181130.xs','text000005'):[('dinc','dinç')],
('40/40_001200.xs','text000017'):[('dinc','dinç'),('tüm koyun','tüm köyün')],
('40/40_001200.xs','text000107'):[('dinc','dinç')],
('03/03_030170.xs','text000009'):[('cooook','çooook')],
('03/03_030170.xs','text000018'):[('cooook','çooook')],
('82/82_001000.xs','text000364'):[('cooook','çooook')],
('07/07_071080.xs','text000006'):[('aynisi','aynısı')],
('08/08_080140.xs','text000006'):[('aynisi','aynısı')],
('81/81_000003.xs','text000006'):[('aynisi','aynısı')],
('05/05_050444.xs','text000015'):[('oz oğlum','öz oğlum')],
('01/01_010320.xs','text000009'):[('bahsetmisken','bahsetmişken')],
('05/05_050570.xs','text000003'):[('kirmis','kırmış')],
('05/05_050656.xs','text000005'):[('kosa kosa','koşa koşa')],
('40/40_002100.xs','text000059'):[('Modern cagin','Modern çağın')],
('00/00_000060.xs','text000002'):[('buyulu','büyülü')],
('03/03_030220.xs','text000021'):[('buyulu','büyülü')],
('01/01_010270.xs','text000018'):[('uctu','uçtu')],
('05/05_050446.xs','text000004'):[('omur boyu','ömür boyu')],
('05/05_050446.xs','text000006'):[('havuc stogunuz','havuç stoğunuz')],
}

# Kök anlamı İngilizce kaynaktan açık olan token düzeltmeleri.
SUCCESS_KEYS={
('03/03_030220.xs','text000010'): [('basarisi','başarısı')],
('05/05_050330.xs','text000006'): [('Basarisizlik','Başarısızlık')],
('06/06_062150.xs','text000008'): [('Basarinin','Başarının')],
('09/09_090100.xs','text000017'): [('basarisizim','başarısızım')],
('20/20_200250.xs','text000061'): [('basarmisti','başarmıştı')],
('30/30_001010.xs','text000015'): [('basarmislar','başarmışlar')],
('40/40_001000.xs','text000033'): [('basarmis','başarmış')],
('40/40_002400.xs','text000069'): [('basarmissin','başarmışsın')],
}
AKIL_KEYS={
('01/01_010300.xs','text000015'):[('akil','akıl')],('02/02_020310.xs','text000014'):[('Akil','Akıl')],
('04/04_040050.xs','text000006'):[('akillilik','akıllılık')],('06/06_062170.xs','text000004'):[('akillicaydi','akıllıcaydı')],
('09/09_090120.xs','text000035'):[('akil','akıl')],('40/40_001200.xs','text000019'):[('akil','akıl')],
('40/40_002100.xs','text000043'):[('akil','akıl')],('81/81_000100.xs','text000051'):[('akil','akıl')],
('03/03_030660.xs','text000001'):[('Aklinizi','Aklınızı')],
}
DON_KEYS={
('00/00_002020.xs','text000012'):[('haritaya don','haritaya dön')],('01/01_010270.xs','text000019'):[('sola donun','sola dönün')],
('02/02_020020.xs','text000005'):[('donemi','dönemi')],('02/02_020020.xs','text000007'):[('donemin','dönemin')],
('02/02_020060.xs','text000007'):[('doneme','döneme')],('03/03_030140.xs','text000005'):[('donemeyebilirsek','dönemeyebilirsek')],
('03/03_030490.xs','text000017'):[('geri donun','geri dönün')],('06/06_060110.xs','text000005'):[('noktaya don','noktaya dön')],
('06/06_067010.xs','text000008'):[('yerinde don','yerinde dön')],('06/06_067101.xs','text000002'):[('noktaya donuk','noktaya dönük')],
('06/06_067303.xs','text000001'):[('ona donuk','ona dönük')],('06/06_068010.xs','text000010'):[('donum noktası','dönüm noktası')],
('06/06_068030.xs','text000004'):[('eve don','eve dön')],('09/09_092035.xs','text000006'):[('donem','dönem')],
('18/18_181030.xs','text000005'):[('donebildiklerin','dönebildiklerin')],('20/20_200230.xs','text000005'):[("Stansbury'ye don","Stansbury'ye dön")],
('20/20_200240.xs','text000005'):[("Monte d'Or'a don","Monte d'Or'a dön")],('20/20_200260.xs','text000046'):[('zamana donun','zamana dönün')],
('30/30_003050.xs','text000008'):[('doneme','döneme')],('40/40_001010.xs','text000049'):[('donemeyiz','dönemeyiz')],
('40/40_001200.xs','text000029'):[('donemde','dönemde')],('40/40_001200.xs','text000069'):[('done done','döne döne')],
('40/40_009000.xs','text000003'):[('Baslik','Başlık'),('donulsun','dönülsün')],('50/50_000125.xs','text000002'):[('donemin','dönemin')],
('80/80_000400.xs','text000002'):[('donulsun','dönülsün')],('81/81_000020.xs','text000007'):[('donulsun','dönülsün')],
('82/82_000001.xs','text000021'):[('dona kalmış','donakalmış')],('82/82_001000.xs','text000260'):[('<CR>Don</C>meyi','<CR>Dön</C>meyi')],
('82/82_002000.xs','text000017'):[('Don','Dön')],('82/82_002000.xs','text000018'):[('don','dön')],
}
YAS_KEYS={
('05/05_050505.xs','text000007'):[('yas perdesi','yaş perdesi')],
}
TUR_KEYS={
('05/05_050810.xs','text000039'):[('bu tur numaraları','bu tür numaraları')],
('30/30_003020.xs','text000005'):[('iki turu','iki türü')],('30/30_009020.xs','text000005'):[('iki turu','iki türü')],
('81/81_000020.xs','text000017'):[('ananas turudur','ananas türüdür')],('81/81_000020.xs','text000018'):[('ananas turudur','ananas türüdür')],
('50/50_000080.xs','text000007'):[("3'tur","3'tür")],
('30/30_006070.xs','text000008'):[('Başka turlusu','Başka türlüsü')],('50/50_000028.xs','text000006'):[('her turlusu','her türlüsü')],
('50/50_000031.xs','text000002'):[('lig usulu','lig usulü'),('tenis turvasini','tenis turnuvasını'),('amma sadece','ama sadece')],
}
IS_KEYS={
('01/01_010335.xs','text000001'):[('Hiçbir ise yaramaz','Hiçbir işe yaramaz')],
('03/03_030480.xs','text000032'):[('numarasının ise yaraması','numarasının işe yaraması')],
('03/03_030484.xs','text000001'):[('Ise koyulalım','İşe koyulalım')],
('03/03_030492.xs','text000014'):[('hep ise karışır','hep işe karışır')],
('03/03_030545.xs','text000013'):[('ise dönmeliyim','işe dönmeliyim')],
('04/04_040130.xs','text000004'):[('ise yarayacak','işe yarayacak')],
('05/05_050570.xs','text000017'):[('bir ise ihtiyacım','bir işe ihtiyacım')],
('06/06_067700.xs','text000001'):[('ise yarar','işe yarar')],
('07/07_070320.xs','text000006'):[('şehri ise karıştırmak','şehri işe karıştırmak')],
('09/09_092040.xs','text000004'):[('İnsan ise almaya','insan işe almaya')],
('18/18_180200.xs','text000003'):[('göz ise yarar','göz işe yarar')],
('18/18_181100.xs','text000003'):[('O zaman ise geri dönelim','O zaman işe geri dönelim')],
('82/82_000008.xs','text000046'):[('dansçı olarak ise alırım','dansçı olarak işe alırım')],
('82/82_001000.xs','text000211'):[('bir de ise yarayabilecek','bir de işe yarayabilecek')],
('82/82_003090.xs','text000001'):[('Başlangıçta, ise tam','Başlangıçta, işe tam')],
('50/50_000125.xs','text000005'):[('islecleri','işleçleri')],
}

for d in (SUCCESS_KEYS,AKIL_KEYS,DON_KEYS,YAS_KEYS,TUR_KEYS,IS_KEYS):
    for k,v in d.items(): RR.setdefault(k,[]).extend(v)

# Birden çok kayıtta anlamı tek olan, güvenli yazım kalıntıları.
SAFE_WORD={
 'Aynisini':'Aynısını','aynisini':'aynısını','aynisiydi':'aynısıydı','aynisi':'aynısı','Aynisi':'Aynısı',
 'semsiye':'şemsiye','Semsiye':'Şemsiye','nese':'neşe','Nese':'Neşe','utangac':'utangaç','Utangac':'Utangaç',
 'siluet':'silüet','Siluet':'Silüet','gimnastikci':'jimnastikçi','Gimnastikci':'Jimnastikçi',
 'cevre':'çevre','Cevre':'Çevre','tarihci':'tarihçi','Tarihci':'Tarihçi','avuc':'avuç','Avuc':'Avuç',
 'vinc':'vinç','Vinc':'Vinç','ifsa':'ifşa','Ifsa':'İfşa','toplanti':'toplantı','Toplanti':'Toplantı',
 'baslik':'başlık','Baslik':'Başlık','gurultu':'gürültü','Gurultu':'Gürültü','gurultulu':'gürültülü','gurultucu':'gürültücü',
 'hayli':'hayli','bicimi':'biçimi','Bicimi':'Biçimi','sikistir':'sıkıştır',
}
WORD_RE=re.compile(r"(?<![A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû])([A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû]+)(?![A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû])")

def controls(s): return base.CTRL_RE.findall(s)

def q_harmony(text):
    # Sadece zaten soru eki biçimindeki bağımsız sözcükleri, önceki Türkçe kelimenin son ünlüsüne göre düzeltir.
    forms={
      'mi':'', 'mı':'','mu':'','mü':'',
      'misin':'sin','mısın':'sın','musun':'sun','müsün':'sün',
      'misiniz':'siniz','mısınız':'sınız','musunuz':'sunuz','müsünüz':'sünüz',
      'miyim':'yim','mıyım':'yım','muyum':'yum','müyüm':'yüm',
      'miyiz':'yiz','mıyız':'yız','muyuz':'yuz','müyüz':'yüz',
      'miydi':'ydi','mıydı':'ydı','muydu':'ydu','müydü':'ydü',
      'miydin':'ydin','mıydın':'ydın','muydun':'ydun','müydün':'ydün',
      'miydim':'ydim','mıydım':'ydım','muydum':'ydum','müydüm':'ydüm',
      'miydiniz':'ydiniz','mıydınız':'ydınız','muydunuz':'ydunuz','müydünüz':'ydünüz',
    }
    pat=re.compile(r'\b('+'|'.join(sorted(map(re.escape,forms),key=len,reverse=True))+r')\b',re.I)
    def repl(m):
      before=base.CTRL_RE.sub(' ',text[:m.start()])
      ws=re.findall(r'[A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû]+',before)
      if not ws:return m.group(0)
      prev=ws[-1].lower().translate(str.maketrans({'â':'a','î':'i','û':'u'})); vs=[c for c in prev if c in 'aeıioöuü']
      if not vs:return m.group(0)
      v=vs[-1]; q='mı' if v in 'aı' else 'mi' if v in 'ei' else 'mu' if v in 'ou' else 'mü'
      low=m.group(0).lower(); suf=forms.get(low)
      if suf is None:return m.group(0)
      # suffix surface follows same vowel class
      tails={
       'sin':{'mı':'sın','mi':'sin','mu':'sun','mü':'sün'}, 'sın':{'mı':'sın','mi':'sin','mu':'sun','mü':'sün'},'sun':{'mı':'sın','mi':'sin','mu':'sun','mü':'sün'},'sün':{'mı':'sın','mi':'sin','mu':'sun','mü':'sün'},
       'siniz':{'mı':'sınız','mi':'siniz','mu':'sunuz','mü':'sünüz'},'sınız':{'mı':'sınız','mi':'siniz','mu':'sunuz','mü':'sünüz'},'sunuz':{'mı':'sınız','mi':'siniz','mu':'sunuz','mü':'sünüz'},'sünüz':{'mı':'sınız','mi':'siniz','mu':'sunuz','mü':'sünüz'},
       'yim':{'mı':'yım','mi':'yim','mu':'yum','mü':'yüm'},'yım':{'mı':'yım','mi':'yim','mu':'yum','mü':'yüm'},'yum':{'mı':'yım','mi':'yim','mu':'yum','mü':'yüm'},'yüm':{'mı':'yım','mi':'yim','mu':'yum','mü':'yüm'},
       'yiz':{'mı':'yız','mi':'yiz','mu':'yuz','mü':'yüz'},'yız':{'mı':'yız','mi':'yiz','mu':'yuz','mü':'yüz'},'yuz':{'mı':'yız','mi':'yiz','mu':'yuz','mü':'yüz'},'yüz':{'mı':'yız','mi':'yiz','mu':'yuz','mü':'yüz'},
       'ydi':{'mı':'ydı','mi':'ydi','mu':'ydu','mü':'ydü'},'ydı':{'mı':'ydı','mi':'ydi','mu':'ydu','mü':'ydü'},'ydu':{'mı':'ydı','mi':'ydi','mu':'ydu','mü':'ydü'},'ydü':{'mı':'ydı','mi':'ydi','mu':'ydu','mü':'ydü'},
       'ydin':{'mı':'ydın','mi':'ydin','mu':'ydun','mü':'ydün'},'ydın':{'mı':'ydın','mi':'ydin','mu':'ydun','mü':'ydün'},'ydun':{'mı':'ydın','mi':'ydin','mu':'ydun','mü':'ydün'},'ydün':{'mı':'ydın','mi':'ydin','mu':'ydun','mü':'ydün'},
       'ydim':{'mı':'ydım','mi':'ydim','mu':'ydum','mü':'ydüm'},'ydım':{'mı':'ydım','mi':'ydim','mu':'ydum','mü':'ydüm'},'ydum':{'mı':'ydım','mi':'ydim','mu':'ydum','mü':'ydüm'},'ydüm':{'mı':'ydım','mi':'ydim','mu':'ydum','mü':'ydüm'},
       'ydiniz':{'mı':'ydınız','mi':'ydiniz','mu':'ydunuz','mü':'ydünüz'},'ydınız':{'mı':'ydınız','mi':'ydiniz','mu':'ydunuz','mü':'ydünüz'},'ydunuz':{'mı':'ydınız','mi':'ydiniz','mu':'ydunuz','mü':'ydünüz'},'ydünüz':{'mı':'ydınız','mi':'ydiniz','mu':'ydunuz','mü':'ydünüz'},
      }
      out=q + (tails.get(suf,{}).get(q,suf) if suf else '')
      if m.group(0)[0].isupper():out=out[0].upper()+out[1:]
      return out
    return pat.sub(repl,text)

def main():
    adv=base.load_adv(ROOT)
    rows=list(csv.DictReader(CSV.open(encoding='utf-8-sig',newline='')))
    v6={(r['file'],r['id']):r['translation'] for r in rows}
    changed=[]; outmap={}; badcodes=[]; overflow=[]; stats=Counter()
    for r in rows:
      key=(r['file'],r['id']); old=r['translation']; s=OV.get(key,old); why=[]
      if s!=old: why.append('kaynak karşılaştırmalı anlam/paragraf geri yükleme'); stats['semantic_override']+=1
      for a,b in RR.get(key,[]):
        if a in s:
          s=s.replace(a,b); why.append(f'kaynak bağlamı: {a}→{b}'); stats['record_fix']+=1
      # Güvenli, anlamı tek olan yazım kalıntıları
      notes=[]
      def wf(m):
        w=m.group(1); nw=SAFE_WORD.get(w,w)
        if nw!=w:notes.append(f'{w}→{nw}')
        return nw
      ns=WORD_RE.sub(wf,s)
      if ns!=s:s=ns; why.append('güvenli yazım: '+', '.join(notes)); stats['safe_word']+=len(notes)
      # soru eki uyumu
      ns=q_harmony(s)
      if ns!=s:s=ns; why.append('Türkçe soru eki ünlü uyumu'); stats['question_harmony']+=1
      s=unicodedata.normalize('NFC',s)
      # V6 kontrol kodu dizisini kesinlikle değiştirme.
      if controls(s)!=controls(old) and not (key in OV and controls(s)==controls(r['original'])):
        badcodes.append({'file':r['file'],'id':r['id'],'before':controls(old),'after':controls(s),'candidate':s})
        s=old; why=['kontrol kodu güvenliği nedeniyle v7 değişikliği geri alındı']; stats['control_revert']+=1
      # yalnız değişen satırı gerçek font advance değerlerine göre yeniden akıt
      if s!=old:
        w,chg,reason=v4.wrap_final(r['original'],s,adv)
        if chg and controls(w)==controls(old):s=w;why.append(reason);stats['wrap']+=1
      px=v4.max_px(s,adv); limit=348 if ('<T>' in r['original'] or (v4.JP_RE.search(r['original']) and r['original'].count('\n')<=2)) else 399
      if px>limit:overflow.append({'file':r['file'],'id':r['id'],'px':px,'limit':limit,'translation':s,'source':r['original']})
      if s!=old:changed.append({'file':r['file'],'id':r['id'],'neden':'; '.join(why),'once_v6':old,'sonra_v7':s,'kaynak':r['original']});stats['changed_rows']+=1
      r['translation']=s;outmap[key]=s
    with CSV.open('w',encoding='utf-8-sig',newline='') as f:
      w=csv.DictWriter(f,fieldnames=['file','id','offset','original','translation']);w.writeheader();w.writerows(rows)
    out=[]
    for line in JSONL.read_text(encoding='utf-8').splitlines():
      o=json.loads(line)
      if o.get('kind')=='text':o['translation']=outmap.get((o['file'],o['id']),o.get('translation',''))
      out.append(json.dumps(o,ensure_ascii=False,separators=(',',':')))
    JSONL.write_text('\n'.join(out)+'\n',encoding='utf-8')
    ers=list(csv.DictReader(EASY.open(encoding='utf-8-sig',newline='')))
    for rr in ers:
      k=(rr['file'],rr['id'])
      if k in outmap:rr['turkce']=outmap[k]
    with EASY.open('w',encoding='utf-8-sig',newline='') as f:
      w=csv.DictWriter(f,fieldnames=ers[0].keys());w.writeheader();w.writerows(ers)
    with (REP/'V7_EK_DEGISIKLIK_RAPORU.csv').open('w',encoding='utf-8-sig',newline='') as f:
      fields=['file','id','neden','once_v6','sonra_v7','kaynak'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(changed)
    (REP/'V7_KONTROL_KODU_GUVENLIK.json').write_text(json.dumps(badcodes,ensure_ascii=False,indent=2),encoding='utf-8')
    with (REP/'V7_TASMA_RISKLERI.csv').open('w',encoding='utf-8-sig',newline='') as f:
      fields=['file','id','px','limit','translation','source'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(overflow)
    print(json.dumps({'rows':len(rows),'stats':dict(stats),'badcodes':len(badcodes),'overflow':len(overflow)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
