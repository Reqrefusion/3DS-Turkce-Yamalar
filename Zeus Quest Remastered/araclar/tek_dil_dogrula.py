#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aşama 34: orijinal kaynak oyunla karşılaştırmalı EN-only LayeredFS doğrulaması."""
import argparse,json,zipfile,collections,sys,re,hashlib
from pathlib import Path
from zeusquest_tool import (AssetFile,metadata_read,read_csv,LANGS,METADATA,FONT_ASSET,
                           u32,i64,bitmap_coverage)
from turkce_font import LETTERS

def verify(game,patch,encsv,uicsv,report=None):
    with zipfile.ZipFile(game) as g,zipfile.ZipFile(patch) as p:
        assert p.testzip() is None, 'Yama ZIP bozuk'
        files=set(p.namelist())-{'README_PATCH.txt'}
        assert METADATA in files and FONT_ASSET in files, 'Yama metadata / font eksik'
        src,_=metadata_read(g.read(METADATA))
        dst,_=metadata_read(p.read(METADATA))
        assert len(src)==len(dst),'metadata satır sayısı değişti'
        en=read_csv(Path(encsv));ui=read_csv(Path(uicsv))
        start,end=LANGS['EN']
        en_keys=set();count=0
        for r in en:
            i=int(r['meta_index']);assert start<=i<end and r['id']==f'META:{i}' and r['kaynak_dil']=='EN'
            assert i not in en_keys;en_keys.add(i)
            assert src[i]==r['kaynak_metin'],f'İngilizce kaynak uyuşmazlığı: {i}'
            expected=r.get('turkce','') or src[i]
            assert dst[i]==expected,f'İngilizce çeviri uyuşmazlığı: {i}'
            count+=expected!=src[i]
        assert len(en_keys)==end-start,'EN kapsamı eksik'
        assert all(src[i]==dst[i] for i in range(len(src)) if i not in en_keys),'EN dışı metadata değişmiş!'
        byfile=collections.defaultdict(list)
        for row in ui:
            byfile[row['dosya']].append(row)
        ui_changed=0;expected_files={METADATA,FONT_ASSET}
        actual_labels=collections.Counter()
        for file,rows in byfile.items():
            orig=AssetFile(g.read(file))
            altered=(AssetFile(p.read(file)) if file in files else orig)
            diff_ids={}
            for r in rows:
                pid=int(r['path_id']); assert r['id']==f'UI:{file}:{pid}'
                d0=orig.object_bytes(orig.index[pid]); d1=altered.object_bytes(altered.index[pid])
                assert orig.index[pid]['class']==114 and i64(d0,20)==385
                sl=u32(d0,248);tl=u32(d1,248)
                s0=d0[252:252+sl].decode('utf-8');s1=d1[252:252+tl].decode('utf-8')
                assert s0==r['kaynak_metin']
                expected=r.get('turkce','') or s0
                assert s1==expected,f'UI eksik/yanlış: {file} {pid} beklenen {expected}'
                if s0!=s1:ui_changed+=1;diff_ids[pid]=expected
                if s0=='Music':actual_labels[(file,pid)]=s1
            if diff_ids:expected_files.add(file)
            # All other Unity objects must be bytewise unchanged (except original text objs).
            if file in files:
                assert len(orig.objects)==len(altered.objects)
                for obj in orig.objects:
                    if obj['pid'] not in diff_ids and not (file==FONT_ASSET and obj['class'] in (28,128)):
                        assert orig.object_bytes(obj)==altered.object_bytes(altered.index[obj['pid']]),f'Diğer Unity nesnesi değişmiş: {file}:{obj["pid"]}'
        assert set(files)==expected_files, f'Beklenmeyen/eksik yama dosyası: {set(files)^expected_files}'
        assert actual_labels=={
            ('romfs/Data/sharedassets1.assets',526):'Müzik',
            ('romfs/Data/sharedassets1.assets',532):'Müzik'},'Music çevirileri eksik'
        music_meta=[(i,src[i],dst[i]) for i in range(start,end) if src[i]=='Music Settings']
        assert music_meta and all(v=='Müzik Ayarları' for i,s,v in music_meta)
        # Font exists, Unicode coverage and existing codes are retained.
        from zeusquest_tool import bitmap_coverage
        f0=bitmap_coverage(g);f1=bitmap_coverage(p)
        assert f0 and f1 and len(f0[1])==517 and len(f1[1])==525
        assert set(f0[1])<=set(f1[1]) and set(map(ord,LETTERS))<=set(f1[1])
        used=''.join(r['turkce'] for r in en+ui)
        missing=sorted({ch for ch in used if ord(ch)>32 and ord(ch) not in f1[1]})
        assert not missing,f'Fontta eksik karakterler: {missing}'
        summ={'dil_yuvasi':'EN','ingilizce_satir':len(en),'degisen_en':count,'ui_satir':len(ui),'degisen_ui':ui_changed,
              'music_ui_labels':{f'{k[0]}:{k[1]}':v for k,v in actual_labels.items()},
              'music_settings':'Müzik Ayarları', 'yunanca_fransizca_diger_metadata':'BIREBIR_KORUNDU',
              'font_glif':len(f1[1]),'fontta_eksik_karakter':missing,'yamalanan_dosya':len(files),
              'yama_icerigi':sorted(files),'test_turu':'statik dosya testi; 3DS/emulator oynanış testi yapılmadı'}
        if report:Path(report).write_text(json.dumps(summ,indent=2,ensure_ascii=False),encoding='utf8')
        print('DOĞRULAMA BAŞARILI\n'+json.dumps({k:v for k,v in summ.items() if k!='yama_icerigi'},ensure_ascii=False,indent=2))
        return summ

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--game',required=True);a.add_argument('--patch',required=True);a.add_argument('--en',required=True);a.add_argument('--ui',required=True);a.add_argument('--report');p=a.parse_args()
    try:verify(p.game,p.patch,p.en,p.ui,p.report)
    except Exception as e:print('DOĞRULAMA HATASI:',e,file=sys.stderr);sys.exit(1)
