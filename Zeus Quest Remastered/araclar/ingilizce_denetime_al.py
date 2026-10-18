#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yalnızca görüntülenen metin CSV'leri için çeviri eksikliği adaylarını bulur.
Teknik etiketler, ekran dışı sabitler veya tam çeviri doğruluğu hakkında hüküm vermez.
"""
import argparse,csv,re,json
from pathlib import Path
from zeusquest_tool import read_csv,write_csv
ENGLISH_WORDS=re.compile(r"\b(?:music|settings|sound|language|continue|cancel|loading|pause|exit|quit|save game|new game|game over|inventory|press|click|start game|play game|the|your|you|please|with|this|those|that|would|could|should|there|where|which)\b",re.I)
MARKUP=re.compile(r'<[^>]+>')
UI_NON_TRANSLATABLE=re.compile(r'^[\d\s%.,/:+\-]+$')
METADATA_KNOWN_UNCHANGED={'META:7656','META:8007','META:8219','META:8221','META:8223','META:8234','META:8277','META:8296','META:9469'}

def audit(meta_csv,ui_csv,out):
    rows=[];stats={}
    for fn,kind in [(meta_csv,'METADATA_EN'),(ui_csv,'UNITY_UI')]:
        cur=read_csv(Path(fn));stats[kind]={'total':len(cur),'same':0,'different':0,'review':0}
        for r in cur:
            orig=r['kaynak_metin'];new=r.get('turkce','') or ''
            same=orig==new
            stats[kind]['same' if same else 'different']+=1
            problems=[]
            if not new.strip(): problems.append('BOS_CEVIRI')
            if same:
                if kind=='METADATA_EN':
                    if r['id'] not in METADATA_KNOWN_UNCHANGED:problems.append('AYNEN_KALAN_METIN')
                elif not UI_NON_TRANSLATABLE.fullmatch(orig):problems.append('AYNEN_KALAN_UI')
            hit=ENGLISH_WORDS.search(MARKUP.sub('',new))
            if hit:problems.append('INGILIZCE_KELIME: '+hit.group(0))
            if problems:
                stats[kind]['review']+=1
                rows.append({'id':r['id'],'tur':'OYUN_METNI' if kind=='METADATA_EN' else 'ARAYUZ',
                             'kaynak_metin':orig,'turkce':new,'kontrol_nedeni':'; '.join(problems),
                             'aciklama':'Aday - oyunda görünürlüğü veya anlamı elle doğrula'})
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    write_csv(out/'INGILIZCE_KALMIS_OLABILIR.csv',list(rows[0]) if rows else ['id','tur','kaynak_metin','turkce','kontrol_nedeni','aciklama'],rows)
    (out/'CEVIRI_DENETIMI.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Denetim:',stats,'\nAday listesi:',out/'INGILIZCE_KALMIS_OLABILIR.csv')
    return stats

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--en',required=True);p.add_argument('--ui',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();audit(a.en,a.ui,a.out)
