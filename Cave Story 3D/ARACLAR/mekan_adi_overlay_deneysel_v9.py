#!/usr/bin/env python3
"""Optional experimental Turkish map-name overlay.
Run on a copy of the V9 stable data directory. It injects MS2 top-screen text into events
that used <MNA in the English original. This is NOT the default because the native map-name
table lives outside the supplied ROMFS and this adds a short script wait.
"""
from pathlib import Path
import argparse,re,csv
MAP={
'0':'Hiçlik','almond':'Çekirdek','ballo1':'Mühür Odası','ballo2':'Mühür Odası','barr':'Kulübe','blcny1':'Balkon','blcny2':'Balkon','cave':'İlk Mağara','cemet':'Mezarlık','cent':'Plantasyon','centw':'Işınlayıcı','chako':"Chako'nun Evi",'clock':'Saat Odası','comu':'Toplantı Salonu','cthu':"Cthulhu'nun Kulübesi",'cthu2':"Cthulhu'nun Kulübesi",'curly':'Kum Bölgesi Konutu','curlys':'Küçük Oda','dark':'Terk Edilmiş Ev','detour1':'Yumurta Koridoru Sapağı','drain':'Karanlık Yer','egend1':'Yan Oda','egend2':'Yan Oda','egg1':'Yumurta No. 01','egg6':'Yumurta No. 06','eggr':'Yumurta Gözlem Odası','eggr2':'Yumurta Gözlem Odası','eggs':'Yumurta Koridoru','eggs2':'Yumurta Koridoru','eggx':'Yumurta No. 00','eggx2':'Yumurta No. 00','escape':'Çöken Kule','fall':'Düşüş','frog':'Sakız','gard':'Depo','hell1':'Kanlı Kutsal Alan - B1','hell2':'Kanlı Kutsal Alan - B2','hell3':'Kanlı Kutsal Alan - B3','hell4':'Geçit','hell42':'Geçit','island':'Ada','itoh':'Depo','jail1':'Hücre No. 1','jail2':'Hücre No. 2','jenka1':"Jenka'nın Evi",'jenka2':"Jenka'nın Evi",'little':'Küçük Ev','lounge':'Dinlenme Alanı','malco':'Güç Kaynağı Odası','mapi':'Depo','mazea':'Labirent Dükkânı','mazeb':'Labirent B','mazed':'Klinik Harabeleri','mazeh':'Labirent H','mazei':'Labirent I','mazem':'Labirent M','mazeo':'Kamp','mazes':'Kaya Odası','mazew':'Labirent W','mibox':'Kayıt Noktası','mimi':'Mimiga Köyü','momo':'Gizlenme Yeri','oside':'Dış Duvar','ostep':'Koridor','pens1':"Arthur'un Evi",'pens2':"Arthur'un Evi",'pixel':'Su Yolu Kulübesi','plant':'Yamashita Çiftliği','pole':'Silah Ustası','pool':'Rezervuar','prefa1':'Prefabrik Bina','prefa2':'Prefabrik Bina','prinny':'İç Duvar','prinny2':'Küçük Mezar','priso1':'Son Mağara','priso2':'Son Mağara (Gizli)','ring1':'Taht Odası','ring2':'Kralın Sofrası','ring3':'Karanlık Boşluk','river':'Su Yolu','sand':'Kum Bölgesi','sande':'Kum Bölgesi','santa':"Santa'nın Evi",'shelt':'Sığınak','start':'Başlangıç Noktası','statue':'Heykel Odası','stream':'Ana Damar','tt_ballo1':'Mühür Odası','tt_hell1':'Kanlı Kutsal Alan - B1','tt_hell2':'Kanlı Kutsal Alan - B2','tt_hell3':'Kanlı Kutsal Alan - B3','tt_hell42':'Geçit','tt_ostep':'Koridor','tt_start':'Başlangıç Noktası','tt_statue':'Heykel Odası','weed':'Çalılıklar','weedb':'Çalılık Kulübesi','weedd':'İnfaz Odası','weeds':'Kayıt Noktası'}
EV=re.compile(r'(?ms)^#(\d{4})\r?\n(.*?)(?=^#\d{4}|\Z)')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--original',default='/mnt/data/v9_work/orig/data');ap.add_argument('--data',required=True);ap.add_argument('--report');a=ap.parse_args();orig=Path(a.original);root=Path(a.data);rows=[]
 for op in sorted((orig/'stage').glob('*.sjs')):
  name=op.stem.lower();title=MAP.get(name)
  if not title:continue
  os=op.read_bytes().decode('cp1252','surrogateescape'); ids=[eid for eid,body in EV.findall(os) if '<MNA' in body]
  if not ids:continue
  lp=root/'stage'/op.name
  if not lp.exists():continue
  s=lp.read_bytes().decode('cp1254','surrogateescape')
  changed=0
  for eid in ids:
   pat=re.compile(r'(?ms)(^#'+re.escape(eid)+r'\r?\n)(.*?)(?=^#\d{4}|\Z)')
   m=pat.search(s)
   if not m:continue
   body=m.group(2)
   marker=f'<MS2<TUR{title}<WAI0040<CLO'
   if marker in body:continue
   pos=body.find('<END')
   if pos<0:continue
   body2=body[:pos]+marker+body[pos:]
   s=s[:m.start(2)]+body2+s[m.end(2):];changed+=1
  if changed:
   lp.write_bytes(s.encode('cp1254','surrogateescape'));rows.append((op.name,title,changed))
 if a.report:
  with open(a.report,'w',encoding='utf-8',newline='') as f:
   w=csv.writer(f,delimiter='\t');w.writerow(['dosya','turkce_ad','eklenen_event']);w.writerows(rows)
 print('files',len(rows),'events',sum(r[2] for r in rows))
if __name__=='__main__':main()
