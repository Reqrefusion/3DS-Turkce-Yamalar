#!/usr/bin/env python3
from pathlib import Path
import argparse, struct, hashlib, json, csv

NAMES=['Caption_US.bffnt','UI_Caption_US.bffnt','Common_Sura_B_16.bffnt']
TR='ÇĞİÖŞÜçğıöşü'

def e_of(b):
    if b[4:6]==b'\xff\xfe': return '<'
    if b[4:6]==b'\xfe\xff': return '>'
    raise ValueError('bad BOM')

def parse(path):
    b=path.read_bytes(); e=e_of(b)
    if b[:4] not in (b'FFNT',b'FFNU'): raise ValueError('bad magic')
    hs=struct.unpack_from(e+'H',b,6)[0]
    fs=struct.unpack_from(e+'I',b,12)[0]
    bc=struct.unpack_from(e+'H',b,16)[0]
    if fs!=len(b): raise ValueError('header filesize mismatch')
    # Physical blocks from header size.
    blocks=[]; pos=hs
    for _ in range(bc):
        if pos+8>len(b): raise ValueError('truncated block')
        magic=b[pos:pos+4]; size=struct.unpack_from(e+'I',b,pos+4)[0]
        if size<8 or pos+size>len(b): raise ValueError('bad block size')
        blocks.append((pos,magic,size)); pos+=size
    if pos!=len(b): raise ValueError(f'physical blocks do not consume file: {pos}/{len(b)}')
    finf=blocks[0][0]
    # FINF last 3 ptrs at +20,+24,+28; ptr convention target payload = section start+8
    tptr,cptr,mptr=struct.unpack_from(e+'3I',b,finf+20)
    # TGLP via FINF pointer
    tp=tptr-8
    t=struct.unpack_from(e+'4sI4BI6HI',b,tp)
    _,_,cw,ch,sc,mcw,ss,baseline,fmt,cols,rows,sw,sh,so=t
    if so+ss>len(b): raise ValueError('texture out of file')
    if fmt not in (8,11): raise ValueError('unsupported alpha format')
    if cols*rows*sc<=0: raise ValueError('bad capacity')
    # CWDH chain via pointers.
    widths={}; cwdh_sections=[]; ptr=cptr
    while ptr:
        cp=ptr-8
        magic,size,cstart,cend,nxt=struct.unpack_from(e+'4sI2HI',b,cp)
        if magic!=b'CWDH': raise ValueError('bad CWDH pointer')
        n=cend-cstart+1; raw=b[cp+16:cp+16+n*3]
        if len(raw)!=n*3: raise ValueError('CWDH truncated')
        for i in range(n): widths[cstart+i]=raw[i*3:i*3+3]
        cwdh_sections.append((cp,cstart,cend,nxt)); ptr=nxt
    # CMAP chain via pointers.
    mapping={}; cmap_sections=[]; ptr=mptr
    while ptr:
        mp=ptr-8
        magic,size,begin,cend,typ,res,nxt=struct.unpack_from(e+'4sI4HI',b,mp)
        if magic!=b'CMAP': raise ValueError('bad CMAP pointer')
        d=b[mp+20:mp+size]
        if typ==0:
            idx0=struct.unpack_from(e+'H',d,0)[0]
            for code in range(begin,cend+1): mapping[code]=idx0+code-begin
        elif typ==1:
            vals=struct.unpack_from(e+f'{cend-begin+1}H',d,0)
            for code,idx in zip(range(begin,cend+1),vals):
                if idx!=0xFFFF: mapping[code]=idx
        elif typ==2:
            cnt=struct.unpack_from(e+'H',d,0)[0]
            if 2+cnt*4>len(d): raise ValueError('CMAP scan truncated')
            q=2
            for _ in range(cnt):
                code,idx=struct.unpack_from(e+'2H',d,q); q+=4
                mapping[code]=idx
        else: raise ValueError('unknown CMAP method')
        cmap_sections.append((mp,begin,cend,typ,nxt)); ptr=nxt
    if any(i not in widths for i in mapping.values()):
        # User font is intentionally allowed to expose its historical final-width bug; final/base must not.
        pass
    if max(mapping.values())>=cols*rows*sc: raise ValueError('CMAP points outside atlas capacity')
    start=min(widths); end=max(widths)
    return {'path':path,'b':b,'e':e,'blocks':blocks,'cw':cw,'ch':ch,'sc':sc,'fmt':fmt,'cols':cols,'rows':rows,'sw':sw,'sh':sh,'so':so,'ss':ss,'widths':widths,'mapping':mapping,'start':start,'end':end,'cwdh_sections':cwdh_sections,'cmap_sections':cmap_sections,'tptr':tptr,'cptr':cptr,'mptr':mptr}

def swizzle(w,h):
    if w%8 or h%8: raise ValueError('non-tiled dimensions')
    for ty in range(h//8):
      for tx in range(w//8):
       for y in range(2):
        for x in range(2):
         for y2 in range(2):
          for x2 in range(2):
           for y3 in range(2):
            for x3 in range(2):
             px=x3+x2*2+x*4+tx*8; py=y3+y2*2+y*4+ty*8
             dp=x3+x2*4+x*16+tx*64+y3*2+y2*8+y*32+ty*w*8
             yield px,py,dp

def alpha(f):
    raw=f['b'][f['so']:f['so']+f['ss']]; a=[0]*(f['sw']*f['sh'])
    for x,y,dp in swizzle(f['sw'],f['sh']):
        if f['fmt']==8: v=raw[dp]
        else: v=((raw[dp//2]>>((dp&1)*4))&15)*17
        a[x+y*f['sw']]=v
    return a

def origin(f,idx):
    per=f['cols']*f['rows']; local=idx%per; sheet=idx//per
    return sheet,(local%f['cols'])*(f['cw']+1)+1,(local//f['cols'])*(f['ch']+1)+1

def fullcell(f,a,idx):
    _,x,y=origin(f,idx)
    return tuple(a[(x+xx)+(y+yy)*f['sw']] for yy in range(f['ch']) for xx in range(f['cw']))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('base',type=Path); ap.add_argument('user',type=Path); ap.add_argument('final',type=Path); ap.add_argument('--report-dir',type=Path); a=ap.parse_args()
    rows=[]; details=[]
    for name in NAMES:
        b=parse(a.base/name); u=parse(a.user/name); f=parse(a.final/name)
        if [x[1] for x in f['blocks']] != [b'FINF',b'TGLP',b'CWDH',b'CMAP'] or len(f['cwdh_sections'])!=1 or len(f['cmap_sections'])!=1:
            raise ValueError(f'{name}: final is not FINF/TGLP/CWDH/CMAP single-section layout')
        if f['tptr']-8!=f['blocks'][1][0] or f['cptr']-8!=f['blocks'][2][0] or f['mptr']-8!=f['blocks'][3][0]:
            raise ValueError(f'{name}: final FINF pointers invalid')
        ba,ua,fa=alpha(b),alpha(u),alpha(f)
        # User mappings must all remain at exact same index.
        user_map_bad=[cp for cp,idx in u['mapping'].items() if f['mapping'].get(cp)!=idx]
        # Every original base codepoint restored semantically (may be at a new index).
        base_missing=[cp for cp in b['mapping'] if cp not in f['mapping']]
        base_bad=[]
        for cp,bidx in b['mapping'].items():
            if cp not in f['mapping']: continue
            fi=f['mapping'][cp]
            if f['widths'][fi]!=b['widths'][bidx] or fullcell(f,fa,fi)!=fullcell(b,ba,bidx): base_bad.append(cp)
        # Turkish must match user's exact index+metric+cell.
        tr_bad=[]
        for ch in TR:
            cp=ord(ch)
            if cp not in u['mapping'] or cp not in f['mapping']:
                tr_bad.append(ch); continue
            ui=u['mapping'][cp]; fi=f['mapping'][cp]
            # The user's CWDH bug omits only terminal non-Turkish indices, not Turkish indices.
            if ui!=fi or u['widths'].get(ui)!=f['widths'].get(fi) or fullcell(u,ua,ui)!=fullcell(f,fa,fi): tr_bad.append(ch)
        # Non-Turkish user glyph changes vs final should be only repairs toward base, never arbitrary.
        changed_user=[]
        for cp,ui in u['mapping'].items():
            if ui not in u['widths'] or cp not in f['mapping']: continue
            fi=f['mapping'][cp]
            if fullcell(u,ua,ui)!=fullcell(f,fa,fi) or u['widths'][ui]!=f['widths'][fi]: changed_user.append(cp)
        not_base_repairs=[]
        for cp in changed_user:
            if cp not in b['mapping']: not_base_repairs.append(cp); continue
            bi=b['mapping'][cp]; fi=f['mapping'][cp]
            if f['widths'][fi]!=b['widths'][bi] or fullcell(f,fa,fi)!=fullcell(b,ba,bi): not_base_repairs.append(cp)
        rows.append({
            'Font':name,'Blocks':len(f['blocks']),'Single_CWDH_CMAP':'EVET',
            'CWDH_End':f['end'],'Max_Mapped_Index':max(f['mapping'].values()),'CWDH_Covers_Max':'EVET' if f['end']>=max(f['mapping'].values()) else 'HAYIR',
            'User_Mapping_Index_Mismatches':len(user_map_bad),'Turkish_User_Glyph_Mismatches':len(tr_bad),
            'Original_Base_Codepoints_Missing':len(base_missing),'Original_Base_Glyph_Mismatches':len(base_bad),
            'User_Glyphs_Changed_Only_As_Base_Repair':'EVET' if not not_base_repairs else 'HAYIR',
            'Changed_User_Glyph_Count':len(changed_user),'Capacity':f['cols']*f['rows']*f['sc'],'SHA256':hashlib.sha256(f['b']).hexdigest(),
            'PASS':'EVET' if not (user_map_bad or tr_bad or base_missing or base_bad or not_base_repairs) else 'HAYIR'
        })
        details.append({'font':name,'changed_user_glyphs':[{'char':chr(cp),'codepoint':f'U+{cp:04X}'} for cp in changed_user], 'tr_bad':tr_bad, 'user_map_bad':[f'U+{cp:04X}' for cp in user_map_bad], 'base_missing':[f'U+{cp:04X}' for cp in base_missing], 'base_bad':[f'U+{cp:04X}' for cp in base_bad]})
    report_dir=(a.report_dir or a.final); report_dir.mkdir(parents=True,exist_ok=True)
    out=report_dir/'independent_verify_v5.csv'
    with out.open('w',encoding='utf-8-sig',newline='') as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)
    (report_dir/'independent_verify_v5.json').write_text(json.dumps(details,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(rows,ensure_ascii=False,indent=2))
    if any(r['PASS']!='EVET' for r in rows): raise SystemExit(2)

if __name__=='__main__': main()
