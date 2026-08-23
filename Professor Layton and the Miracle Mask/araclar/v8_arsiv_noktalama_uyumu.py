from pathlib import Path
import csv,json
root=Path('/mnt/data/Layton_TR_Final_v8')
rows=list(csv.DictReader((root/'ceviri/layton_tr.csv').open(encoding='utf-8-sig',newline='')))
mp=str.maketrans({'‘':"'",'’':"'",'‚':"'",'“':'"','”':'"','„':'"','–':'-','—':'-','\u00a0':' '})
changes=[]
for r in rows:
    old=r['translation']; new=old.translate(mp)
    # final source-reviewed imla fixes exposed by byte-roundtrip examples
    new=new.replace('pesini bırakmadığınızı','peşini bırakmadığınızı')
    new=new.replace("Athena'nin bilgeliği","Athena'nın bilgeliği")
    if new!=old:
        reasons=[]
        if old.translate(mp)!=old: reasons.append('Oyun enjektörünün gerçek saklama biçimiyle uyum için desteklenmeyen tipografik noktalama ASCII eşdeğerine normalize edildi.')
        if 'pesini bırakmadığınızı' in old: reasons.append('“peşini” yazımı düzeltildi.')
        if 'Athena' in old and 'bilgeliği' in old: reasons.append("Athena'nın iyelik eki düzeltildi.")
        changes.append({'file':r['file'],'id':r['id'],'reason':' '.join(reasons),'before':old,'after':new,'source':r['original']})
        r['translation']=new
fields=['file','id','offset','original','translation']
for out in [root/'ceviri/layton_tr.csv',root/'ceviri/CEVIRI_KOLAY.csv']:
    with out.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
# semantic/source-review project structure (template source fields)
tpl=root/'raporlar/orijinal_yedek/layton_tr_v2.jsonl'; cur={(r['file'],r['id']):r['translation'] for r in rows}
with tpl.open(encoding='utf-8') as fi,(root/'ceviri/layton_tr.jsonl').open('w',encoding='utf-8',newline='\n') as fo:
    for line in fi:
        o=json.loads(line)
        if o.get('kind')=='text': o['translation']=cur[(o['file'],o['id'])]
        fo.write(json.dumps(o,ensure_ascii=False,separators=(',',':'))+'\n')
# injection project uses source hashes freshly exported from supplied base archive
base=Path('/mnt/data/v8_base_export.jsonl')
with base.open(encoding='utf-8') as fi,(root/'ceviri/layton_tr_inject_v8.jsonl').open('w',encoding='utf-8',newline='\n') as fo:
    for line in fi:
        o=json.loads(line)
        if o.get('kind')=='text': o['translation']=cur[(o['file'],o['id'])]
        fo.write(json.dumps(o,ensure_ascii=False,separators=(',',':'))+'\n')
rp=root/'raporlar/V8_ARSIV_NOKTALAMA_UYUMU.csv'
with rp.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['file','id','reason','before','after','source']);w.writeheader();w.writerows(changes)
print('changes',len(changes))
