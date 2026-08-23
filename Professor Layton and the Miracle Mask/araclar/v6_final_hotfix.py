#!/usr/bin/env python3
from pathlib import Path
import csv,json,re,sys,unicodedata
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'araclar'))
import tr_iyilestir as base
import v4_quality_pass as v4
CSV=ROOT/'ceviri/layton_tr.csv'; JSONL=ROOT/'ceviri/layton_tr.jsonl'; EASY=ROOT/'ceviri'/'CEVIRI_KOLAY.csv'; REP=ROOT/'raporlar'

OV={
('01/01_010030.xs','text000009'):'<T><M4/2/1/45>Bu baş belasının bu kadar uzun süre\ncezasız hareket edebilmesi endişe verici.\nAnlaşılan polis bu vakayla boğuşuyor.',
('03/03_030110.xs','text000012'):"<T><M1/1/1>Ah evet, kesinötesi. Maskeli Dandleman\ngerçek. Onu bu kadar heyecanötesi\nyapan da bu!",
('03/03_030494.xs','text000001'):'<T>Profesör, vakaları çözme konusundaki\nününüz düşünülürse soruşturmanızın\nsonucunu sabırsızlıkla bekliyorum.',
('05/05_050090.xs','text000010'):'<T><M1/1/2>Evet, geri dönüp pencere pervazlarını\nyine toz almalıyım. Çok titiz\nbir adam... <W>Ama iyi bir adam!',
('05/05_050220.xs','text000009'):'<T><M4/2/1>Suçluyu yakaladığını düşünüyor\nve devriye memurlarını şimdiden\nnormal düzenlerine döndürdü.',
('05/05_050350.xs','text000001'):'<T>Bu kadar çabuk mu döndünüz? Arabaları\nincelemek istemiyor muydunuz?',
('05/05_050505.xs','text000016'):'<T><M2/1/1>Ah! Alçakgönüllülüğün sevimli ama\nbenim yanımda gereksiz. Şapkanın içinde\ndönen mantığı, zekâyı ve bilgeliği biliyorum.',
('05/05_050660.xs','text000016'):'<T><M1/1/1>Geri döndünüz! Siz yokken korku\nneredeyse beni ele geçiriyordu.<W>\nKorku ve pamuk şeker.',
('05/05_050661.xs','text000012'):'<T>Geri döndünüz! Siz yokken korku\nneredeyse beni ele geçiriyordu.<W>\nKorku ve pamuk şeker.',
('07/07_070070.xs','text000003'):'<T>O topun üstüne çıkıyorum, iki gün\nsonra kalçalarım avaz avaz bağırıyor!\nTam bir palyaçoya dönüyorum.',
('07/07_070540.xs','text000001'):'<T>Şansım açılıyor diye hissediyordum;\nsonra kolu çektim ve üç yedi geldi!\nHarikamuazzam, değil mi?',
('07/07_071040.xs','text000017'):'<T><M3/2/1/45>Peki. Az sonra döneceğiz, Aldus.',
('07/07_071041.xs','text000008'):'<T>Ah, geri döndünüz! Şapkanızın\nyüksekliğini ne heyecanla bekliyordum!',
('08/08_080010.xs','text000006'):'...Fark ettiğimde çok şaşırdım, Randall...',
('15/15_000002.xs','text000012'):'Donmuş! Taş gibi!',
('15/15_000038.xs','text000058'):'Henry, Angela...\nEve döndüm.',
('40/40_001200.xs','text000119'):'Zarif görünüşüyle yoldan\ngeçenleri hayranlıktan\ndurduran asil bir beyaz at.\nÇevik toynakları yaklaşan\nvarillerden hızlı ve zarifçe\nsıyrılır; Emmy’nin azmini ve\nönüne çıkan her zorluğa\natılma hevesini paylaşır.',
('40/40_002000.xs','text000035'):'Kendi dostunun ihanetine uğrayan,\nmemleketi harabeye dönen Randall\nintikam yemini ederken pelerinli\nbir figür onu sinsice kışkırtır.',
('50/50_000043.xs','text000002'):'A ve B, on tur süren bir kart oyununda\nkarşı karşıya geliyor. Kurallar basit:\nateş odunu yener, odun suyu yener,\nsu da ateşi yener.\n\nA ateşi üç, odunu beş, suyu iki kez;\nB ise ateşi iki, odunu beş, suyu üç kez\nçekmiş. Hiçbir tur berabere bitmemiş.\n\nBu maçı kimin kazandığını bulabilir misin?',
('50/50_000099.xs','text000006'):"A'yı yaptıktan sonra ipi aşağı\nindirip E'nin altından geçir, sonra\nyukarı çıkarıp C'nin etrafını dön.\n\nSırada en verimli çukur hangisi?",
('50/50_000099.xs','text000008'):"A, C, D ve E'yi çevirdikten sonra\nsırada F var. Son hedefini aklında tutarak\nçukurun sol üstündeki kazıktan başla.\n\nGeriye yalnız B kalır. F'den dümdüz yukarı\nçık, B'nin etrafını dön ve bitişe ulaş!",
('50/50_000151.xs','text000002'):'Tuhaf bir sihir gösterisi başlıyor.\nDağılmış panelleri eski şekline geri\ngetirince üzerlerindeki hayvan ortaya çıkacak.\nİki panelin arasına büyü yapınca o nokta\nmerkez olur ve iki panel yer değiştirir.\nHaydi, büyü yapıp panelleri eski yerlerine\ngeri döndür. Bakalım hangi hayvan çıkacak?',
('50/50_000166.xs','text000003'):"Harika!\n\n[?] ile işaretli kabin Satürn'ü temsil ediyor;\nbu yüzden eskiden üzerinde [S] yazıyordu.\nDönme dolaptaki harfler, Güneş'in\netrafında dönen gezegenleri temsil eder.",
('50/50_000166.xs','text000008'):"M V E M J ? U N dizisi tanıdık değil mi?\nGüneş'in etrafında dönen gezegenlerin,\nen yakından en uzağa doğru sırası!\n\nKabinlerde Güneş Sistemi'ndeki her gezegenin\nilk harfi var. O halde [J] ile [U] arasında\nhangi gezegen var ve ilk harfi nedir?",
('80/80_000200.xs','text000007'):'Dönüp duruyor\nolabilirsin, ama\nen azından hiç\ndüşman yok!',
('82/82_002000.xs','text000023'):'Önce dönsün, sonra ters takla atsın.\nAyağa kalkarsa, başından karnına\nkadar okşamak işe yarayabilir.',
('82/82_003030.xs','text000001'):'Hımm... Heyecanlı görünmelisin. Öyle\nheyecanlısın ki kendi etrafında dönüp duruyorsun!',
('52/52_000037.xs','text000004'):'Her hayaletin üzerindeki sayı,\nilgili ışını tam olarak kaç kez\nyansıtman gerektiğini söyler.',
('50/50_000033.xs','text000001'):"Karo Ası'nı bul!",
('50/50_000033.xs','text000005'):'Karo Ası adı kılıcın tarihi ya\nda efsanelerinden gelmez.\nTamamen silahın şekliyle ilgilidir.',
}

PUZZLE_FIX={
 'cevabini':'cevabını','Cevabini':'Cevabını','cevabin':'cevabın',
 'basi':'başı','Basi':'Başı',
 'taslar':'taşlar','Taslar':'Taşlar','taslarini':'taşlarını','taslarin':'taşların','taslarinla':'taşlarınla','taslarla':'taşlarla',
 'afis':'afiş','Afis':'Afiş','afisi':'afişi','Afisi':'Afişi','afisin':'afişin','afisle':'afişle','afisindeki':'afişindeki','afisinin':'afişinin','Afislerin':'Afişlerin',
 'kiliyor':'kılıyor','Kiliyor':'Kılıyor',
 'yonu':'yönü','Yonu':'Yönü','yonun':'yönün','yondur':'yöndür',
 'satiri':'satırı','Satiri':'Satırı','satirdaki':'satırdaki',
 'kapisinda':'kapısında','Kapisinda':'Kapısında',
 'buyu':'büyü','Buyu':'Büyü',
 'bloguna':'bloğuna','Bloguna':'Bloğuna',
 'Ipucunu':'İpucunu','Ipucunda':'İpucunda','Ipucundan':'İpucundan',
 'kazandi':'kazandı','Kazandi':'Kazandı',
 'seklin':'şeklin','Seklin':'Şeklin','seklini':'şeklini','Seklini':'Şeklini','sekliyle':'şekliyle',
 'islenmis':'işlenmiş','Islenmis':'İşlenmiş',
 'aynisi':'aynısı','Aynisi':'Aynısı',
 'isletir':'işletir','isletmez':'işletmez','isletmiyor':'işletmiyor',
 'calismasinin':'çalışmasının','Calismasinin':'Çalışmasının',
 'Besimiz':'Beşimiz','hesabini':'hesabını','sefi':'şefi','Sefi':'Şefi',
 'suren':'süren','Suren':'Süren','atesi':'ateşi','Atesi':'Ateşi',
 'isinlarin':'ışınların','Isinlarin':'Işınların','isinlari':'ışınları','Isinlari':'Işınları','isinlarini':'ışınlarını','isinla':'ışınla',
 'Gunesin':'Güneşin','gunesin':'güneşin','Gunes':'Güneş','gunes':'güneş',
 'Ayni':'Aynı','Aynisini':'Aynısını',
 'Sali':'Salı','sayisindan':'sayısından','sayisinin':'sayısının','Sayisinin':'Sayısının',
 'sinirli':'sınırlı','Sinirli':'Sınırlı',
 'dolasan':'dolaşan','Dolasan':'Dolaşan',
 'tasindi':'taşındı','Tasindi':'Taşındı','tasmadan':'taşmadan',
 'uc':'uç','Uc':'Uç',
 'seker':'şeker','Seker':'Şeker',
}
WORD_RE=re.compile(r"(?<![A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû])([A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû]+)(?![A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû])")
def controls(s): return base.CTRL_RE.findall(s)
def main():
 adv=base.load_adv(ROOT)
 rows=list(csv.DictReader(CSV.open(encoding='utf-8-sig',newline='')))
 changes=[]; outmap={}; over=[]; bad=[]; stats=Counter()
 for r in rows:
  key=(r['file'],r['id']); old=r['translation']; s=OV.get(key,old); why=[]
  if s!=old: why.append('kaynak karşılaştırmalı son semantik/ifade düzeltmesi'); stats['override']+=1
  if r['file'].startswith(('50/','51/','52/','53/','54/')):
   notes=[]
   def repl(m):
    w=m.group(1); nw=PUZZLE_FIX.get(w,w)
    if nw!=w: notes.append(f'{w}→{nw}')
    return nw
   ns=WORD_RE.sub(repl,s)
   if ns!=s: s=ns; why.append('bulmaca imla: '+', '.join(notes)); stats['puzzle_word']+=len(notes)
  # context phrases
  ph=[
   (r"\bA'yi\b","A'yı"),(r'\bGünün isini\b','Günün işini'),(r'\bisini zorlaştırırsın\b','işini zorlaştırırsın'),
   (r'\bçizgi isini görür\b','çizgi işini görür'),(r'\beleme isini tamamla\b','eleme işini tamamla'),
   (r'\bIsine yaradı mı\b','İşine yaradı mı'),(r'\bSirk sefi\b','Sirk şefi'),(r'\bbasi belaya\b','başı belaya'),
   (r'\bon yarısını\b','ön yarısını'),(r'\bKaro Asi\b','Karo Ası'),(r'\ba\?tesi\b','ateşi'),
   (r'\bsu atesi\b','su ateşi'),(r'\bSinirli taşlarınla\b','Sınırlı taşlarınla'),
  ]
  for a,b in ph:
   ns,n=re.subn(a,b,s)
   if n: s=ns; why.append(f'bağlam imlası: {a}→{b}'); stats['phrase']+=n
  s=unicodedata.normalize('NFC',s)
  if controls(s)!=controls(old):
   bad.append({'file':r['file'],'id':r['id'],'before':controls(old),'after':controls(s)}); s=old; why=['kontrol kodu güvenliği nedeniyle geri alındı']; stats['revert']+=1
  if s!=old:
   w,chg,reason=v4.wrap_final(r['original'],s,adv)
   if chg and controls(w)==controls(old): s=w; why.append(reason); stats['wrap']+=1
  px=v4.max_px(s,adv); limit=348 if ('<T>' in r['original'] or (base.JP_RE.search(r['original']) and r['original'].count('\n')<=2)) else 399
  if px>limit: over.append({'file':r['file'],'id':r['id'],'px':px,'limit':limit,'translation':s})
  if s!=old: changes.append({'file':r['file'],'id':r['id'],'neden':'; '.join(why),'once':old,'sonra':s,'kaynak':r['original']}); stats['changed']+=1
  r['translation']=s; outmap[key]=s
 with CSV.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['file','id','offset','original','translation']);w.writeheader();w.writerows(rows)
 # jsonl
 out=[]
 for line in JSONL.read_text(encoding='utf-8').splitlines():
  o=json.loads(line)
  if o.get('kind')=='text': o['translation']=outmap.get((o['file'],o['id']),o.get('translation',''))
  out.append(json.dumps(o,ensure_ascii=False,separators=(',',':')))
 JSONL.write_text('\n'.join(out)+'\n',encoding='utf-8')
 ers=list(csv.DictReader(EASY.open(encoding='utf-8-sig',newline='')))
 for rr in ers:
  k=(rr['file'],rr['id'])
  if k in outmap: rr['turkce']=outmap[k]
 with EASY.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['file','id','kaynak_japonca','turkce','durum']);w.writeheader();w.writerows(ers)
 # append hotfix report
 fields=['file','id','neden','once','sonra','kaynak']
 with (REP/'V6_SON_HOTFIX_RAPORU.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(changes)
 (REP/'V6_SON_HOTFIX_GUVENLIK.json').write_text(json.dumps(bad,ensure_ascii=False,indent=2),encoding='utf-8')
 with (REP/'V6_SON_HOTFIX_TASMA.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['file','id','px','limit','translation']);w.writeheader();w.writerows(over)
 print(json.dumps({'stats':dict(stats),'overflow':len(over),'badcodes':len(bad)},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
