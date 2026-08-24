#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib

def sha(p):
    h=hashlib.sha256();
    with open(p,'rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
    return h.hexdigest()

def tree(root):
    r=Path(root);return {p.relative_to(r).as_posix():(p.stat().st_size,sha(p)) for p in r.rglob('*') if p.is_file()}

def main():
    ap=argparse.ArgumentParser(description='İki RomFS ağacını isim/boyut/SHA-256 ile karşılaştırır')
    ap.add_argument('english');ap.add_argument('patch');a=ap.parse_args()
    A=tree(a.english);B=tree(a.patch)
    onlyA=sorted(set(A)-set(B));onlyB=sorted(set(B)-set(A));both=set(A)&set(B)
    changed=sorted(x for x in both if A[x]!=B[x]);same=sorted(x for x in both if A[x]==B[x])
    print('English files:',len(A),'Patch files:',len(B))
    print('Sadece English:',len(onlyA),'Sadece Patch:',len(onlyB),'Değişen:',len(changed),'Aynı:',len(same))
    print('\n--- PATCHTE EKSTRA ---');print('\n'.join(onlyB) or '-')
    print('\n--- ORTAK AMA DEĞİŞMİŞ ---')
    for x in changed: print(f'{x}\n  EN {A[x][0]:8} {A[x][1]}\n  TR {B[x][0]:8} {B[x][1]}')
if __name__=='__main__':main()
