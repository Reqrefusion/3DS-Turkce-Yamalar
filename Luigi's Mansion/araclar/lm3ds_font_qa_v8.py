#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,zipfile
from pathlib import Path
from PIL import ImageChops
from lm3ds_font_fix_v8 import decode_gzf,cmap,glyph_tile

def find(z,suffix):
    hits=[n for n in z.namelist() if n.replace('\\','/').endswith(suffix)]
    if not hits: raise FileNotFoundError(suffix)
    return hits[0]

def sha(b): return hashlib.sha256(b).hexdigest()

def diff_font(orig:bytes,new:bytes,expected_changed:set[str]):
    om,oe,oa=decode_gzf(orig); nm,ne,na=decode_gzf(new)
    O=cmap(oe); N=cmap(ne)
    common=set(O)&set(N)
    metric_changed=[]; bitmap_changed=[]
    for ch in sorted(common,key=ord):
        if O[ch][1:4] != N[ch][1:4]: metric_changed.append(ch)
        if ImageChops.difference(glyph_tile(oa,om,O[ch]),glyph_tile(na,nm,N[ch])).getbbox(): bitmap_changed.append(ch)
    return {
      'geometry_orig':(om['original_w'],om['original_h'],len(oe),om['original_image_off'],len(orig)),
      'geometry_new':(nm['original_w'],nm['original_h'],len(ne),nm['original_image_off'],len(new)),
      'metric_changed':metric_changed,'bitmap_changed':bitmap_changed,
      'unexpected_metric':sorted(set(metric_changed)-expected_changed,key=ord),
      'unexpected_bitmap':sorted(set(bitmap_changed)-expected_changed,key=ord),
      'common_count':len(common)
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--original',required=True);ap.add_argument('--location',required=True);ap.add_argument('--ending',required=True);ap.add_argument('--report',required=True);ap.add_argument('--csv',required=True)
    a=ap.parse_args()
    with zipfile.ZipFile(a.original) as z:
        ol=z.read(find(z,'romfs/Region_EU/location.gzf')); oe=z.read(find(z,'romfs/Region_EU/ending.gzf'))
    nl=Path(a.location).read_bytes(); ne=Path(a.ending).read_bytes()
    L=diff_font(ol,nl,set('YÇÖâöğİıŞş'))
    E=diff_font(oe,ne,set('ĞğİŞş'))
    # Note: location repurposes ten non-Turkish donor codepoints; those no longer appear in common set.
    lines=[]
    lines += ['# LM3DS Turkish Font QA v8','',
              'v8 uses only original game glyph pixels; no system font is used.','',
              '## Geometry',
              f"- location original/new: {L['geometry_orig']} -> {L['geometry_new']}",
              f"- ending original/new: {E['geometry_orig']} -> {E['geometry_new']}",
              '', '## Common glyph preservation',
              f"- location common glyphs compared: {L['common_count']}",
              f"- location unexpected metric changes: {L['unexpected_metric']}",
              f"- location unexpected bitmap changes: {L['unexpected_bitmap']}",
              f"- ending common glyphs compared: {E['common_count']}",
              f"- ending unexpected metric changes: {E['unexpected_metric']}",
              f"- ending unexpected bitmap changes: {E['unexpected_bitmap']}",
              '', '## Expected Turkish glyph changes',
              '- location: Y Ç Ö â ö ğ İ ı Ş ş',
              '- ending: Ğ ğ İ Ş ş',
              '', '## SHA-256',
              f'- location.gzf: {sha(nl)}',f'- ending.gzf: {sha(ne)}','']
    ok=(L['geometry_orig']==L['geometry_new'] and E['geometry_orig']==E['geometry_new'] and not L['unexpected_metric'] and not L['unexpected_bitmap'] and not E['unexpected_metric'] and not E['unexpected_bitmap'])
    lines.append('## RESULT')
    lines.append('PASS' if ok else 'FAIL')
    Path(a.report).write_text('\n'.join(lines),encoding='utf-8')
    with open(a.csv,'w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['Font','Glyph','Source method','Advance','Bearing','BBox'])
        for name,path,chars,sources in [
          ('location',a.location,'YÇÖâöğİıŞş',{
            'Y':'location V + T','Ç':'location C + ending Ç cedilla','Ö':'location O + location ü diaeresis','â':'location a + location á/à accents','ö':'location o + location ü diaeresis','ğ':'location g + main ğ breve','İ':'location T stem/serif + location i dot','ı':'location i minus dot','Ş':'location S + ending Ç cedilla','ş':'location s + ending ç cedilla'}),
          ('ending',a.ending,'ĞğİŞş',{'Ğ':'ending G + main ğ breve','ğ':'ending g + main ğ breve','İ':'ending I + ending i dot','Ş':'ending S + ending Ç cedilla','ş':'ending s + ending ç cedilla'})]:
            data=Path(path).read_bytes();m,e,at=decode_gzf(data);cm=cmap(e)
            for ch in chars:
                ent=cm[ch]; bbox=glyph_tile(at,m,ent).point(lambda p:255 if p>=48 else 0).getbbox()
                w.writerow([name,ch,sources[ch],ent[1],ent[3],bbox])
    if not ok: raise SystemExit('Font QA failed')
    print('FONT QA: PASS')

if __name__=='__main__':main()
