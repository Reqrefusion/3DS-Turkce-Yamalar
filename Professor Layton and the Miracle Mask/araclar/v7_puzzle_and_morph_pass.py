#!/usr/bin/env python3
from pathlib import Path
import csv,json,re,sys,unicodedata
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'araclar'))
import tr_iyilestir as base
import v4_quality_pass as v4
CSV=ROOT/'ceviri/layton_tr.csv';JSONL=ROOT/'ceviri/layton_tr.jsonl';EASY=ROOT/'ceviri/CEVIRI_KOLAY.csv';REP=ROOT/'raporlar'

def ctrl(s):return base.CTRL_RE.findall(s)

def tok_replace(s,m):
    rx=re.compile(r'(?<![A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû])('+'|'.join(sorted(map(re.escape,m),key=len,reverse=True))+r')(?![A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû])')
    return rx.sub(lambda x:m[x.group(1)],s)

# Kaynak bağlamıyla anlamı kesin olan genel yazım kalıntıları.
GENERAL={
'yasayanlar':'yaşayanlar','yasiyorsun':'yaşıyorsun','yasindayiz':'yaşındayız','yasanan':'yaşanan','yastan':'yaştan','yasiyoruz':'yaşıyoruz',
'yasayamam':'yaşayamam','yasindayim':'yaşındayım','yasayabilsem':'yaşayabilsem','yasayabilmek':'yaşayabilmek','yasarken':'yaşarken',
'yasiyorlar':'yaşıyorlar','yasayabiliyor':'yaşayabiliyor','yasayabilmesi':'yaşayabilmesi','yasayamaz':'yaşayamaz','yaslanmis':'yaşlanmış','Yasina':'Yaşına',
'yasar':'yaşar','yasa':'yaşa','yasarsin':'yaşarsın','yasayacaklari':'yaşayacakları','yasadilar':'yaşadılar','yasiyordu':'yaşıyordu',
'omur':'ömür','odunc':'ödünç','Odunc':'Ödünç','urun':'ürün','ozledi':'özledi','Aklinizi':'Aklınızı',
}
# Not: "yaslan" (duvara yaslan), "yasak" ve seken mermi anlamındaki "seker" özellikle yok.

PUZZLE={
'golfcu':'golfçü','gecelim':'geçelim','Semadan':'Şemadan','eslestirmek':'eşleştirmek','hesabi':'hesabı','gidisin':'gidişin','semasini':'şemasını',
'aliciyi':'alıcıyı','katildi':'katıldı','siluetlere':'silüetlere','siluetine':'silüetine','siluete':'silüete','kirdi':'kırdı','sapi':'sapı','sapin':'sapın',
'kocani':'koçanı','kir':'kır','atisin':'atışın','Için':'İçin','isliyordum':'işliyordum','isledim':'işledim','nakis':'nakış','besten':'beşten',
'asilmali':'asılmalı','kaldirisi':'kaldırışı','Hayatinizin':'Hayatınızın','Görüs':'Görüş','isitti':'işitti','hac':'haç','Onluk':'Önlük','katliyken':'katlıyken',
'askilar':'askılar','dizilisine':'dizilişine','Saliydi':'Salıydı','bakisi':'bakışı','adimi':'adımı','siluet':'silüet','siluetler':'silüetler',
'golfcu':'golfçü','semadan':'şemadan','semasi':'şeması','semayi':'şemayı','eslestir':'eşleştir','eslestirerek':'eşleştirerek',
}

ROW={
('50/50_000030.xs','text000002'):[('ucunun de','üçünün de')],
('50/50_000049.xs','text000003'):[('sapında sus','sapında süs'),('deseni disinin yani sıra','deseni dışının yanı sıra')],
('50/50_000049.xs','text000006'):[('hiç sus','hiç süs')],
('50/50_000097.xs','text000008'):[('sırası söyle','sırası şöyle')],
('50/50_000033.xs','text000002'):[('Karo Asi','Karo Ası')],
('50/50_000033.xs','text000003'):[("Karo Ası'dir","Karo Ası'dır"),('Ucundan','Ucundan')],
('50/50_000033.xs','text000006'):[('karo asi','karo ası'),('şeklinde bir sus','şeklinde bir süs')],
('50/50_000033.xs','text000008'):[('Karo asi','Karo ası')],
('40/40_001200.xs','text000037'):[('babasının / isini','babasının / işini')],
('82/82_000008.xs','text000046'):[('olarak ise alırım','olarak işe alırım')],
('82/82_001000.xs','text000117'):[('Gurultucu','Gürültücü')],
('40/40_002400.xs','text000066'):[('ve ise koyulalım','ve işe koyulalım')],
('05/05_050600.xs','text000005'):[('aklinizi basinizda','aklınızı başınızda')],
('08/08_080020.xs','text000017'):[('koyun','köyün')],
('40/40_001200.xs','text000017'):[('koyun','köyün')],
('40/40_001500.xs','text000035'):[('Koyun','Köyün')],
('81/81_000020.xs','text000017'):[('turudur','türüdür')],
('81/81_000020.xs','text000018'):[('turudur','türüdür')],
('40/40_001200.xs','text000037'):[('babasının / isini','babasının / işini')],
('07/07_071120.xs','text000014'):[('hani us','hanı üs')],
('02/02_020070.xs','text000008'):[('bu koyu','bu köyü'),('diplomasi almak','diploması almak')],
('02/02_020070.xs','text000010'):[('operasyon ussu','operasyon üssü'),('kullanirim','kullanırım')],
('02/02_020020.xs','text000006'):[("Azran'in","Azran'ın"),('esi benzeri','eşi benzeri')],
('02/02_020030.xs','text000004'):[('gecelim','geçelim')],
('02/02_020019.xs','text000010'):[('adimiz','adımız')],
('81/81_000007.xs','text000014'):[('<CR>green</CR>','<CR>yeşil</CR>'),(' urun ',' ürün ')],
('81/81_000100.xs','text000001'):[('Bir urun','Bir ürün')],
('05/05_050446.xs','text000020'):[('omur boyu','ömür boyu'),('havuc stogunuz','havuç stoğunuz')],
('06/06_068140.xs','text000002'):[('omur boyu','ömür boyu')],
('07/07_071232.xs','text000002'):[('odunc','ödünç')],
('30/30_008010.xs','text000003'):[('Odunc','Ödünç')],
('40/40_002100.xs','text000074'):[('Odunc','Ödünç')],
('82/82_001000.xs','text000351'):[('ozledi','özledi')],
}

COLOR={'green':'yeşil','yellow':'sarı','red':'kırmızı','blue':'mavi','Green':'Yeşil','Yellow':'Sarı','Red':'Kırmızı','Blue':'Mavi'}

def main():
 adv=base.load_adv(ROOT);rows=list(csv.DictReader(CSV.open(encoding='utf-8-sig',newline='')));outmap={};chg=[];stats=Counter();bad=[];over=[]
 for r in rows:
  key=(r['file'],r['id']);old=r['translation'];s=old;why=[]
  ns=tok_replace(s,GENERAL)
  if ns!=s:s=ns;why.append('Türkçe biçimbilim/imla kalıntısı');stats['general']+=1
  if r['file'].startswith(('50/','51/','52/','53/','54/')):
   ns=tok_replace(s,PUZZLE)
   if ns!=s:s=ns;why.append('bulmaca yönergesi/çözüm metni imla düzeltmesi');stats['puzzle']+=1
  # Renk kategorileri oyun verisiyle ilişkili; CR etiketi korunarak yalnız görünen sözcük çevrilir.
  for a,b in COLOR.items():
   ns=s.replace(f'<CR>{a}</CR>',f'<CR>{b}</CR>')
   if ns!=s:s=ns;why.append(f'renk etiketi çevirisi: {a}→{b}');stats['color']+=1
  # UI terminolojisi
  ns=s.replace('Touch Screen','Dokunmatik Ekran').replace('<CR>Submit</C>','<CR>Gönder</C>')
  if ns!=s:s=ns;why.append('İngilizce kalmış UI terimi Türkçeleştirildi');stats['ui']+=1
  for a,b in ROW.get(key,[]):
   if a in s:s=s.replace(a,b);why.append(f'kaynak bağlamı: {a}→{b}');stats['row']+=1
  s=unicodedata.normalize('NFC',s)
  if ctrl(s)!=ctrl(old):
   # CR/C gibi kontrol etiketlerinin içindeki görünen kelime değişimi kontrol dizisini değiştirmez.
   bad.append({'file':r['file'],'id':r['id'],'before':ctrl(old),'after':ctrl(s),'candidate':s});s=old;why=['kontrol kodu güvenliği nedeniyle geri alındı'];stats['revert']+=1
  if s!=old:
   w,d,reason=v4.wrap_final(r['original'],s,adv)
   if d and ctrl(w)==ctrl(old):s=w;why.append(reason);stats['wrap']+=1
  px=v4.max_px(s,adv);limit=348 if ('<T>' in r['original'] or (v4.JP_RE.search(r['original']) and r['original'].count('\n')<=2)) else 399
  if px>limit:over.append({'file':r['file'],'id':r['id'],'px':px,'limit':limit,'translation':s})
  if s!=old:chg.append({'file':r['file'],'id':r['id'],'neden':'; '.join(why),'once':old,'sonra':s,'kaynak':r['original']});stats['changed']+=1
  r['translation']=s;outmap[key]=s
 with CSV.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
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
 with EASY.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=ers[0].keys());w.writeheader();w.writerows(ers)
 with (REP/'V7_BULMACA_VE_IMLA_EK_RAPORU.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=['file','id','neden','once','sonra','kaynak']);w.writeheader();w.writerows(chg)
 (REP/'V7_BULMACA_VE_IMLA_KONTROL_GUVENLIK.json').write_text(json.dumps(bad,ensure_ascii=False,indent=2),encoding='utf-8')
 with (REP/'V7_BULMACA_VE_IMLA_TASMA.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=['file','id','px','limit','translation']);w.writeheader();w.writerows(over)
 print(json.dumps({'rows':len(rows),'stats':dict(stats),'badcodes':len(bad),'overflow':len(over)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
