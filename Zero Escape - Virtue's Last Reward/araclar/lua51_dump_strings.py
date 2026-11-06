#!/usr/bin/env python3
from pathlib import Path
import argparse
from lua51 import load,walk

def main():
    ap=argparse.ArgumentParser(description='Lua 5.1 bytecode içindeki string constantlarını döker')
    ap.add_argument('file');ap.add_argument('-o','--output');a=ap.parse_args();r,p=load(a.file)
    rows=[];n=0
    for pi,pr in enumerate(walk(p)):
        for ci,(t,v) in enumerate(pr['constants']):
            if t==4 and v is not None:
                s=v.decode('utf-8','replace');rows.append(f'P{pi:03} C{ci:04} {s}');n+=1
    text='\n'.join(rows)+'\n';print(f'{Path(a.file).name}: {n} string')
    if a.output:Path(a.output).write_text(text,encoding='utf-8')
    else:print(text,end='')
if __name__=='__main__':main()
