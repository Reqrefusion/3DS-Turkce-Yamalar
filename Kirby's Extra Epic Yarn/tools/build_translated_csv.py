from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ktl.project import read_zip_languages

def main():
    ap=argparse.ArgumentParser(description='Kaynak ZIP + Türkçe etiket sözlüğünden tüm dilleri yan yana CSV üretir.')
    ap.add_argument('source',nargs='?',default=str(ROOT/'input'/'source.zip'))
    ap.add_argument('translations',nargs='?',default=str(ROOT/'data'/'translations_tr.json'))
    ap.add_argument('out',nargs='?',default=str(ROOT/'data'/'Kirby_TR_regenerated.csv'))
    a=ap.parse_args()
    langs,rows=read_zip_languages(a.source)
    tr=json.loads(Path(a.translations).read_text(encoding='utf-8'))
    missing=[]
    for r in rows:
        label=r['Label']; value=tr.get(label,'')
        if not value and r.get('EU_English','').strip(): missing.append(label)
        r['Turkish']=value; r['Status']='FINAL_REVIEWED' if value else 'INTENTIONAL_EMPTY'; r['Notes']='EU metin yapısı korunarak translations_tr.json üzerinden üretildi.'
    if missing: raise SystemExit('Eksik Türkçe etiket: '+', '.join(missing[:30]))
    fields=['Index','Label']+langs+['Turkish','Status','Notes']
    with open(a.out,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    print(f'OK: {len(rows)} satır -> {a.out}')
if __name__=='__main__':main()
