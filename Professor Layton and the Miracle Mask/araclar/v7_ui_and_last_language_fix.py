import csv,json,re
from pathlib import Path
root=Path('/mnt/data/Layton_TR_Final_v7'); p=root/'ceviri/layton_tr.csv'
with p.open(encoding='utf-8-sig',newline='') as f:
 rd=csv.DictReader(f); fields=rd.fieldnames; rows=list(rd)
R={}
def add(f,i,*pairs):R.setdefault((f,i),[]).extend(pairs)
# Last source-confirmed orthography / semantics
for k in [('18/18_181140.xs','text000002'),('20/20_200250.xs','text000085'),('20/20_200260.xs','text000042')]: add(*k,('inkar','inkâr'))
for k in [('01/01_010140.xs','text000034'),('50/50_000112.xs','text000008')]: add(*k,('utanc','utanç'))
add('40/40_001200.xs','text000089',('mahkum','mahkûm'),('Ustalığı\nsudur','Ustalığı\nşudur'),('Ustalığı sudur','Ustalığı şudur'))
add('30/30_008070.xs','text000006',('kiran','kıran'))
add('05/05_050800.xs','text000013',('en azi','en azı'))
add('40/40_001200.xs','text000085',('saclarinin','saçlarının'),("Şans Tanricasi'yla","Şans Tanrıçası'yla"))
add('05/05_050430.xs','text000003',('esinizi uzdum','eşinizi üzdüm'))
add('40/40_001000.xs','text000161',('yapisinda','yapısında'))
add('40/40_001000.xs','text000079',('eslik edip','eşlik edip'))
add('40/40_001200.xs','text000111',('Sık sık','sık sık'),('nehir kiyisinda','nehir kıyısında'))
add('81/81_000020.xs','text000016',('Bu asıl <CR>purple</CR>','Bu asil <CR>mor</CR>'))
# descriptive CR terms in collection/puzzle minigame. Proper item names are intentionally preserved.
common={
 'purple':'mor','white':'beyaz','Black':'siyah','black':'siyah',
 'apple':'elma','pineapple':'ananas','banana':'muz','cups':'fincanlar','teapot':'demlik','saucer':'tabak',
 'compass':'pusula','lantern':'fener','camera':'kamera','ocarina':'okarina','violin':'keman','doughnut':'donut',
 'loaf':'somun','cake':'kek','cactus':'kaktüs','flowers':'çiçekler','hat':'şapka','tie':'kravat','shoes':'ayakkabı',
 'bunny':'tavşan','teddies':'oyuncak ayılar','kitty':'kedi','teddy':'oyuncak ayı','car':'araba','helicopters':'helikopterler',
 'ship':'gemi','china':'porselen','clock':'saat','books':'kitaplar','painting':'tablo',
 'white teddy':'beyaz oyuncak ayı','white bunny':'beyaz tavşan'
}
changes=[]
for r in rows:
 b=r['translation']; s=b
 for a,b2 in R.get((r['file'],r['id']),[]):s=s.replace(a,b2)
 if r['file'].startswith('81/'):
  def cr(m):
   x=m.group(1); return '<CR>'+common.get(x,x)+'</CR>'
  s=re.sub(r'<CR>(.*?)</CR>',cr,s,flags=re.S)
 if s!=b:
  r['translation']=s;changes.append((r['file'],r['id'],b,s))
with p.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
with (root/'ceviri/layton_tr.jsonl').open('w',encoding='utf-8') as f:
 for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
with (root/'raporlar/V7_UI_VE_SON_DIL_DUZELTMELERI.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['file','id','once','sonra']);w.writerows(changes)
print('last_changed',len(changes))
