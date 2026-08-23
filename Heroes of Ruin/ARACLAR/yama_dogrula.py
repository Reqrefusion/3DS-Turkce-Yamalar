#!/usr/bin/env python3
from pathlib import Path
import sys,struct
sys.path.insert(0,str(Path(__file__).resolve().parent))
from hor_formats import blz_decompress,parse_darc,bcfnt_codepoints,parse_strl_raw
base=Path(__file__).resolve().parents[1];title='0004000000074000';rom=base/'YAMA_HAZIR/luma/titles'/title/'romfs'
errs=[]; total=0
for p in sorted((rom/'_UK').glob('*.strl_')):
    try: total+=len(parse_strl_raw(blz_decompress(p.read_bytes())))
    except Exception as e: errs.append(f'{p.name}: {e}')

def secs(b):
    pos=struct.unpack_from('<H',b,6)[0]
    for _ in range(struct.unpack_from('<H',b,0x10)[0]):
        sz=struct.unpack_from('<I',b,pos+4)[0]
        yield pos,b[pos:pos+4],b[pos:pos+sz]
        pos+=sz

def txl_names(tx):
    cnt=struct.unpack_from('<H',tx,8)[0]; out=[]
    for i in range(cnt):
        st=12+struct.unpack_from('<I',tx,12+4*i)[0]; en=tx.index(0,st); out.append(tx[st:en].decode('ascii'))
    return out

def mat_entries(mat):
    cnt=struct.unpack_from('<I',mat,8)[0]; offs=[struct.unpack_from('<I',mat,12+4*i)[0] for i in range(cnt)]
    return [mat[off:(offs[i+1] if i+1<cnt else len(mat))] for i,off in enumerate(offs)]

ui=list((rom/'UI').glob('aniscene_*.arc_')); checked=0
for p in ui:
    try:
        packed=p.read_bytes(); raw=blz_decompress(packed); a=parse_darc(raw)
        if packed[-4:]==b'\0\0\0\0': errs.append(f'{p.name}: canonical BLZ yerine stored')
        paths={n.path for n in a.nodes if not n.is_dir}
        subs={'timg/tr_sub_bg.bclim','timg/tr_sub_text.bclim'}
        if not subs<=paths: continue
        checked+=1
        bc=[n for n in a.nodes if not n.is_dir and n.path.endswith('.bclyt')]
        if len(bc)!=1: raise ValueError(f'BCLYT sayısı {len(bc)}')
        b=raw[bc[0].field1:bc[0].field1+bc[0].field2]
        tx=mat=None; panes={}
        for pos,sig,sec in secs(b):
            if sig==b'txl1': tx=sec
            elif sig==b'mat1': mat=sec
            elif sig==b'pic1':
                name=sec[0x0c:0x1c].split(b'\0',1)[0].decode('ascii','replace')
                if name in ('TR_SubBG','TR_SubText'):
                    panes[name]={
                        'visible':bool(sec[8]&1),'alpha':sec[10],
                        'z':struct.unpack_from('<f',sec,0x2c)[0],
                        'mat':struct.unpack_from('<H',sec,0x5c)[0],
                        'uvs':struct.unpack_from('<H',sec,0x5e)[0]
                    }
        if tx is None or mat is None: raise ValueError('txl1/mat1 yok')
        names=txl_names(tx); mats=mat_entries(mat)
        timg={Path(n.path).name for n in a.nodes if not n.is_dir and n.path.startswith('timg/')}
        if not set(names)<=timg: errs.append(f'{p.name}: txl1 olmayan texture ismi içeriyor')
        if names[-2:]!=['tr_sub_bg.bclim','tr_sub_text.bclim']: errs.append(f'{p.name}: TR texture sırası bozuk')
        for pane_name, tex_name, want_z in [('TR_SubBG','tr_sub_bg.bclim',20.0),('TR_SubText','tr_sub_text.bclim',21.0)]:
            q=panes.get(pane_name)
            if not q: errs.append(f'{p.name}: {pane_name} pane yok'); continue
            if not q['visible'] or q['alpha']!=255 or abs(q['z']-want_z)>1e-5 or q['uvs']!=1:
                errs.append(f'{p.name}: {pane_name} görünürlük alanları bozuk {q}')
            if q['mat']>=len(mats): errs.append(f'{p.name}: {pane_name} material id taşmış'); continue
            me=mats[q['mat']]
            if len(me)<0x38: errs.append(f'{p.name}: material kısa'); continue
            flags=struct.unpack_from('<I',me,0x30)[0]
            if (flags&3)!=1: errs.append(f'{p.name}: {pane_name} texmap sayısı !=1')
            texidx=struct.unpack_from('<H',me,0x34)[0]
            if texidx>=len(names) or names[texidx]!=tex_name:
                errs.append(f'{p.name}: {pane_name} material texture zinciri yanlış ({texidx})')
        for sp in subs:
            n=next(x for x in a.nodes if not x.is_dir and x.path==sp); x=raw[n.field1:n.field1+n.field2]
            if len(x)<0x28 or x[-0x28:-0x24]!=b'CLIM': errs.append(f'{p.name}: {sp} CLIM yok'); continue
            baseoff=len(x)-0x28; fmt=struct.unpack_from('<I',x,baseoff+0x20)[0]; dl=struct.unpack_from('<I',x,baseoff+0x24)[0]
            if fmt!=8: errs.append(f'{p.name}: {sp} format {fmt}, beklenen RGBA4444=8')
            if dl!=baseoff: errs.append(f'{p.name}: {sp} data length yanlış')
            if not any(x[:baseoff]): errs.append(f'{p.name}: {sp} piksel verisi tamamen sıfır')
    except Exception as e: errs.append(f'{p.name}: {e}')
try:
    cps=bcfnt_codepoints(blz_decompress((base/'FONT/demo_font.bcfnt_').read_bytes()))
    need=set(map(ord,'ÇĞİÖŞÜçğıöşüÂâéîû'))
    if not need<=cps: errs.append('font: Türkçe CMAP eksik')
except Exception as e: errs.append(f'font: {e}')
print('STRL kayıt:',total);print('Altyazılı sahne arşivi:',checked);print('Font: OK' if not any(x.startswith('font:') for x in errs) else 'Font: HATA')
if errs:
    print('\nHATALAR:');print('\n'.join(errs));raise SystemExit(1)
print('Render zinciri pic1 -> mat1 -> txl1 -> BCLIM: OK')
print('Altyazı texture formatı: RGBA4444 (oyun içi kullanılan format)')
print('Pane Z: 20/21 (oyun sahne aralığı içinde)')
print('BLZ: canonical/sıkıştırılmış')
print('SONUÇ: OK')
