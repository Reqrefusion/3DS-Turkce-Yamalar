import csv,json,re
from pathlib import Path
root=Path('/mnt/data/Layton_TR_Final_v7'); p=root/'ceviri/layton_tr.csv'
with p.open(encoding='utf-8-sig',newline='') as f:
 rd=csv.DictReader(f); fields=rd.fieldnames; rows=list(rd)
exact={
'Hakli':'Haklı','haklidir':'haklıdır','hakliydin':'haklıydın','hakliymissiniz':'haklıymışsınız','haklisindir':'haklısındır',
'bakisini':'bakışını','bakisindan':'bakışından','issizlik':'ıssızlık','kaybolusuna':'kayboluşuna','kaybolusunu':'kayboluşunu','olusunu':'oluşunu',
'çıkarin':'çıkarın','kralicenizden':'kraliçenizden','Hayatinin':'Hayatının','kitabiyim':'kitabıyım','kitabim':'kitabım','kitabimi':'kitabımı',
'Inis':'İniş','inisin':'inişin','islerim':'işlerim','isleriniz':'işleriniz','islerinizi':'işlerinizi','islerin':'işlerin','isini':'işini','isinmaya':'ısınmaya',
'tasli':'taşlı','kus':'kuş','Kus':'Kuş','yas':'yaş',
}
pat=re.compile(r'(?<![\wÇĞİÖŞÜçğıöşüÂÎÛâîû])('+'|'.join(map(re.escape,sorted(exact,key=len,reverse=True)))+r')(?![\wÇĞİÖŞÜçğıöşüÂÎÛâîû])')
changes=[]
for r in rows:
 b=r['translation']; s=pat.sub(lambda m: exact[m.group(1)],b)
 # source-aware phrase improvements
 if (r['file'],r['id'])==('40/40_002400.xs','text000007'):
  s=s.replace('Ee... güç haklıdır!','Ee... güçlü olan haklıdır!')
 if (r['file'],r['id'])==('40/40_001010.xs','text000033'):
  s=s.replace("Thornley's\nGörge",'Thornley Boğazı').replace("Thornley's Görge",'Thornley Boğazı')
 if s!=b:
  r['translation']=s; changes.append((r['file'],r['id'],b,s))
with p.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
with (root/'ceviri/layton_tr.jsonl').open('w',encoding='utf-8') as f:
 for r in rows: f.write(json.dumps(r,ensure_ascii=False)+'\n')
# regenerate easy from current if recognizable
pe=root/'ceviri/CEVIRI_KOLAY.csv'
if pe.exists():
 with pe.open(encoding='utf-8-sig',newline='') as f:
  rd=csv.DictReader(f); ef=rd.fieldnames; er=list(rd)
 tc=next((c for c in ef if c.lower() in ('translation','ceviri','çeviri','turkce','türkçe')),None)
 if tc:
  d={(r['file'],r['id']):r['translation'] for r in rows}
  for e in er:
   k=(e.get('file',''),e.get('id',''))
   if k in d:e[tc]=d[k]
  with pe.open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.DictWriter(f,fieldnames=ef);w.writeheader();w.writerows(er)
print('stem_changed',len(changes))
