#!/usr/bin/env python3
from pathlib import Path
import argparse
from lua51 import load,walk

def main():
    ap=argparse.ArgumentParser(description='Lua bytecode string constantlarında metin ara')
    ap.add_argument('root');ap.add_argument('queries',nargs='+');a=ap.parse_args();root=Path(a.root)
    fs=[root] if root.is_file() else sorted(root.rglob('*.lua'))
    for p in fs:
        try:_,pr=load(p)
        except:continue
        for q in walk(pr):
            for t,v in q['constants']:
                if t==4 and v:
                    s=v.decode('utf-8','replace')
                    if any(x.casefold() in s.casefold() for x in a.queries):print(f'{p}: {s}')
if __name__=='__main__':main()
