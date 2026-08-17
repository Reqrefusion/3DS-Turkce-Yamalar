#!/usr/bin/env python3
from pathlib import Path
import argparse,struct,subprocess,tempfile,sys,json,hashlib
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));import aat3ds_tr_v3 as t
# Turkish target glyphs in the patched font and the ORIGINAL Japanese donor glyphs
# recovered from the monotonic untouched CMAP neighbours.
MAP={
'ğ':(87,141,'あ','g'),'Ğ':(86,145,'う','G'),'İ':(88,150,'か','I'),'Ö':(90,152,'き','O'),
'ı':(89,158,'こ','i'),'ö':(91,160,'さ','o'),'Ü':(95,162,'し','U'),'Ç':(85,164,'す','C'),
'Ş':(110,166,'せ','S'),'ü':(109,186,'は','u'),'ç':(99,189,'ひ','c'),'ş':(111,192,'ふ','s')}

def cwdh(font):
    f=font.find(b'FINF');o=struct.unpack_from('<I',font,f+0x18)[0]-8;r={};seen=set()
    while o not in seen:
        seen.add(o);sig,size,s,e,n=struct.unpack_from('<4sI2HI',font,o);assert sig==b'CWDH';p=o+16
        for gi in range(s,e+1):r[gi]=p+(gi-s)*3
        if not n:break
        o=n-8
    return r

def patch_font(raw):
    f=bytearray(raw);info=t._ffnt_sheet_decode(raw);cw,ch,cols,w,h=info['cw'],info['ch'],info['cols'],info['w'],info['h'];px=cw+1;py=ch+1
    def cell(idx):
        x=(idx%cols)*px;row=idx//cols;y=h-(row+1)*py
        a=[[info['bmp'][(y+yy)*w+x+xx] for xx in range(cw)] for yy in range(ch)];a.reverse();return a
    def put(idx,a):
        b=[r[:] for r in a];b.reverse();x=(idx%cols)*px;row=idx//cols;y=h-(row+1)*py
        for yy in range(ch):
            for xx in range(cw):info['bmp'][(y+yy)*w+x+xx]=b[yy][xx]
    wd=cwdh(raw);rows=[]
    for tr,(target,source,jp,base) in MAP.items():
        tc=cell(target); sc=cell(source)
        before_src_sha=hashlib.sha256(bytes(v for row in sc for v in row)).hexdigest()
        target_sha=hashlib.sha256(bytes(v for row in tc for v in row)).hexdigest()
        put(source,tc)
        # Make redirect-before/after metric paths identical too.
        f[wd[source]:wd[source]+3]=f[wd[target]:wd[target]+3]
        rows.append({'tr':tr,'jp_donor':jp,'target':target,'source':source,'source_before_sha256':before_src_sha,'target_sha256':target_sha})
    sheet=t._ffnt_sheet_encode(info);f[info['data_off']:info['data_off']+len(sheet)]=sheet
    return bytes(f),rows

def main():
    ap=argparse.ArgumentParser();ap.add_argument('pack_dat');ap.add_argument('pack_inc');ap.add_argument('out_pack_dat');ap.add_argument('out_pack_inc');ap.add_argument('--fast-lz11')
    a=ap.parse_args();pack=Path(a.pack_dat).read_bytes();incb=Path(a.pack_inc).read_bytes();inc=t.parse_pack_inc(incb);repl={};reports={}
    for idx in (41,42):
        raw=t.lz11_decompress(pack,inc[idx]['offset'])[0];repl[idx],reports[str(idx)]=patch_font(raw)
    comp={}
    for idx,raw in repl.items():
        if a.fast_lz11:
            with tempfile.TemporaryDirectory() as td:
                x=Path(td)/'in';y=Path(td)/'out';x.write_bytes(raw);subprocess.run([a.fast_lz11,str(x),str(y)],check=True,stdout=subprocess.DEVNULL);comp[idx]=y.read_bytes()
        else: comp[idx]=t.lz11_compress(raw)
    out=bytearray();newinc=bytearray()
    for r in inc:
        idx=r['index'];off=len(out)
        if idx in comp: blob=comp[idx];dec=len(repl[idx]);cs=len(blob)
        else: blob=pack[r['offset']:r['offset']+r['compressed']];dec=r['decompressed'];cs=r['compressed']
        out.extend(blob)
        while len(out)%4:out.append(0)
        newinc.extend(struct.pack('<QIII',off,dec,cs,r['ident']))
    Path(a.out_pack_dat).write_bytes(out);Path(a.out_pack_inc).write_bytes(newinc)
    print(json.dumps({'changed_entries':[41,42],'donor_sync':reports,'pack_size':len(out)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
