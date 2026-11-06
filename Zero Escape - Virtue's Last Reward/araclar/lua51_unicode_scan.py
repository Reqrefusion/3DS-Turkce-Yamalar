#!/usr/bin/env python3
from pathlib import Path
import argparse,collections
from lua51 import load,walk

def files(root):
    p=Path(root)
    return [p] if p.is_file() else sorted(p.rglob('*.lua'))

def main():
    ap=argparse.ArgumentParser(description='Lua 5.1 bytecode stringlerinde ASCII dışı Unicode karakter frekansı')
    ap.add_argument('path');a=ap.parse_args();cnt=collections.Counter();bad=[];n=0
    for p in files(a.path):
        try:
            _,pr=load(p)
            for q in walk(pr):
                for t,v in q['constants']:
                    if t==4 and v:
                        try:s=v.decode('utf-8')
                        except UnicodeDecodeError:bad.append(str(p));continue
                        cnt.update(ch for ch in s if ord(ch)>127)
            n+=1
        except Exception as e: bad.append(f'{p}: {e}')
    print('Okunan Lua:',n)
    for ch,c in cnt.most_common():print(f'U+{ord(ch):04X} {repr(ch):6} {c}')
    if bad:
        print('\nHatalar:');print('\n'.join(bad[:100]))
if __name__=='__main__':main()
