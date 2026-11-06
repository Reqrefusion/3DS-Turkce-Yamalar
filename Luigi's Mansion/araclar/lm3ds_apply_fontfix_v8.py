#!/usr/bin/env python3
import argparse, zipfile
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(description='Replace only location.gzf and ending.gzf inside an LM3DS LayeredFS patch zip.')
    ap.add_argument('--patch',required=True)
    ap.add_argument('--location',required=True)
    ap.add_argument('--ending',required=True)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    loc=Path(a.location).read_bytes(); end=Path(a.ending).read_bytes()
    replaced={'location':False,'ending':False}
    with zipfile.ZipFile(a.patch) as zin, zipfile.ZipFile(a.out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as zout:
        for info in zin.infolist():
            name=info.filename.replace('\\','/')
            data=zin.read(info.filename)
            if name.endswith('/romfs/Region_EU/location.gzf'):
                data=loc; replaced['location']=True
            elif name.endswith('/romfs/Region_EU/ending.gzf'):
                data=end; replaced['ending']=True
            zout.writestr(info,data)
        if not replaced['location'] or not replaced['ending']:
            raise SystemExit(f'Missing font path(s) in patch: {replaced}')
    with zipfile.ZipFile(a.out) as z: bad=z.testzip()
    if bad: raise SystemExit(f'ZIP CRC failure: {bad}')
    print('OK:',a.out)
if __name__=='__main__': main()
