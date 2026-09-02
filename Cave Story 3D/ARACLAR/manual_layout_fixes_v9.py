#!/usr/bin/env python3
from pathlib import Path
import argparse, csv
FIXES={
'armsitem.sjs':[
("Arthur'un mezar taşının yakınında bulundu.","Arthur'un mezarının yanında bulundu.","227px üstü satır; anlam korunarak doğal ve kısa ifade."),
("Toplantı Salonu'ndaki şöminede bulundu.","Toplantı Salonu şöminesinde bulundu.","Metin kutusu genişliğini aşan satır kısaltıldı."),
("Ma Pignon'dan alınmış bir mantar rozeti.","Ma Pignon'dan aldığın mantar rozeti.","Daha doğal Türkçe ve daha kısa satır."),
("gerekiyordu; sanırım işini de yapıyordu...","bekleniyordu; işini de yaptı sanırım...","Uzun satır kısaltıldı, kaynak anlam korundu."),
("dört yönden birine doğru hızlanabilirsin.","dört yönden birine hızlanabilirsin.","Gereksiz 'doğru' kaldırıldı; satır genişliği düşürüldü."),
("bulduğu sandıklarda uyumayı ÇOK sever.","bulduğu sandıklarda uyumaya bayılır.","Daha doğal ve kısa Türkçe."),
("güçlendirmek için ateş tuşunu basılı tut.","ateş tuşunu basılı tutarak güçlendir.","Daha dengeli satır ve doğal emir cümlesi."),
("Chaba tarafından Labirent\r\nDükkânı'nda yapıldı.","Chaba, Labirent Dükkânı'nda yaptı.","Dört satırlık eşya açıklaması üç satıra indirildi."),
],
'stage/ring3.sjs':[("Buradan canlı çıkmana izin vermeyeceğim!!!","Buradan sağ çıkmana izin vermem!!!","Tehdit tonu korunup satır gerçek piksel genişliğine uyarlandı.")],
'stage/tt_ballo1.sjs':[("Kutsal Alan Süre Denemesi'ni tamamladın!","Kutsal Alan süre denemesini bitirdin!","234px satır kısaltıldı; anlam korunuyor.")],
'stage/almond.sjs':[("Çekme Halatını Curly'nin etrafına sardın.","Çekme Halatını Curly'ye sardın.","Kaynak eylem korunarak uzun satır sadeleştirildi.")],
'stage/cent.sjs':[("Ma Pignon'u Curly'nin ağzına tıkıştırdın.","Ma Pignon'u Curly'nin ağzına koydun.","Kaynak eylemi koruyan daha doğal ve kısa Türkçe.")],
'stage/hell2.sjs':[("Sevdiği hayat,\r\nbir gecede harabeye döndü...\r\n...Yalnız kızgın küllerin altında\r\nkaldı.","Sevdiği hayat bir gecede\r\nharabeye döndü...\r\n...Yalnız kızgın küllerle örtüldü.","Dört satır üç satıra indirildi; kaynak 'shrouded by ashes' daha doğru aktarıldı.")],
'stage/tt_hell2.sjs':[("Sevdiği hayat,\r\nbir gecede harabeye döndü...\r\n...Yalnız kızgın küllerin altında\r\nkaldı.","Sevdiği hayat bir gecede\r\nharabeye döndü...\r\n...Yalnız kızgın küllerle örtüldü.","Dört satır üç satıra indirildi; kaynak anlam düzeltildi.")],
'stage/momo.sjs':[("Doktor'dan ilk kaçan\r\nItoh oldu; ama\r\nburadan çok uzaklaştığını\r\nsan mıyorum.","Doktor'dan ilk kaçan Itoh'du;\r\nama buradan fazla uzağa\r\ngidemediğini düşünüyorum.","Dört satır üç satıra indirildi.")],
'stage/oside.sjs':[("Kaçtıktan sonra sen ve Kazuma,\r\ndağların güvenli koynunda,\r\ngözlerden uzakta\r\nmütevazı bir hayat sürdünüz...","Kaçtıktan sonra sen ve Kazuma,\r\ndağların güvenli koynunda,\r\ngözlerden uzak yaşadınız...","Dört satır üç satıra indirildi; bitiş anlatımı sadeleştirildi.")],
'stage/shelt.sjs':[("Kazuma: ve hayır, annem yanımda\r\ndeğil\r\nKazuma: korkarım hâlâ\r\nDoktor'la olabilir","Kazuma: hayır, annem burada değil\r\nKazuma: korkarım hâlâ\r\nDoktor'la olabilir","Dört satır üç satıra indirildi, konuşma akışı düzeltildi.")],
}
# typo variant current V8 has 'sanmıyorum' not 'san mıyorum'
FIXES['stage/momo.sjs'].append(("Doktor'dan ilk kaçan\r\nItoh oldu; ama\r\nburadan çok uzaklaştığını\r\nsanmıyorum.","Doktor'dan ilk kaçan Itoh'du;\r\nama buradan fazla uzağa\r\ngidemediğini düşünüyorum.","Dört satır üç satıra indirildi."))

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--data',default=str(Path(__file__).resolve().parents[1]/'000400000004D200/romfs/data')); ap.add_argument('--report',default=str(Path(__file__).resolve().parents[1]/'RAPORLAR/SATIR_MANUEL_DUZELTMELERI_V9.tsv')); a=ap.parse_args()
 root=Path(a.data); rows=[]
 for rel,fixes in FIXES.items():
  p=root/rel; s=p.read_bytes().decode('cp1254','surrogateescape'); before=s
  for old,new,why in fixes:
   n=s.count(old)
   if n: s=s.replace(old,new); rows.append((rel,n,old.replace('\r','\\r').replace('\n','\\n'),new.replace('\r','\\r').replace('\n','\\n'),why))
  if s!=before: p.write_bytes(s.encode('cp1254','surrogateescape'))
 Path(a.report).parent.mkdir(parents=True,exist_ok=True)
 with open(a.report,'w',encoding='utf-8',newline='') as f:
  w=csv.writer(f,delimiter='\t'); w.writerow(['dosya','adet','eski','yeni','gerekce']); w.writerows(rows)
 print('applied',sum(r[1] for r in rows),'replacements in',len(set(r[0] for r in rows)),'files')
 for r in rows: print(r[0],r[1],r[4])
if __name__=='__main__': main()
