#!/usr/bin/env python3
import argparse,hashlib
from lua51 import load,walk

def sig(path):
    _,p=load(path); ps=list(walk(p));
    code=[b''.join(x['code']) for x in ps]
    shape=[(len(x['code']),len(x['constants']),len(x['protos']),x['nups'],x['numparams'],x['is_vararg'],x['maxstack']) for x in ps]
    h=hashlib.sha256(b''.join(code)).hexdigest();return ps,shape,h

def main():
    ap=argparse.ArgumentParser(description='İki Lua 5.1 chunkının instruction/işlev yapısını stringlerden bağımsız karşılaştırır')
    ap.add_argument('a');ap.add_argument('b');x=ap.parse_args();pa,sa,ha=sig(x.a);pb,sb,hb=sig(x.b)
    print('A proto:',len(pa),'code sha256:',ha);print('B proto:',len(pb),'code sha256:',hb)
    print('Instruction bytes aynı:',ha==hb);print('Proto shape aynı:',sa==sb)
    if sa!=sb:
        for i,(u,v) in enumerate(zip(sa,sb)):
            if u!=v:print('İlk shape farkı proto',i,u,v);break
if __name__=='__main__':main()
