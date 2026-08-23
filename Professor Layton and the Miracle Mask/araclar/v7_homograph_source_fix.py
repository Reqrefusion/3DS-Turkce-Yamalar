import csv,json,re
from pathlib import Path
root=Path('/mnt/data/Layton_TR_Final_v7'); p=root/'ceviri/layton_tr.csv'
with p.open(encoding='utf-8-sig',newline='') as f:
 rd=csv.DictReader(f); fields=rd.fieldnames; rows=list(rd)
R={}
def add(f,i,*pairs): R.setdefault((f,i),[]).extend(pairs)
# Homographs resolved against source
add('05/05_050810.xs','text000039',('bu tur','bu tür'))
for k in [('04/04_040130.xs','text000027'),('40/40_002100.xs','text000089'),('81/81_000020.xs','text000052')]: add(*k,('sus','süs'))
for tid in ['text000002','text000007']: add('50/50_000033.xs',tid,('Asi','Ası'))
add('01/01_010270.xs','text000009',('yonun','yönün'),('Şu esrarengiz','şu esrarengiz'),('coook','çoook'))
add('07/07_070260.xs','text000014',('vicdanimi','vicdanımı'),('utanc','utanç'))
add('07/07_071020.xs','text000010',('vicdanim','vicdanım'))
add('40/40_001000.xs','text000035',('operasyon ussu','operasyon üssü'),('karargahı','karargâhı'))
add('05/05_050661.xs','text000011',('siz ucunuz','siz üçünüz'))
add('09/09_090180.xs','text000014',('gereken sani','gereken şanı'))
add('82/82_001000.xs','text000403',('kullanirim','kullanırım'))
add('04/04_040055.xs','text000005',('kocanin','koçanın'))
add('30/30_008070.xs','text000006',('bel kiran','bel kıran'))
add('06/06_060110.xs','text000005',('noktaya\ndon','noktaya\ndön'),('noktaya don','noktaya dön'))
add('40/40_001000.xs','text000115',('barisi','barışı'),('İnsan sayısı','insan sayısı'))
add('52/52_000038.xs','text000001',('gücünü asar','gücünü aşar'))
for k in [('18/18_182051.xs','text000001'),('30/30_002010.xs','text000001')]: add(*k,('Malikanesi','Malikânesi'))
for k in [('40/40_001000.xs','text000079'),('40/40_001100.xs','text000032')]: add(*k,('Ledorelarin','Ledoreların'))
for k in [('01/01_010335.xs','text000034'),('03/03_030030.xs','text000003'),('07/07_070510.xs','text000013'),('08/08_080140.xs','text000016'),('15/15_000030.xs','text000011')]: add(*k,('yari','yarı'))
for k in [('82/82_001000.xs','text000139'),('82/82_001000.xs','text000153'),('82/82_001000.xs','text000290'),('82/82_001000.xs','text000348')]: add(*k,('sefi','şefi'))
for k in [('03/03_030630.xs','text000005'),('05/05_050140.xs','text000007'),('40/40_001200.xs','text000111'),('81/81_000100.xs','text000015')]: add(*k,('esi','eşi'))
for k in [('06/06_067609.xs','text000004'),('40/40_001010.xs','text000041'),('80/80_000200.xs','text000015')]: add(*k,('kil payı','kıl payı'))
# one semantic overcorrection: regal/noble, not 'main'
add('81/81_000100.xs','text000015',('popüler asıl muzun','popüler asil muzun'))
# remaining suffix spellings from exact-source review
add('40/40_001200.xs','text000057',('bakisini','bakışını'),('pek azi','pek azı'))
add('82/82_003090.xs','text000003',('bakisini','bakışını'))
add('82/82_000002.xs','text000013',('bakisindan','bakışından'))
# title/wording consistency
add('40/40_001000.xs','text000156',('Yeraltına Inis','Yeraltına İniş'))
add('40/40_001010.xs','text000037',('zorlu bir inisin','zorlu bir inişin'),('iyi mizahi','iyi mizahı'))
# explicit work/heating spellings missed by earlier exact map
for k in [('18/18_180040.xs','text000003'),('81/81_000010.xs','text000029')]: add(*k,('islerim','işlerim'))
add('01/01_010240.xs','text000009',('isleriniz','işleriniz'))
add('03/03_030135.xs','text000003',('islerinizi','işlerinizi'))
add('40/40_001000.xs','text000025',('islerin gidisi','işlerin gidişi'))
add('40/40_001200.xs','text000037',('isini','işini'))
add('06/06_060280.xs','text000001',('isinmaya','ısınmaya'),('Şu\nçürümüş','şu\nçürümüş'),('Şu çürümüş','şu çürümüş'))
# book/life forms
for k in [('07/07_070530.xs','text000001'),('09/09_093070.xs','text000001')]: add(*k,('kitabiyim','kitabıyım'))
add('07/07_071150.xs','text000013',('kitabim','kitabım'))
add('40/40_001010.xs','text000007',('kitabimi','kitabımı'))
add('06/06_060010.xs','text000001',('Hayatinin','Hayatının'))
# accent suffix forms
for rkey in [('01/01_010230.xs','text000010'),('05/05_050630.xs','text000052'),('05/05_050661.xs','text000018'),('07/07_070330.xs','text000009'),('08/08_080080.xs','text000017'),('08/08_080090.xs','text000054'),('20/20_200020.xs','text000006'),('20/20_200040.xs','text000009')]: add(*rkey,('çıkarin','çıkarın'))
add('03/03_030050.xs','text000002',('kralicenizden','kraliçenizden'))
# haklı forms and source-specific wordplay
for f,i in [('07/07_070230.xs','text000011'),('07/07_070410.xs','text000009'),('30/30_001020.xs','text000019')]: add(f,i,('Hakli','Haklı'))
add('40/40_001010.xs','text000033',('haklidir','haklıdır'),('issizlik','ıssızlık'))
add('01/01_010180.xs','text000049',('hakliydin','haklıydın'))
add('03/03_030484.xs','text000113',('hakliymissiniz','haklıymışsınız'))
add('06/06_060010.xs','text000020',('haklisindir','haklısındır'))
add('40/40_002400.xs','text000007',('güç haklidir','güçlü olan haklıdır'))
# disappearance morphology
for k in [('19/19_190410.xs','text000001'),('19/19_190415.xs','text000001')]: add(*k,('kaybolusuna','kayboluşuna'))
add('40/40_001000.xs','text000043',('kaybolusunu','kayboluşunu'),('inkar','inkâr'))
add('08/08_080050.xs','text000004',('yok olusunu','yok oluşunu'))

changes=[]
for r in rows:
 b=r['translation']; s=b
 for a,b2 in R.get((r['file'],r['id']),[]): s=s.replace(a,b2)
 if s!=b: r['translation']=s; changes.append((r['file'],r['id'],b,s))
with p.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
with (root/'ceviri/layton_tr.jsonl').open('w',encoding='utf-8') as f:
 for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
with (root/'raporlar/V7_KAYNAK_HOMOGRAF_DUZELTMELERI.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['file','id','once','sonra']);w.writerows(changes)
print('homograph_changed',len(changes))
